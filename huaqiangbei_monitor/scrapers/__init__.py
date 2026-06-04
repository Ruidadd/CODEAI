"""价格抓取模块"""

from .base import BaseScraper, PriceInfo
from .szlcsc import SzlcscScraper
from .allchips import AllchipsScraper
from .icsmart import IcsmartScraper
from .ickey import IckeyScraper

__all__ = [
    "BaseScraper",
    "PriceInfo",
    "SzlcscScraper",
    "AllchipsScraper",
    "IcsmartScraper",
    "IckeyScraper",
]


def get_all_scrapers():
    return [
        SzlcscScraper(),
        AllchipsScraper(),
        IcsmartScraper(),
        IckeyScraper(),
    ]
