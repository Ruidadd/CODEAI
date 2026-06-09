"""规则驱动的爬虫 — 抓取归抓取, 解析交给 parser 引擎

抓取流程:
  1. 若配置了 api_url, 先打 JSON 接口(最稳, JS 站点的数据多来自此类 XHR)
  2. 否则(或接口无果)抓搜索页 HTML, 由引擎依次尝试 内嵌JSON → DOM
反爬拦截在 _get 里统一检测并抛 ScrapeBlockedError, 被 search() 捕获降级为空结果。
"""

import logging

from .base import BaseScraper, PriceInfo
from ..parse_rules import ParseRule
from ..parser import parse_json_payload, parse_html_payload

logger = logging.getLogger(__name__)


class RuleScraper(BaseScraper):
    rule: ParseRule = None  # 子类覆盖

    def __init__(self):
        super().__init__()
        if self.rule is None:
            raise ValueError(f"{type(self).__name__} 未配置 rule")
        self.source_id = self.rule.source_id
        self.source_name = self.rule.source_name

    def _search(self, part_number: str) -> list[PriceInfo]:
        # 策略一: JSON API
        if self.rule.api_url:
            infos = self._search_api(part_number)
            if infos:
                return infos

        # 策略二: 搜索页 HTML(内嵌JSON → DOM)
        return self._search_html(part_number)

    def _search_api(self, part_number: str) -> list[PriceInfo]:
        url = self.rule.api_url.format(keyword=part_number)
        resp = self._get(
            url,
            headers={
                "Referer": self.rule.base_url + "/",
                "X-Requested-With": "XMLHttpRequest",
            },
        )
        infos = parse_json_payload(resp.text, self.rule, part_number)
        if infos:
            logger.debug("[%s] API 命中 %d 条", self.source_name, len(infos))
        return infos

    def _search_html(self, part_number: str) -> list[PriceInfo]:
        url = self.rule.search_url.format(keyword=part_number)
        resp = self._get(url)
        return parse_html_payload(resp.text, self.rule, part_number)
