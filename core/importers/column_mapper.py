"""取込ファイルの列マッピング支援。

アップロードされた CSV/Excel の列名を内部フィールド名へ対応付ける。
difflib による曖昧一致で候補を予め埋め、確定したマッピングはテンプレート
として保存して次回以降自動適用する。
"""
from __future__ import annotations

import difflib
import json

import pandas as pd

from core.models import MappingProfile


def suggest_mapping(source_columns: list[str], target_fields: dict[str, list[str]]) -> dict[str, str]:
    """target_field -> source_column の対応候補を返す。

    target_fields: {internal_field: [別名候補, ...]} 形式。
    """
    result: dict[str, str] = {}
    normalized = {c: str(c).strip() for c in source_columns}
    for field, aliases in target_fields.items():
        best = None
        for alias in aliases:
            # 完全一致 > 部分一致 > 曖昧一致
            exact = [c for c, n in normalized.items() if n == alias]
            if exact:
                best = exact[0]
                break
            contains = [c for c, n in normalized.items() if alias in n or n in alias]
            if contains and best is None:
                best = contains[0]
        if best is None:
            close = difflib.get_close_matches(aliases[0], list(normalized.values()), n=1, cutoff=0.6)
            if close:
                best = next(c for c, n in normalized.items() if n == close[0])
        if best is not None:
            result[field] = best
    return result


def apply_mapping(df: pd.DataFrame, mapping: dict[str, str],
                  required: list[str]) -> pd.DataFrame:
    """mapping (field -> source column) で列を選択・改名する。"""
    missing = [f for f in required if f not in mapping or mapping[f] not in df.columns]
    if missing:
        raise ValueError(f"必須フィールドが未マッピングです: {missing}")
    cols = {src: field for field, src in mapping.items() if src in df.columns}
    return df[list(cols.keys())].rename(columns=cols)


def save_mapping_profile(session, import_type: str, name: str, mapping: dict,
                         is_default: bool = True) -> int:
    if is_default:
        for p in session.query(MappingProfile).filter_by(import_type=import_type, is_default=True):
            p.is_default = False
    profile = MappingProfile(import_type=import_type, profile_name=name,
                             mapping_json=json.dumps(mapping, ensure_ascii=False),
                             is_default=is_default)
    session.add(profile)
    session.commit()
    return profile.id


def load_default_mapping(session, import_type: str) -> dict | None:
    p = (session.query(MappingProfile)
         .filter_by(import_type=import_type, is_default=True)
         .order_by(MappingProfile.created_at.desc()).first())
    return json.loads(p.mapping_json) if p else None


def clean_number(value) -> float:
    """千位区切り・全角・円記号などを除去して float 化。"""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s or s in {"-", "—", "ー"}:
        return 0.0
    for ch in [",", "‚", "，", "円", "¥", "　", " "]:
        s = s.replace(ch, "")
    s = s.replace("△", "-").replace("▲", "-")
    try:
        return float(s)
    except ValueError:
        return 0.0
