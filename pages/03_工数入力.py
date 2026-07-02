"""工数入力：従業員×プロジェクト×日。週グリッドまたは月次%の2方式。"""
import streamlit as st

st.set_page_config(page_title="工数入力", page_icon="⏱️", layout="wide")

from datetime import date, timedelta

import pandas as pd

from core.models import Employee, EmployeeMonthCost, Project, TimesheetEntry
from core.ui import bootstrap

session = bootstrap()

st.title("⏱️ 工数入力")

employees = session.query(Employee).filter_by(is_active=True).order_by(Employee.employee_code).all()
projects = session.query(Project).filter_by(status="active").order_by(Project.project_code).all()
if not employees or not projects:
    st.info("従業員・プロジェクトのマスタが必要です（デモデータ投入 or マスタ管理で登録）。")
    st.stop()

emp_label = {f"{e.employee_code} {e.name}": e for e in employees}
prj_label = {f"{p.project_code}（{p.name}）": p for p in projects}

sel_emp = st.selectbox("従業員", list(emp_label.keys()))
emp = emp_label[sel_emp]

mode = st.radio("入力方式", ["週次グリッド（日×プロジェクト）", "月次まとめ（プロジェクト×時間）"],
                horizontal=True)

if mode.startswith("週次"):
    week_start = st.date_input("週の開始日（月曜）", value=date.today() - timedelta(days=date.today().weekday()))
    days = [week_start + timedelta(days=i) for i in range(5)]

    sel_projects = st.multiselect("対象プロジェクト", list(prj_label.keys()),
                                  default=list(prj_label.keys())[:2])
    if sel_projects:
        existing = {}
        for t in (session.query(TimesheetEntry)
                  .filter(TimesheetEntry.employee_id == emp.id,
                          TimesheetEntry.work_date.in_(days)).all()):
            existing[(t.project_id, t.work_date)] = t.hours

        grid = pd.DataFrame(
            {d.strftime("%m/%d(%a)"): [existing.get((prj_label[p].id, d), 0.0) for p in sel_projects]
             for d in days},
            index=sel_projects)
        edited = st.data_editor(grid, use_container_width=True)

        if st.button("保存", type="primary"):
            n = 0
            for p_label in sel_projects:
                prj = prj_label[p_label]
                for d in days:
                    hours = float(edited.loc[p_label, d.strftime("%m/%d(%a)")] or 0)
                    rec = (session.query(TimesheetEntry)
                           .filter_by(employee_id=emp.id, project_id=prj.id, work_date=d).first())
                    if hours > 0:
                        if rec is None:
                            rec = TimesheetEntry(employee_id=emp.id, project_id=prj.id,
                                                 work_date=d, hours=hours)
                            session.add(rec)
                        else:
                            rec.hours = hours
                            rec.status = "submitted"
                        n += 1
                    elif rec is not None:
                        session.delete(rec)
            session.commit()
            st.success(f"保存しました（{n} 件）")
else:
    st.markdown("月の総工数をプロジェクト別にまとめて入力します（時間または%のどちらでも、比率として扱われます）。")
    ym = st.text_input("対象年月 (YYYY-MM)", value=date.today().strftime("%Y-%m"))
    emc = (session.query(EmployeeMonthCost)
           .filter_by(employee_id=emp.id, year_month=ym).first())
    if emc:
        st.caption(f"給与実績の総労働時間: {emc.actual_work_hours} h（配賦の分母）")

    rows = pd.DataFrame({"プロジェクト": list(prj_label.keys()), "時間または%": 0.0})
    edited = st.data_editor(rows, use_container_width=True, hide_index=True)
    if st.button("保存（当月のまとめ入力として登録）", type="primary"):
        y, m = map(int, ym.split("-"))
        anchor = date(y, m, 15)  # 月次まとめは月中央の1レコードに集約
        n = 0
        for _, r in edited.iterrows():
            hours = float(r["時間または%"] or 0)
            if hours <= 0:
                continue
            prj = prj_label[r["プロジェクト"]]
            rec = (session.query(TimesheetEntry)
                   .filter_by(employee_id=emp.id, project_id=prj.id, work_date=anchor).first())
            if rec is None:
                rec = TimesheetEntry(employee_id=emp.id, project_id=prj.id,
                                     work_date=anchor, hours=hours, note="月次まとめ入力")
                session.add(rec)
            else:
                rec.hours = hours
            n += 1
        session.commit()
        st.success(f"保存しました（{n} プロジェクト）")

st.divider()
st.subheader("この従業員の直近の記入")
recent = pd.read_sql(
    f"""select t.work_date, p.project_code, t.hours, t.status
        from timesheet_entries t join projects p on p.id = t.project_id
        where t.employee_id = {emp.id} order by t.work_date desc limit 20""",
    session.get_bind())
st.dataframe(recent, use_container_width=True)
