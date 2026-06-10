"""数据库模型"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Boolean, Text, UniqueConstraint, Index
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import DB_PATH


class Base(DeclarativeBase):
    pass


class Component(Base):
    """监控的元器件"""
    __tablename__ = "components"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), unique=True, nullable=False, comment="型号/料号")
    description = Column(String(500), comment="描述")
    category = Column(String(100), comment="分类")
    is_active = Column(Boolean, default=True, comment="是否启用监控")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Component {self.part_number}>"


class PriceRecord(Base):
    """价格记录"""
    __tablename__ = "price_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), nullable=False, comment="型号")
    source = Column(String(50), nullable=False, comment="数据来源")
    source_name = Column(String(100), comment="来源名称")
    price = Column(Float, nullable=False, comment="单价(元)")
    currency = Column(String(10), default="CNY")
    min_qty = Column(Integer, default=1, comment="最小起购量")
    stock_qty = Column(Integer, comment="库存数量")
    supplier = Column(String(200), comment="供应商")
    url = Column(Text, comment="详情链接")
    raw_price_text = Column(String(100), comment="原始价格文本")
    scraped_at = Column(DateTime, default=datetime.utcnow, comment="抓取时间")

    __table_args__ = (
        Index("ix_price_records_part_source", "part_number", "source"),
        Index("ix_price_records_scraped_at", "scraped_at"),
    )

    def __repr__(self):
        return f"<PriceRecord {self.part_number} {self.source} ¥{self.price}>"


class PriceAlert(Base):
    """价格告警记录"""
    __tablename__ = "price_alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    part_number = Column(String(100), nullable=False)
    source = Column(String(50), nullable=False)
    old_price = Column(Float, nullable=False)
    new_price = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False, comment="变化百分比")
    direction = Column(String(10), comment="up/down")
    alerted_at = Column(DateTime, default=datetime.utcnow)
    is_notified = Column(Boolean, default=False)

    def __repr__(self):
        return f"<PriceAlert {self.part_number} {self.change_pct:+.1f}%>"


def get_engine(db_path: str = DB_PATH):
    # check_same_thread=False: Web 服务多线程(请求线程+后台抓取线程)共用引擎
    return create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )


def get_session(engine=None):
    if engine is None:
        engine = get_engine()
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    return Session()


def init_db(db_path: str = DB_PATH):
    engine = get_engine(db_path)
    Base.metadata.create_all(engine)
    return engine
