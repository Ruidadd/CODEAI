"""
Tests for the business tracker modules.
"""

import pytest
from datetime import datetime, timedelta

from digital_employee.database.crud import DatabaseCRUD
from digital_employee.trackers.project_tracker import ProjectTracker, ProjectStatus
from digital_employee.trackers.meeting_tracker import MeetingTracker
from digital_employee.trackers.contract_tracker import ContractTracker, ContractStatus
from digital_employee.trackers.employee_tracker import EmployeeTracker


@pytest.fixture
def db(tmp_path):
    """Provide a temporary in-memory database for tests."""
    return DatabaseCRUD(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def project_tracker(db):
    return ProjectTracker(db=db)


@pytest.fixture
def meeting_tracker(db):
    return MeetingTracker(db=db)


@pytest.fixture
def contract_tracker(db):
    return ContractTracker(db=db)


@pytest.fixture
def employee_tracker(db):
    return EmployeeTracker(db=db)


# ─────────────────────────────────────────────
# Database Tests
# ─────────────────────────────────────────────

def test_db_crud(db):
    doc = db.create("test_col", {"name": "Alice", "role": "engineer"})
    assert doc["id"] is not None
    assert doc["name"] == "Alice"

    fetched = db.get("test_col", doc["id"])
    assert fetched["name"] == "Alice"

    updated = db.update("test_col", doc["id"], {"role": "senior engineer"})
    assert updated["role"] == "senior engineer"

    found = db.find("test_col", {"name": "Alice"})
    assert len(found) == 1

    deleted = db.delete("test_col", doc["id"])
    assert deleted is True

    assert db.get("test_col", doc["id"]) is None


# ─────────────────────────────────────────────
# Project Tracker Tests
# ─────────────────────────────────────────────

def test_create_project(project_tracker):
    project = project_tracker.create_project(
        name="Q4 Product Launch",
        owner_email="pm@example.com",
        priority="high",
        deadline=datetime.utcnow() + timedelta(days=30),
    )
    assert project["name"] == "Q4 Product Launch"
    assert project["status"] == ProjectStatus.ON_TRACK
    assert project["owner_email"] == "pm@example.com"


def test_stale_project_detection(project_tracker):
    # Create a project with an old last_update_at
    project = project_tracker.create_project(
        name="Old Project",
        owner_email="pm@example.com",
        priority="high",
    )
    # Manually set stale date
    project_tracker.db.update("projects", project["id"], {
        "last_update_at": (datetime.utcnow() - timedelta(days=5)).isoformat()
    })

    stale = project_tracker.get_stale_projects()
    assert any(p["name"] == "Old Project" for p in stale)


def test_at_risk_project_deadline(project_tracker):
    project = project_tracker.create_project(
        name="Urgent Project",
        owner_email="pm@example.com",
        deadline=datetime.utcnow() + timedelta(days=3),  # Due in 3 days
        priority="high",
    )

    at_risk = project_tracker.get_at_risk_projects()
    assert any(p["name"] == "Urgent Project" for p in at_risk)


def test_project_health_score(project_tracker):
    project = project_tracker.create_project(
        name="Healthy Project",
        owner_email="pm@example.com",
        priority="medium",
    )
    score = project_tracker.calculate_health_score(project)
    assert 0 <= score <= 100
    assert score == 100  # Fresh project should be 100


# ─────────────────────────────────────────────
# Meeting Tracker Tests
# ─────────────────────────────────────────────

def test_register_meeting(meeting_tracker):
    meeting = meeting_tracker.register_meeting(
        title="Sprint Planning",
        start_time=datetime.utcnow() + timedelta(days=1),
        end_time=datetime.utcnow() + timedelta(days=1, hours=1),
        organizer_email="scrum@example.com",
        participants=["dev1@example.com", "dev2@example.com"],
    )
    assert meeting["title"] == "Sprint Planning"
    assert meeting["status"] == "scheduled"
    assert len(meeting["participants"]) == 2


def test_overdue_action_items(meeting_tracker):
    meeting = meeting_tracker.register_meeting(
        title="Old Meeting",
        start_time=datetime.utcnow() - timedelta(days=10),
        end_time=datetime.utcnow() - timedelta(days=10, hours=-1),
        organizer_email="mgr@example.com",
        participants=["emp@example.com"],
    )
    # Add overdue action item
    meeting_tracker.store_processed_results(meeting["id"], {
        "action_items": [
            {
                "task": "Send report",
                "owner": "emp@example.com",
                "deadline": (datetime.utcnow() - timedelta(days=5)).isoformat(),
                "priority": "high",
            }
        ],
        "decisions": [],
        "open_questions": [],
        "summary": "Test meeting",
    })

    overdue = meeting_tracker.get_overdue_action_items()
    assert len(overdue) >= 1
    assert overdue[0]["task"] == "Send report"


# ─────────────────────────────────────────────
# Contract Tracker Tests
# ─────────────────────────────────────────────

def test_create_contract(contract_tracker):
    contract = contract_tracker.create_contract(
        title="SaaS License Agreement",
        contract_type="vendor",
        counterparty="Acme Corp",
        owner_email="legal@example.com",
        start_date=datetime.utcnow() - timedelta(days=180),
        end_date=datetime.utcnow() + timedelta(days=25),
        value=50000.0,
    )
    assert contract["title"] == "SaaS License Agreement"
    assert contract["counterparty"] == "Acme Corp"


def test_expiry_alerts(contract_tracker):
    contract = contract_tracker.create_contract(
        title="Expiring Contract",
        contract_type="vendor",
        counterparty="Vendor Inc",
        owner_email="legal@example.com",
        start_date=datetime.utcnow() - timedelta(days=365),
        end_date=datetime.utcnow() + timedelta(days=5),  # Expiring in 5 days
    )

    alerts = contract_tracker.get_alerts_due()
    assert any(a["id"] == contract["id"] for a in alerts)


def test_pending_signatures(contract_tracker):
    contract = contract_tracker.create_contract(
        title="NDA",
        contract_type="nda",
        counterparty="Partner Co",
        owner_email="legal@example.com",
        start_date=datetime.utcnow(),
        signatories=["ceo@example.com", "partner@example.com"],
    )
    contract_tracker.db.update("contracts", contract["id"], {
        "status": ContractStatus.PENDING_SIGNATURE
    })

    pending = contract_tracker.get_pending_signatures()
    assert any(p["id"] == contract["id"] for p in pending)


# ─────────────────────────────────────────────
# Employee Tracker Tests
# ─────────────────────────────────────────────

def test_register_employee(employee_tracker):
    emp = employee_tracker.register_employee(
        email="alice@example.com",
        name="Alice Smith",
        department="Engineering",
        role="Software Engineer",
    )
    assert emp["email"] == "alice@example.com"
    assert emp["name"] == "Alice Smith"


def test_signal_recording(employee_tracker):
    employee_tracker.register_employee(
        email="bob@example.com",
        name="Bob Jones",
    )
    # Record some signals
    employee_tracker.ingest_email_signal("bob@example.com")
    employee_tracker.ingest_teams_signal("bob@example.com", channel="general")

    signals = employee_tracker.get_employee_signals("bob@example.com", days=1)
    assert len(signals) >= 2


def test_health_analysis_low_activity(employee_tracker):
    employee_tracker.register_employee(
        email="quiet@example.com",
        name="Quiet Employee",
    )
    # Set last activity to 10 days ago
    employees = employee_tracker.db.find("employees", {"email": "quiet@example.com"})
    employee_tracker.db.update("employees", employees[0]["id"], {
        "last_activity_at": (datetime.utcnow() - timedelta(days=10)).isoformat()
    })

    health = employee_tracker.analyze_employee_health("quiet@example.com")
    assert health["needs_attention"] is True
    assert health["health_status"] in ("watch", "support_needed")
