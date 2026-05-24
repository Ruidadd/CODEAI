"""
Alert engine: detects threshold breaches and dispatches notifications.
"""
import json
import requests
from datetime import datetime
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

from . import storage
from .config import ALERT_THRESHOLDS, AlertConfig

console = Console()


def _pct_change(old: float, new: float) -> float:
    if old == 0:
        return 0.0
    return (new - old) / old * 100.0


def check_dram_alert(dram_type: str, new_price: float, cfg: AlertConfig,
                     db_path: str = storage.DB_PATH) -> None:
    prev = storage.get_latest_dram(dram_type, db_path)
    if prev is None:
        return
    pct = _pct_change(prev["price_usd"], new_price)
    threshold = ALERT_THRESHOLDS["dram_price_change_pct"]
    if abs(pct) >= threshold:
        direction = "SPIKE" if pct > 0 else "DROP"
        severity = "HIGH" if abs(pct) >= threshold * 2 else "MEDIUM"
        msg = (f"DRAM {direction}: {dram_type} moved {pct:+.2f}% "
               f"(${prev['price_usd']:.4f} → ${new_price:.4f}/GB)")
        _dispatch(category="dram_price", severity=severity, message=msg,
                  metadata={"dram_type": dram_type, "old": prev["price_usd"],
                             "new": new_price, "pct_change": pct},
                  cfg=cfg, db_path=db_path)


def check_gpu_price_alert(provider: str, region: str, instance_type: str,
                           new_price: float, cfg: AlertConfig,
                           db_path: str = storage.DB_PATH) -> None:
    prev = storage.get_latest_gpu_price(provider, region, instance_type, db_path)
    if prev is None:
        return
    old_price = prev["spot_price_usd"] or prev["on_demand_usd"]
    if old_price is None:
        return
    pct = _pct_change(old_price, new_price)
    threshold = ALERT_THRESHOLDS["gpu_price_change_pct"]
    if abs(pct) >= threshold:
        direction = "UP" if pct > 0 else "DOWN"
        severity = "HIGH" if abs(pct) >= threshold * 2 else "MEDIUM"
        msg = (f"GPU PRICE {direction}: {provider}/{region}/{instance_type} "
               f"moved {pct:+.2f}% (${old_price:.4f} → ${new_price:.4f}/hr)")
        _dispatch(category="gpu_price", severity=severity, message=msg,
                  metadata={"provider": provider, "region": region,
                             "instance": instance_type, "old": old_price,
                             "new": new_price, "pct_change": pct},
                  cfg=cfg, db_path=db_path)


def check_gpu_availability_alert(provider: str, region: str, instance_type: str,
                                  available: bool, cfg: AlertConfig,
                                  db_path: str = storage.DB_PATH) -> None:
    with storage.get_conn(db_path) as conn:
        prev = conn.execute(
            """SELECT available FROM gpu_availability
               WHERE provider=? AND region=? AND instance_type=?
               ORDER BY ts DESC LIMIT 1""",
            (provider, region, instance_type),
        ).fetchone()

    if prev is None:
        return
    if prev["available"] == 1 and not available:
        msg = (f"GPU UNAVAILABLE: {provider}/{region}/{instance_type} "
               f"— capacity collapsed")
        _dispatch(category="gpu_availability", severity="HIGH", message=msg,
                  metadata={"provider": provider, "region": region, "instance": instance_type},
                  cfg=cfg, db_path=db_path)
    elif prev["available"] == 0 and available:
        msg = (f"GPU RESTORED: {provider}/{region}/{instance_type} "
               f"— capacity back online")
        _dispatch(category="gpu_availability", severity="INFO", message=msg,
                  metadata={"provider": provider, "region": region, "instance": instance_type},
                  cfg=cfg, db_path=db_path)


def _dispatch(category: str, severity: str, message: str,
              metadata: Optional[Dict] = None, cfg: Optional[AlertConfig] = None,
              db_path: str = storage.DB_PATH) -> None:
    storage.insert_alert(category, severity, message, metadata, db_path)

    if cfg and cfg.log_to_console:
        _print_alert(severity, message)

    if cfg and cfg.webhook_url:
        _send_webhook(cfg.webhook_url, severity, message, metadata)


def _print_alert(severity: str, message: str) -> None:
    color_map = {"HIGH": "bold red", "MEDIUM": "bold yellow", "INFO": "bold green"}
    color = color_map.get(severity, "white")
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    text = Text()
    text.append(f"[{ts}] ", style="dim")
    text.append(f"[{severity}] ", style=color)
    text.append(message)
    console.print(Panel(text, border_style=color.split()[-1]))


def _send_webhook(url: str, severity: str, message: str,
                  metadata: Optional[Dict] = None) -> None:
    payload = {
        "severity": severity,
        "message": message,
        "ts": datetime.utcnow().isoformat(),
        "metadata": metadata or {},
    }
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass
