"""声明式解析规则 — 各站点的字段候选键与选择器

校准真实站点时, 只需在这里增删候选键/选择器, 无需改 parser.py。
建议配合 tests/fixtures/ 下保存的真实页面样本, 跑 test_parsers.py 验证。

字段说明:
  embedded_json_vars  : 内嵌 JSON 的 script id / 全局变量名候选
  part_keys           : JSON 中"型号"字段的候选键(大小写不敏感)
  price_keys          : "单价"字段候选键
  ladder_keys         : "阶梯价数组"字段候选键
  ladder_price_keys   : 阶梯价单项里"价格"的候选键
  min_qty_keys/stock_keys/product_id_keys/supplier_keys : 同理
  dom_*               : DOM 兜底解析用的 CSS 选择器候选(按顺序命中即用)
  detail_url_template : 详情页 URL 模板, {id} 用 product_id 填充
"""

from dataclasses import dataclass, field


@dataclass
class ParseRule:
    source_id: str
    source_name: str
    base_url: str
    search_url: str
    api_url: str = ""  # 有 JSON API 时优先用; 含 {keyword}

    # ── 内嵌 JSON / API JSON 字段候选 ──
    embedded_json_vars: list[str] = field(default_factory=list)
    part_keys: list[str] = field(default_factory=list)
    price_keys: list[str] = field(default_factory=list)
    ladder_keys: list[str] = field(default_factory=list)
    ladder_price_keys: list[str] = field(default_factory=list)
    min_qty_keys: list[str] = field(default_factory=list)
    stock_keys: list[str] = field(default_factory=list)
    product_id_keys: list[str] = field(default_factory=list)
    supplier_keys: list[str] = field(default_factory=list)
    detail_url_template: str = ""

    # ── DOM 兜底选择器候选 ──
    dom_container: list[str] = field(default_factory=list)
    dom_part: list[str] = field(default_factory=list)
    dom_price: list[str] = field(default_factory=list)
    dom_min_qty: list[str] = field(default_factory=list)
    dom_stock: list[str] = field(default_factory=list)
    dom_supplier: list[str] = field(default_factory=list)
    dom_link: list[str] = field(default_factory=list)


# 通用内嵌 JSON 变量名(各框架常见全局态)
_COMMON_JSON_VARS = [
    "__NEXT_DATA__",
    "__NUXT__",
    "__INITIAL_STATE__",
    "window.__INITIAL_STATE__",
    "__APP_DATA__",
    "__PRELOADED_STATE__",
]


