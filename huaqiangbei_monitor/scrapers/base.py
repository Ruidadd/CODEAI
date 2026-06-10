"""爬虫基类"""

import time
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from ..config import HEADERS, REQUEST_TIMEOUT, REQUEST_DELAY_SECONDS, BLOCKED_SIGNATURES

logger = logging.getLogger(__name__)


class ScrapeBlockedError(Exception):
    """检测到反爬拦截(网络策略/验证码/JS挑战)"""


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
        # 先做拦截识别(在 raise_for_status 之前), 让诊断信息更明确
        self._check_blocked(resp)
        resp.raise_for_status()
        return resp

    @staticmethod
    def _check_blocked(resp: requests.Response) -> None:
        """识别反爬拦截: 出站网络策略的固定短响应、验证码页、JS挑战页"""
        body = resp.text or ""
        status = getattr(resp, "status_code", None)
        stripped = body.strip()

        # 403/429 且响应体极短 → 多为网络策略/WAF 拦截而非真实业务 403
        if status in (403, 429) and len(stripped) <= 64:
            raise ScrapeBlockedError(
                f"疑似网络策略/WAF 拦截 (HTTP {status}, 响应仅 {len(body)} 字节): "
                f"{stripped!r} — 需在放行该域名的网络环境下运行"
            )
        # 通用短响应拦截(如远程环境代理的固定 21 字节)
        if 0 < len(stripped) <= 32 and "<" not in body:
            raise ScrapeBlockedError(
                f"疑似网络策略拦截(响应仅 {len(body)} 字节): {stripped!r}"
            )
        low = body.lower()
        for sig in BLOCKED_SIGNATURES:
            if sig in low:
                raise ScrapeBlockedError(f"页面命中反爬特征: {sig!r}")

    def search(self, part_number: str) -> list[PriceInfo]:
        """搜索元器件价格，返回 PriceInfo 列表"""
        try:
            return self._search(part_number)
        except ScrapeBlockedError as e:
            logger.warning("[%s] %s — 跳过 %s", self.source_name, e, part_number)
            return []
        except Exception as e:
            logger.warning("[%s] 搜索 %s 失败: %s", self.source_name, part_number, e)
            return []

    @abstractmethod
    def _search(self, part_number: str) -> list[PriceInfo]:
        pass

    def _parse_price(self, text) -> Optional[float]:
        """从字符串中提取价格数字(委托给解析引擎)"""
        from ..parser import parse_price
        return parse_price(text)

    def _parse_qty(self, text) -> Optional[int]:
        from ..parser import parse_qty
        return parse_qty(text)
