"""配賦エンジンの不変式テスト。

- 人件費保存則: 配賦額 + 未配賦額 == 全負荷人件費合計
- 間接費保存則: 配賦後合計 == プール合計（全ドライバ）
- 工数ゼロ従業員はデフォルト配分 or 未配賦として顕在化し、消えない
- 分母は給与実績時間: 記入漏れ分は partial_hours として未配賦になる
"""
import pandas as pd
import pytest

from core.allocation.engine import (
    aggregate_labor_by_project,
    allocate_overhead_to_projects,
    compute_employee_fully_loaded_cost,
    compute_labor_allocation,
    compute_overhead_pool,
    compute_project_month_pl,
    rollup_division_month_pl,
)

YM = "2026-05"


@pytest.fixture
def emc():
    df = pd.DataFrame([
        # eid, div, gross, employer_si, housing, hours
        {"employee_id": 1, "division_id": 10, "year_month": YM,
         "gross_pay": 500_000, "employer_social_insurance": 77_500,
         "housing_cost": 60_000, "actual_work_hours": 160.0},
        {"employee_id": 2, "division_id": 10, "year_month": YM,
         "gross_pay": 400_000, "employer_social_insurance": 62_000,
         "housing_cost": 0, "actual_work_hours": 160.0},
        {"employee_id": 3, "division_id": 20, "year_month": YM,
         "gross_pay": 600_000, "employer_social_insurance": 93_000,
         "housing_cost": 45_000, "actual_work_hours": 150.0},
        {"employee_id": 4, "division_id": 20, "year_month": YM,
         "gross_pay": 300_000, "employer_social_insurance": 46_500,
         "housing_cost": 0, "actual_work_hours": 140.0},
    ])
    return compute_employee_fully_loaded_cost(df)


@pytest.fixture
def timesheets():
    return pd.DataFrame([
        # emp1: 50/50 on two projects, fully logged (160h)
        {"employee_id": 1, "project_id": 100, "work_date": "2026-05-11", "hours": 80.0},
        {"employee_id": 1, "project_id": 101, "work_date": "2026-05-18", "hours": 80.0},
        # emp2: logs only 120h of 160h paid -> 25% unallocated (partial)
        {"employee_id": 2, "project_id": 100, "work_date": "2026-05-12", "hours": 120.0},
        # emp3: no timesheet at all -> falls back to default project
        # emp4: no timesheet, no default -> fully unallocated
    ])


@pytest.fixture
def default_projects():
    return pd.DataFrame([
        {"employee_id": 3, "project_id": 200, "year_month": YM, "weight": 1.0},
    ])


def test_fully_loaded_cost(emc):
    row = emc[emc["employee_id"] == 1].iloc[0]
    assert row["total_loaded_cost"] == 500_000 + 77_500 + 60_000


def test_labor_conservation(emc, timesheets, default_projects):
    allocated, unallocated = compute_labor_allocation(emc, timesheets, default_projects, YM)
    total = allocated["allocated_labor_cost"].sum() + unallocated["unallocated_cost"].sum()
    assert total == pytest.approx(emc["total_loaded_cost"].sum())


def test_fifty_fifty_split(emc, timesheets, default_projects):
    allocated, _ = compute_labor_allocation(emc, timesheets, default_projects, YM)
    e1 = allocated[allocated["employee_id"] == 1]
    loaded = emc.loc[emc["employee_id"] == 1, "total_loaded_cost"].iloc[0]
    assert e1["allocated_labor_cost"].tolist() == pytest.approx([loaded / 2, loaded / 2])


def test_partial_hours_visible(emc, timesheets, default_projects):
    """記入 120h / 給与 160h → 25% が partial_hours として未配賦に残る。"""
    allocated, unallocated = compute_labor_allocation(emc, timesheets, default_projects, YM)
    loaded = emc.loc[emc["employee_id"] == 2, "total_loaded_cost"].iloc[0]
    e2_alloc = allocated[allocated["employee_id"] == 2]["allocated_labor_cost"].sum()
    assert e2_alloc == pytest.approx(loaded * 120 / 160)
    part = unallocated[(unallocated["employee_id"] == 2)]
    assert part["reason"].iloc[0] == "partial_hours"
    assert part["unallocated_cost"].iloc[0] == pytest.approx(loaded * 40 / 160)


def test_default_project_fallback(emc, timesheets, default_projects):
    allocated, unallocated = compute_labor_allocation(emc, timesheets, default_projects, YM)
    e3 = allocated[allocated["employee_id"] == 3]
    assert len(e3) == 1
    assert e3["project_id"].iloc[0] == 200
    assert bool(e3["from_default"].iloc[0]) is True
    loaded = emc.loc[emc["employee_id"] == 3, "total_loaded_cost"].iloc[0]
    assert e3["allocated_labor_cost"].iloc[0] == pytest.approx(loaded)
    assert 3 not in unallocated["employee_id"].tolist()


