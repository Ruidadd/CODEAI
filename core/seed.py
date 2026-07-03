"""デモデータ投入。

実データと同じ構造（列名・科目名・部門名・花名スタイルのプロジェクト
コード）で、数値はすべて架空。2026-03〜2026-05 の3ヶ月分を投入し、
全ページがそのまま動く状態にする。
"""
from __future__ import annotations

import random
from datetime import date, timedelta

from core.models import (
    AccountMapping,
    DepartmentMapping,
    Division,
    Employee,
    EmployeeDefaultProject,
    EmployeeMonthCost,
    GLOverheadFact,
    HousingLease,
    InsuranceRate,
    LegacyActual,
    Project,
    ProjectBudget,
    ProjectMonthActual,
    TimesheetEntry,
)

MONTHS = ["2026-03", "2026-04", "2026-05"]

DIVISIONS = [
    ("DEV_SUPPORT", "開発支援", False),
    ("COCKPIT", "コックピット開発", False),
    ("AD_ADAS", "AD/ADAS開発", False),
    ("AI", "AI開発", False),
    ("EV", "電動化開発", False),
    ("ADMIN", "管理部門・営業", True),
]

# (code, name, division_code) — 花名スタイル
PROJECTS = [
    ("herb", "地図開発マネジメント・技術支援", "DEV_SUPPORT"),
    ("oxalis", "ADASログ分析", "DEV_SUPPORT"),
    ("orchid", "コックピット開発(D社)", "COCKPIT"),
    ("aerides", "メータ開発(D社/S社)", "COCKPIT"),
    ("turkey", "コックピット派遣", "COCKPIT"),
    ("watermelon", "国内更新版地図", "AD_ADAS"),
    ("antelope", "EHPソースコード", "AD_ADAS"),
    ("samurai", "ADAS評価", "AD_ADAS"),
    ("aiko", "AI開発支援PoC", "AI"),
    ("volt", "電動化制御開発", "EV"),
]

# (code, name, division_code, gross, si_emp, hours, housing_rent, emp_share)
EMPLOYEES = [
    ("1001", "山田 太郎", "DEV_SUPPORT", 520_000, 74_500, 160.0, 0, 0),
    ("1002", "李 明", "DEV_SUPPORT", 480_000, 68_900, 152.5, 110_000, 25_000),
    ("1003", "佐藤 花子", "COCKPIT", 560_000, 80_300, 158.0, 0, 0),
    ("1004", "王 芳", "COCKPIT", 610_000, 87_300, 160.0, 120_000, 25_000),
    ("1005", "鈴木 一郎", "COCKPIT", 450_000, 64_100, 144.0, 0, 0),
    ("1006", "陳 偉", "AD_ADAS", 640_000, 91_500, 162.0, 130_000, 25_000),
    ("1007", "田中 良子", "AD_ADAS", 530_000, 75_900, 155.0, 0, 0),
    ("1008", "劉 洋", "AD_ADAS", 500_000, 71_600, 150.0, 105_000, 25_000),
    ("1009", "高橋 健", "AI", 590_000, 84_500, 158.0, 0, 0),
    ("1010", "張 麗", "EV", 470_000, 67_200, 148.0, 100_000, 25_000),
    ("1011", "伊藤 誠", "ADMIN", 420_000, 60_100, 150.0, 0, 0),
    ("1012", "呉 静", "ADMIN", 380_000, 54_400, 146.0, 0, 0),
]

# 従業員→デフォルトプロジェクト（BSE管理表「投入project」相当）
DEFAULT_PROJECT = {
    "1001": "herb", "1002": "oxalis", "1003": "orchid", "1004": "aerides",
    "1005": "turkey", "1006": "watermelon", "1007": "antelope", "1008": "samurai",
    "1009": "aiko", "1010": "volt",
}

