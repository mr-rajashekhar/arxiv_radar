"""
Arxiv Research Radar — main orchestrator.

Daily flow:
  fetch -> dedup -> score -> filter -> summarize -> write digest -> email

Idempotent: if today's run already succeeded, exits immediately. Safe to invoke
every few minutes (e.g., from Task Scheduler retry loop) — see register_task.ps1.
"""

from __future__ import annotations

import json
import logging
import socket
import sys
from datetime import datetime
from pathlib import Path

import yaml

from llm_client import TrapiClient
from arxiv_client import fetch_recent
from memory import Memory
from scorer import score_papers, select_top, triage_papers
from summarizer import summarize
from deliver import write_digest, send_email


ROOT = Path(__file__).resolve().parent
STATE_FILE = ROOT / "state" / "last_run.json"


def already_ran_today() -> bool:
    """True iff today's run finished successfully (idempotency guard)."""
    if not STATE_FILE.exists():
        return False
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        return (
            data.get("date") == datetime.now().strftime("%Y-%m-%d")
            and data.get("status") == "ok"
        )
    except Exception:
        return False


def mark_success(n_selected: int) -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({
            "date": datetime.now().strftime("%Y-%m-%d"),
            "status": "ok",
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "n_selected": n_selected,
        }, indent=2),
        encoding="utf-8",
    )


def has_internet(host: str = "export.arxiv.org", port: int = 443, timeout: float = 3.0) -> bool:
    """Cheap connectivity probe (~ms). Returns False if DNS or TCP fails."""
    try:
        socket.create_connection((host, port), timeout=timeout).close()
        return True
    except OSError:
        return False