RULES: dict[str, ParseRule] = {
    "szlcsc": ParseRule(
        source_id="szlcsc",
        source_name="立创商城",
        base_url="https://www.szlcsc.com",
        search_url="https://so.szlcsc.com/global.html?k={keyword}",
        api_url="https://so.szlcsc.com/s?q={keyword}&pageSize=10&pageIndex=1&hy=IC",
        embedded_json_vars=_COMMON_JSON_VARS,
        part_keys=["productCode", "productModel", "productModelType", "model", "partNumber"],
        price_keys=["discountPrice", "price", "productPrice", "unitPrice", "salePrice"],
        ladder_keys=["productPriceList", "priceList", "ladderPriceList", "priceTiers"],
        ladder_price_keys=["productPrice", "price", "unitPrice"],
        min_qty_keys=["minBuyNumber", "minPackNumber", "minOrderQty", "moq"],
        stock_keys=["stockNumber", "stockCount", "stock", "totalStock"],
        product_id_keys=["productId", "id", "productCode"],
        supplier_keys=["brandName", "supplier", "shopName"],
        detail_url_template="https://item.szlcsc.com/{id}.html",
        dom_container=[".product-item", ".search-item", "[class*='product-card']", "tr[class*='product']"],
        dom_part=["[class*='part-number']", "[class*='model']", ".product-code", "a[class*='title']"],
        dom_price=["[class*='price']", ".product-price", "td.price"],
        dom_min_qty=["[class*='min-buy']", "[class*='moq']"],
        dom_stock=["[class*='stock']", "[class*='inventory']"],
        dom_supplier=["[class*='brand']", "[class*='supplier']"],
        dom_link=["a[href]"],
    ),
    "allchips": ParseRule(
        source_id="allchips",
        source_name="Allchips芯片网",
        base_url="https://www.allchips.com",
        search_url="https://www.allchips.com/search?q={keyword}",
        embedded_json_vars=_COMMON_JSON_VARS,
        part_keys=["partNumber", "mpn", "model", "partNo", "goodsName"],
        price_keys=["price", "unitPrice", "salePrice", "minPrice"],
        ladder_keys=["priceList", "ladderPrice", "priceLadder"],
        ladder_price_keys=["price", "unitPrice"],
        min_qty_keys=["moq", "minOrderQty", "minQty"],
        stock_keys=["stock", "qty", "inventory", "stockQty"],
        product_id_keys=["id", "goodsId", "productId"],
        supplier_keys=["supplier", "brand", "manufacturer", "seller"],
        dom_container=["table.search-result tr", ".product-list-item", "[class*='search-result'] tr", ".list-row"],
        dom_part=["td:nth-child(1)", "[class*='part']", "[class*='mpn']", "a[class*='title']"],
        dom_price=["[class*='price']", "td:nth-child(3)", "td:nth-child(4)"],
        dom_min_qty=["[class*='moq']", "[class*='min']"],
        dom_stock=["[class*='stock']", "[class*='qty']"],
        dom_supplier=["[class*='supplier']", "[class*='brand']"],
        dom_link=["a[href]"],
    ),
    "icsmart": ParseRule(
        source_id="icsmart",
        source_name="华强北网(ICSMART)",
        base_url="https://www.icsmart.cn",
        search_url="https://www.icsmart.cn/search?keyword={keyword}",
        embedded_json_vars=_COMMON_JSON_VARS,
        part_keys=["goodsName", "model", "partNumber", "title", "spec"],
        price_keys=["price", "unitPrice", "salePrice", "shopPrice"],
        ladder_keys=["priceList", "ladderPrice"],
        ladder_price_keys=["price", "unitPrice"],
        min_qty_keys=["moq", "minBuyNum", "minQty"],
        stock_keys=["stock", "stockNum", "qty"],
        product_id_keys=["goodsId", "id", "productId"],
        supplier_keys=["supplier", "shopName", "sellerName", "company"],
        detail_url_template="https://www.icsmart.cn/goods/{id}.html",
        dom_container=[".goods-list-item", ".product-item", "[class*='goods-item']", "table.product-table tr"],
        dom_part=["[class*='goods-name']", "[class*='model']", "[class*='part']", "td:first-child"],
        dom_price=["[class*='price']", "[class*='unit-price']", "td.price"],
        dom_min_qty=["[class*='moq']", "[class*='min-buy']"],
        dom_stock=["[class*='stock']", "[class*='qty']", "td.stock"],
        dom_supplier=["[class*='supplier']", "[class*='seller']", "td.supplier"],
        dom_link=["a[href]"],
    ),
    "ickey": ParseRule(
        source_id="ickey",
        source_name="云汉芯城",
        base_url="https://www.ickey.cn",
        search_url="https://www.ickey.cn/search-products-{keyword}.html",
        embedded_json_vars=_COMMON_JSON_VARS,
        part_keys=["partNumber", "model", "goodsName", "mpn", "title"],
        price_keys=["price", "unitPrice", "salePrice", "minPrice"],
        ladder_keys=["priceList", "ladderPrice", "priceLadder"],
        ladder_price_keys=["price", "unitPrice"],
        min_qty_keys=["moq", "minOrderQty", "minQty"],
        stock_keys=["stock", "qty", "inventory"],
        product_id_keys=["id", "goodsId", "productId"],
        supplier_keys=["supplier", "brand", "manufacturer"],
        dom_container=["table.product-table tbody tr", ".product-row", "[class*='search-item']"],
        dom_part=["td:nth-child(1)", "[class*='part']", "[class*='model']", "a[class*='title']"],
        dom_price=["[class*='price']", "td:nth-child(2)", "td:nth-child(3)"],
        dom_min_qty=["[class*='moq']", "[class*='min']"],
        dom_stock=["[class*='stock']", "td:nth-child(4)"],
        dom_supplier=["[class*='supplier']", "[class*='brand']"],
        dom_link=["a[href]"],
    ),
}
