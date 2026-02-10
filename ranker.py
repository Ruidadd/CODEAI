import json
import logging
import re

from openai import OpenAI

from config import DIGEST_PAPER_COUNT, KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

logger = logging.getLogger(__name__)

RANKING_SYSTEM_PROMPT = """你是一位资深 AI 研究专家。你将收到一批最近的 arXiv 论文（标题 + 摘要片段）。
请为每篇论文的重要性和影响力打分（1-10分）。评分标准：

1. 新颖性：是否提出了真正的新思路，而非渐进式改进？
2. 潜在影响：是否可能改变研究或工程实践？
3. 广泛兴趣：是否对广泛的研究者/工程师有价值？
4. 技术深度：方法是否严谨？

请严格返回 JSON 数组，格式如下（不要添加其他文字）：
[{"id": 0, "score": 8}, {"id": 1, "score": 6}, ...]

其中 id 对应论文在输入列表中的序号（从0开始），score 为1-10的整数。"""


def _parse_scores(text: str) -> list[dict]:
    """Parse JSON scores from LLM response, with fallback extraction."""
    text = text.strip()
    # Try direct JSON parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # Try extracting from markdown code block
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    # Try extracting JSON array
    match = re.search(r"\[[\s\S]*\]", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    logger.warning(f"Failed to parse LLM ranking response: {text[:200]}...")
    return []


def _format_batch(papers: list[dict]) -> str:
    """Format a batch of papers for the ranking prompt."""
    lines = []
    for i, p in enumerate(papers):
        abstract_snippet = p["abstract"][:300]
        authors_str = ", ".join(p["authors"][:3])
        if len(p["authors"]) > 3:
            authors_str += " et al."
        lines.append(
            f"[{i}] {p['title']}\n"
            f"    Authors: {authors_str}\n"
            f"    Categories: {', '.join(p['categories'])}\n"
            f"    Abstract: {abstract_snippet}..."
        )
    return "\n\n".join(lines)


def rank_papers(papers: list[dict]) -> list[dict]:
    """Rank papers by importance using Kimi LLM and return the top N."""
    if not papers:
        return []

    client = OpenAI(api_key=KIMI_API_KEY, base_url=KIMI_BASE_URL)
    batch_size = 25

    for paper in papers:
        paper["importance_score"] = 5  # default score

    for batch_start in range(0, len(papers), batch_size):
        batch = papers[batch_start : batch_start + batch_size]
        batch_text = _format_batch(batch)
        batch_num = batch_start // batch_size + 1
        total_batches = (len(papers) + batch_size - 1) // batch_size
        logger.info(f"Ranking batch {batch_num}/{total_batches} ({len(batch)} papers)")

        try:
            response = client.chat.completions.create(
                model=KIMI_MODEL,
                temperature=0.1,
                max_tokens=2000,
                messages=[
                    {"role": "system", "content": RANKING_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": f"请为以下论文打分：\n\n{batch_text}",
                    },
                ],
            )
            scores = _parse_scores(response.choices[0].message.content)
            for item in scores:
                idx = item.get("id")
                score = item.get("score", 5)
                if idx is not None and 0 <= idx < len(batch):
                    batch[idx]["importance_score"] = score
        except Exception:
            logger.exception(f"Failed to rank batch {batch_num}, using default scores")

    # Sort by score descending, then by number of categories (broader = more important)
    papers.sort(
        key=lambda p: (p["importance_score"], len(p["categories"])), reverse=True
    )

    top_papers = papers[: DIGEST_PAPER_COUNT]
    logger.info(
        f"Selected top {len(top_papers)} papers "
        f"(score range: {top_papers[-1]['importance_score']}-{top_papers[0]['importance_score']})"
    )
    return top_papers
