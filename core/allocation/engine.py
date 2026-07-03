"""原価配賦エンジン。

純粋な pandas 関数群（DataFrame in / DataFrame out）。DB に触るのは
run_allocation() のみ。単位はすべて円、year_month は 'YYYY-MM'。

配賦ロジックの要点
------------------
1. 全負荷人件費 = 支給合計 + 会社負担社会保険(料率推算) + 社宅純コスト
2. 人件費配賦は「給与実績の総労働時間」を分母にする。工数の記入漏れは
   既存プロジェクトの単価を歪めず「未配賦」として顕在化する。
3. 工数ゼロの従業員はデフォルト配分（BSE管理表由来）でフォールバックし、
   それも無ければ未配賦へ。何も黙って捨てない。
4. 間接費プールは事業部タグ付き分→当該事業部のプロジェクトへ、
   全社分→全プロジェクトへ、選択ドライバの重みで配賦する。
   配賦後合計 == プール合計（保存則）を常に満たす。
"""
from __future__ import annotations

import pandas as pd

from core.allocation.drivers import DRIVERS

LABOR_COLS = ["gross_pay", "employer_social_insurance", "housing_cost"]


# ---------------------------------------------------------------- labor side


def compute_employee_fully_loaded_cost(employee_month_costs: pd.DataFrame) -> pd.DataFrame:
    """total_loaded_cost = 支給合計 + 会社負担社保 + 社宅純コスト を付加する。"""
    df = employee_month_costs.copy()
    for c in LABOR_COLS:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0.0).astype(float)
    df["total_loaded_cost"] = df[LABOR_COLS].sum(axis=1)
    return df


