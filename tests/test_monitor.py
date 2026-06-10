"""基础功能测试"""

import pytest
import tempfile
import os
from datetime import datetime

from huaqiangbei_monitor.models import init_db
from huaqiangbei_monitor.storage import PriceStorage
from huaqiangbei_monitor.scrapers.base import PriceInfo
from huaqiangbei_monitor.monitor import PriceMonitor


@pytest.fixture
def tmp_db(tmp_path):
    db_file = str(tmp_path / "test.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def storage(tmp_db):
    return PriceStorage(tmp_db)


@pytest.fixture
def monitor(tmp_db):
    return PriceMonitor(db_path=tmp_db)


class TestStorage:
    def test_add_and_list_components(self, storage):
        storage.add_component("STM32F103C8T6", "STM32 MCU", "MCU")
        storage.add_component("NE555", "定时器", "模拟IC")
        comps = storage.list_components()
        parts = [c.part_number for c in comps]
        assert "STM32F103C8T6" in parts
        assert "NE555" in parts

    def test_add_duplicate_component(self, storage):
        storage.add_component("ESP32")
        storage.add_component("ESP32")  # 重复添加不应报错
        comps = storage.list_components()
        assert sum(1 for c in comps if c.part_number == "ESP32") == 1

    def test_remove_component(self, storage):
        storage.add_component("AO3400")
        storage.remove_component("AO3400")
        comps = storage.list_components(active_only=True)
        assert all(c.part_number != "AO3400" for c in comps)

    def test_save_price(self, storage):
        info = PriceInfo(
            part_number="STM32F103C8T6",
            source="szlcsc",
            source_name="立创商城",
            price=9.80,
            min_qty=1,
            stock_qty=1000,
            supplier="立创商城",
        )
        record, alert = storage.save_price(info)
        assert record.price == 9.80
        assert alert is None  # 第一条记录不触发告警

    def test_price_alert_triggered(self, storage):
        for price in [10.0, 11.0]:  # 10% 涨幅 > 5% 阈值
            info = PriceInfo(
                part_number="LM358",
                source="szlcsc",
                source_name="立创商城",
                price=price,
                min_qty=1,
            )
            storage.save_price(info)

        alerts = storage.get_recent_alerts(hours=1)
        assert len(alerts) >= 1
        assert alerts[0].direction == "up"
        assert abs(alerts[0].change_pct - 10.0) < 0.1

    def test_no_alert_small_change(self, storage):
        for price in [10.0, 10.2]:  # 2% 涨幅 < 5% 阈值
            info = PriceInfo(
                part_number="NE555",
                source="szlcsc",
                source_name="立创商城",
                price=price,
                min_qty=1,
            )
            storage.save_price(info)

        alerts = storage.get_recent_alerts(hours=1)
        assert len(alerts) == 0

    def test_get_latest_prices_returns_datetime(self, storage):
        """回归: get_latest_prices 须返回 ORM 对象, scraped_at 为 datetime 而非 str"""
        for src, name, price in [
            ("szlcsc", "立创商城", 9.8),
            ("icsmart", "华强北网", 8.5),
        ]:
            storage.save_price(
                PriceInfo("STM32F103C8T6", src, name, price, min_qty=1)
            )
        rows = storage.get_latest_prices("STM32F103C8T6")
        assert len(rows) == 2
        for r in rows:
            assert isinstance(r.scraped_at, datetime)
            # 报表会调用 strftime, 这里确保不抛异常
            assert r.scraped_at.strftime("%m-%d %H:%M")
        # 按价格升序
        assert rows[0].price <= rows[1].price

    def test_get_latest_prices_one_per_source(self, storage):
        """同一来源多次抓取, 只返回最新一条"""
        for price in [10.0, 10.1, 10.5]:
            storage.save_price(
                PriceInfo("NE555", "szlcsc", "立创商城", price, min_qty=1)
            )
        rows = storage.get_latest_prices("NE555")
        assert len(rows) == 1
        assert rows[0].price == 10.5

    def test_get_stats(self, storage):
        storage.add_component("W25Q64")
        stats = storage.get_stats()
        assert stats["total_components"] >= 1
        assert "total_records" in stats


class TestMonitor:
    def test_monitor_add_list(self, monitor):
        monitor.add_component("AMS1117-3.3", "LDO稳压器")
        comps = monitor.list_components()
        assert any(c.part_number == "AMS1117-3.3" for c in comps)

    def test_monitor_stats(self, monitor):
        stats = monitor.get_stats()
        assert isinstance(stats, dict)
        assert "total_components" in stats


class TestPriceInfo:
    def test_price_info_str(self):
        info = PriceInfo(
            part_number="STM32F103C8T6",
            source="szlcsc",
            source_name="立创商城",
            price=9.80,
        )
        s = str(info)
        assert "立创商城" in s
        assert "STM32F103C8T6" in s

    def test_parse_price(self):
        from huaqiangbei_monitor.scrapers.base import BaseScraper

        class _Stub(BaseScraper):
            source_id = "test"
            source_name = "Test"

            def _search(self, _):
                return []

        s = _Stub()
        assert s._parse_price("¥9.80") == 9.80
        assert s._parse_price("CNY 12.5") == 12.5
        assert s._parse_price("0.035") == 0.035
        assert s._parse_price("N/A") is None

    def test_parse_qty(self):
        from huaqiangbei_monitor.scrapers.base import BaseScraper

        class _Stub(BaseScraper):
            source_id = "test"
            source_name = "Test"

            def _search(self, _):
                return []

        s = _Stub()
        assert s._parse_qty("1,000") == 1000
        assert s._parse_qty("50 PCS") == 50
        assert s._parse_qty("") is None
