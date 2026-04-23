"""
One-time: auto-seed profile.md from the user's own papers.

Reads a handful of known text/pdf files, concatenates excerpts, and asks the LLM
to produce a structured research-interest profile.

Usage:
    python bootstrap_profile.py            # writes ./profile.md
    python bootstrap_profile.py --force    # overwrite even if exists
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from llm_client import TrapiClient

log = logging.getLogger(__name__)

HOME = Path(r"C:\Users\t-tereddy")

# Sources: prefer already-extracted .txt files (cheap); fall back to .pdf via PyPDF2 if needed.
SOURCES = [
    HOME / "xwind_asplos_clean.txt",
    HOME / "heron_arxiv.txt",
    HOME / "pdf_extracted_text.txt",
    HOME / "xwind_v6.txt",
]

PDF_SOURCES = [
    HOME / "Greenferencing_asplos.pdf",
    HOME / "slasher_msft_preprint.pdf",
]


SYSTEM = """You analyze a researcher's own writing and produce a concise research-interest
profile to be used as a filter for daily arxiv paper recommendations.

Return a markdown document with EXACTLY these sections:

# Research Profile

## INTERESTED_IN
- bullet list of concrete topics, systems, techniques the researcher works on

## NOT_INTERESTED_IN
- bullet list of adjacent-but-irrelevant areas (pure theory, unrelated domains)

## KEY_TERMS
- bullet list of 10-20 keywords/phrases useful for arxiv search

Keep it tight: 10-20 bullets per section max. Base everything on the provided text;
do not invent."""


def _read_txt(p: Path, max_chars: int = 20000) -> str:
    try:
        return p.read_text(encoding="utf-8", errors="ignore")[:max_chars]
    except Exception as e:
        log.warning("skip %s: %s", p, e)
        return ""


def _read_pdf(p: Path, max_chars: int = 15000) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            log.warning("no pypdf/PyPDF2 installed; skipping %s", p)
            return ""
    try:
        reader = PdfReader(str(p))
        chunks = []
        for page in reader.pages[:15]:
            chunks.append(page.extract_text() or "")
        return "\n".join(chunks)[:max_chars]
    except Exception as e:
        log.warning("skip pdf %s: %s", p, e)
        return ""


def collect_corpus() -> str:
    parts: list[str] = []
    for p in SOURCES:
        if p.exists():
            t = _read_txt(p)
            if t:
                parts.append(f"=== {p.name} ===\n{t}\n")
    for p in PDF_SOURCES:
        if p.exists():
            t = _read_pdf(p)
            if t:
                parts.append(f"=== {p.name} ===\n{t}\n")
    return "\n".join(parts)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="overwrite existing profile.md")
    ap.add_argument("--output", default="profile.md")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    out = Path(args.output)
    if out.exists() and not args.force:
        log.info("%s already exists. Use --force to overwrite.", out)
        return

    corpus = collect_corpus()
    if not corpus.strip():
        raise SystemExit("No source papers found on disk; cannot bootstrap profile.")

    log.info("Calling LLM with %d chars of corpus...", len(corpus))
    client = TrapiClient()
    profile = client.chat(
        [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": corpus[:80000]},
        ],
    )
    out.write_text(profile.strip() + "\n", encoding="utf-8")
    log.info("Wrote %s (%d chars). REVIEW AND EDIT BEFORE FIRST RUN.", out, len(profile))


if __name__ == "__main__":
    main()
