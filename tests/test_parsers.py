"""解析引擎 fixture 测试台 — 全部离线, 不联网

校准真实站点: 把采集的页面存到 tests/fixtures/, 仿照下方用例新增断言,
解析不对就改 parse_rules.py 的候选键/选择器, 重跑本文件。
"""

from pathlib import Path

import pytest

from huaqiangbei_monitor.parse_rules import RULES, ParseRule
from huaqiangbei_monitor.parser import (
    parse_price,
    parse_qty,
    parse_json_payload,
    parse_html_payload,
    parse_payload,
    extract_embedded_json,
    find_product_records,
    _balanced_json,
)
from huaqiangbei_monitor.scrapers.base import BaseScraper, ScrapeBlockedError

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


# ─── 数值解析 ────────────────────────────────────────────────────────────────
class TestNumberParsing:
    @pytest.mark.parametrize("raw,expected", [
        ("¥9.80", 9.80),
        ("￥0.31", 0.31),
        ("CNY 12.5", 12.5),
        ("RMB12", 12.0),
        ("9.85元", 9.85),
        ("1,234.56", 1234.56),
        (9.6, 9.6),
        (10, 10.0),
        ("缺货", None),
        ("0", None),       # 0 价无效
        (None, None),
    ])
    def test_parse_price(self, raw, expected):
        assert parse_price(raw) == expected

    @pytest.mark.parametrize("raw,expected", [
        ("库存 86000", 86000),
        ("1,000", 1000),
        ("50 PCS", 50),
        ("10万+", 10),
        ("", None),
        (None, None),
        (1200, 1200),
    ])
    def test_parse_qty(self, raw, expected):
        assert parse_qty(raw) == expected


# ─── JSON 工具 ───────────────────────────────────────────────────────────────
class TestJsonTools:
    def test_balanced_json_object(self):
        s = 'var x = {"a": {"b": [1,2]}, "c": "}"} ; rest'
        start = s.index("{")
        assert _balanced_json(s, start) == '{"a": {"b": [1,2]}, "c": "}"}'

    def test_balanced_json_handles_string_with_brace(self):
        s = '{"name": "a{b}c"}'
        assert _balanced_json(s, 0) == s

    def test_extract_next_data(self):
        html = load("allchips_nextjs_sample.html")
        objs = extract_embedded_json(html, ["__NEXT_DATA__"])
        assert len(objs) == 1
        assert objs[0]["page"] == "/search"

    def test_extract_window_assignment(self):
        html = (
            "<html><script>window.__INITIAL_STATE__ = "
            '{"list":[{"model":"NE555","price":0.4}]};</script></html>'
        )
        objs = extract_embedded_json(html, ["__INITIAL_STATE__", "window.__INITIAL_STATE__"])
        assert objs and objs[0]["list"][0]["model"] == "NE555"


# ─── 商品数组定位 ────────────────────────────────────────────────────────────
class TestProductFinder:
    def test_prefers_list_with_part_keys_over_price_ladder(self):
        """嵌套的阶梯价数组不应盖过真正的商品列表"""
        obj = {
            "data": {
                "list": [
                    {"partNumber": "A", "priceList": [{"price": 1.0}, {"price": 0.9}]},
                    {"partNumber": "B", "priceList": [{"price": 2.0}]},
                ]
            }
        }
        recs = find_product_records(
            obj, part_keys=["partNumber"], price_keys=["price"], ladder_keys=["priceList"]
        )
        assert len(recs) == 2
        assert {r["partNumber"] for r in recs} == {"A", "B"}


# ─── 立创: JSON API ──────────────────────────────────────────────────────────
class TestSzlcscJson:
    def test_parse_api_ladder_price(self):
        text = load("szlcsc_api_sample.json")
        infos = parse_json_payload(text, RULES["szlcsc"], "STM32F103C8T6")
        # 仅型号匹配的一条
        assert len(infos) == 1
        info = infos[0]
        assert info.source == "szlcsc"
        assert info.price == 9.85           # 阶梯价首档
        assert info.min_qty == 1
        assert info.stock_qty == 12860
        assert "ST" in info.supplier
        assert info.url == "https://item.szlcsc.com/12345.html"

    def test_query_filters_other_parts(self):
        text = load("szlcsc_api_sample.json")
        infos = parse_json_payload(text, RULES["szlcsc"], "LM358DR")
        assert len(infos) == 1
        assert infos[0].price == 0.42
        assert infos[0].min_qty == 10


# ─── Allchips: 内嵌 Next.js JSON ─────────────────────────────────────────────
class TestAllchipsEmbedded:
    def test_parse_nextjs_embedded(self):
        html = load("allchips_nextjs_sample.html")
        infos = parse_html_payload(html, RULES["allchips"], "STM32F103C8T6")
        assert len(infos) == 2
        primary = [i for i in infos if i.supplier == "Allchips自营"][0]
        assert primary.price == 9.60        # priceList 首档
        assert primary.stock_qty == 8500
        assert primary.min_qty == 1


# ─── ICSMART: DOM 兜底 ───────────────────────────────────────────────────────
class TestIcsmartDom:
    def test_parse_dom_table(self):
        html = load("icsmart_dom_sample.html")
        infos = parse_html_payload(html, RULES["icsmart"], "NE555")
        # NE555P / NE555DR 命中, LM358N 被型号过滤
        assert len(infos) == 2
        prices = sorted(i.price for i in infos)
        assert prices == [0.31, 0.38]
        cheapest = min(infos, key=lambda i: i.price)
        assert cheapest.stock_qty == 120000
        assert "档口" in cheapest.supplier
        assert cheapest.url.startswith("https://www.icsmart.cn/goods/")

    def test_auto_dispatch_html(self):
        """parse_payload 应自动识别 HTML 走内嵌/DOM 路径"""
        html = load("icsmart_dom_sample.html")
        infos = parse_payload(html, RULES["icsmart"], "NE555")
        assert len(infos) == 2


# ─── 反爬拦截检测 ────────────────────────────────────────────────────────────
class TestBlockedDetection:
    def _resp(self, text):
        class R:
            pass
        r = R()
        r.text = text
        return r

    def test_detects_short_proxy_block(self):
        with pytest.raises(ScrapeBlockedError):
            BaseScraper._check_blocked(self._resp("Access Denied"))  # 短且无标签

    def test_detects_captcha_page(self):
        html = "<html><body>请输入验证码完成人机验证</body></html>"
        with pytest.raises(ScrapeBlockedError):
            BaseScraper._check_blocked(self._resp(html))

    def test_normal_page_not_blocked(self):
        html = load("icsmart_dom_sample.html")
        BaseScraper._check_blocked(self._resp(html))  # 不抛异常即通过
