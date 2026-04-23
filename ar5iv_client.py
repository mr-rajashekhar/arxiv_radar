"""
ar5iv HTML fetcher — pulls the Introduction and Conclusion/Discussion sections
from https://ar5iv.labs.arxiv.org/html/<id>, giving the summarizer richer context
than the abstract alone.

Graceful: any failure (network, missing ar5iv page, parse error) returns "" and
the summarizer falls back to abstract-only.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

log = logging.getLogger(__name__)

AR5IV_URL = "https://ar5iv.labs.arxiv.org/html/{arxiv_id}"

# Section headings (lowercased) to extract, in order of preference.
_WANTED_INTRO = ("introduction", "motivation", "overview")
_WANTED_CONCLUSION = ("conclusion", "conclusions", "discussion", "summary",
                      "concluding remarks", "discussion and conclusion")


def _clean(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) > max_chars:
        text = text[:max_chars].rsplit(" ", 1)[0] + " …"
    return text


def _extract_section(soup, wanted_titles: tuple[str, ...], max_chars: int) -> str:
    """Find an <h2>/<h3> whose visible text matches any of wanted_titles,
    then concatenate all text until the next heading of equal/higher level."""
    for header in soup.find_all(["h1", "h2", "h3"]):
        title = re.sub(r"^\d+(\.\d+)*\s*", "", header.get_text(" ", strip=True)).strip().lower()
        if not title:
            continue
        if any(title == w or title.startswith(w + " ") or title == w + "." for w in wanted_titles):
            parts: list[str] = []
            stop_tag = header.name  # stop at same-level heading
            for sib in header.find_all_next():
                if sib.name in ("h1", "h2") or (sib.name == "h3" and stop_tag in ("h2", "h3")):
                    if sib is not header:
                        break
                if sib.name in ("p", "li"):
                    txt = sib.get_text(" ", strip=True)
                    if txt:
                        parts.append(txt)
                        if sum(len(p) for p in parts) > max_chars * 2:
                            break
            return _clean(" ".join(parts), max_chars)
    return ""


def fetch_ar5iv_sections(
    arxiv_id: str,
    intro_chars: int = 1800,
    conclusion_chars: int = 1200,
    timeout: float = 8.0,
) -> dict:
    """Return {'intro': str, 'conclusion': str}. Empty strings on any failure."""
    out = {"intro": "", "conclusion": ""}
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError:
        log.warning("ar5iv fetcher needs requests + beautifulsoup4; skipping.")
        return out

    url = AR5IV_URL.format(arxiv_id=arxiv_id)
    try:
        r = requests.get(url, timeout=timeout, headers={
            "User-Agent": "arxiv_radar/1.0 (personal research digest)"
        })
        if r.status_code != 200:
            log.info("ar5iv %s: HTTP %d", arxiv_id, r.status_code)
            return out
        # ar5iv pages often start with a disclaimer about unconverted papers.
        if "This HTML conversion" in r.text and "failed" in r.text[:2000].lower():
            log.info("ar5iv %s: conversion failed upstream", arxiv_id)
            return out

        from bs4 import BeautifulSoup  # re-import for type checker
        soup = BeautifulSoup(r.text, "html.parser")
        # Strip bibliographies + equations to keep extracted text clean.
        for bad in soup.select(".ltx_bibliography, .ltx_equation, .ltx_Math, .ltx_tabular, figure, nav"):
            bad.decompose()

        out["intro"] = _extract_section(soup, _WANTED_INTRO, intro_chars)
        out["conclusion"] = _extract_section(soup, _WANTED_CONCLUSION, conclusion_chars)
    except Exception as e:
        log.info("ar5iv %s fetch failed: %s", arxiv_id, e)
    return out
