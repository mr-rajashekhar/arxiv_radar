"""
Arxiv fetcher — returns papers submitted in the last N hours across given categories.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone

import arxiv

log = logging.getLogger(__name__)


@dataclass
class Paper:
    arxiv_id: str
    title: str
    abstract: str
    authors: list[str]
    url: str
    pdf_url: str
    published: str  # ISO
    primary_category: str

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize_id(entry_id: str) -> str:
    # entry_id looks like http://arxiv.org/abs/2401.12345v2 -> 2401.12345
    tail = entry_id.rsplit("/", 1)[-1]
    return tail.split("v")[0]


def fetch_recent(
    categories: list[str],
    lookback_hours: int = 36,
    max_results: int = 300,
) -> list[Paper]:
    query = " OR ".join(f"cat:{c}" for c in categories)
    search = arxiv.Search(
        query=query,
        max_results=max_results,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)
    client = arxiv.Client(page_size=100, delay_seconds=3, num_retries=3)

    papers: list[Paper] = []
    for result in client.results(search):
        pub = result.published
        if pub.tzinfo is None:
            pub = pub.replace(tzinfo=timezone.utc)
        if pub < cutoff:
            # results are descending by date, so we can break
            break
        papers.append(
            Paper(
                arxiv_id=_normalize_id(result.entry_id),
                title=result.title.strip().replace("\n", " "),
                abstract=result.summary.strip().replace("\n", " "),
                authors=[a.name for a in result.authors],
                url=result.entry_id,
                pdf_url=result.pdf_url,
                published=pub.isoformat(),
                primary_category=result.primary_category,
            )
        )
    log.info("Fetched %d papers from arxiv (last %dh)", len(papers), lookback_hours)
    return papers


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ps = fetch_recent(["cs.DC", "cs.AR"], lookback_hours=48, max_results=50)
    for p in ps[:5]:
        print(p.arxiv_id, "-", p.title)
