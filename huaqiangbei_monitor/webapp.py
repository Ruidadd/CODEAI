"""Web 实时监控面板 — Flask 后端

提供 JSON API + 单页仪表盘:
  GET  /                      仪表盘页面
  GET  /api/stats             系统统计
  GET  /api/components        监控型号列表(含最新最低价与环比涨跌)
  POST /api/components        添加监控型号  {"part_number": "..."}
  GET  /api/prices/<part>     某型号各来源最新报价(含环比)
  GET  /api/history/<part>    价格历史(按来源分组, 供图表)
  GET  /api/alerts            最近告警
  POST /api/fetch             立即触发一次抓取(后台线程, 不阻塞)

启动: python main.py web [--port 8000] [--fetch-interval 30]
fetch-interval > 0 时启动后台线程定时抓取, 前端轮询即可看到实时变化。
"""

import logging
import threading
from datetime import datetime

from flask import Flask, jsonify, render_template, request

from .monitor import PriceMonitor

logger = logging.getLogger(__name__)

# 单线程串行抓取, 避免并发触发把源站打挂/重复入库
_fetch_lock = threading.Lock()
_last_fetch: dict = {"at": None, "stats": None, "running": False}


def create_app(db_path: str | None = None) -> Flask:
    app = Flask(__name__)
    monitor = PriceMonitor(db_path=db_path)
    app.config["MONITOR"] = monitor

    # ── 页面 ──────────────────────────────────────────────────────
    @app.get("/")
    def index():
        return render_template("index.html")

    # ── API ───────────────────────────────────────────────────────
    @app.get("/api/stats")
    def api_stats():
        stats = monitor.get_stats()
        stats["last_fetch_at"] = _last_fetch["at"]
        stats["fetch_running"] = _last_fetch["running"]
        return jsonify(stats)

    @app.get("/api/components")
    def api_components():
        result = []
        for comp in monitor.list_components():
            latest = monitor.get_latest_prices(comp.part_number)
            best = latest[0] if latest else None  # 已按价格升序
            change_pct = None
            if best:
                two = monitor.storage.get_latest_two(comp.part_number, best.source)
                if len(two) == 2 and two[1].price > 0:
                    change_pct = (two[0].price - two[1].price) / two[1].price * 100
            result.append({
                "part_number": comp.part_number,
                "description": comp.description or "",
                "category": comp.category or "",
                "best_price": best.price if best else None,
                "best_source": best.source_name if best else None,
                "stock_qty": best.stock_qty if best else None,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "updated_at": best.scraped_at.isoformat() if best else None,
                "source_count": len(latest),
            })
        return jsonify(result)

    @app.post("/api/components")
    def api_add_component():
        data = request.get_json(silent=True) or {}
        part = (data.get("part_number") or "").strip().upper()
        if not part:
            return jsonify({"error": "part_number 不能为空"}), 400
        monitor.add_component(part, data.get("description", ""), data.get("category", ""))
        return jsonify({"ok": True, "part_number": part})

    @app.get("/api/prices/<part>")
    def api_prices(part):
        part = part.upper()
        rows = []
        for r in monitor.get_latest_prices(part):
            two = monitor.storage.get_latest_two(part, r.source)
            change_pct = None
            if len(two) == 2 and two[1].price > 0:
                change_pct = (two[0].price - two[1].price) / two[1].price * 100
            rows.append({
                "source": r.source,
                "source_name": r.source_name,
                "price": r.price,
                "min_qty": r.min_qty,
                "stock_qty": r.stock_qty,
                "supplier": r.supplier,
                "url": r.url,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "scraped_at": r.scraped_at.isoformat() if r.scraped_at else None,
            })
        return jsonify(rows)

    @app.get("/api/history/<part>")
    def api_history(part):
        days = request.args.get("days", 7, type=int)
        records = monitor.get_price_history(part.upper(), days=days)
        series: dict[str, dict] = {}
        for r in records:
            s = series.setdefault(
                r.source, {"source": r.source, "source_name": r.source_name, "points": []}
            )
            s["points"].append({
                "t": r.scraped_at.isoformat() if r.scraped_at else None,
                "price": r.price,
            })
        return jsonify(list(series.values()))

    @app.get("/api/alerts")
    def api_alerts():
        hours = request.args.get("hours", 48, type=int)
        return jsonify([
            {
                "part_number": a.part_number,
                "source": a.source,
                "old_price": a.old_price,
                "new_price": a.new_price,
                "change_pct": round(a.change_pct, 2),
                "direction": a.direction,
                "alerted_at": a.alerted_at.isoformat() if a.alerted_at else None,
            }
            for a in monitor.get_recent_alerts(hours=hours)
        ])

    @app.post("/api/fetch")
    def api_fetch():
        if _last_fetch["running"]:
            return jsonify({"ok": False, "message": "已有抓取任务在运行"}), 409
        threading.Thread(target=_do_fetch, args=(monitor,), daemon=True).start()
        return jsonify({"ok": True, "message": "抓取已在后台启动"})

    return app


def _do_fetch(monitor: PriceMonitor):
    if not _fetch_lock.acquire(blocking=False):
        return
    _last_fetch["running"] = True
    try:
        stats = monitor.run_once()
        _last_fetch["stats"] = stats
        _last_fetch["at"] = datetime.utcnow().isoformat()
    except Exception as e:
        logger.error("后台抓取异常: %s", e)
    finally:
        _last_fetch["running"] = False
        _fetch_lock.release()


def start_background_fetcher(monitor: PriceMonitor, interval_minutes: int):
    """后台定时抓取线程, 让面板数据持续更新"""
    import time

    def loop():
        while True:
            _do_fetch(monitor)
            time.sleep(interval_minutes * 60)

    t = threading.Thread(target=loop, daemon=True, name="bg-fetcher")
    t.start()
    logger.info("后台抓取线程已启动, 间隔 %d 分钟", interval_minutes)


def run_server(host: str, port: int, db_path: str | None, fetch_interval: int):
    app = create_app(db_path)
    if fetch_interval > 0:
        start_background_fetcher(app.config["MONITOR"], fetch_interval)
    app.run(host=host, port=port, debug=False, threaded=True)
