"""多策略解析引擎 — 纯函数, 不依赖网络

解析顺序: 内嵌JSON(__NEXT_DATA__/__NUXT__/window.X) → API JSON → DOM 选择器。
所有函数只吃文本(html/json 字符串)吐 PriceInfo, 因此可被 fixture 测试台离线驱动。
真实站点校准时只需调整 parse_rules.py 里的候选键/选择器, 无需改本文件。
"""

import json
import re
import logging
from typing import Optional, Any

from bs4 import BeautifulSoup

from .scrapers.base import PriceInfo
from .parse_rules import ParseRule

logger = logging.getLogger(__name__)


# ─── 基础数值解析 ────────────────────────────────────────────────────────────
def parse_price(value: Any) -> Optional[float]:
    """从任意值(字符串/数字)中提取单价"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value > 0 else None
    text = str(value).strip().replace(",", "")
    for token in ("￥", "¥", "CNY", "RMB", "元", "$"):
        text = text.replace(token, "")
    match = re.search(r"(\d+\.?\d*)", text)
    if not match:
        return None
    try:
        price = float(match.group(1))
        return price if price > 0 else None
    except ValueError:
        return None


def parse_qty(value: Any) -> Optional[int]:
    """提取数量(库存/起购量)"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip().replace(",", "").replace("+", "")
    match = re.search(r"(\d+)", text)
    if not match:
        return None
    try:
        return int(match.group(1))
    except ValueError:
        return None


# ─── JSON 提取工具 ───────────────────────────────────────────────────────────
def _try_json(text: str) -> Optional[Any]:
    """尝试解析 JSON, 兼容被二次编码成字符串的情况"""
    if not text or not text.strip():
        return None
    try:
        obj = json.loads(text)
    except (json.JSONDecodeError, ValueError):
        return None
    # 二次编码: "{\"a\":1}"
    if isinstance(obj, str):
        try:
            return json.loads(obj)
        except (json.JSONDecodeError, ValueError):
            return obj
    return obj


