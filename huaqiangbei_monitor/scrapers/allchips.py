"""Allchips 芯片网爬虫"""

from .rule_scraper import RuleScraper
from ..parse_rules import RULES


class AllchipsScraper(RuleScraper):
    rule = RULES["allchips"]
