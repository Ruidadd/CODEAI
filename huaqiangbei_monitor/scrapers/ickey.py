"""云汉芯城爬虫"""

from .rule_scraper import RuleScraper
from ..parse_rules import RULES


class IckeyScraper(RuleScraper):
    rule = RULES["ickey"]
