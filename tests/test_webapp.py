"""Web 面板 API 测试 — 用 Flask test client, 不起真实服务"""

import pytest

from huaqiangbei_monitor.webapp import create_app
from huaqiangbei_monitor.storage import PriceStorage
from huaqiangbei_monitor.scrapers.base import PriceInfo


@pytest.fixture
def client(tmp_path):
    db = str(tmp_path / "web.db")
    st = PriceStorage(db)
    st.add_component("STM32F103C8T6")
    # 两轮价格, 第二轮触发告警(+15%)
    for price in (10.0, 11.5):
        st.save_price(PriceInfo(
            "STM32F103C8T6", "szlcsc", "立创商城", price,
            min_qty=1, stock_qty=5000, supplier="立创自营",
        ))
    st.save_price(PriceInfo(
        "STM32F103C8T6", "icsmart", "华强北网(ICSMART)", 8.8,
        min_qty=10, stock_qty=3000, supplier="华强北档口",
    ))
    app = create_app(db)
    app.testing = True
    return app.test_client()


class TestPages:
    def test_index_serves_dashboard(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "华强北元器件价格监控" in r.get_data(as_text=True)


class TestApi:
    def test_stats(self, client):
        data = client.get("/api/stats").get_json()
        assert data["total_components"] == 1
        assert data["total_records"] == 3
        assert data["total_alerts"] == 1

    def test_components_overview(self, client):
        data = client.get("/api/components").get_json()
        assert len(data) == 1
        comp = data[0]
        assert comp["part_number"] == "STM32F103C8T6"
        assert comp["best_price"] == 8.8          # 最低价来源
        assert comp["source_count"] == 2

    def test_latest_prices_with_change(self, client):
        data = client.get("/api/prices/STM32F103C8T6").get_json()
        assert len(data) == 2
        assert data[0]["price"] <= data[1]["price"]  # 升序
        szlcsc = next(r for r in data if r["source"] == "szlcsc")
        assert szlcsc["change_pct"] == 15.0          # 10 → 11.5

    def test_history_grouped_by_source(self, client):
        data = client.get("/api/history/STM32F103C8T6?days=7").get_json()
        by_src = {s["source"]: s for s in data}
        assert len(by_src["szlcsc"]["points"]) == 2
        assert by_src["szlcsc"]["points"][0]["price"] == 10.0

    def test_alerts(self, client):
        data = client.get("/api/alerts?hours=24").get_json()
        assert len(data) == 1
        assert data[0]["direction"] == "up"
        assert data[0]["change_pct"] == 15.0

    def test_add_component(self, client):
        r = client.post("/api/components", json={"part_number": "ne555"})
        assert r.get_json()["part_number"] == "NE555"  # 自动大写
        parts = [c["part_number"] for c in client.get("/api/components").get_json()]
        assert "NE555" in parts

    def test_add_component_empty_rejected(self, client):
        r = client.post("/api/components", json={"part_number": "  "})
        assert r.status_code == 400
