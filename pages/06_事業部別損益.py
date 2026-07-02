"""事業部別・会社全体の損益（単月/累計、未配賦人件費の顕在化つき）。"""
import streamlit as st

st.set_page_config(page_title="事業部別損益", page_icon="🏢", layout="wide")

import pandas as pd

from core.reporting.report_data import (
    company_totals,
    division_pl_report,
    load_allocation_results,
    load_budgets,
    load_unallocated,
)
from core.ui import bootstrap, month_options

session = bootstrap()

st.title("🏢 事業部別・会社全体損益")

months = month_options(session)
if not months:
    st.info("データがありません。")
    st.stop()

c1, c2 = st.columns([1, 1])
ym = c1.selectbox("対象年月", months)
period = c2.radio("期間", ["単月", "累計(YTD)"], horizontal=True)
cumulative = period.startswith("累計")

results = load_allocation_results(session)
unallocated = load_unallocated(session)
if results.empty:
    st.warning("配賦結果がありません。「05 プロジェクト別損益」で配賦を実行してください。")
    st.stop()

report = division_pl_report(results, unallocated, load_budgets(session), ym, cumulative)
if report.empty:
    st.warning(f"{ym} の配賦結果がありません。")
    st.stop()

totals = company_totals(report)
k1, k2, k3, k4 = st.columns(4)
k1.metric("会社売上高", f"{totals.get('revenue', 0):,.0f} 円")
k2.metric("会社粗利(配賦後)", f"{totals.get('gross_margin', 0):,.0f} 円")
k3.metric("未配賦人件費", f"{totals.get('unallocated_cost', 0):,.0f} 円")
k4.metric("営業貢献(粗利-未配賦)", f"{totals.get('operating_margin', 0):,.0f} 円")

display_cols = {
    "division_name": "事業部", "revenue": "売上高",
    "direct_outsourcing_cost": "外注費", "allocated_labor_cost": "人件費(配賦)",
    "unallocated_cost": "未配賦人件費", "total_labor_cost": "人件費計",
    "allocated_overhead_cost": "間接費(配賦)", "gross_margin": "粗利",
    "operating_margin": "営業貢献",
}
if "revenue_budget" in report.columns:
    display_cols |= {"revenue_budget": "売上予算", "revenue_achievement": "達成率"}

table = report[list(display_cols.keys())].rename(columns=display_cols)
money_cols = [v for k, v in display_cols.items() if k not in ("division_name", "revenue_achievement")]
st.dataframe(
    table.style.format({c: "{:,.0f}" for c in money_cols} | {"達成率": "{:.1%}"}, na_rep="—"),
    use_container_width=True)

st.caption("※ 未配賦人件費 = 工数未記入・記入漏れ分（管理部門など間接人員を含む）。"
           "配賦人件費＋未配賦人件費＝給与全額（保存則）なので、隠れコストはありません。")

st.subheader("未配賦人件費の内訳")
if not unallocated.empty:
    un = unallocated[unallocated["year_month"] == ym] if not cumulative else \
        unallocated[(unallocated["year_month"].str[:4] == ym[:4]) & (unallocated["year_month"] <= ym)]
    if not un.empty:
        detail = un.groupby(["employee_name", "division_name", "reason"], as_index=False)[
            "unallocated_cost"].sum().sort_values("unallocated_cost", ascending=False)
        detail["reason"] = detail["reason"].map({"no_hours": "工数記入なし",
                                                 "partial_hours": "記入漏れ(部分)"})
        st.dataframe(detail.rename(columns={
            "employee_name": "従業員", "division_name": "事業部",
            "reason": "理由", "unallocated_cost": "金額"})
            .style.format({"金額": "{:,.0f}"}), use_container_width=True)
    else:
        st.success("未配賦はありません。")

st.subheader("事業部別 売上・粗利")
chart = report.set_index("division_name")[["revenue", "gross_margin"]]
st.bar_chart(chart)
