"""MF会計PLUS 推移表（損益計算書）・プロジェクト実績・予算・社宅・BSE の取込。"""
import streamlit as st

st.set_page_config(page_title="MF会計・その他取込", page_icon="📥", layout="wide")

import pandas as pd

from core.importers.mf_gl_importer import parse_mf_pl_file, unclassified_accounts, upsert_gl_facts
from core.importers.misc_importers import (
    upsert_default_projects,
    upsert_housing_leases,
    upsert_legacy_actuals,
    upsert_project_actuals,
    upsert_project_budgets,
)
from core.ui import bootstrap, read_uploaded_table, show_import_summary

session = bootstrap()

st.title("📥 データ取込：MF会計・実績・予算・社宅・BSE")

tab_mf, tab_actuals, tab_budget, tab_housing, tab_bse, tab_legacy = st.tabs([
    "MF会計 推移表", "プロジェクト実績", "予算", "社宅台帳", "BSE(デフォルト配分)", "現行Excel実績(突合用)"])

# ------------------------------------------------------------------ MF会計
with tab_mf:
    st.markdown("""
MF会計PLUS の **推移表（損益計算書）** をそのまま CSV で出力してアップロードしてください。
ヘッダ行（期間・事業者名など）は自動でスキップし、科目×月に展開します。
部門別に出力した場合は下で部門名を指定してください（未指定＝全社共通費）。
""")
    dept = st.text_input("この取込の部門（MF側で部門を絞って出力した場合のみ）", value="")
    up = st.file_uploader("推移表CSV / Excel", type=["csv", "xlsx", "xls"], key="mf")
    if up is not None:
        raw = read_uploaded_table(up, header=None)
        st.dataframe(raw.head(8), use_container_width=True)
        year_hint = st.number_input("対象年（自動判定できない場合に使用）", value=2026, step=1)
        if st.button("取込実行", type="primary", key="mf_btn"):
            try:
                long_df = parse_mf_pl_file(raw, year=int(year_hint))
                summary = upsert_gl_facts(session, long_df, department=dept, source_file=up.name)
                show_import_summary(summary)
            except ValueError as e:
                st.error(str(e))
    unclassified = unclassified_accounts(session)
    if unclassified:
        st.warning("未分類の勘定科目があります（配賦対象に含まれません）。"
                   "「08 マスタ管理 > 勘定科目区分」で設定してください: "
                   + ", ".join(unclassified))

# ------------------------------------------------------------ project actuals
with tab_actuals:
    st.markdown("""
プロジェクト（花名）×月の **売上高・外注費** を取込みます。
列：`project_code, year_month, revenue, outsourcing_cost`
※ 将来は MF会計のプロジェクトタグ運用により、この取込は MF 推移表に統合できます。
""")
    up = st.file_uploader("実績CSV / Excel", type=["csv", "xlsx", "xls"], key="pa")
    if up is not None:
        df = read_uploaded_table(up)
        st.dataframe(df.head(10), use_container_width=True)
        if st.button("取込実行", type="primary", key="pa_btn"):
            show_import_summary(upsert_project_actuals(session, df, up.name))

# ------------------------------------------------------------------- budgets
with tab_budget:
    st.markdown("""
プロジェクト×月の予算。列：`project_code, year_month, revenue_budget,
outsourcing_budget, labor_budget, overhead_budget`（現行予算Excelから整形して年1回）
""")
    up = st.file_uploader("予算CSV / Excel", type=["csv", "xlsx", "xls"], key="bud")
    if up is not None:
        df = read_uploaded_table(up)
        st.dataframe(df.head(10), use_container_width=True)
        if st.button("取込実行", type="primary", key="bud_btn"):
            show_import_summary(upsert_project_budgets(session, df, up.name))

# ------------------------------------------------------------------- housing
with tab_housing:
    st.markdown("""
社宅台帳。列：`employee_code, move_in, move_out, monthly_rent, employee_share`
（月額家賃は管理費込・会社支払額。employee_share は本人負担＝給与控除額。
入退去や家賃改定のときだけ更新すれば、各月への展開は自動です）
""")
    template = pd.DataFrame([{"employee_code": "0101", "move_in": "2026-01-01",
                              "move_out": "", "monthly_rent": 120000, "employee_share": 25000}])
    st.download_button("テンプレートCSVをダウンロード",
                       template.to_csv(index=False).encode("utf-8-sig"),
                       "housing_template.csv", "text/csv")
    up = st.file_uploader("社宅台帳CSV / Excel", type=["csv", "xlsx", "xls"], key="hl")
    if up is not None:
        df = read_uploaded_table(up, dtype=str)
        st.dataframe(df.head(10), use_container_width=True)
        if st.button("取込実行", type="primary", key="hl_btn"):
            show_import_summary(upsert_housing_leases(session, df))
            st.info("社宅コストは次回の給与取込時（再取込でも可）に各月へ反映されます。")

# ----------------------------------------------------------------------- BSE
with tab_bse:
    st.markdown("""
BSE管理表の「氏名×投入project」を取込み、**工数未入力時のデフォルト配分**として使います。
列：`employee_name`（または `employee_code`）, `project_code`
""")
    ym = st.text_input("適用年月 (YYYY-MM)", value="2026-05", key="bse_ym")
    up = st.file_uploader("BSE CSV / Excel", type=["csv", "xlsx", "xls"], key="bse")
    if up is not None:
        df = read_uploaded_table(up, dtype=str)
        st.dataframe(df.head(10), use_container_width=True)
        if st.button("取込実行", type="primary", key="bse_btn"):
            show_import_summary(upsert_default_projects(session, df, ym))

# -------------------------------------------------------------------- legacy
with tab_legacy:
    st.markdown("""
現行Excel（推移表/事業部別損益）の月次合計。突合レビュー専用。
列：`year_month, scope_type(company|division), division_name, revenue,
outsourcing_cost, labor_cost, overhead_cost, operating_profit`
""")
    up = st.file_uploader("現行実績CSV / Excel", type=["csv", "xlsx", "xls"], key="leg")
    if up is not None:
        df = read_uploaded_table(up)
        st.dataframe(df.head(10), use_container_width=True)
        if st.button("取込実行", type="primary", key="leg_btn"):
            show_import_summary(upsert_legacy_actuals(session, df, up.name))
