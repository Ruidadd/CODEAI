"""プロジェクト原価管理システム — トップページ"""
import streamlit as st

st.set_page_config(page_title="プロジェクト原価管理", page_icon="📊", layout="wide")

from sqlalchemy import select

from core.models import Division, Employee, EmployeeMonthCost, Project, TimesheetEntry
from core.seed import seed_demo_data
from core.ui import bootstrap

session = bootstrap()

st.title("📊 プロジェクト原価管理システム")
st.caption("工数 × 給与 × MF会計PLUS から、プロジェクト別の全負荷原価と損益を算出します")

n_div = session.query(Division).count()
n_emp = session.query(Employee).count()
n_prj = session.query(Project).count()
n_pay = session.query(EmployeeMonthCost).count()
n_ts = session.query(TimesheetEntry).count()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("事業部", n_div)
c2.metric("従業員", n_emp)
c3.metric("プロジェクト", n_prj)
c4.metric("給与データ(人月)", n_pay)
c5.metric("工数レコード", n_ts)

if n_div == 0:
    st.info("データがまだありません。デモデータを投入して全ページを試せます。")
    if st.button("🚀 デモデータを投入する", type="primary"):
        result = seed_demo_data(session)
        st.success(f"デモデータ投入完了: {result}")
        st.rerun()

st.divider()

st.markdown("""
### 月次運用の流れ

| 順序 | 作業 | ページ | 担当 |
|---|---|---|---|
| 1 | 給与データ取込（支給控除一覧表CSV） | 01 データ取込・給与 | 管理部 |
| 2 | MF会計 推移表取込 | 02 データ取込・MF会計 | 管理部 |
| 3 | 工数の入力・承認 | 03 工数入力 / 04 工数承認 | 各PM・部長 |
| 4 | 配賦実行 → プロジェクト別損益確認 | 05 プロジェクト別損益 | 管理部 |
| 5 | 事業部・会社合計、予実、突合の確認 | 06〜07 | 経営層 |

### 原価の考え方

- **全負荷人件費** = 支給合計 ＋ 会社負担社会保険（料率推算）＋ 社宅純コスト（会社支払家賃 − 本人負担）
- **人件費配賦**：給与実績の総労働時間を分母に、記入工数の比率で各プロジェクトへ。
  記入漏れは「未配賦」として顕在化し、既存プロジェクトの単価を歪めません。
- **間接費配賦**：MF会計の販管費科目を、選択したドライバ（人件費比 / 工数比 / 売上比）で配賦。
- 工数未記入の月は BSE 管理表由来の**デフォルト配分**でフォールバック（レポート上で区別表示）。
""")
