"""华强北网 (ICSMART) 爬虫"""

import logging
from bs4 import BeautifulSoup

from .base import BaseScraper, PriceInfo

logger = logging.getLogger(__name__)

SEARCH_URL = "https://www.icsmart.cn/search?keyword={keyword}"


class IcsmartScraper(BaseScraper):
    source_id = "icsmart"
    source_name = "华强北网(ICSMART)"

    def _search(self, part_number: str) -> list[PriceInfo]:
        url = SEARCH_URL.format(keyword=part_number)
        try:
            resp = self._get(url)
            soup = BeautifulSoup(resp.text, "lxml")
        except Exception as e:
            logger.debug("[ICSMART] 请求失败: %s", e)
            return []

        results = []

        # 尝试多种常见的列表选择器
        items = (
            soup.select(".goods-list-item")
            or soup.select(".product-item")
            or soup.select("[class*='goods-item']")
            or soup.select("table.product-table tr")
        )

        for item in items[:8]:
            # 型号
            part_el = item.select_one(
                "[class*='model'], [class*='part'], [class*='goods-name'], td:first-child"
            )
            if not part_el:
                continue
            part_text = part_el.get_text(strip=True)
            if part_number.upper() not in part_text.upper():
                continue

            # 价格
            price_el = item.select_one(
                "[class*='price'], [class*='unit-price'], td.price"
            )
            if not price_el:
                continue
            price = self._parse_price(price_el.get_text())
            if not price or price <= 0:
                continue

            # 库存
            stock_el = item.select_one("[class*='stock'], [class*='qty'], td.stock")
            stock = self._parse_qty(stock_el.get_text()) if stock_el else None

            # 供应商
            supplier_el = item.select_one("[class*='supplier'], [class*='seller'], td.supplier")
            supplier = supplier_el.get_text(strip=True) if supplier_el else "华强北"

            link = item.select_one("a[href]")
            url_detail = link.get("href") if link else None
            if url_detail and not url_detail.startswith("http"):
                url_detail = "https://www.icsmart.cn" + url_detail

            results.append(
                PriceInfo(
                    part_number=part_number,
                    source=self.source_id,
                    source_name=self.source_name,
                    price=price,
                    stock_qty=stock,
                    supplier=supplier,
                    url=url_detail,
                    raw_price_text=price_el.get_text(strip=True),
                )
            )

        return results
