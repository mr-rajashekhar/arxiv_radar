"""
LLM relevance scorer — batched, JSON-structured output.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Iterable

from llm_client import TrapiClient
from arxiv_client import Paper

log = logging.getLogger(__name__)


SYSTEM_PROMPT = """You are a research-paper relevance scorer for a specific researcher.
You will be given (1) the researcher's interest profile and (2) a batch of arxiv papers.
For EACH paper, output a JSON object with:
  - "id":     the arxiv_id you were given (string, unchanged)
  - "score":  integer 0-10 (10 = extremely relevant, 0 = irrelevant)
  - "reason": one short sentence justifying the score, grounded in the profile

Rules:
- Be strict. Most papers should score 0-4. Reserve 7+ for papers clearly aligned
  with the researcher's INTERESTED_IN topics.
- Consider systems angle, sustainability, carbon/energy, DC scheduling, LLM inference
  infrastructure, distributed systems — not pure ML theory unless profile says so.
- Return a single JSON array, no markdown, no commentary."""


TRIAGE_SYSTEM_PROMPT = """You are a fast first-pass triage scorer. You'll get the researcher's
profile and a batch of arxiv paper TITLES ONLY. For each, output a JSON object:
  - "id":    the arxiv_id (unchanged)
  - "score": integer 0-10 (coarse; based on title alone)

Rules:
- Be lenient: if the title even *might* touch the researcher's interests, score >= 5.
- Be decisive: clearly off-topic titles score 0-2.
- NO "reason" field. Output only id + score to save tokens.
- Return a single JSON array, no markdown, no commentary."""


USER_TEMPLATE = """RESEARCHER PROFILE
==================
{profile}

PAPERS TO SCORE
===============
{papers_json}

Return a JSON array of {n} objects, one per paper, in the same order."""


TRIAGE_USER_TEMPLATE = """RESEARCHER PROFILE
==================
{profile}

TITLES TO TRIAGE
================
{papers_json}

Return a JSON array of {n} objects: [{{"id":..., "score":0-10}}, ...]"""


def _extract_json_array(text: str) -> list[dict]:
    # Strip markdown fences if present
    t = text.strip()
    t = re.sub(r"^```(?:json)?", "", t).strip()
    t = re.sub(r"```$", "", t).strip()
    # Find first [ and last ]
    lo = t.find("[")
    hi = t.rfind("]")
    if lo == -1 or hi == -1:
        raise ValueError(f"No JSON array in model output: {text[:200]}")
    return json.loads(t[lo : hi + 1])


def triage_papers(
    papers: list[Paper],
    profile: str,
    client: TrapiClient,
    batch_size: int = 40,
    threshold: int = 4,
) -> list[Paper]:
    """Cheap first pass: titles only, minimal output. Return papers to keep."""
    keep: list[Paper] = []
    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        papers_json = json.dumps(
            [{"id": p.arxiv_id, "title": p.title} for p in batch],
            ensure_ascii=False,
        )
        user = TRIAGE_USER_TEMPLATE.format(
            profile=profile, papers_json=papers_json, n=len(batch)
        )
        try:
            raw = client.chat(
                [
                    {"role": "system", "content": TRIAGE_SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
            )
            arr = _extract_json_array(raw)
            scored = {str(item.get("id", "")).strip(): int(item.get("score", 0)) for item in arr}
        except Exception as e:
            log.error("Triage batch %d failed: %s; passing all through", i // batch_size, e)
            scored = {p.arxiv_id: 10 for p in batch}

        for p in batch:
            if scored.get(p.arxiv_id, 0) >= threshold:
                keep.append(p)
        log.info(
            "Triage batch %d-%d: kept %d/%d",
            i, i + len(batch),
            sum(1 for p in batch if scored.get(p.arxiv_id, 0) >= threshold),
            len(batch),
        )
    log.info("Triage total: kept %d / %d (threshold=%d)", len(keep), len(papers), threshold)
    return keep


def score_papers(
    papers: list[Paper],
    profile: str,
    client: TrapiClient,
    batch_size: int = 15,
) -> dict[str, tuple[int, str]]:
    """Return mapping arxiv_id -> (score, reason)."""
    results: dict[str, tuple[int, str]] = {}
    for i in range(0, len(papers), batch_size):
        batch = papers[i : i + batch_size]
        papers_json = json.dumps(
            [
                {"id": p.arxiv_id, "title": p.title, "abstract": p.abstract[:1200]}
                for p in batch
            ],
            ensure_ascii=False,
        )
        user = USER_TEMPLATE.format(profile=profile, papers_json=papers_json, n=len(batch))
        try:
            raw = client.chat(
                [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user},
                ],
            )
            arr = _extract_json_array(raw)
            for item in arr:
                pid = str(item.get("id", "")).strip()
                score = int(item.get("score", 0))
                reason = str(item.get("reason", "")).strip()
                if pid:
                    results[pid] = (score, reason)
        except Exception as e:
            log.error("Scoring batch %d failed: %s", i // batch_size, e)
            # Fall back: score 0 for missing so pipeline continues
            for p in batch:
                results.setdefault(p.arxiv_id, (0, f"scoring_error: {e}"))
        log.info("Scored batch %d-%d", i, i + len(batch))
    return results


def select_top(
    papers: list[Paper],
    scores: dict[str, tuple[int, str]],
    threshold: int,
    cap: int,
) -> list[tuple[Paper, int, str]]:
    scored = [
        (p, *scores.get(p.arxiv_id, (0, "no_score")))
        for p in papers
    ]
    scored = [t for t in scored if t[1] >= threshold]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:cap]
