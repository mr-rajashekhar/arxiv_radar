"""
Per-paper summarizer — produces a structured 7-field summary tailored to the researcher.

Fields: problem, contribution, results, setup, baselines, why_for_you, caveat.
"""

from __future__ import annotations

import json
import logging
import re

from llm_client import TrapiClient
from arxiv_client import Paper

log = logging.getLogger(__name__)


SYSTEM = """You produce terse, high-signal paper summaries for a specific researcher.

Return a JSON object with EXACTLY these 7 keys, each a short string (no markdown, no bullets):
- "problem":     1-2 sentences stating the gap or pain the paper addresses.
- "contribution":1-2 sentences on the key technical novelty (mechanism / design / algorithm).
- "results":     1 sentence with the headline quantitative win (e.g., "2.3x throughput vs vLLM").
- "setup":       models, hardware, workload used for evaluation (one short phrase).
- "baselines":   systems/methods compared against (comma-separated; "N/A" if absent).
- "why_for_you": 1 sentence tying the paper to the researcher's profile/interests.
- "caveat":      1 sentence on limitations, scope gaps, or what's unclear.

Be direct. No fluff, no restating the title. If a field is genuinely unknown from the abstract, write "unclear from abstract".
Output ONLY the JSON object, no prose before or after."""


USER_TEMPLATE = """RESEARCHER PROFILE
==================
{profile}

PAPER
=====
Title: {title}
Authors: {authors}
Arxiv: {url}

Abstract:
{abstract}
{extra}
"""


_EXTRA_TEMPLATE = """
Introduction (excerpt from ar5iv HTML):
{intro}

Conclusion (excerpt from ar5iv HTML):
{conclusion}
"""


FALLBACK = {
    "problem": "(summary failed)",
    "contribution": "see abstract",
    "results": "unclear",
    "setup": "unclear",
    "baselines": "unclear",
    "why_for_you": "manual review needed",
    "caveat": "LLM summary unavailable",
}


def _extract_json(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        raise ValueError(f"no JSON object in response: {text[:200]}")
    return json.loads(m.group(0))


def summarize(paper: Paper, profile: str, client: TrapiClient,
              use_ar5iv: bool = True) -> dict:
    extra = ""
    if use_ar5iv:
        try:
            from ar5iv_client import fetch_ar5iv_sections
            sec = fetch_ar5iv_sections(paper.arxiv_id)
            if sec["intro"] or sec["conclusion"]:
                extra = _EXTRA_TEMPLATE.format(
                    intro=sec["intro"] or "(not available)",
                    conclusion=sec["conclusion"] or "(not available)",
                )
                log.info("ar5iv enriched %s (intro=%d, concl=%d chars)",
                         paper.arxiv_id, len(sec["intro"]), len(sec["conclusion"]))
        except Exception as e:
            log.info("ar5iv enrichment skipped for %s: %s", paper.arxiv_id, e)

    user = USER_TEMPLATE.format(
        profile=profile,
        title=paper.title,
        authors=", ".join(paper.authors[:6]) + (" et al." if len(paper.authors) > 6 else ""),
        url=paper.url,
        abstract=paper.abstract[:3500],
        extra=extra,
    )
    try:
        raw = client.chat(
            [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": user},
            ],
        )
        data = _extract_json(raw)
        out = {k: str(data.get(k, "unclear")).strip() for k in FALLBACK.keys()}
        return out
    except Exception as e:
        log.error("Summarize failed for %s: %s", paper.arxiv_id, e)
        fb = dict(FALLBACK)
        fb["problem"] = f"(summary failed: {e})"
        return fb
