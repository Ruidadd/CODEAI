import json
import logging
import re

from openai import OpenAI

from config import KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = """你是一位资深 AI 研究员，为每周论文精选撰写精炼的论文摘要。
你的读者是技术背景的忙碌研究者/工程师——他们需要在30秒内理解每篇论文的核心。

对每篇论文，请生成以下三个部分的结构化摘要：
1. 问题 (Problem)：这篇论文要解决什么问题？（1-2句话）
2. 解决方案 (Solution)：提出了什么方法？（2-3句话）
3. 创新之处 (Innovation)：与现有工作相比，新颖之处在哪里？（1-2句话）

用简体中文撰写，技术术语、模型名称和英文专有名词保留英文（如 Transformer, RLHF, GPT-4）。

请严格返回 JSON，格式如下（不要添加其他文字）：
{"problem": "...", "solution": "...", "innovation": "..."}"""


def _parse_summary(text: str) -> dict | None:
    """Parse JSON summary from LLM response."""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        try:
            return json.loads(match.group(1).strip())
        except json.JSONDecodeError:
            pass
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass
    return None


def summarize_papers(papers: list[dict]) -> list[dict]:
    """Generate structured summaries for each paper using Kimi LLM."""
    client = OpenAI(api_key=KIMI_API_KEY, base_url=KIMI_BASE_URL)
    results = []

    for i, paper in enumerate(papers):
        logger.info(f"Summarizing paper {i + 1}/{len(papers)}: {paper['title'][:60]}...")
        authors_str = ", ".join(paper["authors"][:5])
        if len(paper["authors"]) > 5:
            authors_str += " et al."

        user_prompt = (
            f"请总结这篇论文：\n\n"
            f"Title: {paper['title']}\n"
            f"Authors: {authors_str}\n"
            f"Categories: {', '.join(paper['categories'])}\n"
            f"Abstract: {paper['abstract']}"
        )

        try:
            response = client.chat.completions.create(
                model=KIMI_MODEL,
                temperature=0.3,
                max_tokens=1000,
                messages=[
                    {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
            )
            summary = _parse_summary(response.choices[0].message.content)
            if summary and all(k in summary for k in ("problem", "solution", "innovation")):
                paper["summary"] = summary
            else:
                logger.warning(f"Invalid summary format for paper {i + 1}, using fallback")
                paper["summary"] = {
                    "problem": "摘要生成失败，请查看原文。",
                    "solution": "摘要生成失败，请查看原文。",
                    "innovation": "摘要生成失败，请查看原文。",
                }
        except Exception:
            logger.exception(f"Failed to summarize paper {i + 1}")
            paper["summary"] = {
                "problem": "摘要生成失败，请查看原文。",
                "solution": "摘要生成失败，请查看原文。",
                "innovation": "摘要生成失败，请查看原文。",
            }

        results.append(paper)

    logger.info(f"Summarized {len(results)} papers")
    return results
