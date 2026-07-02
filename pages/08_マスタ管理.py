"""マスタ管理：事業部・従業員・プロジェクト・科目区分・部門マッピング・料率・社宅。"""
import streamlit as st

st.set_page_config(page_title="マスタ管理", page_icon="⚙️", layout="wide")

import pandas as pd
from sqlalchemy import select

from core.models import (
    AccountMapping,
    DepartmentMapping,
    Division,
    Employee,
    HousingLease,
    InsuranceRate,
    Project,
)
from core.ui import bootstrap

session = bootstrap()

st.title("⚙️ マスタ管理")

tab_div, tab_emp, tab_prj, tab_acct, tab_dept, tab_rate, tab_housing = st.tabs([
    "事業部", "従業員", "プロジェクト", "勘定科目区分", "部門マッピング", "社保料率", "社宅台帳"])

with tab_div:
    df = pd.read_sql(select(Division), session.get_bind())
    st.dataframe(df, use_container_width=True)
    with st.form("add_div"):
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("コード")
        name = c2.text_input("名称")
        is_oh = c3.checkbox("間接部門（管理・営業）")
        if st.form_submit_button("追加") and code and name:
            session.add(Division(code=code, name=name, is_overhead=is_oh))
            session.commit()
            st.rerun()

with tab_emp:
    df = pd.read_sql(select(Employee), session.get_bind())
    st.dataframe(df, use_container_width=True)
    st.caption("従業員は給与取込時に自動作成されます。ここでは名称修正・無効化のみ想定。")
    with st.form("add_emp"):
        c1, c2 = st.columns(2)
        code = c1.text_input("従業員番号")
        name = c2.text_input("氏名")
        if st.form_submit_button("追加") and code and name:
            session.add(Employee(employee_code=code, name=name))
            session.commit()
            st.rerun()

with tab_prj:
    prj = pd.read_sql(
        """select p.id, p.project_code as 花名, p.name as プロジェクト名,
                  d.name as 事業部, p.status
           from projects p left join divisions d on d.id = p.division_id""",
        session.get_bind())
    st.dataframe(prj, use_container_width=True)
    divisions = session.query(Division).all()
    div_by_name = {d.name: d for d in divisions}
    with st.form("add_prj"):
        c1, c2, c3 = st.columns(3)
        code = c1.text_input("花名（プロジェクトコード）")
        name = c2.text_input("名称")
        div_name = c3.selectbox("事業部", list(div_by_name.keys())) if div_by_name else None
        if st.form_submit_button("追加") and code and div_name:
            session.add(Project(project_code=code, name=name or code,
                                division_id=div_by_name[div_name].id))
            session.commit()
            st.rerun()

with tab_acct:
    st.markdown("MF会計の勘定科目を **overhead(間接費・配賦対象) / labor / outsourcing / revenue / excluded** に区分します。"
                "未分類（空欄）の科目は配賦されません。")
    df = pd.read_sql(select(AccountMapping), session.get_bind())
    edited = st.data_editor(
        df, use_container_width=True, hide_index=True,
        column_config={
            "internal_category": st.column_config.SelectboxColumn(
                "区分", options=["overhead", "labor", "outsourcing", "revenue", "excluded"]),
        },
        disabled=["id", "account_code", "account_name"])
    if st.button("区分を保存", type="primary"):
        for _, row in edited.iterrows():
            rec = session.get(AccountMapping, int(row["id"]))
            rec.internal_category = row["internal_category"] or None
        session.commit()
        st.success("保存しました")

with tab_dept:
    st.markdown("給与システム・MF会計の部門名 → 内部事業部の対応。")
    df = pd.read_sql(
        """select m.id, m.source_department_name as 外部部門名, d.name as 事業部
           from department_mapping m join divisions d on d.id = m.division_id""",
        session.get_bind())
    st.dataframe(df, use_container_width=True)
    divisions = {d.name: d for d in session.query(Division).all()}
    with st.form("add_dept"):
        c1, c2 = st.columns(2)
        src = c1.text_input("外部部門名（例: 開発支援東日本）")
        div_name = c2.selectbox("事業部", list(divisions.keys())) if divisions else None
        if st.form_submit_button("追加") and src and div_name:
            session.add(DepartmentMapping(source_department_name=src,
                                          division_id=divisions[div_name].id))
            session.commit()
            st.rerun()

with tab_rate:
    st.markdown("会社負担の社会保険料率（支給合計に対する割合）。給与取込時の推算に使います。"
                "合計が実効負担率になります（未設定時は 15.5%）。")
    df = pd.read_sql(select(InsuranceRate), session.get_bind())
    st.dataframe(df, use_container_width=True)
    if not df.empty:
        st.info(f"現在の合計料率: {df.groupby('rate_name')['rate'].last().sum():.2%}")
    with st.form("add_rate"):
        c1, c2, c3 = st.columns(3)
        name = c1.text_input("料率名（例: 健康保険(会社)）")
        rate = c2.number_input("料率", value=0.05, format="%.4f")
        eff = c3.text_input("適用開始月 (YYYY-MM)", value="2026-01")
        if st.form_submit_button("追加") and name:
            session.add(InsuranceRate(rate_name=name, rate=rate, effective_from=eff))
            session.commit()
            st.rerun()

with tab_housing:
    df = pd.read_sql(
        """select h.id, e.employee_code, e.name as 従業員, h.move_in as 入居日,
                  h.move_out as 退去日, h.monthly_rent as 月額家賃,
                  h.employee_share as 本人負担, h.note
           from housing_leases h join employees e on e.id = h.employee_id""",
        session.get_bind())
    st.dataframe(df.style.format({"月額家賃": "{:,.0f}", "本人負担": "{:,.0f}"}),
                 use_container_width=True)
    st.caption("一括登録は「02 データ取込 > 社宅台帳」から。反映は次回給与取込時。")
