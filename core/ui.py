"""Streamlit ページ共通のヘルパー。"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.db import get_session, init_db


def bootstrap():
    """全ページ冒頭で呼ぶ：DB初期化とセッション取得。"""
    init_db()
    return get_session()


def month_options(session) -> list[str]:
    """データが存在する年月の一覧（給与・実績・GLの和集合、降順）。"""
    from sqlalchemy import select

    from core.models import EmployeeMonthCost, GLOverheadFact, ProjectMonthActual

    months: set[str] = set()
    for model in (EmployeeMonthCost, ProjectMonthActual, GLOverheadFact):
        for (ym,) in session.execute(select(model.year_month).distinct()):
            months.add(ym)
    return sorted(months, reverse=True)


def fmt_money(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].map(lambda v: f"{v:,.0f}" if pd.notna(v) else "")
    return out


def fmt_pct(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    out = df.copy()
    for c in cols:
        if c in out.columns:
            out[c] = out[c].map(lambda v: f"{v:.1%}" if pd.notna(v) else "—")
    return out


def show_import_summary(summary):
    st.success(f"取込完了：新規 {summary.inserted} 件 / 更新 {summary.updated} 件 / スキップ {summary.skipped} 件")
    for w in summary.warnings:
        st.warning(w)


def read_uploaded_table(uploaded, dtype=None, header="infer") -> pd.DataFrame:
    """CSV/Excel 両対応の読み込み。従業員番号の先頭ゼロを保持するため dtype=str 推奨。"""
    name = uploaded.name.lower()
    if name.endswith((".xlsx", ".xls")):
        return pd.read_excel(uploaded, dtype=dtype, header=header)
    for enc in ("utf-8-sig", "utf-8", "cp932"):
        try:
            uploaded.seek(0)
            return pd.read_csv(uploaded, dtype=dtype, encoding=enc, header=header)
        except UnicodeDecodeError:
            continue
    raise ValueError("ファイルの文字コードを判定できません（UTF-8 か Shift_JIS で保存してください）")
