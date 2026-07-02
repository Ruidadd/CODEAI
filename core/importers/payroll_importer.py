"""給与データ（支給控除一覧表）取込。

実際の給与システム出力（支給控除一覧表(部門別)）の項目名を既定マッピング
とする。CSV は「1行=1従業員×1月」の形を想定（PDF帳票をCSV出力したもの、
または給与システムの明細CSV）。

会社負担社会保険は帳票に含まれないため、insurance_rates の料率で推算する。
"""
from __future__ import annotations

from dataclasses import dataclass, field

import pandas as pd

from core.importers.column_mapper import apply_mapping, clean_number, suggest_mapping
from core.models import (
    DepartmentMapping,
    Division,
    Employee,
    EmployeeMonthCost,
    HousingLease,
    InsuranceRate,
)

# 内部フィールド -> 給与帳票上の項目名（別名）
PAYROLL_FIELDS: dict[str, list[str]] = {
    "employee_code": ["従業員番号", "社員番号", "社員コード"],
    "employee_name": ["従業員", "氏名", "従業員名"],
    "department": ["部門", "所属", "所属部門"],
    "actual_work_hours": ["総労働時間", "総労働時間（平日）", "労働時間"],
    "gross_pay": ["支給合計", "総支給額", "支給額合計"],
    "employee_social_insurance": ["社会保険料合計", "社会保険料"],
    "housing_deduction": ["社宅入居費(控除)", "社宅入居費", "社宅控除"],
    "year_month": ["対象年月", "支給年月", "年月"],
}
REQUIRED_FIELDS = ["employee_code", "employee_name", "gross_pay"]


@dataclass
class ImportSummary:
    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    warnings: list[str] = field(default_factory=list)


def default_payroll_mapping(source_columns: list[str]) -> dict[str, str]:
    return suggest_mapping(source_columns, PAYROLL_FIELDS)


def parse_payroll_file(df: pd.DataFrame, mapping: dict[str, str],
                       year_month: str | None = None) -> pd.DataFrame:
    """列マッピングを適用し、数値列をクリーニングした DataFrame を返す。"""
    out = apply_mapping(df, mapping, REQUIRED_FIELDS)
    for c in ["gross_pay", "employee_social_insurance", "housing_deduction"]:
        if c in out.columns:
            out[c] = out[c].map(clean_number)
        else:
            out[c] = 0.0
    if "actual_work_hours" in out.columns:
        out["actual_work_hours"] = out["actual_work_hours"].map(clean_number)
    else:
        out["actual_work_hours"] = 0.0
    if "year_month" not in out.columns:
        if not year_month:
            raise ValueError("year_month 列が無い場合は取込画面で対象年月を指定してください")
        out["year_month"] = year_month
    out["employee_code"] = out["employee_code"].astype(str).str.strip()
    out = out[out["employee_code"].str.len() > 0]
    out = out[out["gross_pay"] != 0]  # 合計行・空行を除外
    return out.reset_index(drop=True)


def employer_si_rate(session, year_month: str) -> float:
    """適用中の会社負担料率の合計を返す（無ければ 0.155 ≒ 現行Excelの15.5%）。"""
    rates = (session.query(InsuranceRate)
             .filter(InsuranceRate.effective_from <= year_month).all())
    latest: dict[str, tuple[str, float]] = {}
    for r in rates:
        cur = latest.get(r.rate_name)
        if cur is None or r.effective_from > cur[0]:
            latest[r.rate_name] = (r.effective_from, r.rate)
    if not latest:
        return 0.155
    return sum(v for _, v in latest.values())


def housing_net_cost(session, employee_id: int, year_month: str) -> float:
    """社宅台帳から当月の会社純負担（家賃-本人負担）を求める。"""
    first_day = f"{year_month}-01"
    total = 0.0
    for lease in session.query(HousingLease).filter_by(employee_id=employee_id):
        move_in = lease.move_in.strftime("%Y-%m")
        move_out = lease.move_out.strftime("%Y-%m") if lease.move_out else "9999-12"
        if move_in <= year_month <= move_out:
            total += float(lease.monthly_rent) - float(lease.employee_share)
    return total


def upsert_employee_month_costs(session, df: pd.DataFrame,
                                source_file: str = "") -> ImportSummary:
    """(employee, year_month) キーで冪等 upsert。従業員は無ければ自動作成。"""
    summary = ImportSummary()
    dept_map = {m.source_department_name: m.division_id
                for m in session.query(DepartmentMapping).all()}
    divisions = {d.name: d.id for d in session.query(Division).all()}

    for _, row in df.iterrows():
        code = str(row["employee_code"]).strip()
        emp = session.query(Employee).filter_by(employee_code=code).first()
        if emp is None:
            emp = Employee(employee_code=code, name=str(row.get("employee_name", code)))
            session.add(emp)
            session.flush()
            summary.warnings.append(f"従業員を新規作成: {code} {emp.name}")

        dept_raw = str(row.get("department", "") or "").strip()
        division_id = dept_map.get(dept_raw) or divisions.get(dept_raw)
        if dept_raw and division_id is None:
            summary.warnings.append(f"部門未マッピング: '{dept_raw}' ({emp.name})")

        ym = str(row["year_month"])
        rate = employer_si_rate(session, ym)
        employer_si = float(row["gross_pay"]) * rate
        housing = housing_net_cost(session, emp.id, ym)

        rec = (session.query(EmployeeMonthCost)
               .filter_by(employee_id=emp.id, year_month=ym).first())
        if rec is None:
            rec = EmployeeMonthCost(employee_id=emp.id, year_month=ym)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        rec.division_id = division_id
        rec.gross_pay = float(row["gross_pay"])
        rec.employee_social_insurance = float(row.get("employee_social_insurance", 0) or 0)
        rec.employer_social_insurance = employer_si
        rec.housing_cost = housing
        rec.actual_work_hours = float(row.get("actual_work_hours", 0) or 0)
        rec.source_file = source_file
    session.commit()
    return summary
