"""立创商城爬虫"""

from .rule_scraper import RuleScraper
from ..parse_rules import RULES


class SzlcscScraper(RuleScraper):
    rule = RULES["szlcsc"]
