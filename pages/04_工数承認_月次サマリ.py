"""工数の月次サマリ・承認。記入率（vs 給与実績時間）を可視化する。"""
import streamlit as st

st.set_page_config(page_title="工数承認", page_icon="✅", layout="wide")

import pandas as pd
from sqlalchemy import select

from core.models import Employee, EmployeeMonthCost, Project, TimesheetEntry
from core.ui import bootstrap, month_options

session = bootstrap()

st.title("✅ 工数承認・月次サマリ")

months = month_options(session)
if not months:
    st.info("データがありません。")
    st.stop()
ym = st.selectbox("対象年月", months)

ts = pd.read_sql(select(TimesheetEntry), session.get_bind())
if ts.empty:
    st.info("工数データがありません。")
    st.stop()
ts["year_month"] = pd.to_datetime(ts["work_date"]).dt.strftime("%Y-%m")
ts = ts[ts["year_month"] == ym]

emp = pd.read_sql(select(Employee.id.label("employee_id"), Employee.employee_code,
                         Employee.name.label("employee_name")), session.get_bind())
prj = pd.read_sql(select(Project.id.label("project_id"), Project.project_code),
                  session.get_bind())
emc = pd.read_sql(select(EmployeeMonthCost), session.get_bind())
emc = emc[emc["year_month"] == ym][["employee_id", "actual_work_hours"]]

if ts.empty:
    st.warning(f"{ym} の工数記入はありません。")
else:
    pivot = (ts.merge(emp, on="employee_id").merge(prj, on="project_id")
             .pivot_table(index=["employee_code", "employee_name"], columns="project_code",
                          values="hours", aggfunc="sum", fill_value=0.0))
    pivot["記入合計"] = pivot.sum(axis=1)
    pivot = pivot.reset_index().merge(
        emp.merge(emc, on="employee_id", how="left")[["employee_code", "actual_work_hours"]],
        on="employee_code", how="left")
    pivot["給与実績時間"] = pivot["actual_work_hours"].fillna(0)
    pivot["記入率"] = (pivot["記入合計"] / pivot["給与実績時間"].replace(0, pd.NA)).astype(float)
    pivot = pivot.drop(columns=["actual_work_hours"])

    st.subheader("従業員×プロジェクト 工数マトリクス")
    st.dataframe(
        pivot.style.format({c: "{:.1f}" for c in pivot.select_dtypes("number").columns}
                           | {"記入率": "{:.0%}"}),
        use_container_width=True)

    low = pivot[pivot["記入率"].fillna(0) < 0.8]
    if not low.empty:
        st.warning("記入率が80%未満の従業員がいます（未記入分は配賦されず「未配賦人件費」になります）: "
                   + ", ".join(low["employee_name"].tolist()))

    st.subheader("承認")
    pending = ts[ts["status"] != "approved"]
    st.caption(f"未承認レコード: {len(pending)} 件")
    approver = st.text_input("承認者名", value="")
    if st.button("この月の全工数を承認する", type="primary", disabled=not approver):
        from datetime import datetime
        n = 0
        for t in (session.query(TimesheetEntry).all()):
            if t.work_date.strftime("%Y-%m") == ym and t.status != "approved":
                t.status = "approved"
                t.approved_by = approver
                t.approved_at = datetime.utcnow()
                n += 1
        session.commit()
        st.success(f"{n} 件を承認しました")
        st.rerun()

# 記入が全く無い従業員（給与はあるのに）を表示
if not emc.empty:
    logged_ids = set(ts["employee_id"].unique()) if not ts.empty else set()
    paid = emp.merge(emc, on="employee_id")
    missing = paid[~paid["employee_id"].isin(logged_ids)]
    if not missing.empty:
        st.info("当月給与はあるが工数記入ゼロの従業員（デフォルト配分 or 未配賦扱い）: "
                + ", ".join(missing["employee_name"].tolist()))
