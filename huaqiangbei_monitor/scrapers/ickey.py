"""云汉芯城爬虫"""

import logging
from bs4 import BeautifulSoup

from .base import BaseScraper, PriceInfo

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.ickey.cn/search-products-{keyword}.html"


class IckeyScraper(BaseScraper):
    source_id = "ickey"
    source_name = "云汉芯城"

    def _search(self, part_number: str) -> list[PriceInfo]:
        url = SEARCH_URL.format(keyword=part_number)
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.debug("[云汉] 请求失败: %s", e)
            return []

        results = []
        rows = (
            soup.select("table.product-table tbody tr")
            or soup.select(".product-row")
            or soup.select("[class*='search-item']")
        )

        for row in rows[:8]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # 型号匹配
            part_text = cells[0].get_text(strip=True) if cells else ""
            if part_number.upper() not in part_text.upper():
                continue

            # 价格
            price = None
            raw_text = ""
            for cell in cells[1:]:
                text = cell.get_text(strip=True)
                p = self._parse_price(text)
                if p and 0.001 < p < 100000:
                    price = p
                    raw_text = text
                    break

            if price is None:
                continue

            stock_el = row.select_one("[class*='stock'], td:nth-child(4)")
            stock = self._parse_qty(stock_el.get_text()) if stock_el else None

            link = row.select_one("a[href]")
            url_detail = link.get("href") if link else None
            if url_detail and not url_detail.startswith("http"):
                url_detail = "https://www.ickey.cn" + url_detail

            results.append(
                PriceInfo(
                    part_number=part_number,
                    source=self.source_id,
                    source_name=self.source_name,
                    price=price,
                    stock_qty=stock,
                    supplier="云汉芯城",
                    url=url_detail,
                    raw_price_text=raw_text,
                )
            )

        return results
