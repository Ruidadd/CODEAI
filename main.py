#!/usr/bin/env python3
"""Weekly AI Papers Digest - Main orchestrator.

Fetches recent AI/ML papers from arXiv, ranks them by importance using Kimi LLM,
generates structured bilingual summaries, and sends a weekly email digest.
"""

import logging
import sys

from emailer import send_digest
from fetcher import fetch_recent_papers
from ranker import rank_papers
from summarizer import summarize_papers

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("weekly-digest")


def main() -> None:
    logger.info("=== Weekly AI Papers Digest ===")

    # Step 1: Fetch recent papers from arXiv
    logger.info("Step 1/4: Fetching papers from arXiv...")
    papers = fetch_recent_papers()
    if not papers:
        logger.warning("No papers found for the past week. Exiting.")
        sys.exit(0)

    # Step 2: Rank papers by importance
    logger.info("Step 2/4: Ranking papers by importance...")
    top_papers = rank_papers(papers)
    if not top_papers:
        logger.error("Ranking returned no papers. Exiting.")
        sys.exit(1)

    # Step 3: Generate structured summaries
    logger.info("Step 3/4: Generating structured summaries...")
    summarized_papers = summarize_papers(top_papers)

    # Step 4: Send email digest
    logger.info("Step 4/4: Sending email digest...")
    try:
        send_digest(summarized_papers)
    except Exception:
        logger.exception("Failed to send email. Dumping digest to stdout as fallback.")
        _dump_to_stdout(summarized_papers)
        sys.exit(1)

    logger.info("=== Done! ===")


def _dump_to_stdout(papers: list[dict]) -> None:
    """Print digest to stdout as fallback when email fails."""
    print("\n" + "=" * 60)
    print("WEEKLY AI PAPERS DIGEST (email failed, stdout fallback)")
    print("=" * 60)
    for i, paper in enumerate(papers, 1):
        summary = paper.get("summary", {})
        print(f"\n#{i} [{paper.get('importance_score', '?')}/10] {paper['title']}")
        print(f"   PDF: {paper['pdf_url']}")
        print(f"   问题: {summary.get('problem', 'N/A')}")
        print(f"   解决方案: {summary.get('solution', 'N/A')}")
        print(f"   创新之处: {summary.get('innovation', 'N/A')}")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
