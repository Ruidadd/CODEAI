"""
SQLite storage layer for price snapshots and alerts.
"""
import sqlite3
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .config import DB_PATH


def get_conn(db_path: str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DB_PATH) -> None:
    with get_conn(db_path) as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS dram_prices (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                dram_type   TEXT NOT NULL,
                price_usd   REAL NOT NULL,
                source      TEXT,
                unit        TEXT DEFAULT 'per GB'
            );

            CREATE TABLE IF NOT EXISTS gpu_prices (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ts              TEXT NOT NULL,
                provider        TEXT NOT NULL,
                region          TEXT NOT NULL,
                instance_type   TEXT NOT NULL,
                spot_price_usd  REAL,
                on_demand_usd   REAL,
                price_type      TEXT DEFAULT 'spot'
            );

            CREATE TABLE IF NOT EXISTS gpu_availability (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                ts              TEXT NOT NULL,
                provider        TEXT NOT NULL,
                region          TEXT NOT NULL,
                instance_type   TEXT NOT NULL,
                available       INTEGER NOT NULL,
                pool_size       INTEGER
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                category    TEXT NOT NULL,
                severity    TEXT NOT NULL,
                message     TEXT NOT NULL,
                metadata    TEXT
            );

            CREATE INDEX IF NOT EXISTS idx_dram_ts   ON dram_prices(ts);
            CREATE INDEX IF NOT EXISTS idx_gpu_ts    ON gpu_prices(ts);
            CREATE INDEX IF NOT EXISTS idx_avail_ts  ON gpu_availability(ts);
        """)


def insert_dram_price(dram_type: str, price_usd: float, source: str = "", unit: str = "per GB", db_path: str = DB_PATH) -> None:
    ts = datetime.utcnow().isoformat()
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO dram_prices (ts, dram_type, price_usd, source, unit) VALUES (?,?,?,?,?)",
            (ts, dram_type, price_usd, source, unit),
        )


def insert_gpu_price(provider: str, region: str, instance_type: str,
                     spot_price: Optional[float], on_demand: Optional[float],
                     price_type: str = "spot", db_path: str = DB_PATH) -> None:
    ts = datetime.utcnow().isoformat()
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO gpu_prices
               (ts, provider, region, instance_type, spot_price_usd, on_demand_usd, price_type)
               VALUES (?,?,?,?,?,?,?)""",
            (ts, provider, region, instance_type, spot_price, on_demand, price_type),
        )


def insert_gpu_availability(provider: str, region: str, instance_type: str,
                             available: bool, pool_size: Optional[int] = None,
                             db_path: str = DB_PATH) -> None:
    ts = datetime.utcnow().isoformat()
    with get_conn(db_path) as conn:
        conn.execute(
            """INSERT INTO gpu_availability
               (ts, provider, region, instance_type, available, pool_size)
               VALUES (?,?,?,?,?,?)""",
            (ts, provider, region, instance_type, int(available), pool_size),
        )


def insert_alert(category: str, severity: str, message: str,
                 metadata: Optional[Dict] = None, db_path: str = DB_PATH) -> None:
    ts = datetime.utcnow().isoformat()
    with get_conn(db_path) as conn:
        conn.execute(
            "INSERT INTO alerts (ts, category, severity, message, metadata) VALUES (?,?,?,?,?)",
            (ts, category, severity, message, json.dumps(metadata or {})),
        )


def get_latest_dram(dram_type: str, db_path: str = DB_PATH) -> Optional[sqlite3.Row]:
    with get_conn(db_path) as conn:
        return conn.execute(
            "SELECT * FROM dram_prices WHERE dram_type=? ORDER BY ts DESC LIMIT 1",
            (dram_type,),
        ).fetchone()


def get_latest_gpu_price(provider: str, region: str, instance_type: str,
                          db_path: str = DB_PATH) -> Optional[sqlite3.Row]:
    with get_conn(db_path) as conn:
        return conn.execute(
            """SELECT * FROM gpu_prices
               WHERE provider=? AND region=? AND instance_type=?
               ORDER BY ts DESC LIMIT 1""",
            (provider, region, instance_type),
        ).fetchone()


def get_recent_prices(table: str, hours: int = 24, db_path: str = DB_PATH) -> List[sqlite3.Row]:
    cutoff = f"datetime('now', '-{hours} hours')"
    with get_conn(db_path) as conn:
        return conn.execute(
            f"SELECT * FROM {table} WHERE ts >= {cutoff} ORDER BY ts DESC"
        ).fetchall()


def get_recent_alerts(hours: int = 24, db_path: str = DB_PATH) -> List[sqlite3.Row]:
    return get_recent_prices("alerts", hours, db_path)
