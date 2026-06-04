"""爬虫基类"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY_SECONDS

logger = logging.getLogger(__name__)


@dataclass
class PriceInfo:
    part_number: str
    source: str
    source_name: str
    price: float
    currency: str = "CNY"
    min_qty: int = 1
    stock_qty: Optional[int] = None
    supplier: Optional[str] = None
    url: Optional[str] = None
    raw_price_text: Optional[str] = None
    scraped_at: datetime = field(default_factory=datetime.utcnow)

    def __str__(self):
        return f"[{self.source_name}] {self.part_number} ¥{self.price:.4f} 起购:{self.min_qty}"


class BaseScraper(ABC):
    source_id: str = ""
    source_name: str = ""

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self._last_request_time = 0.0

    def _throttle(self):
        """控制请求频率"""
        elapsed = time.time() - self._last_request_time
        if elapsed < REQUEST_DELAY_SECONDS:
            time.sleep(REQUEST_DELAY_SECONDS - elapsed)
        self._last_request_time = time.time()

    @retry(
        retry=retry_if_exception_type((requests.Timeout, requests.ConnectionError)),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    def _get(self, url: str, **kwargs) -> requests.Response:
        self._throttle()
        resp = self.session.get(url, timeout=REQUEST_TIMEOUT, **kwargs)
        resp.raise_for_status()
        return resp

    def search(self, part_number: str) -> list[PriceInfo]:
        """搜索元器件价格，返回 PriceInfo 列表"""
        try:
            return self._search(part_number)
        except Exception as e:
            logger.warning("[%s] 搜索 %s 失败: %s", self.source_name, part_number, e)
            return []

    @abstractmethod
    def _search(self, part_number: str) -> list[PriceInfo]:
        pass

    def _parse_price(self, text: str) -> Optional[float]:
        """从字符串中提取价格数字"""
        import re
        text = text.strip().replace(",", "").replace("￥", "").replace("¥", "").replace("CNY", "")
        match = re.search(r"(\d+\.?\d*)", text)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
        return None

    def _parse_qty(self, text: str) -> Optional[int]:
        import re
        text = text.strip().replace(",", "")
        match = re.search(r"(\d+)", text)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                return None
        return None
