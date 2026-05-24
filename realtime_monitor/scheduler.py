"""
Main monitoring scheduler: polls all data sources at configured intervals,
persists data, and fires alerts on threshold breaches.
"""
import logging
import time
import threading
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.text import Text

from . import storage
from .config import AlertConfig, POLL_INTERVALS
from .collectors import dram as dram_collector
from .collectors import aws_gpu, azure_gpu, gcp_gpu
from . import alerts as alert_engine

logger = logging.getLogger(__name__)
console = Console()


def _collect_dram(cfg: AlertConfig, db_path: str) -> None:
    try:
        prices = dram_collector.fetch_prices()
        for dram_type, price in prices.items():
            alert_engine.check_dram_alert(dram_type, price, cfg, db_path)
            storage.insert_dram_price(dram_type, price, db_path=db_path)
        logger.info("DRAM poll: %d types collected", len(prices))
    except Exception as exc:
        logger.error("DRAM collection error: %s", exc)


def _collect_gpu(cfg: AlertConfig, db_path: str) -> None:
    collectors = [aws_gpu.fetch_spot_prices, azure_gpu.fetch_spot_prices, gcp_gpu.fetch_spot_prices]
    for fetch_fn in collectors:
        try:
            records = fetch_fn()
            for rec in records:
                provider = rec["provider"]
                region = rec["region"]
                itype = rec["instance_type"]
                price = rec.get("spot_price_usd")
                available = rec.get("available", False)

                if price is not None:
                    alert_engine.check_gpu_price_alert(provider, region, itype, price, cfg, db_path)
                    storage.insert_gpu_price(provider, region, itype, price, None, db_path=db_path)

                alert_engine.check_gpu_availability_alert(provider, region, itype, available, cfg, db_path)
                storage.insert_gpu_availability(provider, region, itype, available, db_path=db_path)

            logger.info("%s GPU poll: %d records", fetch_fn.__module__.split(".")[-1], len(records))
        except Exception as exc:
            logger.error("GPU collection error (%s): %s", fetch_fn.__module__, exc)


def _make_status_table(db_path: str) -> Table:
    table = Table(title="Realtime Alternative Data Monitor", expand=True)
    table.add_column("Category", style="cyan", no_wrap=True)
    table.add_column("Key", style="white")
    table.add_column("Latest Value", justify="right", style="green")
    table.add_column("Timestamp", style="dim")

    with storage.get_conn(db_path) as conn:
        for row in conn.execute(
            """SELECT dram_type, price_usd, ts FROM dram_prices
               WHERE (dram_type, ts) IN (
                   SELECT dram_type, MAX(ts) FROM dram_prices GROUP BY dram_type
               ) ORDER BY dram_type"""
        ):
            table.add_row("DRAM Price", row["dram_type"], f"${row['price_usd']:.4f}/GB", row["ts"][:19])

        for row in conn.execute(
            """SELECT provider||'/'||region AS loc, instance_type, spot_price_usd, ts
               FROM gpu_prices
               WHERE (provider, region, instance_type, ts) IN (
                   SELECT provider, region, instance_type, MAX(ts)
                   FROM gpu_prices GROUP BY provider, region, instance_type
               ) ORDER BY provider, region, instance_type
               LIMIT 20"""
        ):
            price_str = f"${row['spot_price_usd']:.4f}/hr" if row["spot_price_usd"] else "N/A"
            table.add_row("GPU Spot", f"{row['loc']} {row['instance_type']}", price_str, row["ts"][:19])

    return table


class Monitor:
    def __init__(self, db_path: str = storage.DB_PATH, cfg: Optional[AlertConfig] = None,
                 once: bool = False):
        self.db_path = db_path
        self.cfg = cfg or AlertConfig(log_to_console=True)
        self.once = once
        self._stop = threading.Event()

    def run(self) -> None:
        storage.init_db(self.db_path)
        console.print("[bold cyan]Starting realtime alternative data monitor...[/]")

        if self.once:
            _collect_dram(self.cfg, self.db_path)
            _collect_gpu(self.cfg, self.db_path)
            return

        next_dram = 0.0
        next_gpu = 0.0
        interval = 5  # main loop tick seconds

        try:
            while not self._stop.is_set():
                now = time.time()

                if now >= next_dram:
                    threading.Thread(target=_collect_dram, args=(self.cfg, self.db_path),
                                     daemon=True).start()
                    next_dram = now + POLL_INTERVALS["dram"]

                if now >= next_gpu:
                    threading.Thread(target=_collect_gpu, args=(self.cfg, self.db_path),
                                     daemon=True).start()
                    next_gpu = now + POLL_INTERVALS["gpu_cloud"]

                time.sleep(interval)

        except KeyboardInterrupt:
            console.print("\n[yellow]Monitor stopped.[/]")

    def stop(self) -> None:
        self._stop.set()
