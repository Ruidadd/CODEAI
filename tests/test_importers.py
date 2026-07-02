"""取込パイプラインのテスト：列マッピング、冪等性、実フォーマット解析。"""
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from core.db import make_memory_session
from core.importers.column_mapper import apply_mapping, clean_number, suggest_mapping
from core.importers.mf_gl_importer import parse_mf_pl_file, unclassified_accounts, upsert_gl_facts
from core.importers.misc_importers import (
    upsert_default_projects,
    upsert_housing_leases,
    upsert_project_actuals,
)
from core.importers.payroll_importer import (
    PAYROLL_FIELDS,
    default_payroll_mapping,
    parse_payroll_file,
    upsert_employee_month_costs,
)
from core.models import (
    Division,
    Employee,
    EmployeeMonthCost,
    GLOverheadFact,
    HousingLease,
    InsuranceRate,
    Project,
    ProjectMonthActual,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def session():
    s = make_memory_session()
    s.add(Division(code="DEV_SUPPORT", name="開発支援"))
    s.add(Division(code="ADMIN", name="管理部門", is_overhead=True))
    s.commit()
    return s


# ------------------------------------------------------------- column mapper


def test_suggest_mapping_real_headers():
    cols = ["従業員番号", "従業員", "部門", "契約種別", "総労働時間",
            "支給合計", "社会保険料合計", "社宅入居費(控除)"]
    m = suggest_mapping(cols, PAYROLL_FIELDS)
    assert m["employee_code"] == "従業員番号"
    assert m["gross_pay"] == "支給合計"
    assert m["actual_work_hours"] == "総労働時間"
    assert m["housing_deduction"] == "社宅入居費(控除)"


def test_apply_mapping_missing_required():
    df = pd.DataFrame({"a": [1]})
    with pytest.raises(ValueError, match="必須フィールド"):
        apply_mapping(df, {"employee_code": "missing_col"}, ["employee_code"])


def test_clean_number():
    assert clean_number("122,128,360") == 122128360
    assert clean_number("△1,494") == -1494
    assert clean_number("-") == 0.0
    assert clean_number(None) == 0.0
    assert clean_number(1500.5) == 1500.5


# ------------------------------------------------------------------- payroll


def test_payroll_import_idempotent(session):
    raw = pd.read_csv(FIXTURES / "sample_payroll.csv", dtype=str)
    mapping = default_payroll_mapping(list(raw.columns))
    df = parse_payroll_file(raw, mapping, year_month="2026-05")

    s1 = upsert_employee_month_costs(session, df, "sample_payroll.csv")
    assert s1.inserted == 5 and s1.updated == 0
    s2 = upsert_employee_month_costs(session, df, "sample_payroll.csv")
    assert s2.inserted == 0 and s2.updated == 5
    assert session.query(EmployeeMonthCost).count() == 5
    assert session.query(Employee).count() == 5


def test_payroll_employer_si_estimated(session):
    session.add_all([
        InsuranceRate(rate_name="健康保険", rate=0.05, effective_from="2026-01"),
        InsuranceRate(rate_name="厚生年金", rate=0.0915, effective_from="2026-01"),
    ])
    session.commit()
    raw = pd.read_csv(FIXTURES / "sample_payroll.csv", dtype=str)
    df = parse_payroll_file(raw, default_payroll_mapping(list(raw.columns)), year_month="2026-05")
    upsert_employee_month_costs(session, df)
    emp = session.query(Employee).filter_by(employee_code="0101").first()
    rec = session.query(EmployeeMonthCost).filter_by(employee_id=emp.id).first()
    assert float(rec.employer_social_insurance) == pytest.approx(520000 * (0.05 + 0.0915))


def test_payroll_housing_cost_from_lease(session):
    raw = pd.read_csv(FIXTURES / "sample_payroll.csv", dtype=str)
    df = parse_payroll_file(raw, default_payroll_mapping(list(raw.columns)), year_month="2026-05")
    upsert_employee_month_costs(session, df)  # employees now exist

    leases = pd.DataFrame([{
        "employee_code": "0101", "move_in": "2026-02-01", "move_out": "",
        "monthly_rent": 120000, "employee_share": 25000,
    }])
    upsert_housing_leases(session, leases)
    # re-import payroll -> housing cost now reflected
    upsert_employee_month_costs(session, df)
    emp = session.query(Employee).filter_by(employee_code="0101").first()
    rec = session.query(EmployeeMonthCost).filter_by(employee_id=emp.id, year_month="2026-05").first()
    assert float(rec.housing_cost) == 95000  # 120000 - 25000


def test_housing_lease_period_respected(session):
    raw = pd.read_csv(FIXTURES / "sample_payroll.csv", dtype=str)
    df = parse_payroll_file(raw, default_payroll_mapping(list(raw.columns)), year_month="2026-05")
    upsert_employee_month_costs(session, df)
    leases = pd.DataFrame([{
        "employee_code": "0102", "move_in": "2026-06-15", "move_out": "",
        "monthly_rent": 100000, "employee_share": 25000,
    }])
    upsert_housing_leases(session, leases)
    upsert_employee_month_costs(session, df)  # 2026-05 < move_in month
    emp = session.query(Employee).filter_by(employee_code="0102").first()
    rec = session.query(EmployeeMonthCost).filter_by(employee_id=emp.id, year_month="2026-05").first()
    assert float(rec.housing_cost) == 0


# ---------------------------------------------------------------------- MF PL


def test_mf_pl_parse_real_format():
    raw = pd.read_csv(FIXTURES / "sample_mf_pl.csv", header=None)
    long = parse_mf_pl_file(raw)
    assert set(long.columns) == {"account_name", "year_month", "amount"}
    # subtotal rows excluded
    assert "販売費及び一般管理費合計" not in long["account_name"].tolist()
    assert "営業利益" not in long["account_name"].tolist()
    # year detected from '2026/01〜2026/05'
    assert long["year_month"].str.startswith("2026-").all()
    rent_may = long[(long["account_name"] == "地代家賃") & (long["year_month"] == "2026-05")]
    assert rent_may["amount"].iloc[0] == 3998942


def test_mf_gl_upsert_idempotent_and_unclassified(session):
    raw = pd.read_csv(FIXTURES / "sample_mf_pl.csv", header=None)
    long = parse_mf_pl_file(raw)
    s1 = upsert_gl_facts(session, long, source_file="mf.csv")
    assert s1.inserted == len(long)
    s2 = upsert_gl_facts(session, long, source_file="mf.csv")
    assert s2.inserted == 0 and s2.updated == len(long)
    assert session.query(GLOverheadFact).count() == len(long)
    # all new accounts land in the unclassified queue
    assert "地代家賃" in unclassified_accounts(session)


# ------------------------------------------------------------- misc importers


def test_project_actuals_autocreate_and_idempotent(session):
    df = pd.DataFrame([
        {"project_code": "herb", "year_month": "2026-05", "revenue": 7260000, "outsourcing_cost": 1500000},
        {"project_code": "turkey", "year_month": "2026-05", "revenue": 14255000, "outsourcing_cost": 0},
    ])
    s1 = upsert_project_actuals(session, df)
    assert s1.inserted == 2
    assert session.query(Project).count() == 2
    s2 = upsert_project_actuals(session, df)
    assert s2.updated == 2
    assert session.query(ProjectMonthActual).count() == 2


def test_default_projects_by_name(session):
    session.add(Employee(employee_code="0201", name="丁 毅"))
    session.commit()
    df = pd.DataFrame([
        {"employee_name": "丁毅", "project_code": "T社外"},   # spaces ignored
        {"employee_name": "不明 太郎", "project_code": "X"},  # unknown -> warning
    ])
    s = upsert_default_projects(session, df, "2026-05")
    assert s.inserted == 1
    assert s.skipped == 1
    assert any("特定できません" in w for w in s.warnings)
