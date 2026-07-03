"""Database bootstrap and session helpers."""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from core.models import Base

DATA_DIR = Path(os.environ.get("PROJECT_COSTING_DATA_DIR", Path(__file__).resolve().parent.parent / "data"))
DB_PATH = DATA_DIR / "project_costing.db"

_engine = None
_SessionLocal = None


def get_engine(db_url: str | None = None):
    global _engine, _SessionLocal
    if _engine is None:
        if db_url is None:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            db_url = f"sqlite:///{DB_PATH}"
        _engine = create_engine(db_url, future=True)
        _SessionLocal = sessionmaker(bind=_engine, future=True, expire_on_commit=False)
    return _engine


def init_db(db_url: str | None = None):
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    return engine


def get_session() -> Session:
    if _SessionLocal is None:
        init_db()
    return _SessionLocal()


def make_memory_session() -> Session:
    """Independent in-memory DB (tests)."""
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine, future=True, expire_on_commit=False)()