def disable_retry_task(task_name: str = "ArxivRadar") -> None:
    """Disable the scheduled task so the 5-min retry loop stops for today.
    A companion task 'ArxivRadar-Reset' re-enables it tomorrow at 6:59 AM.
    No-op (logs a warning) if schtasks.exe is unavailable or the task doesn't exist.
    """
    import subprocess
    try:
        r = subprocess.run(
            ["schtasks", "/Change", "/TN", task_name, "/DISABLE"],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            logging.getLogger("radar").info("Disabled scheduled task '%s' for today.", task_name)
        else:
            logging.getLogger("radar").warning(
                "Could not disable task '%s' (rc=%d): %s", task_name, r.returncode, r.stderr.strip()
            )
    except Exception as e:
        logging.getLogger("radar").warning("disable_retry_task failed: %s", e)


def setup_logging(logs_dir: Path) -> Path:
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_path, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return log_path


def load_config() -> dict:
    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_profile(path: Path) -> str:
    if not path.exists():
        raise SystemExit(
            f"{path} not found. Run `python bootstrap_profile.py` first, "
            "then review and edit the generated profile."
        )
    return path.read_text(encoding="utf-8")


def write_fallback_digest(digest_path: Path, papers, reason: str) -> None:
    """If LLM fails entirely, still drop a titles-only digest."""
    lines = [f"# Arxiv Radar — {datetime.now().strftime('%Y-%m-%d')} (FALLBACK)\n\n",
             f"_LLM pipeline failed: {reason}. Raw titles below._\n\n"]
    for p in papers[:50]:
        lines.append(f"- [{p.title}]({p.url}) — `{p.primary_category}`\n")
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text("".join(lines), encoding="utf-8")


def main() -> int:
    # Skip weekends — arxiv.org doesn't post new submissions on Sat/Sun
    # (paper announcements are batched Mon-Fri evenings ET).
    weekday = datetime.now().weekday()  # Mon=0 .. Sun=6
    if weekday >= 5:
        print(f"arxiv_radar: weekend ({datetime.now().strftime('%A')}); skipping run.")
        disable_retry_task()  # quiet the 5-min loop today
        return 0

    # Fast-path guards — keep retries cheap.
    if already_ran_today():
        print("arxiv_radar: today's digest already delivered; exiting.")
        # Safety net: ensure the retry loop is disabled (idempotent).
        disable_retry_task()
        return 0
    if not has_internet():
        print("arxiv_radar: no internet; will retry on next trigger.")
        return 0

    cfg = load_config()
    log_path = setup_logging(ROOT / cfg["paths"]["logs_dir"])
    log = logging.getLogger("radar")
    log.info("=== Arxiv Radar run started; log=%s ===", log_path)

    profile = load_profile(ROOT / cfg["paths"]["profile_file"])
    mem = Memory(ROOT / cfg["paths"]["db_file"])

    # 1. Fetch — Mon/Tue need a longer lookback to capture Friday's papers.
    # arxiv announces Mon-Fri at ~20:00 UTC; submissions can be 60-80h old by
    # the time we run on Tuesday morning IST. Dedup will drop overlap with
    # earlier runs.
    base_lookback = cfg["arxiv"]["lookback_hours"]
    weekday = datetime.now().weekday()  # Mon=0..Sun=6
    if weekday in (0, 1):  # Monday, Tuesday
        lookback = max(base_lookback, 96)
        log.info("%s detected: extending lookback to %dh (base=%dh)",
                 datetime.now().strftime("%A"), lookback, base_lookback)
    else:
        lookback = base_lookback

    papers = fetch_recent(
        cfg["arxiv"]["categories"],
        lookback_hours=lookback,
        max_results=cfg["arxiv"]["max_results"],
    )
    if not papers:
        log.warning("No papers fetched; exiting.")
        # Mark success so the 5-min retry loop stops; nothing will change today.
        mark_success(0)
        disable_retry_task()
        return 0

    # 2. Dedup
    new_ids = mem.filter_new([p.arxiv_id for p in papers])
    new_papers = [p for p in papers if p.arxiv_id in new_ids]
    log.info("%d new papers after dedup (of %d fetched)", len(new_papers), len(papers))
    if not new_papers:
        log.info("Nothing new today; exiting without sending email.")
        mark_success(0)
        disable_retry_task()
        return 0

    digest_path = ROOT / cfg["paths"]["digests_dir"] / f"{datetime.now().strftime('%Y-%m-%d')}.md"
    selected_rows: list = []
    skipped: list = []

    # 3. Score + 4. Summarize (with graceful fallback)
    try:
        client = TrapiClient(
            api_path=cfg["llm"]["api_path"],
            model=cfg["llm"]["model"],
            api_version=cfg["llm"]["api_version"],
            scope=cfg["llm"]["scope"],
        )

        # Stage 1 (optional): cheap title-only triage
        triage_cfg = cfg["scoring"].get("triage", {}) or {}
        if triage_cfg.get("enabled", False):
            candidates = triage_papers(
                new_papers, profile, client,
                batch_size=triage_cfg.get("batch_size", 40),
                threshold=triage_cfg.get("threshold", 4),
            )
        else:
            candidates = new_papers

        if not candidates:
            log.info("Triage dropped everything; nothing to score.")
            scores = {}
            top = []
        else:
            scores = score_papers(
                candidates, profile, client,
                batch_size=cfg["scoring"]["batch_size"],
            )
            top = select_top(
                candidates, scores,
                threshold=cfg["scoring"]["threshold"],
                cap=cfg["scoring"]["max_summaries"],
            )
        log.info("Selected %d papers above threshold %d",
                 len(top), cfg["scoring"]["threshold"])

        selected_rows = []
        for paper, score, reason in top:
            log.info("Summarizing %s (score=%d)", paper.arxiv_id, score)
            summary_md = summarize(
                paper, profile, client,
                use_ar5iv=cfg["scoring"].get("use_ar5iv", True),
            )
            selected_rows.append((paper, score, reason, summary_md))

        # Everything not selected (but scored) -> skipped list
        chosen_ids = {p.arxiv_id for p, _, _, _ in selected_rows}
        skipped = [
            (p.title, scores.get(p.arxiv_id, (0, ""))[0])
            for p in new_papers
            if p.arxiv_id not in chosen_ids
        ]
        skipped.sort(key=lambda x: x[1], reverse=True)

        write_digest(digest_path, selected_rows, skipped)

        # Memory update: all new_papers marked seen; triaged-out get score 0
        chosen_ids = {p.arxiv_id for p, _, _, _ in selected_rows}
        for p in new_papers:
            s = scores.get(p.arxiv_id, 0)
            mem.mark(p.arxiv_id, s if isinstance(s, int) else s[0],
                     delivered=(p.arxiv_id in chosen_ids))

    except Exception as e:
        log.exception("LLM pipeline failed: %s", e)
        write_fallback_digest(digest_path, new_papers, str(e))
        for p in new_papers:
            mem.mark(p.arxiv_id, None, delivered=False)

    # 5. Email
    email_ok = False
    if cfg["email"].get("enabled", False):
        try:
            subject = f"{cfg['email']['subject_prefix']} {datetime.now().strftime('%Y-%m-%d')}"
            send_email(
                digest_path=digest_path,
                selected=selected_rows,
                skipped_titles=skipped,
                sender=cfg["email"]["sender"],
                recipient=cfg["email"]["recipient"],
                subject=subject,
                smtp_host=cfg["email"]["smtp_host"],
                smtp_port=cfg["email"]["smtp_port"],
            )
            email_ok = True
        except Exception as e:
            log.exception("Email send failed: %s", e)
            # Return non-zero so Task Scheduler retries trigger us again.
            log.info("=== Arxiv Radar run done (FAILED email) ===")
            return 2
    else:
        log.info("Email disabled in config; digest available at %s", digest_path)
        email_ok = True  # running in no-email mode is still a "success"

    if email_ok:
        mark_success(len(selected_rows))
        disable_retry_task()  # stops the 5-min repeat loop until tomorrow's reset task
    log.info("=== Arxiv Radar run done ===")
    return 0


if __name__ == "__main__":
    sys.exit(main())
