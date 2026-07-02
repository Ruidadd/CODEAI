"""給与データ（支給控除一覧表）取込ページ。"""
import streamlit as st

st.set_page_config(page_title="給与データ取込", page_icon="🧾", layout="wide")

from core.importers.column_mapper import save_mapping_profile, load_default_mapping
from core.importers.payroll_importer import (
    PAYROLL_FIELDS,
    REQUIRED_FIELDS,
    default_payroll_mapping,
    parse_payroll_file,
    upsert_employee_month_costs,
)
from core.ui import bootstrap, read_uploaded_table, show_import_summary

session = bootstrap()

st.title("🧾 データ取込：給与（支給控除一覧表）")
st.markdown("""
給与システムから **支給控除一覧表** を CSV/Excel で出力してアップロードしてください。
必要な列：従業員番号・従業員・部門・総労働時間・支給合計・社会保険料合計（・社宅入居費）。
同じ月を再取込しても重複しません（上書き更新）。
""")

col1, col2 = st.columns([1, 2])
with col1:
    year_month = st.text_input("対象年月 (YYYY-MM)", value="2026-05")

uploaded = st.file_uploader("給与CSV / Excel", type=["csv", "xlsx", "xls"])

if uploaded is not None:
    df = read_uploaded_table(uploaded, dtype=str)
    st.subheader("プレビュー")
    st.dataframe(df.head(10), use_container_width=True)

    st.subheader("列マッピング")
    saved = load_default_mapping(session, "payroll")
    suggested = default_payroll_mapping(list(df.columns))
    if saved:
        # 保存済みテンプレートのうち今回のファイルに存在する列だけ活かす
        suggested.update({f: c for f, c in saved.items() if c in df.columns})

    mapping: dict[str, str] = {}
    cols = st.columns(4)
    options = ["（未使用）"] + list(df.columns)
    for i, (field, aliases) in enumerate(PAYROLL_FIELDS.items()):
        default = suggested.get(field, "（未使用）")
        idx = options.index(default) if default in options else 0
        label = f"{aliases[0]}" + ("（必須）" if field in REQUIRED_FIELDS else "")
        sel = cols[i % 4].selectbox(label, options, index=idx, key=f"map_{field}")
        if sel != "（未使用）":
            mapping[field] = sel

    if st.button("取込実行", type="primary"):
        try:
            parsed = parse_payroll_file(df, mapping, year_month=year_month)
            summary = upsert_employee_month_costs(session, parsed, uploaded.name)
            save_mapping_profile(session, "payroll", "前回使用", mapping)
            show_import_summary(summary)
            st.info("会社負担社会保険は料率マスタから自動推算、社宅コストは社宅台帳から自動反映されます。"
                    "料率・台帳は「08 マスタ管理」で設定してください。")
        except ValueError as e:
            st.error(str(e))
