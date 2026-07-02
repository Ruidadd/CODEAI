"""SQLAlchemy 2.0 ORM models for the project-costing system.

単位はすべて「円」。year_month は 'YYYY-MM' 形式の文字列。
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------- master data


class Division(Base):
    """事業部（開発支援 / コックピット開発 / AD・ADAS開発 / AI開発 / 電動化開発 / 管理・営業）"""

    __tablename__ = "divisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(32), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    is_overhead: Mapped[bool] = mapped_column(Boolean, default=False)  # 管理部門・営業部など

    projects: Mapped[list["Project"]] = relationship(back_populates="division")


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_code: Mapped[str] = mapped_column(String(16), unique=True)  # 従業員番号
    name: Mapped[str] = mapped_column(String(64))
    work_location: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Project(Base):
    """プロジェクト。project_code は現行運用の「花名」（herb, oxalis, turkey, ...）"""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_code: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(128))
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"))
    status: Mapped[str] = mapped_column(String(16), default="active")  # active|closed
    start_date: Mapped[date | None] = mapped_column(Date)
    end_date: Mapped[date | None] = mapped_column(Date)

    division: Mapped[Division] = relationship(back_populates="projects")


# -------------------------------------------------------- payroll month facts


class EmployeeMonthCost(Base):
    """給与データ（支給控除一覧表）由来の従業員×月コスト事実。"""

    __tablename__ = "employee_month_costs"
    __table_args__ = (UniqueConstraint("employee_id", "year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    division_id: Mapped[int | None] = mapped_column(ForeignKey("divisions.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)

    gross_pay: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 支給合計
    employee_social_insurance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 社会保険料合計(本人)
    employer_social_insurance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 会社負担(料率推算/手動上書き)
    housing_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 社宅純コスト(会社負担-本人負担)
    actual_work_hours: Mapped[float] = mapped_column(Float, default=0)  # 総労働時間

    source_file: Mapped[str | None] = mapped_column(String(256))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class InsuranceRate(Base):
    """会社負担の社会保険料率（適用開始月つき）。rate は 支給合計 に対する割合。"""

    __tablename__ = "insurance_rates"
    __table_args__ = (UniqueConstraint("rate_name", "effective_from"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    rate_name: Mapped[str] = mapped_column(String(64))  # 健康保険 / 介護保険 / 厚生年金 / 子ども・子育て拠出 / 雇用保険
    rate: Mapped[float] = mapped_column(Float)
    effective_from: Mapped[str] = mapped_column(String(7))  # 'YYYY-MM'


class HousingLease(Base):
    """社宅台帳：従業員×賃貸契約。月次コストは期間から自動展開する。"""

    __tablename__ = "housing_leases"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    move_in: Mapped[date] = mapped_column(Date)  # 入居日
    move_out: Mapped[date | None] = mapped_column(Date)  # 退去日（None=継続中）
    monthly_rent: Mapped[float] = mapped_column(Numeric(14, 2))  # 月額家賃（管理費込・会社支払）
    employee_share: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # 本人負担（社宅入居費控除）
    note: Mapped[str | None] = mapped_column(Text)


# --------------------------------------------------------------- time tracking


class EmployeeDefaultProject(Base):
    """従業員→プロジェクトの月次デフォルト配分（BSE管理表「投入project」由来）。

    weight は同一従業員×月内での相対比率（合計は正規化される）。
    工数未入力の月のフォールバックとして使う。
    """

    __tablename__ = "employee_default_projects"
    __table_args__ = (UniqueConstraint("employee_id", "project_id", "year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    weight: Mapped[float] = mapped_column(Float, default=1.0)
    source: Mapped[str | None] = mapped_column(String(64))  # e.g. 'BSE管理表'


class TimesheetEntry(Base):
    __tablename__ = "timesheet_entries"
    __table_args__ = (UniqueConstraint("employee_id", "project_id", "work_date"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    work_date: Mapped[date] = mapped_column(Date, index=True)
    hours: Mapped[float] = mapped_column(Float)
    status: Mapped[str] = mapped_column(String(16), default="submitted")  # draft|submitted|approved
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    approved_by: Mapped[str | None] = mapped_column(String(64))
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)


# --------------------------------------------------- project revenue & budgets


class ProjectMonthActual(Base):
    """プロジェクト×月の直接実績（売上高・外注費）。現行の事業部別損益と同じ粒度。"""

    __tablename__ = "project_month_actuals"
    __table_args__ = (UniqueConstraint("project_id", "year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    outsourcing_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    source_file: Mapped[str | None] = mapped_column(String(256))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ProjectBudget(Base):
    __tablename__ = "project_budgets"
    __table_args__ = (UniqueConstraint("project_id", "year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    revenue_budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    outsourcing_budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    labor_budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    overhead_budget: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    source_file: Mapped[str | None] = mapped_column(String(256))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------ GL / overhead


class GLOverheadFact(Base):
    """MF会計PLUS 推移表(損益計算書)由来の科目×月×金額の事実。"""

    __tablename__ = "gl_overhead_facts"
    __table_args__ = (UniqueConstraint("account_name", "department_raw", "year_month"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    account_code: Mapped[str | None] = mapped_column(String(16))
    account_name: Mapped[str] = mapped_column(String(64))
    department_raw: Mapped[str] = mapped_column(String(64), default="")  # MF部門名（未使用なら空）
    department_division_id: Mapped[int | None] = mapped_column(ForeignKey("divisions.id"))
    amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    source_file: Mapped[str | None] = mapped_column(String(256))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AccountMapping(Base):
    """勘定科目→内部区分。未分類(NULL)は取込画面で警告キューに出す。"""

    __tablename__ = "account_mapping"
    __table_args__ = (UniqueConstraint("account_name",),)

    id: Mapped[int] = mapped_column(primary_key=True)
    account_code: Mapped[str | None] = mapped_column(String(16))
    account_name: Mapped[str] = mapped_column(String(64))
    internal_category: Mapped[str | None] = mapped_column(String(16))  # overhead|labor|outsourcing|revenue|excluded


class DepartmentMapping(Base):
    """外部システムの部門名 → 内部事業部。給与・MF両方で使う。"""

    __tablename__ = "department_mapping"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_department_name: Mapped[str] = mapped_column(String(64), unique=True)
    division_id: Mapped[int] = mapped_column(ForeignKey("divisions.id"))


class MappingProfile(Base):
    """取込ファイルの列マッピングテンプレート。"""

    __tablename__ = "mapping_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    import_type: Mapped[str] = mapped_column(String(32))  # payroll|mf_gl|project_actuals|budget|housing|bse
    profile_name: Mapped[str] = mapped_column(String(64))
    mapping_json: Mapped[str] = mapped_column(Text)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# ------------------------------------------------------------- engine output


class AllocationRun(Base):
    __tablename__ = "allocation_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    driver: Mapped[str] = mapped_column(String(32))
    run_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[str | None] = mapped_column(Text)


class AllocationResult(Base):
    __tablename__ = "allocation_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    allocation_run_id: Mapped[int] = mapped_column(ForeignKey("allocation_runs.id"))
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)

    revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    direct_outsourcing_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    allocated_labor_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    allocated_overhead_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_margin: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_margin_pct: Mapped[float | None] = mapped_column(Float)
    labor_from_default: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # うちデフォルト配分由来


class AllocationUnallocated(Base):
    """配賦できなかった人件費（工数ゼロ かつ デフォルト配分なし、または残余時間分）。"""

    __tablename__ = "allocation_unallocated"

    id: Mapped[int] = mapped_column(primary_key=True)
    allocation_run_id: Mapped[int] = mapped_column(ForeignKey("allocation_runs.id"))
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"))
    division_id: Mapped[int | None] = mapped_column(ForeignKey("divisions.id"))
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    unallocated_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    reason: Mapped[str | None] = mapped_column(String(64))  # no_hours|partial_hours


# ------------------------------------------------------------ reconciliation


class LegacyActual(Base):
    """現行Excel（推移表/事業部別損益）の月次合計。突合レビュー用。"""

    __tablename__ = "legacy_actuals"
    __table_args__ = (UniqueConstraint("year_month", "scope_type", "division_id"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    year_month: Mapped[str] = mapped_column(String(7), index=True)
    scope_type: Mapped[str] = mapped_column(String(16))  # division|company
    division_id: Mapped[int | None] = mapped_column(ForeignKey("divisions.id"))
    revenue: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    outsourcing_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    labor_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    overhead_cost: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    operating_profit: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    source_file: Mapped[str | None] = mapped_column(String(256))
    imported_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