# MF会計PLUSの実在科目名で seed（区分も設定済みにして即動かす）
ACCOUNTS = [
    ("売上高", "revenue"),
    ("受取出向料", "revenue"),
    ("外注費(製)", "outsourcing"),
    ("役員報酬", "labor"),
    ("事務員給与", "labor"),
    ("法定福利費", "labor"),
    ("地代家賃", "overhead"),
    ("通信費", "overhead"),
    ("水道光熱費", "overhead"),
    ("旅費交通費", "overhead"),
    ("支払手数料", "overhead"),
    ("福利厚生費", "overhead"),
    ("リース料", "overhead"),
    ("接待交際費", "overhead"),
    ("税理士報酬", "overhead"),
    ("法人税·住民税·事業税", "excluded"),
]

# 給与システムの部門名 → 内部事業部
DEPT_MAPPING = [
    ("開発支援東日本", "DEV_SUPPORT"),
    ("AI開発東日本", "AI"),
    ("名古屋", "COCKPIT"),
    ("管理部(大森)", "ADMIN"),
    ("営業部(大森)", "ADMIN"),
    ("管理部(名古屋)", "ADMIN"),
    ("営業部(名古屋)", "ADMIN"),
    ("役員", "ADMIN"),
]

INSURANCE_RATES = [
    ("健康保険(会社)", 0.0499, "2026-01"),
    ("介護保険(会社)", 0.0080, "2026-01"),
    ("厚生年金(会社)", 0.0915, "2026-01"),
    ("子ども・子育て拠出金", 0.0036, "2026-01"),
    ("雇用保険(会社)", 0.0095, "2026-01"),
]