def _balanced_json(s: str, start: int) -> Optional[str]:
    """从 start 处的 { 或 [ 起, 提取配平的 JSON 片段(正确处理字符串与转义)"""
    if start >= len(s) or s[start] not in "{[":
        return None
    open_ch = s[start]
    close_ch = "}" if open_ch == "{" else "]"
    depth, in_str, esc = 0, False, False
    for i in range(start, len(s)):
        c = s[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == open_ch:
                depth += 1
            elif c == close_ch:
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
    return None


def extract_embedded_json(html: str, var_names: list[str]) -> list[Any]:
    """从 <script> 中提取内嵌 JSON

    覆盖三种常见形态:
      1. <script id="__NEXT_DATA__" type="application/json">{...}</script>
      2. <script type="application/json">{...}</script>
      3. window.__INITIAL_STATE__ = {...};  /  window.__NUXT__=(...)
    """
    objs: list[Any] = []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return objs

    for script in soup.find_all("script"):
        text = script.string or script.get_text() or ""
        if not text.strip():
            continue
        sid = script.get("id", "") or ""
        stype = script.get("type", "") or ""

        # 形态 1/2: 整个 script 体就是 JSON
        if sid in var_names or stype == "application/json":
            obj = _try_json(text.strip())
            if obj is not None:
                objs.append(obj)
                continue

        # 形态 3: 赋值语句, 抓等号后第一个配平的对象/数组
        for var in var_names:
            for m in re.finditer(re.escape(var) + r"\s*=\s*", text):
                brace = text.find("{", m.end())
                bracket = text.find("[", m.end())
                candidates = [p for p in (brace, bracket) if p != -1]
                if not candidates:
                    continue
                snippet = _balanced_json(text, min(candidates))
                if snippet:
                    obj = _try_json(snippet)
                    if obj is not None:
                        objs.append(obj)
    return objs


# ─── 商品数组定位 ────────────────────────────────────────────────────────────
def _has_any_key(d: dict, keys: list[str]) -> bool:
    low = {k.lower() for k in d.keys()}
    return any(k.lower() in low for k in keys)


def find_product_records(
    obj: Any, part_keys: list[str], price_keys: list[str],
    ladder_keys: list[str], max_depth: int = 10,
) -> list[dict]:
    """递归查找看起来像商品列表的 dict 数组

    判定标准: list 内的 dict 至少含一个 价格键 或 阶梯价键 或 型号键。
    多个候选取最长的一个 (商品列表通常最长)。
    """
    signal_keys = price_keys + ladder_keys + part_keys
    candidates: list[list[dict]] = []

    def visit(node: Any, depth: int):
        if depth > max_depth:
            return
        if isinstance(node, list):
            dicts = [x for x in node if isinstance(x, dict)]
            if dicts and any(_has_any_key(x, signal_keys) for x in dicts):
                candidates.append(dicts)
            for x in node:
                visit(x, depth + 1)
        elif isinstance(node, dict):
            for v in node.values():
                visit(v, depth + 1)

    visit(obj, 0)
    if not candidates:
        return []

    # 评分: 优先含"型号字段"的列表(真商品列表), 其次取更长的
    # —— 避免误选嵌套的阶梯价数组(那些只有价格、无型号)
    def score(lst: list[dict]) -> tuple[int, int]:
        with_part = sum(1 for x in lst if _has_any_key(x, part_keys))
        return (with_part, len(lst))

    candidates.sort(key=score, reverse=True)
    return candidates[0]


def _get_field(d: dict, keys: list[str]) -> Any:
    """大小写不敏感地取第一个存在且非空的候选键"""
    low = {k.lower(): v for k, v in d.items()}
    for k in keys:
        v = low.get(k.lower())
        if v not in (None, "", [], {}):
            return v
    return None


def _extract_price_from_record(rec: dict, rule: ParseRule) -> Optional[float]:
    """从商品 dict 提取单价: 先直接价, 再阶梯价首档"""
    direct = _get_field(rec, rule.price_keys)
    price = parse_price(direct)
    if price:
        return price

    ladder = _get_field(rec, rule.ladder_keys)
    if isinstance(ladder, list) and ladder:
        first = ladder[0]
        if isinstance(first, dict):
            return parse_price(_get_field(first, rule.ladder_price_keys))
        return parse_price(first)
    return None


def _match_part(part_text: Optional[str], query: str) -> bool:
    """型号匹配(双向子串, 大小写不敏感); 无型号字段时放行交由价格校验"""
    if not part_text:
        return True
    a, b = str(part_text).upper(), query.upper()
    return a in b or b in a


def records_to_priceinfo(
    records: list[dict], rule: ParseRule, query: str,
) -> list[PriceInfo]:
    results: list[PriceInfo] = []
    for rec in records:
        price = _extract_price_from_record(rec, rule)
        if not price:
            continue
        part_field = _get_field(rec, rule.part_keys)
        if not _match_part(part_field, query):
            continue

        url = None
        if rule.detail_url_template:
            pid = _get_field(rec, rule.product_id_keys)
            if pid:
                url = rule.detail_url_template.format(id=pid)

        results.append(
            PriceInfo(
                part_number=query,
                source=rule.source_id,
                source_name=rule.source_name,
                price=price,
                min_qty=parse_qty(_get_field(rec, rule.min_qty_keys)) or 1,
                stock_qty=parse_qty(_get_field(rec, rule.stock_keys)),
                supplier=(_get_field(rec, rule.supplier_keys) or rule.source_name),
                url=url,
                raw_price_text=str(_get_field(rec, rule.price_keys) or price),
            )
        )
    return results


# ─── DOM 解析 ────────────────────────────────────────────────────────────────
def _select_first_text(node, selectors: list[str]) -> Optional[str]:
    for sel in selectors:
        try:
            el = node.select_one(sel)
        except Exception:
            continue
        if el:
            txt = el.get_text(strip=True)
            if txt:
                return txt
    return None


def parse_dom(html: str, rule: ParseRule, query: str) -> list[PriceInfo]:
    """DOM 选择器兜底解析"""
    if not rule.dom_container:
        return []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return []

    containers = []
    for sel in rule.dom_container:
        try:
            found = soup.select(sel)
        except Exception:
            found = []
        if found:
            containers = found
            break

    results: list[PriceInfo] = []
    for node in containers[:15]:
        price = parse_price(_select_first_text(node, rule.dom_price))
        if not price:
            continue
        part_text = _select_first_text(node, rule.dom_part)
        if not _match_part(part_text, query):
            continue

        link = None
        for sel in rule.dom_link or []:
            try:
                a = node.select_one(sel)
            except Exception:
                a = None
            if a and a.get("href"):
                link = a["href"]
                if not link.startswith("http"):
                    link = rule.base_url.rstrip("/") + "/" + link.lstrip("/")
                break

        results.append(
            PriceInfo(
                part_number=query,
                source=rule.source_id,
                source_name=rule.source_name,
                price=price,
                min_qty=parse_qty(_select_first_text(node, rule.dom_min_qty)) or 1,
                stock_qty=parse_qty(_select_first_text(node, rule.dom_stock)),
                supplier=_select_first_text(node, rule.dom_supplier) or rule.source_name,
                url=link,
                raw_price_text=_select_first_text(node, rule.dom_price),
            )
        )
    return results


# ─── 顶层入口 ────────────────────────────────────────────────────────────────
def parse_json_payload(text: str, rule: ParseRule, query: str) -> list[PriceInfo]:
    """解析一段 JSON 文本(API 响应)"""
    obj = _try_json(text)
    if obj is None:
        return []
    records = find_product_records(obj, rule.part_keys, rule.price_keys, rule.ladder_keys)
    return records_to_priceinfo(records, rule, query)


def parse_html_payload(text: str, rule: ParseRule, query: str) -> list[PriceInfo]:
    """解析一段 HTML 文本: 先内嵌 JSON, 失败再 DOM"""
    for obj in extract_embedded_json(text, rule.embedded_json_vars):
        records = find_product_records(
            obj, rule.part_keys, rule.price_keys, rule.ladder_keys
        )
        infos = records_to_priceinfo(records, rule, query)
        if infos:
            logger.debug("[%s] 内嵌JSON 命中 %d 条", rule.source_id, len(infos))
            return infos
    return parse_dom(text, rule, query)


def parse_payload(text: str, rule: ParseRule, query: str) -> list[PriceInfo]:
    """自动判别 JSON / HTML 并解析"""
    stripped = text.lstrip()
    if stripped[:1] in ("{", "["):
        infos = parse_json_payload(text, rule, query)
        if infos:
            return infos
    return parse_html_payload(text, rule, query)
