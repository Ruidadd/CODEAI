"""レポート用のデータ読み出し・集計（単月/累計、予実対比）。"""
from __future__ import annotations

import pandas as pd
from sqlalchemy import select

from core.models import (
    AllocationResult,
    AllocationRun,
    AllocationUnallocated,
    Division,
    Employee,
    LegacyActual,
    Project,
    ProjectBudget,
)


def _read(session, stmt) -> pd.DataFrame:
    return pd.read_sql(stmt, session.get_bind())


def load_projects(session) -> pd.DataFrame:
    prj = _read(session, select(Project.id.label("project_id"),
                                Project.project_code, Project.name.label("project_name"),
                                Project.division_id))
    div = _read(session, select(Division.id.label("division_id"),
                                Division.name.label("division_name"), Division.is_overhead))
    return prj.merge(div, on="division_id", how="left")


def load_allocation_results(session) -> pd.DataFrame:
    res = _read(session, select(AllocationResult))
    if res.empty:
        return res
    return res.merge(load_projects(session), on="project_id", how="left")


def load_unallocated(session) -> pd.DataFrame:
    un = _read(session, select(AllocationUnallocated))
    if un.empty:
        return un
    emp = _read(session, select(Employee.id.label("employee_id"), Employee.name.label("employee_name")))
    div = _read(session, select(Division.id.label("division_id"), Division.name.label("division_name")))
    return un.merge(emp, on="employee_id", how="left").merge(div, on="division_id", how="left")


def load_budgets(session) -> pd.DataFrame:
    b = _read(session, select(ProjectBudget))
    if b.empty:
        return b
    return b.merge(load_projects(session), on="project_id", how="left")


def load_runs(session) -> pd.DataFrame:
    return _read(session, select(AllocationRun))


def load_legacy(session) -> pd.DataFrame:
    leg = _read(session, select(LegacyActual))
    if leg.empty:
        return leg
    div = _read(session, select(Division.id.label("division_id"), Division.name.label("division_name")))
    # division_id が全NULL（company行のみ）だと object dtype になり merge できないため揃える
    leg["division_id"] = pd.to_numeric(leg["division_id"], errors="coerce")
    div["division_id"] = pd.to_numeric(div["division_id"], errors="coerce")
    return leg.merge(div, on="division_id", how="left")


VALUE_COLS = ["revenue", "direct_outsourcing_cost", "allocated_labor_cost",
              "allocated_overhead_cost", "total_cost", "gross_margin", "labor_from_default"]
BUDGET_COLS = ["revenue_budget", "outsourcing_budget", "labor_budget", "overhead_budget"]


def filter_period(df: pd.DataFrame, year_month: str, cumulative: bool) -> pd.DataFrame:
    """単月 or 年初からの累計（同一年の <= year_month）で絞る。"""
    if df.empty:
        return df
    if cumulative:
        year = year_month[:4]
        return df[(df["year_month"].str[:4] == year) & (df["year_month"] <= year_month)]
    return df[df["year_month"] == year_month]


def project_pl_report(results: pd.DataFrame, budgets: pd.DataFrame,
                      year_month: str, cumulative: bool) -> pd.DataFrame:
    """プロジェクト別 実績×予算の対比表。"""
    if results.empty:
        return pd.DataFrame()
    act = filter_period(results, year_month, cumulative)
    if act.empty:
        return pd.DataFrame()
    grouped = act.groupby(["project_id", "project_code", "project_name", "division_name"],
                          as_index=False)[VALUE_COLS].sum()
    grouped["gross_margin_pct"] = grouped.apply(
        lambda r: r["gross_margin"] / r["revenue"] if r["revenue"] else None, axis=1)

    if not budgets.empty:
        bud = filter_period(budgets, year_month, cumulative)
        bud_g = bud.groupby("project_id", as_index=False)[BUDGET_COLS].sum()
        bud_g["total_cost_budget"] = (bud_g["outsourcing_budget"] + bud_g["labor_budget"]
                                      + bud_g["overhead_budget"])
        bud_g["gross_margin_budget"] = bud_g["revenue_budget"] - bud_g["total_cost_budget"]
        grouped = grouped.merge(bud_g, on="project_id", how="left")
        for c in BUDGET_COLS + ["total_cost_budget", "gross_margin_budget"]:
            grouped[c] = grouped[c].fillna(0.0)
        grouped["revenue_variance"] = grouped["revenue"] - grouped["revenue_budget"]
        grouped["revenue_achievement"] = grouped.apply(
            lambda r: r["revenue"] / r["revenue_budget"] if r["revenue_budget"] else None, axis=1)
        grouped["margin_variance"] = grouped["gross_margin"] - grouped["gross_margin_budget"]
    return grouped


