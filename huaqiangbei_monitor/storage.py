"""数据存储与查询"""

import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from .models import Component, PriceRecord, PriceAlert, get_session, init_db
from .scrapers.base import PriceInfo
from .config import PRICE_CHANGE_ALERT_THRESHOLD

logger = logging.getLogger(__name__)


class PriceStorage:
    def __init__(self, db_path: Optional[str] = None):
        from .models import get_engine
        engine = get_engine(db_path) if db_path else get_engine()
        init_db(db_path) if db_path else init_db()
        from sqlalchemy.orm import sessionmaker
        self._Session = sessionmaker(bind=engine, expire_on_commit=False)

    def _session(self) -> Session:
        return self._Session()

    # ─── 元器件管理 ───────────────────────────────────────────────
    def add_component(self, part_number: str, description: str = "", category: str = "") -> Component:
        with self._session() as s:
            comp = s.query(Component).filter_by(part_number=part_number).first()
            if not comp:
                comp = Component(
                    part_number=part_number,
                    description=description,
                    category=category,
                )
                s.add(comp)
                s.commit()
                logger.info("添加监控元器件: %s", part_number)
            return comp

    def remove_component(self, part_number: str):
        with self._session() as s:
            comp = s.query(Component).filter_by(part_number=part_number).first()
            if comp:
                comp.is_active = False
                s.commit()

    def list_components(self, active_only: bool = True) -> list[Component]:
        with self._session() as s:
            q = s.query(Component)
            if active_only:
                q = q.filter_by(is_active=True)
            return q.all()

    # ─── 价格记录 ─────────────────────────────────────────────────
    def save_price(self, info: PriceInfo) -> tuple[PriceRecord, Optional[PriceAlert]]:
        """保存价格，检测变化并生成告警"""
        record = PriceRecord(
            part_number=info.part_number,
            source=info.source,
            source_name=info.source_name,
            price=info.price,
            currency=info.currency,
            min_qty=info.min_qty,
            stock_qty=info.stock_qty,
            supplier=info.supplier,
            url=info.url,
            raw_price_text=info.raw_price_text,
            scraped_at=info.scraped_at,
        )

        alert = None
        with self._session() as s:
            # 获取该来源的上一条记录
            prev = (
                s.query(PriceRecord)
                .filter_by(part_number=info.part_number, source=info.source)
                .order_by(PriceRecord.scraped_at.desc())
                .first()
            )

            s.add(record)
            s.flush()

            if prev and prev.price > 0:
                change_pct = (info.price - prev.price) / prev.price * 100
                if abs(change_pct) >= PRICE_CHANGE_ALERT_THRESHOLD:
                    alert = PriceAlert(
                        part_number=info.part_number,
                        source=info.source,
                        old_price=prev.price,
                        new_price=info.price,
                        change_pct=change_pct,
                        direction="up" if change_pct > 0 else "down",
                    )
                    s.add(alert)
                    logger.warning(
                        "价格变化告警: %s [%s] %+.1f%% (%.4f → %.4f)",
                        info.part_number, info.source_name, change_pct,
                        prev.price, info.price,
                    )

            s.commit()

        return record, alert

    def get_latest_prices(self, part_number: str) -> list[PriceRecord]:
        """获取某型号各来源的最新价格"""
        with self._session() as s:
            # SQLite 子查询：每个来源取最新一条
            from sqlalchemy import text
            results = s.execute(
                text("""
                    SELECT * FROM price_records p1
                    WHERE part_number = :part
                    AND scraped_at = (
                        SELECT MAX(scraped_at) FROM price_records p2
                        WHERE p2.part_number = p1.part_number
                        AND p2.source = p1.source
                    )
                """),
                {"part": part_number},
            ).fetchall()
            return results

    def get_price_history(
        self,
        part_number: str,
        source: Optional[str] = None,
        days: int = 30,
    ) -> list[PriceRecord]:
        with self._session() as s:
            since = datetime.utcnow() - timedelta(days=days)
            q = (
                s.query(PriceRecord)
                .filter(PriceRecord.part_number == part_number)
                .filter(PriceRecord.scraped_at >= since)
            )
            if source:
                q = q.filter(PriceRecord.source == source)
            return q.order_by(PriceRecord.scraped_at.asc()).all()

    def get_recent_alerts(self, hours: int = 24) -> list[PriceAlert]:
        with self._session() as s:
            since = datetime.utcnow() - timedelta(hours=hours)
            return (
                s.query(PriceAlert)
                .filter(PriceAlert.alerted_at >= since)
                .order_by(PriceAlert.alerted_at.desc())
                .all()
            )

    def get_stats(self) -> dict:
        with self._session() as s:
            return {
                "total_components": s.query(Component).filter_by(is_active=True).count(),
                "total_records": s.query(PriceRecord).count(),
                "total_alerts": s.query(PriceAlert).count(),
                "unread_alerts": s.query(PriceAlert).filter_by(is_notified=False).count(),
            }