def test_zero_hours_no_default_goes_unallocated(emc, timesheets, default_projects):
    _, unallocated = compute_labor_allocation(emc, timesheets, default_projects, YM)
    e4 = unallocated[unallocated["employee_id"] == 4]
    assert len(e4) == 1
    assert e4["reason"].iloc[0] == "no_hours"
    loaded = emc.loc[emc["employee_id"] == 4, "total_loaded_cost"].iloc[0]
    assert e4["unallocated_cost"].iloc[0] == pytest.approx(loaded)


def test_overlogged_hours_capped(emc, default_projects):
    """記入合計が給与時間を超えたら記入合計を分母にし、配賦率100%を超えない。"""
    ts = pd.DataFrame([
        {"employee_id": 1, "project_id": 100, "work_date": "2026-05-11", "hours": 120.0},
        {"employee_id": 1, "project_id": 101, "work_date": "2026-05-12", "hours": 80.0},
    ])
    allocated, unallocated = compute_labor_allocation(emc, ts, default_projects, YM)
    e1 = allocated[allocated["employee_id"] == 1]
    loaded = emc.loc[emc["employee_id"] == 1, "total_loaded_cost"].iloc[0]
    assert e1["allocated_labor_cost"].sum() == pytest.approx(loaded)
    assert e1["allocation_pct"].sum() == pytest.approx(1.0)


GL = pd.DataFrame([
    {"year_month": YM, "account_name": "地代家賃", "department_division_id": None, "amount": 3_000_000},
    {"year_month": YM, "account_name": "通信費", "department_division_id": 10, "amount": 500_000},
    {"year_month": YM, "account_name": "外注費(製)", "department_division_id": None, "amount": 9_999_999},  # not overhead
])
AM = pd.DataFrame([
    {"account_name": "地代家賃", "internal_category": "overhead"},
    {"account_name": "通信費", "internal_category": "overhead"},
    {"account_name": "外注費(製)", "internal_category": "outsourcing"},
])
PROJECTS = pd.DataFrame([
    {"project_id": 100, "division_id": 10},
    {"project_id": 101, "division_id": 10},
    {"project_id": 200, "division_id": 20},
])
ACTUALS = pd.DataFrame([
    {"project_id": 100, "year_month": YM, "revenue": 10_000_000, "outsourcing_cost": 6_000_000},
    {"project_id": 101, "year_month": YM, "revenue": 5_000_000, "outsourcing_cost": 2_000_000},
    {"project_id": 200, "year_month": YM, "revenue": 8_000_000, "outsourcing_cost": 4_000_000},
])


@pytest.mark.parametrize("driver", ["labor_cost", "labor_hours", "revenue"])
def test_overhead_conservation(emc, timesheets, default_projects, driver):
    allocated, _ = compute_labor_allocation(emc, timesheets, default_projects, YM)
    labor = aggregate_labor_by_project(allocated)
    pool = compute_overhead_pool(GL, AM, YM)
    out = allocate_overhead_to_projects(pool, PROJECTS, labor, ACTUALS, driver, YM)
    assert out["allocated_overhead_cost"].sum() == pytest.approx(pool["amount"].sum())


def test_overhead_excludes_non_overhead_accounts():
    pool = compute_overhead_pool(GL, AM, YM)
    assert "外注費(製)" not in pool["account_name"].tolist()
    assert pool["amount"].sum() == 3_500_000


def test_division_tagged_pool_stays_in_division(emc, timesheets, default_projects):
    allocated, _ = compute_labor_allocation(emc, timesheets, default_projects, YM)
    labor = aggregate_labor_by_project(allocated)
    pool = pd.DataFrame([
        {"account_name": "通信費", "department_division_id": 10, "amount": 500_000},
    ])
    out = allocate_overhead_to_projects(pool, PROJECTS, labor, ACTUALS, "revenue", YM)
    merged = out.merge(PROJECTS, on="project_id")
    assert (merged["division_id"] == 10).all()
    assert out["allocated_overhead_cost"].sum() == pytest.approx(500_000)


def test_project_pl_and_division_rollup(emc, timesheets, default_projects):
    allocated, unallocated = compute_labor_allocation(emc, timesheets, default_projects, YM)
    labor = aggregate_labor_by_project(allocated)
    pool = compute_overhead_pool(GL, AM, YM)
    overhead = allocate_overhead_to_projects(pool, PROJECTS, labor, ACTUALS, "labor_cost", YM)
    pl = compute_project_month_pl(ACTUALS, labor, overhead, YM)

    # P&L identity per project
    for _, r in pl.iterrows():
        assert r["total_cost"] == pytest.approx(
            r["direct_outsourcing_cost"] + r["allocated_labor_cost"] + r["allocated_overhead_cost"])
        assert r["gross_margin"] == pytest.approx(r["revenue"] - r["total_cost"])

    div = rollup_division_month_pl(pl, unallocated, PROJECTS)
    # 事業部人件費の保存則: 配賦 + 未配賦 == 給与合計
    labor_total = div["total_labor_cost"].sum()
    assert labor_total == pytest.approx(emc["total_loaded_cost"].sum())
