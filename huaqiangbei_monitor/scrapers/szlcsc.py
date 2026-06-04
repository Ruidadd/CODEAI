"""立创商城爬虫 - 通过公开搜索 API 获取价格"""

import json
import logging
from typing import Optional

from .base import BaseScraper, PriceInfo

logger = logging.getLogger(__name__)

SEARCH_API = "https://so.szlcsc.com/s?q={keyword}&pageSize=10&pageIndex=1&hy=IC"
DETAIL_URL = "https://item.szlcsc.com/{product_id}.html"


class SzlcscScraper(BaseScraper):
    source_id = "szlcsc"
    source_name = "立创商城"

    def _search(self, part_number: str) -> list[PriceInfo]:
        url = SEARCH_API.format(keyword=part_number)
        try:
            resp = self._get(
                url,
                headers={
                    **self.session.headers,
                    "Referer": "https://www.szlcsc.com/",
                    "X-Requested-With": "XMLHttpRequest",
                },
            )
            data = resp.json()
        except (ValueError, Exception) as e:
            logger.debug("[立创] API解析失败，尝试备用方式: %s", e)
            return self._search_html(part_number)

        results = []
        products = (
            data.get("data", {}).get("productList", [])
            or data.get("data", {}).get("zhList", [])
            or []
        )

        for item in products[:5]:
            price = self._extract_price(item)
            if price is None:
                continue

            part = item.get("productCode") or item.get("productModel") or part_number
            if part_number.upper() not in part.upper() and part.upper() not in part_number.upper():
                continue

            stock = item.get("stockNumber") or item.get("stockCount")
            product_id = item.get("productId") or item.get("id")
            url_detail = DETAIL_URL.format(product_id=product_id) if product_id else None

            results.append(
                PriceInfo(
                    part_number=part_number,
                    source=self.source_id,
                    source_name=self.source_name,
                    price=price,
                    min_qty=int(item.get("minBuyNumber", 1) or 1),
                    stock_qty=int(stock) if stock else None,
                    supplier="立创商城",
                    url=url_detail,
                    raw_price_text=str(price),
                )
            )

        return results

    def _extract_price(self, item: dict) -> Optional[float]:
        """从商品数据提取单价"""
        for key in ("discountPrice", "price", "productPrice", "unitPrice"):
            val = item.get(key)
            if val:
                price = self._parse_price(str(val))
                if price and price > 0:
                    return price

        price_list = item.get("priceList") or item.get("ladderPriceList") or []
        if price_list:
            try:
                first = price_list[0]
                price = self._parse_price(str(first.get("price") or first.get("unitPrice") or ""))
                if price and price > 0:
                    return price
            except (IndexError, TypeError):
                pass
        return None

    def _search_html(self, part_number: str) -> list[PriceInfo]:
        """HTML 备用解析"""
        from bs4 import BeautifulSoup

        url = f"https://so.szlcsc.com/global.html?k={part_number}"
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception:
            return []

        results = []
        cards = soup.select(".product-item, .search-item, [class*='product-card']")
        for card in cards[:5]:
            price_el = card.select_one("[class*='price'], .product-price")
            if not price_el:
                continue
            price = self._parse_price(price_el.get_text())
            if price is None or price <= 0:
                continue

            part_el = card.select_one("[class*='part-number'], [class*='model'], .product-code")
            part = (part_el.get_text(strip=True) if part_el else part_number)

            results.append(
                PriceInfo(
                    part_number=part_number,
                    source=self.source_id,
                    source_name=self.source_name,
                    price=price,
                    supplier="立创商城",
                    raw_price_text=price_el.get_text(strip=True),
                )
            )
        return results
