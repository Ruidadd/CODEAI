"""突合レビュー：新システム vs 現行Excel の会社合計比較（移行期の信頼構築）。"""
import streamlit as st

st.set_page_config(page_title="突合レビュー", page_icon="🔍", layout="wide")

from core.reporting.report_data import (
    load_allocation_results,
    load_legacy,
    load_unallocated,
    reconciliation_report,
)
from core.ui import bootstrap, month_options

session = bootstrap()

st.title("🔍 突合レビュー（新システム vs 現行Excel）")
st.markdown("""
並行運用期間中、新システムの合計値が現行Excel（推移表・事業部別損益）と
どこまで一致しているかを確認するページです。**完全一致は期待しません**
（締めタイミング差・按分方法差・未配賦人件費の扱いなど説明可能な差異が正常）。
""")

months = month_options(session)
if not months:
    st.info("データがありません。")
    st.stop()
ym = st.selectbox("対象年月", months)

results = load_allocation_results(session)
unallocated = load_unallocated(session)
legacy = load_legacy(session)

report = reconciliation_report(results, unallocated, legacy, ym)
if report.empty:
    st.warning(f"{ym} の現行Excel実績が未取込です（02 データ取込 > 現行Excel実績）。"
               "または配賦が未実行です。")
    st.stop()


def color_variance(v):
    if isinstance(v, float):
        if abs(v) < 0.02:
            return "background-color: #d4edda"  # <2%: green
        if abs(v) < 0.05:
            return "background-color: #fff3cd"  # <5%: yellow
        return "background-color: #f8d7da"      # else: red
    return ""


st.dataframe(
    report.style.format({"新システム": "{:,.0f}", "現行Excel": "{:,.0f}",
                         "差異": "{:,.0f}", "差異率": "{:.1%}"}, na_rep="—")
    .map(color_variance, subset=["差異率"]),
    use_container_width=True)

st.markdown("""
**説明可能な差異の例**
- 締め日カットオフ差（月末計上 vs 支払日計上）
- 人件費：新システムは社宅純コスト・会社負担社保（料率推算）込みの全負荷ベース
- 間接費：現行Excelは販管費を事業部止まり、新システムはプロジェクトまで配賦
- 工数記入が浸透するまでは未配賦人件費が大きめに出ます（正常）
""")
