"""プロジェクト別損益：配賦実行、単月/累計、予実対比。"""
import streamlit as st

st.set_page_config(page_title="プロジェクト別損益", page_icon="💹", layout="wide")

import pandas as pd

from core.allocation.drivers import DRIVER_LABELS
from core.allocation.engine import run_allocation
from core.reporting.report_data import (
    load_allocation_results,
    load_budgets,
    load_runs,
    project_pl_report,
)
from core.ui import bootstrap, month_options

session = bootstrap()

st.title("💹 プロジェクト別損益（全負荷原価）")

months = month_options(session)
if not months:
    st.info("データがありません。先にデータを取込むかデモデータを投入してください。")
    st.stop()

c1, c2, c3, c4 = st.columns([1, 1, 1, 2])
ym = c1.selectbox("対象年月", months)
period = c2.radio("期間", ["単月", "累計(YTD)"], horizontal=True)
driver = c3.selectbox("間接費配賦ドライバ", list(DRIVER_LABELS.keys()),
                      format_func=lambda k: DRIVER_LABELS[k])

runs = load_runs(session)
run_info = runs[runs["year_month"] == ym] if not runs.empty else pd.DataFrame()
with c4:
    st.write("")
    if st.button(f"▶ {ym} の配賦を実行", type="primary"):
        with st.spinner("配賦計算中..."):
            run_allocation(session, ym, driver)
        st.success("配賦完了")
        st.rerun()
    if not run_info.empty:
        r = run_info.iloc[-1]
        st.caption(f"最終実行: {r['run_at']}（ドライバ: {DRIVER_LABELS.get(r['driver'], r['driver'])}）")

results = load_allocation_results(session)
if results.empty:
    st.warning("配賦結果がまだありません。上のボタンで配賦を実行してください。")
    st.stop()

cumulative = period.startswith("累計")
if cumulative:
    # 累計は対象年月までの各月の配賦結果が必要。未実行の月を知らせる。
    year = ym[:4]
    needed = [m for m in months if m[:4] == year and m <= ym]
    have = set(results["year_month"].unique())
    missing = [m for m in needed if m not in have]
    if missing:
        st.warning(f"累計に含まれない未配賦の月があります: {', '.join(sorted(missing))}（各月の配賦を実行してください）")

report = project_pl_report(results, load_budgets(session), ym, cumulative)
if report.empty:
    st.warning(f"{ym} の配賦結果がありません。")
    st.stop()

total_rev = report["revenue"].sum()
total_margin = report["gross_margin"].sum()
k1, k2, k3, k4 = st.columns(4)
k1.metric("売上高", f"{total_rev:,.0f} 円")
k2.metric("全負荷粗利", f"{total_margin:,.0f} 円")
k3.metric("粗利率", f"{total_margin / total_rev:.1%}" if total_rev else "—")
if "revenue_budget" in report.columns and report["revenue_budget"].sum() > 0:
    k4.metric("売上予算達成率", f"{total_rev / report['revenue_budget'].sum():.1%}")

divisions = ["すべて"] + sorted(report["division_name"].dropna().unique().tolist())
sel_div = st.selectbox("事業部フィルタ", divisions)
view = report if sel_div == "すべて" else report[report["division_name"] == sel_div]

display_cols = {
    "project_code": "花名", "project_name": "プロジェクト", "division_name": "事業部",
    "revenue": "売上高", "direct_outsourcing_cost": "外注費",
    "allocated_labor_cost": "人件費(配賦)", "allocated_overhead_cost": "間接費(配賦)",
    "total_cost": "総原価", "gross_margin": "粗利", "gross_margin_pct": "粗利率",
}
if "revenue_budget" in view.columns:
    display_cols |= {"revenue_budget": "売上予算", "revenue_variance": "売上差異",
                     "revenue_achievement": "達成率", "gross_margin_budget": "粗利予算",
                     "margin_variance": "粗利差異"}
if view["labor_from_default"].sum() > 0:
    display_cols["labor_from_default"] = "うちデフォルト配分"

table = view[list(display_cols.keys())].rename(columns=display_cols)
money_cols = [v for k, v in display_cols.items()
              if k not in ("project_code", "project_name", "division_name",
                           "gross_margin_pct", "revenue_achievement")]
st.dataframe(
    table.style.format({c: "{:,.0f}" for c in money_cols}
                       | {"粗利率": "{:.1%}", "達成率": "{:.1%}"}, na_rep="—"),
    use_container_width=True, height=420)

if view["labor_from_default"].sum() > 0:
    st.caption("※「うちデフォルト配分」= 工数未記入のためBSE管理表由来のデフォルト比率で配賦した人件費。"
               "実録工数が入ると自動的に置き換わります。")

st.subheader("プロジェクト別 粗利")
chart_df = view.set_index("project_code")[["gross_margin"]]
st.bar_chart(chart_df)
