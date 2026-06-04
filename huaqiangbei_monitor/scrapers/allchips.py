"""Allchips 芯片网爬虫"""

import logging
from bs4 import BeautifulSoup

from .base import BaseScraper, PriceInfo

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.allchips.com/search?q={keyword}"


class AllchipsScraper(BaseScraper):
    source_id = "allchips"
    source_name = "Allchips芯片网"

    def _search(self, part_number: str) -> list[PriceInfo]:
        url = SEARCH_URL.format(keyword=part_number)
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.debug("[Allchips] 请求失败: %s", e)
            return []

        results = []
        rows = soup.select("table.search-result tr, .product-list-item, [class*='search-result'] tr")
        if not rows:
            rows = soup.select("tr[class*='product'], .list-row")

        for row in rows[:10]:
            cells = row.find_all("td")
            if len(cells) < 3:
                continue

            # 第一列通常是型号
            part_cell = cells[0].get_text(strip=True)
            if part_number.upper() not in part_cell.upper():
                continue

            # 寻找价格列
            price = None
            for cell in cells:
                text = cell.get_text(strip=True)
                if any(c in text for c in ["¥", "￥", "CNY", "RMB"]) or (
                    text and text[0].isdigit() and "." in text
                ):
                    price = self._parse_price(text)
                    if price and price > 0:
                        break

            if price is None:
                continue

            # 库存
            stock = None
            for cell in cells:
                qty = self._parse_qty(cell.get_text(strip=True))
                if qty and qty > 0 and qty != price:
                    stock = qty
                    break

            link = row.select_one("a[href]")
            url_detail = link["href"] if link else None
            if url_detail and not url_detail.startswith("http"):
                url_detail = "https://www.allchips.com" + url_detail

            results.append(
                PriceInfo(
                    part_number=part_number,
                    source=self.source_id,
                    source_name=self.source_name,
                    price=price,
                    stock_qty=stock,
                    url=url_detail,
                    raw_price_text=str(price),
                )
            )

        return results
