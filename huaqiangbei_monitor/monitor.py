"""监控核心逻辑"""

import logging
import time
from datetime import datetime
from typing import Optional

import schedule

from .scrapers import get_all_scrapers
from .storage import PriceStorage
from .config import DEFAULT_INTERVAL_MINUTES, DEFAULT_COMPONENTS

logger = logging.getLogger(__name__)


class PriceMonitor:
    def __init__(self, db_path: Optional[str] = None):
        self.storage = PriceStorage(db_path)
        self.scrapers = get_all_scrapers()

    def run_once(self, part_numbers: Optional[list[str]] = None) -> dict:
        """执行一次全量抓取，返回统计结果"""
        if part_numbers is None:
            components = self.storage.list_components(active_only=True)
            part_numbers = [c.part_number for c in components]

        if not part_numbers:
            logger.info("没有监控的元器件，跳过本次抓取")
            return {"fetched": 0, "saved": 0, "alerts": 0}

        stats = {"fetched": 0, "saved": 0, "alerts": 0, "errors": 0}
        started_at = datetime.now()

        logger.info("开始抓取 %d 个型号，使用 %d 个数据源", len(part_numbers), len(self.scrapers))

        for part_number in part_numbers:
            for scraper in self.scrapers:
                try:
                    results = scraper.search(part_number)
                    stats["fetched"] += len(results)
                    for price_info in results:
                        _, alert = self.storage.save_price(price_info)
                        stats["saved"] += 1
                        if alert:
                            stats["alerts"] += 1
                except Exception as e:
                    logger.error("[%s] 抓取 %s 异常: %s", scraper.source_name, part_number, e)
                    stats["errors"] += 1

        elapsed = (datetime.now() - started_at).total_seconds()
        logger.info(
            "抓取完成: 获取 %d 条, 保存 %d 条, 告警 %d 条, 耗时 %.1fs",
            stats["fetched"], stats["saved"], stats["alerts"], elapsed,
        )
        return stats

    def run_scheduler(
        self,
        part_numbers: Optional[list[str]] = None,
        interval_minutes: int = DEFAULT_INTERVAL_MINUTES,
    ):
        """启动定时监控（阻塞）"""
        logger.info("启动定时监控，间隔 %d 分钟", interval_minutes)
        self.run_once(part_numbers)  # 立即执行一次
        schedule.every(interval_minutes).minutes.do(self.run_once, part_numbers=part_numbers)
        while True:
            schedule.run_pending()
            time.sleep(30)

    def add_component(self, part_number: str, description: str = "", category: str = ""):
        self.storage.add_component(part_number, description, category)

    def remove_component(self, part_number: str):
        self.storage.remove_component(part_number)

    def list_components(self) -> list:
        return self.storage.list_components()

    def get_latest_prices(self, part_number: str):
        return self.storage.get_latest_prices(part_number)

    def get_price_history(self, part_number: str, source: Optional[str] = None, days: int = 30):
        return self.storage.get_price_history(part_number, source, days)

    def get_recent_alerts(self, hours: int = 24):
        return self.storage.get_recent_alerts(hours)

    def get_stats(self) -> dict:
        return self.storage.get_stats()
