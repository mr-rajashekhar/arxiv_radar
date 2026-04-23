"""
Standalone email test — sends an existing digest (or a dummy body) via Gmail SMTP.
Does NOT fetch arxiv, score, or summarize.

Usage:
    python test_email.py                       # sends today's digest
    python test_email.py --file digests\2026-04-21.md
    python test_email.py --dummy               # sends a one-line test email
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

import yaml

from deliver import send_email

ROOT = Path(__file__).resolve().parent


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", default=None, help="path to a markdown digest to send")
    ap.add_argument("--dummy", action="store_true", help="send a trivial test body instead")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    with open(ROOT / "config.yaml", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    if args.dummy:
        path = ROOT / "digests" / "_email_test.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"# Arxiv Radar — email plumbing test\n\n"
            f"Sent at {datetime.now().isoformat()} from {cfg['email']['sender']}.\n\n"
            f"If you see this, SMTP auth + delivery work.\n",
            encoding="utf-8",
        )
    elif args.file:
        path = Path(args.file)
    else:
        # default: today's digest
        today = datetime.now().strftime("%Y-%m-%d")
        path = ROOT / cfg["paths"]["digests_dir"] / f"{today}.md"

    if not path.exists():
        print(f"ERROR: {path} not found. Use --dummy or --file.", file=sys.stderr)
        return 1

    subject = f"{cfg['email']['subject_prefix']} [TEST] {path.name}"
    send_email(
        digest_path=path,
        selected=[],
        skipped_titles=[],
        sender=cfg["email"]["sender"],
        recipient=cfg["email"]["recipient"],
        subject=subject,
        smtp_host=cfg["email"]["smtp_host"],
        smtp_port=cfg["email"]["smtp_port"],
    )
    print(f"OK: sent {path} to {cfg['email']['recipient']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
