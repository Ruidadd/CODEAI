"""MF会計PLUS 推移表（損益計算書）取込。

実際のエクスポート形式:
  - 先頭数行がヘッダ（期間 / 単位 / 事業者名 / 部門名・プロジェクト名・取引先名）
  - 以降は 行=勘定科目、列=1月..N月・合計・構成比 の横持ち表
これを縦持ち（科目×月×金額）に melt して gl_overhead_facts へ upsert する。

部門別にエクスポートした場合は取込時に「この取込の部門」を指定する
（department 引数）。未指定は全社扱い。
"""
from __future__ import annotations

import re

import pandas as pd

from core.importers.column_mapper import clean_number
from core.importers.payroll_importer import ImportSummary
from core.models import AccountMapping, DepartmentMapping, Division, GLOverheadFact

MONTH_COL_RE = re.compile(r"^(\d{1,2})月$")
SKIP_COLS = {"合計", "構成比", "前期残高", "期間残高"}
# 推移表に現れる集計行（科目ではない）
SUBTOTAL_ROWS = {
    "売上高合計", "売上原価", "売上総利益", "販売費及び一般管理費合計", "営業利益",
    "営業外収益合計", "営業外費用合計", "経常利益", "特別利益合計", "特別損失合計",
    "税引前当期純利益", "当期純利益", "材料費合計", "労務費合計", "製造経費合計",
    "当期総製造費用", "期首仕掛品棚卸高", "期末仕掛品棚卸高", "他勘定振替高",
    "当期製品製造原価",
}


def detect_header_and_frame(raw: pd.DataFrame) -> tuple[pd.DataFrame, int | None]:
    """ヘッダ行（「1月」等の月列を含む行）を探して整形した表と年を返す。"""
    year = None
    header_idx = None
    for i in range(min(10, len(raw))):
        cells = [str(c) for c in raw.iloc[i].tolist() if pd.notna(c)]
        for c in cells:
            m = re.search(r"(\d{4})/\d{2}", c)
            if m:
                year = int(m.group(1))
        if any(MONTH_COL_RE.match(str(c).strip()) for c in cells):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("月列（1月, 2月, ...）を含むヘッダ行が見つかりません")
    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [str(c).strip() if pd.notna(c) else "" for c in raw.iloc[header_idx]]
    df = df.rename(columns={df.columns[0]: "account_name"})
    df = df[df["account_name"].notna()]
    df["account_name"] = df["account_name"].astype(str).str.strip()
    df = df[df["account_name"] != ""]
    return df, year


def melt_pl_wide(df: pd.DataFrame, year: int) -> pd.DataFrame:
    """横持ち推移表 → 縦持ち（account_name, year_month, amount）。"""
    month_cols = [c for c in df.columns if MONTH_COL_RE.match(str(c))]
    if not month_cols:
        raise ValueError("月列が見つかりません")
    keep = df[~df["account_name"].isin(SUBTOTAL_ROWS)]
    long = keep.melt(id_vars=["account_name"], value_vars=month_cols,
                     var_name="month", value_name="amount")
    long["amount"] = long["amount"].map(clean_number)
    long = long[long["amount"] != 0]
    long["year_month"] = long["month"].map(
        lambda m: f"{year}-{int(MONTH_COL_RE.match(m).group(1)):02d}")
    return long[["account_name", "year_month", "amount"]].reset_index(drop=True)


def parse_mf_pl_file(raw: pd.DataFrame, year: int | None = None) -> pd.DataFrame:
    df, detected_year = detect_header_and_frame(raw)
    y = year or detected_year
    if y is None:
        raise ValueError("対象年を特定できません。取込画面で年を指定してください")
    return melt_pl_wide(df, y)


def upsert_gl_facts(session, long_df: pd.DataFrame, department: str = "",
                    source_file: str = "") -> ImportSummary:
    """(account_name, department, year_month) キーで冪等 upsert。

    未知の勘定科目は account_mapping に internal_category=NULL で登録し、
    warnings で「未分類科目」として知らせる。
    """
    summary = ImportSummary()
    dept_map = {m.source_department_name: m.division_id
                for m in session.query(DepartmentMapping).all()}
    div_names = {d.name: d.id for d in session.query(Division).all()}
    division_id = dept_map.get(department) or div_names.get(department)
    if department and division_id is None:
        summary.warnings.append(f"部門未マッピング: '{department}'（全社扱いで取込みます）")

    known = {a.account_name for a in session.query(AccountMapping).all()}
    for _, row in long_df.iterrows():
        name = row["account_name"]
        if name not in known:
            session.add(AccountMapping(account_name=name, internal_category=None))
            known.add(name)
            summary.warnings.append(f"未分類の勘定科目: {name}（マスタ管理で区分を設定してください）")
        rec = (session.query(GLOverheadFact)
               .filter_by(account_name=name, department_raw=department,
                          year_month=row["year_month"]).first())
        if rec is None:
            rec = GLOverheadFact(account_name=name, department_raw=department,
                                 year_month=row["year_month"])
            session.add(rec)
            summary.inserted += 1
        else:
            summary.updated += 1
        rec.amount = float(row["amount"])
        rec.department_division_id = division_id
        rec.source_file = source_file
    session.commit()
    return summary


def unclassified_accounts(session) -> list[str]:
    return [a.account_name for a in session.query(AccountMapping)
            .filter(AccountMapping.internal_category.is_(None)).all()]