def seed_demo_data(session) -> dict:
    """全テーブルへデモデータを投入。既に事業部があれば何もしない。"""
    if session.query(Division).count() > 0:
        return {"status": "skipped", "reason": "データが既に存在します"}

    rng = random.Random(14)  # 再現性のため固定シード

    divisions = {}
    for code, name, is_oh in DIVISIONS:
        d = Division(code=code, name=name, is_overhead=is_oh)
        session.add(d)
        divisions[code] = d
    session.flush()

    projects = {}
    for code, name, div_code in PROJECTS:
        p = Project(project_code=code, name=name, division_id=divisions[div_code].id)
        session.add(p)
        projects[code] = p
    session.flush()

    for src, div_code in DEPT_MAPPING:
        session.add(DepartmentMapping(source_department_name=src,
                                      division_id=divisions[div_code].id))
    for name, cat in ACCOUNTS:
        session.add(AccountMapping(account_name=name, internal_category=cat))
    for name, rate, eff in INSURANCE_RATES:
        session.add(InsuranceRate(rate_name=name, rate=rate, effective_from=eff))
    session.flush()

    employer_rate = sum(r for _, r, _ in INSURANCE_RATES)

    employees = {}
    for code, name, div_code, gross, si, hours, rent, share in EMPLOYEES:
        e = Employee(employee_code=code, name=name)
        session.add(e)
        employees[code] = e
    session.flush()

    # 社宅台帳（rent>0 の従業員のみ）
    for code, name, div_code, gross, si, hours, rent, share in EMPLOYEES:
        if rent > 0:
            session.add(HousingLease(employee_id=employees[code].id,
                                     move_in=date(2026, 1, 1), move_out=None,
                                     monthly_rent=rent, employee_share=share))

    # 月次給与コスト
    for ym in MONTHS:
        for code, name, div_code, gross, si, hours, rent, share in EMPLOYEES:
            jitter = rng.uniform(0.97, 1.05)
            g = round(gross * jitter)
            session.add(EmployeeMonthCost(
                employee_id=employees[code].id, division_id=divisions[div_code].id,
                year_month=ym, gross_pay=g, employee_social_insurance=round(si * jitter),
                employer_social_insurance=round(g * employer_rate),
                housing_cost=(rent - share) if rent > 0 else 0,
                actual_work_hours=round(hours * rng.uniform(0.95, 1.05), 2),
                source_file="seed"))

    # デフォルト配分（全員・全月）
    for ym in MONTHS:
        for emp_code, prj_code in DEFAULT_PROJECT.items():
            session.add(EmployeeDefaultProject(
                employee_id=employees[emp_code].id, project_id=projects[prj_code].id,
                year_month=ym, weight=1.0, source="BSE管理表"))

    # 工数：一部の従業員は複数プロジェクトに記入、一部は未記入（デフォルト配分/未配賦を実演）
    split_assign = {
        "1001": [("herb", 0.6), ("oxalis", 0.4)],
        "1003": [("orchid", 0.5), ("aerides", 0.5)],
        "1006": [("watermelon", 0.7), ("antelope", 0.3)],
        "1007": [("antelope", 0.8), ("samurai", 0.2)],
    }
    logged_employees = {"1001", "1003", "1004", "1005", "1006", "1007", "1008"}
    # 1002, 1009, 1010: 工数未記入 → デフォルト配分でフォールバック
    # 1011, 1012 (管理部門): 工数もデフォルトも無し → 未配賦(間接人件費)として顕在化
    for ym in MONTHS:
        y, m = map(int, ym.split("-"))
        for code, name, div_code, gross, si, hours, rent, share in EMPLOYEES:
            if code not in logged_employees:
                continue
            assigns = split_assign.get(code) or [(DEFAULT_PROJECT[code], 1.0)]
            # 週次っぽく4営業日に分けて記入（合計は所定時間の9割前後）
            total_hours = hours * rng.uniform(0.85, 1.0)
            for i, (prj_code, ratio) in enumerate(assigns):
                for w in range(4):
                    d = date(y, m, 2 + w * 7 + i)
                    session.add(TimesheetEntry(
                        employee_id=employees[code].id, project_id=projects[prj_code].id,
                        work_date=d, hours=round(total_hours * ratio / 4, 2),
                        status="approved"))

    # プロジェクト実績・予算
    base_actuals = {
        "herb": (7_260_000, 1_500_000), "oxalis": (5_000_000, 2_600_000),
        "orchid": (24_000_000, 20_000_000), "aerides": (30_000_000, 27_000_000),
        "turkey": (14_000_000, 0), "watermelon": (60_000_000, 30_000_000),
        "antelope": (18_000_000, 12_000_000), "samurai": (9_000_000, 4_500_000),
        "aiko": (0, 0), "volt": (6_000_000, 3_200_000),
    }
    for ym in MONTHS:
        for code, (rev, out) in base_actuals.items():
            jitter = rng.uniform(0.8, 1.2)
            session.add(ProjectMonthActual(
                project_id=projects[code].id, year_month=ym,
                revenue=round(rev * jitter), outsourcing_cost=round(out * jitter),
                source_file="seed"))
            session.add(ProjectBudget(
                project_id=projects[code].id, year_month=ym,
                revenue_budget=rev, outsourcing_budget=out,
                labor_budget=round(rev * 0.12), overhead_budget=round(rev * 0.05),
                source_file="seed"))

    # MF会計 間接費（全社プール）
    overhead_amounts = {
        "地代家賃": 4_000_000, "通信費": 500_000, "水道光熱費": 280_000,
        "旅費交通費": 900_000, "支払手数料": 600_000, "福利厚生費": 550_000,
        "リース料": 200_000, "接待交際費": 150_000, "税理士報酬": 300_000,
    }
    for ym in MONTHS:
        for name, amount in overhead_amounts.items():
            session.add(GLOverheadFact(
                year_month=ym, account_name=name, department_raw="",
                amount=round(amount * rng.uniform(0.85, 1.15)), source_file="seed"))

    # 現行Excel実績（突合レビュー用・会社合計のみ）
    for ym in MONTHS:
        rev = sum(v[0] for v in base_actuals.values())
        out = sum(v[1] for v in base_actuals.values())
        session.add(LegacyActual(
            year_month=ym, scope_type="company", division_id=None,
            revenue=round(rev * rng.uniform(0.95, 1.05)),
            outsourcing_cost=round(out * rng.uniform(0.95, 1.05)),
            labor_cost=round(sum(e[3] for e in EMPLOYEES) * 1.155),
            overhead_cost=round(sum(overhead_amounts.values()) * rng.uniform(0.9, 1.1)),
            operating_profit=0, source_file="seed"))

    session.commit()
    return {"status": "ok", "months": MONTHS,
            "employees": len(EMPLOYEES), "projects": len(PROJECTS)}