def division_pl_report(results: pd.DataFrame, unallocated: pd.DataFrame,
                       budgets: pd.DataFrame, year_month: str, cumulative: bool) -> pd.DataFrame:
    """事業部別（未配賦人件費行を含む）。"""
    if results.empty:
        return pd.DataFrame()
    act = filter_period(results, year_month, cumulative)
    if act.empty:
        return pd.DataFrame()
    g = act.groupby(["division_id", "division_name"], as_index=False)[VALUE_COLS].sum()

    if not unallocated.empty:
        un = filter_period(unallocated, year_month, cumulative)
        un_g = un.groupby("division_id", as_index=False)["unallocated_cost"].sum()
        g = g.merge(un_g, on="division_id", how="outer")
        # 未配賦しかない事業部（管理部門など）の名前を補完
        names = unallocated[["division_id", "division_name"]].drop_duplicates()
        g["division_name"] = g["division_name"].fillna(
            g["division_id"].map(names.set_index("division_id")["division_name"]))
    else:
        g["unallocated_cost"] = 0.0
    for c in VALUE_COLS + ["unallocated_cost"]:
        if c in g.columns:
            g[c] = g[c].fillna(0.0)
    g["total_labor_cost"] = g["allocated_labor_cost"] + g["unallocated_cost"]
    g["operating_margin"] = g["gross_margin"] - g["unallocated_cost"]

    if not budgets.empty:
        bud = filter_period(budgets, year_month, cumulative)
        bud_g = bud.groupby("division_id", as_index=False)[BUDGET_COLS].sum()
        g = g.merge(bud_g, on="division_id", how="left")
        for c in BUDGET_COLS:
            g[c] = g[c].fillna(0.0)
        g["revenue_achievement"] = g.apply(
            lambda r: r["revenue"] / r["revenue_budget"] if r.get("revenue_budget") else None, axis=1)
    return g


def company_totals(division_report: pd.DataFrame) -> pd.Series:
    if division_report.empty:
        return pd.Series(dtype=float)
    return division_report.select_dtypes("number").drop(columns=["division_id"], errors="ignore").sum()


def reconciliation_report(results: pd.DataFrame, unallocated: pd.DataFrame,
                          legacy: pd.DataFrame, year_month: str) -> pd.DataFrame:
    """新システム vs 現行Excel の会社合計突合（単月）。"""
    if legacy.empty:
        return pd.DataFrame()
    leg = legacy[(legacy["year_month"] == year_month) & (legacy["scope_type"] == "company")]
    if leg.empty:
        return pd.DataFrame()
    act = results[results["year_month"] == year_month] if not results.empty else pd.DataFrame()
    un = unallocated[unallocated["year_month"] == year_month] if not unallocated.empty else pd.DataFrame()

    new_vals = {
        "売上高": act["revenue"].sum() if not act.empty else 0.0,
        "外注費": act["direct_outsourcing_cost"].sum() if not act.empty else 0.0,
        "人件費(配賦+未配賦)": (act["allocated_labor_cost"].sum() if not act.empty else 0.0)
                          + (un["unallocated_cost"].sum() if not un.empty else 0.0),
        "間接費(配賦)": act["allocated_overhead_cost"].sum() if not act.empty else 0.0,
    }
    old = leg.iloc[0]
    old_vals = {
        "売上高": float(old["revenue"]),
        "外注費": float(old["outsourcing_cost"]),
        "人件費(配賦+未配賦)": float(old["labor_cost"]),
        "間接費(配賦)": float(old["overhead_cost"]),
    }
    rows = []
    for k in new_vals:
        n, o = new_vals[k], old_vals[k]
        rows.append({"科目": k, "新システム": n, "現行Excel": o, "差異": n - o,
                     "差異率": (n - o) / o if o else None})
    return pd.DataFrame(rows)
