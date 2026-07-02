"""配賦ドライバ：間接費プールをプロジェクトへ按分する重みの計算。

各ドライバは「プロジェクト単位の行を持つ DataFrame」を受け取り、
project_id を index とした非負の重み Series を返す。重みの合計が 0 の
場合は呼び出し側で均等割りにフォールバックする。
"""
from __future__ import annotations

from typing import Callable

import pandas as pd

DriverFn = Callable[[pd.DataFrame], "pd.Series"]


def driver_by_labor_cost(rows: pd.DataFrame) -> pd.Series:
    return rows.set_index("project_id")["allocated_labor_cost"].clip(lower=0)


def driver_by_labor_hours(rows: pd.DataFrame) -> pd.Series:
    return rows.set_index("project_id")["allocated_hours"].clip(lower=0)


def driver_by_revenue(rows: pd.DataFrame) -> pd.Series:
    return rows.set_index("project_id")["revenue"].clip(lower=0)


DRIVERS: dict[str, DriverFn] = {
    "labor_cost": driver_by_labor_cost,
    "labor_hours": driver_by_labor_hours,
    "revenue": driver_by_revenue,
}

DRIVER_LABELS = {
    "labor_cost": "配賦人件費比",
    "labor_hours": "工数比",
    "revenue": "売上高比",
}
