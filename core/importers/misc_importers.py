"""その他の取込：プロジェクト実績/予算・社宅台帳・BSE管理表・現行Excel実績。"""
from __future__ import annotations

from datetime import date, datetime

import pandas as pd

from core.importers.column_mapper import clean_number
from core.importers.payroll_importer import ImportSummary
from core.models import (
    Division,
    Employee,
    EmployeeDefaultProject,
    HousingLease,
    LegacyActual,
    Project,
    ProjectBudget,
    ProjectMonthActual,
)


def _get_or_create_project(session, code: str, division_id: int | None = None,
                           summary: ImportSummary | None = None) -> Project:
    prj = session.query(Project).filter_by(project_code=code).first()
    if prj is None:
        if division_id is None:
            division_id = session.query(Division).first().id
        prj = Project(project_code=code, name=code, division_id=division_id)
        session.add(prj)
        session.flush()
        if summary is not None:
            summary.warnings.append(f"プロジェクトを新規作成: {code}（マスタ管理で事業部を確認してください）")
    return prj


def upsert_project_actuals(session, df: pd.DataFrame, source_file: str = "") -> ImportSummary:
    """columns: project_code, year_month, revenue, outsourcing_cost"""
    summary = ImportSummary()
    for _, row in df.iterrows():
        prj = _get_or_create_project(session, str(row["project_code"]).strip(), summary=summary)
        ym = str(row["year_month"])
        rec = (session.query(ProjectMonthActual)
               .filter_by(project_id=prj.id, year_month=ym).first())
        if rec is None:
            rec = ProjectMonthActual(project_id=prj.id, year_month=ym)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        rec.revenue = clean_number(row.get("revenue"))
        rec.outsourcing_cost = clean_number(row.get("outsourcing_cost"))
        rec.source_file = source_file
    session.commit()
    return summary


def upsert_project_budgets(session, df: pd.DataFrame, source_file: str = "") -> ImportSummary:
    """columns: project_code, year_month, revenue_budget, outsourcing_budget,
    labor_budget, overhead_budget"""
    summary = ImportSummary()
    for _, row in df.iterrows():
        prj = _get_or_create_project(session, str(row["project_code"]).strip(), summary=summary)
        ym = str(row["year_month"])
        rec = (session.query(ProjectBudget)
               .filter_by(project_id=prj.id, year_month=ym).first())
        if rec is None:
            rec = ProjectBudget(project_id=prj.id, year_month=ym)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        for col in ["revenue_budget", "outsourcing_budget", "labor_budget", "overhead_budget"]:
            setattr(rec, col, clean_number(row.get(col)))
        rec.source_file = source_file
    session.commit()
    return summary


def _to_date(v) -> date | None:
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() in ("", "nan", "None"):
        return None
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    return pd.to_datetime(str(v)).date()


def upsert_housing_leases(session, df: pd.DataFrame) -> ImportSummary:
    """社宅台帳: columns: employee_code, move_in, move_out, monthly_rent, employee_share"""
    summary = ImportSummary()
    for _, row in df.iterrows():
        code = str(row["employee_code"]).strip()
        emp = session.query(Employee).filter_by(employee_code=code).first()
        if emp is None:
            summary.warnings.append(f"従業員が見つかりません: {code}（先に給与データを取込むか従業員を登録）")
            summary.skipped += 1
            continue
        move_in = _to_date(row["move_in"])
        rec = (session.query(HousingLease)
               .filter_by(employee_id=emp.id, move_in=move_in).first())
        if rec is None:
            rec = HousingLease(employee_id=emp.id, move_in=move_in,
                               monthly_rent=0, employee_share=0)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        rec.move_out = _to_date(row.get("move_out"))
        rec.monthly_rent = clean_number(row.get("monthly_rent"))
        rec.employee_share = clean_number(row.get("employee_share"))
        rec.note = str(row.get("note") or "") or None
    session.commit()
    return summary


def upsert_default_projects(session, df: pd.DataFrame, year_month: str,
                            source: str = "BSE管理表") -> ImportSummary:
    """BSE管理表「氏名×投入project」→ デフォルト配分。

    columns: employee_name(または employee_code), project_code
    同名従業員は名前一致（空白無視）で解決する。
    """
    summary = ImportSummary()
    employees = session.query(Employee).all()
    by_code = {e.employee_code: e for e in employees}
    by_name = {e.name.replace(" ", "").replace("　", ""): e for e in employees}

    for _, row in df.iterrows():
        emp = None
        if "employee_code" in row and pd.notna(row.get("employee_code")):
            emp = by_code.get(str(row["employee_code"]).strip())
        if emp is None and "employee_name" in row and pd.notna(row.get("employee_name")):
            key = str(row["employee_name"]).replace(" ", "").replace("　", "")
            emp = by_name.get(key)
        if emp is None:
            summary.warnings.append(f"従業員を特定できません: {row.to_dict()}")
            summary.skipped += 1
            continue
        code = str(row["project_code"]).strip()
        if not code or code in ("-", "nan"):
            summary.skipped += 1
            continue
        prj = _get_or_create_project(session, code, summary=summary)
        rec = (session.query(EmployeeDefaultProject)
               .filter_by(employee_id=emp.id, project_id=prj.id, year_month=year_month).first())
        if rec is None:
            rec = EmployeeDefaultProject(employee_id=emp.id, project_id=prj.id,
                                         year_month=year_month, weight=1.0, source=source)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
    session.commit()
    return summary


def upsert_legacy_actuals(session, df: pd.DataFrame, source_file: str = "") -> ImportSummary:
    """現行Excelの月次合計: columns: year_month, scope_type, division_name,
    revenue, outsourcing_cost, labor_cost, overhead_cost, operating_profit"""
    summary = ImportSummary()
    div_names = {d.name: d.id for d in session.query(Division).all()}
    for _, row in df.iterrows():
        scope = str(row.get("scope_type", "company"))
        div_id = None
        if scope == "division":
            div_id = div_names.get(str(row.get("division_name", "")).strip())
            if div_id is None:
                summary.warnings.append(f"事業部が見つかりません: {row.get('division_name')}")
                summary.skipped += 1
                continue
        ym = str(row["year_month"])
        rec = (session.query(LegacyActual)
               .filter_by(year_month=ym, scope_type=scope, division_id=div_id).first())
        if rec is None:
            rec = LegacyActual(year_month=ym, scope_type=scope, division_id=div_id)
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        for col in ["revenue", "outsourcing_cost", "labor_cost", "overhead_cost", "operating_profit"]:
            setattr(rec, col, clean_number(row.get(col)))
        rec.source_file = source_file
    session.commit()
    return summary
