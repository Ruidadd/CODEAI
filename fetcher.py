import logging
from datetime import datetime, timedelta, timezone

import arxiv

from config import ARXIV_CATEGORIES, LOOKBACK_DAYS, MAX_FETCH_RESULTS

logger = logging.getLogger(__name__)


def fetch_recent_papers() -> list[dict]:
    """Fetch recent papers from arXiv in configured categories."""
    category_query = " OR ".join(f"cat:{cat}" for cat in ARXIV_CATEGORIES)
    logger.info(f"Querying arXiv: {category_query}")

    client = arxiv.Client(page_size=100, delay_seconds=3.0, num_retries=3)

    search = arxiv.Search(
        query=category_query,
        max_results=MAX_FETCH_RESULTS,
        sort_by=arxiv.SortCriterion.SubmittedDate,
        sort_order=arxiv.SortOrder.Descending,
    )

    cutoff_date = datetime.now(tz=timezone.utc) - timedelta(days=LOOKBACK_DAYS)

    papers = []
    for result in client.results(search):
        published = result.published.replace(tzinfo=timezone.utc)
        if published < cutoff_date:
            break

        papers.append(
            {
                "arxiv_id": result.entry_id,
                "title": result.title.replace("\n", " ").strip(),
                "abstract": result.summary.replace("\n", " ").strip(),
                "authors": [a.name for a in result.authors],
                "categories": result.categories,
                "published": result.published.isoformat(),
                "pdf_url": result.pdf_url,
                "primary_category": result.primary_category,
            }
        )

    logger.info(f"Fetched {len(papers)} papers from the past {LOOKBACK_DAYS} days")
    return papers