def compute_labor_allocation(
    employee_month_costs: pd.DataFrame,
    timesheets: pd.DataFrame,
    default_projects: pd.DataFrame,
    year_month: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """人件費を従業員×プロジェクトに配賦する。

    Parameters
    ----------
    employee_month_costs : compute_employee_fully_loaded_cost 済み。
        columns: employee_id, division_id, year_month, total_loaded_cost,
                 actual_work_hours
    timesheets : columns: employee_id, project_id, work_date(or year_month), hours
    default_projects : columns: employee_id, project_id, year_month, weight

    Returns
    -------
    (allocated_df, unallocated_df)
    allocated_df : employee_id, project_id, allocated_hours, allocation_pct,
                   allocated_labor_cost, from_default(bool)
    unallocated_df : employee_id, division_id, unallocated_cost, reason
    """
    emc = employee_month_costs[employee_month_costs["year_month"] == year_month].copy()
    if emc.empty:
        empty_alloc = pd.DataFrame(
            columns=["employee_id", "project_id", "allocated_hours", "allocation_pct",
                     "allocated_labor_cost", "from_default"])
        empty_unalloc = pd.DataFrame(
            columns=["employee_id", "division_id", "unallocated_cost", "reason"])
        return empty_alloc, empty_unalloc

    ts = timesheets.copy()
    if not ts.empty:
        if "year_month" not in ts.columns:
            ts["year_month"] = pd.to_datetime(ts["work_date"]).dt.strftime("%Y-%m")
        ts = ts[ts["year_month"] == year_month]
        ts = ts.groupby(["employee_id", "project_id"], as_index=False)["hours"].sum()
    else:
        ts = pd.DataFrame(columns=["employee_id", "project_id", "hours"])

    dp = default_projects.copy()
    if not dp.empty:
        dp = dp[dp["year_month"] == year_month]

    allocated_rows: list[dict] = []
    unallocated_rows: list[dict] = []

    for _, emp in emc.iterrows():
        eid = emp["employee_id"]
        cost = float(emp["total_loaded_cost"])
        paid_hours = float(emp.get("actual_work_hours") or 0)
        emp_ts = ts[ts["employee_id"] == eid]
        logged = float(emp_ts["hours"].sum()) if not emp_ts.empty else 0.0

        if logged > 0:
            # 分母は給与実績の総労働時間。ただし記入合計が上回る場合は記入合計
            # を分母にして配賦率が 100% を超えないようにする。
            denom = max(paid_hours, logged)
            for _, row in emp_ts.iterrows():
                pct = float(row["hours"]) / denom
                allocated_rows.append({
                    "employee_id": eid,
                    "project_id": row["project_id"],
                    "allocated_hours": float(row["hours"]),
                    "allocation_pct": pct,
                    "allocated_labor_cost": cost * pct,
                    "from_default": False,
                })
            remainder = cost * (1 - logged / denom)
            if remainder > 1e-9:
                unallocated_rows.append({
                    "employee_id": eid,
                    "division_id": emp.get("division_id"),
                    "unallocated_cost": remainder,
                    "reason": "partial_hours",
                })
        else:
            emp_dp = dp[dp["employee_id"] == eid] if not dp.empty else pd.DataFrame()
            if not emp_dp.empty and emp_dp["weight"].sum() > 0:
                wsum = float(emp_dp["weight"].sum())
                for _, row in emp_dp.iterrows():
                    pct = float(row["weight"]) / wsum
                    allocated_rows.append({
                        "employee_id": eid,
                        "project_id": row["project_id"],
                        "allocated_hours": 0.0,
                        "allocation_pct": pct,
                        "allocated_labor_cost": cost * pct,
                        "from_default": True,
                    })
            else:
                unallocated_rows.append({
                    "employee_id": eid,
                    "division_id": emp.get("division_id"),
                    "unallocated_cost": cost,
                    "reason": "no_hours",
                })

    allocated_df = pd.DataFrame(allocated_rows, columns=[
        "employee_id", "project_id", "allocated_hours", "allocation_pct",
        "allocated_labor_cost", "from_default"])
    unallocated_df = pd.DataFrame(unallocated_rows, columns=[
        "employee_id", "division_id", "unallocated_cost", "reason"])
    return allocated_df, unallocated_df


def aggregate_labor_by_project(allocated_df: pd.DataFrame) -> pd.DataFrame:
    """従業員×プロジェクト明細 → プロジェクト単位に集計。"""
    if allocated_df.empty:
        return pd.DataFrame(columns=["project_id", "allocated_labor_cost",
                                     "allocated_hours", "labor_from_default"])
    df = allocated_df.copy()
    df["labor_from_default"] = df["allocated_labor_cost"].where(df["from_default"], 0.0)
    out = df.groupby("project_id", as_index=False).agg(
        allocated_labor_cost=("allocated_labor_cost", "sum"),
        allocated_hours=("allocated_hours", "sum"),
        labor_from_default=("labor_from_default", "sum"),
    )
    return out


# -------------------------------------------------------------- overhead side


def compute_overhead_pool(
    gl_facts: pd.DataFrame, account_mapping: pd.DataFrame, year_month: str
) -> pd.DataFrame:
    """internal_category == 'overhead' の科目だけを抽出したプール。

    Returns columns: account_name, department_division_id (NaN=全社), amount
    """
    gl = gl_facts[gl_facts["year_month"] == year_month].copy()
    if gl.empty:
        return pd.DataFrame(columns=["account_name", "department_division_id", "amount"])
    am = account_mapping[["account_name", "internal_category"]]
    gl = gl.merge(am, on="account_name", how="left")
    pool = gl[gl["internal_category"] == "overhead"].copy()
    if "department_division_id" not in pool.columns:
        pool["department_division_id"] = pd.NA
    return pool[["account_name", "department_division_id", "amount"]]


def allocate_overhead_to_projects(
    overhead_pool: pd.DataFrame,
    projects: pd.DataFrame,
    labor_by_project: pd.DataFrame,
    project_actuals: pd.DataFrame,
    driver: str,
    year_month: str,
) -> pd.DataFrame:
    """間接費プールをプロジェクトへ配賦する。

    projects : columns project_id, division_id
    labor_by_project : aggregate_labor_by_project の出力
    project_actuals : columns project_id, year_month, revenue, outsourcing_cost

    Returns: project_id, allocated_overhead_cost
    保存則: 出力合計 == プール合計（対象プロジェクトが1件も無い事業部プール
    は全社扱いに繰上げて必ず配る）。
    """
    if overhead_pool.empty:
        return pd.DataFrame(columns=["project_id", "allocated_overhead_cost"])

    pa = project_actuals[project_actuals["year_month"] == year_month] if not project_actuals.empty \
        else pd.DataFrame(columns=["project_id", "revenue", "outsourcing_cost"])

    base = projects[["project_id", "division_id"]].copy()
    base = base.merge(labor_by_project, on="project_id", how="left")
    base = base.merge(pa[["project_id", "revenue"]] if "revenue" in pa.columns else pa,
                      on="project_id", how="left")
    for c in ["allocated_labor_cost", "allocated_hours", "revenue"]:
        if c not in base.columns:
            base[c] = 0.0
        base[c] = base[c].fillna(0.0).astype(float)

    # 当月に何らかの活動があるプロジェクトのみ配賦対象にする
    active = base[(base["allocated_labor_cost"] > 0) | (base["allocated_hours"] > 0)
                  | (base["revenue"] > 0)].copy()
    if active.empty:
        active = base.copy()  # 全く活動が無ければ全プロジェクト均等割り

    driver_fn = DRIVERS[driver]
    result: dict[int, float] = {pid: 0.0 for pid in base["project_id"]}

    # 事業部タグ付きプールと全社プールに分けて配る
    pool = overhead_pool.copy()
    pool["department_division_id"] = pool["department_division_id"].astype("Float64")
    grouped = pool.groupby("department_division_id", dropna=False)["amount"].sum()

    for div_id, amount in grouped.items():
        if pd.isna(div_id):
            targets = active
        else:
            targets = active[active["division_id"] == int(div_id)]
            if targets.empty:
                targets = active  # 対象なし→全社扱いに繰上げ（金額を落とさない）
        weights = driver_fn(targets)
        total_w = float(weights.sum())
        if total_w <= 0:
            weights = pd.Series(1.0, index=targets["project_id"])  # 均等割り
            total_w = float(weights.sum())
        for pid, w in weights.items():
            result[pid] = result.get(pid, 0.0) + float(amount) * float(w) / total_w

    out = pd.DataFrame({"project_id": list(result.keys()),
                        "allocated_overhead_cost": list(result.values())})
    return out[out["allocated_overhead_cost"] != 0].reset_index(drop=True)


# ----------------------------------------------------------------- P&L rollup


def compute_project_month_pl(
    project_actuals: pd.DataFrame,
    labor_by_project: pd.DataFrame,
    overhead_by_project: pd.DataFrame,
    year_month: str,
) -> pd.DataFrame:
    """プロジェクト×月の全成本損益。allocation_results と同じ列構成。"""
    pa = project_actuals[project_actuals["year_month"] == year_month].copy() \
        if not project_actuals.empty else pd.DataFrame(columns=["project_id", "revenue", "outsourcing_cost"])
    pa = pa.rename(columns={"outsourcing_cost": "direct_outsourcing_cost"})
    keep = [c for c in ["project_id", "revenue", "direct_outsourcing_cost"] if c in pa.columns]
    pa = pa[keep]

    df = pa.merge(labor_by_project, on="project_id", how="outer")
    df = df.merge(overhead_by_project, on="project_id", how="outer")
    for c in ["revenue", "direct_outsourcing_cost", "allocated_labor_cost",
              "allocated_overhead_cost", "labor_from_default"]:
        if c not in df.columns:
            df[c] = 0.0
        df[c] = df[c].fillna(0.0).astype(float)

    df["total_cost"] = (df["direct_outsourcing_cost"] + df["allocated_labor_cost"]
                        + df["allocated_overhead_cost"])
    df["gross_margin"] = df["revenue"] - df["total_cost"]
    df["gross_margin_pct"] = df.apply(
        lambda r: r["gross_margin"] / r["revenue"] if r["revenue"] else None, axis=1)
    df["year_month"] = year_month
    cols = ["project_id", "year_month", "revenue", "direct_outsourcing_cost",
            "allocated_labor_cost", "allocated_overhead_cost", "total_cost",
            "gross_margin", "gross_margin_pct", "labor_from_default"]
    return df[cols].sort_values("project_id").reset_index(drop=True)


def rollup_division_month_pl(
    project_pl: pd.DataFrame, unallocated_labor: pd.DataFrame, projects: pd.DataFrame
) -> pd.DataFrame:
    """事業部単位に集計し、未配賦人件費を加えて実額と突合可能にする。"""
    if project_pl.empty:
        div = pd.DataFrame(columns=["division_id", "revenue", "direct_outsourcing_cost",
                                    "allocated_labor_cost", "allocated_overhead_cost",
                                    "gross_margin"])
    else:
        merged = project_pl.merge(projects[["project_id", "division_id"]],
                                  on="project_id", how="left")
        div = merged.groupby("division_id", as_index=False)[
            ["revenue", "direct_outsourcing_cost", "allocated_labor_cost",
             "allocated_overhead_cost", "gross_margin"]].sum()

    if not unallocated_labor.empty:
        un = unallocated_labor.groupby("division_id", as_index=False)["unallocated_cost"].sum()
        div = div.merge(un, on="division_id", how="outer")
    else:
        div["unallocated_cost"] = 0.0
    for c in ["revenue", "direct_outsourcing_cost", "allocated_labor_cost",
              "allocated_overhead_cost", "gross_margin", "unallocated_cost"]:
        if c not in div.columns:
            div[c] = 0.0
        div[c] = div[c].fillna(0.0).astype(float)
    div["total_labor_cost"] = div["allocated_labor_cost"] + div["unallocated_cost"]
    div["operating_margin"] = div["gross_margin"] - div["unallocated_cost"]
    return div.reset_index(drop=True)


def rollup_company_month_pl(division_pl: pd.DataFrame) -> pd.DataFrame:
    if division_pl.empty:
        return pd.DataFrame()
    num_cols = division_pl.select_dtypes("number").columns.drop("division_id", errors="ignore")
    total = division_pl[num_cols].sum().to_frame().T
    total.insert(0, "scope", "company")
    return total


# ------------------------------------------------------------- orchestration


def run_allocation(session, year_month: str, driver: str = "labor_cost") -> pd.DataFrame:
    """DB から入力を読み、配賦を実行し、結果を保存して project P&L を返す。"""
    from sqlalchemy import delete, select

    from core.models import (
        AllocationResult,
        AllocationRun,
        AllocationUnallocated,
        AccountMapping,
        EmployeeDefaultProject,
        EmployeeMonthCost,
        GLOverheadFact,
        Project,
        ProjectMonthActual,
        TimesheetEntry,
    )

    def read(stmt):
        return pd.read_sql(stmt, session.get_bind())

    emc = read(select(EmployeeMonthCost))
    ts = read(select(TimesheetEntry))
    dp = read(select(EmployeeDefaultProject))
    pa = read(select(ProjectMonthActual))
    gl = read(select(GLOverheadFact))
    am = read(select(AccountMapping))
    prj = read(select(Project.id.label("project_id"), Project.division_id))

    emc = compute_employee_fully_loaded_cost(emc)
    allocated, unallocated = compute_labor_allocation(emc, ts, dp, year_month)
    labor_by_project = aggregate_labor_by_project(allocated)
    pool = compute_overhead_pool(gl, am, year_month)
    overhead = allocate_overhead_to_projects(pool, prj, labor_by_project, pa, driver, year_month)
    project_pl = compute_project_month_pl(pa, labor_by_project, overhead, year_month)

    # 同月の旧 run を削除して置き換え（run 履歴は残さず常に最新のみ保持）
    old_runs = session.execute(
        select(AllocationRun.id).where(AllocationRun.year_month == year_month)).scalars().all()
    if old_runs:
        session.execute(delete(AllocationResult).where(AllocationResult.allocation_run_id.in_(old_runs)))
        session.execute(delete(AllocationUnallocated).where(AllocationUnallocated.allocation_run_id.in_(old_runs)))
        session.execute(delete(AllocationRun).where(AllocationRun.id.in_(old_runs)))

    run = AllocationRun(year_month=year_month, driver=driver)
    session.add(run)
    session.flush()
    for _, r in project_pl.iterrows():
        session.add(AllocationResult(
            allocation_run_id=run.id, project_id=int(r["project_id"]), year_month=year_month,
            revenue=r["revenue"], direct_outsourcing_cost=r["direct_outsourcing_cost"],
            allocated_labor_cost=r["allocated_labor_cost"],
            allocated_overhead_cost=r["allocated_overhead_cost"],
            total_cost=r["total_cost"], gross_margin=r["gross_margin"],
            gross_margin_pct=r["gross_margin_pct"] if pd.notna(r["gross_margin_pct"]) else None,
            labor_from_default=r["labor_from_default"],
        ))
    for _, r in unallocated.iterrows():
        session.add(AllocationUnallocated(
            allocation_run_id=run.id, employee_id=int(r["employee_id"]),
            division_id=int(r["division_id"]) if pd.notna(r["division_id"]) else None,
            year_month=year_month, unallocated_cost=r["unallocated_cost"], reason=r["reason"],
        ))
    session.commit()
    return project_pl
