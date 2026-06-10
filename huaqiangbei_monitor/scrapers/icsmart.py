"""华强北网 (ICSMART) 爬虫"""

from .rule_scraper import RuleScraper
from ..parse_rules import RULES


class IcsmartScraper(RuleScraper):
    rule = RULES["icsmart"]
