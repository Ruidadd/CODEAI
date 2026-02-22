"""
Employee work status tracker — observes communication signals to
understand team health without intrusive surveillance.

PRIVACY PRINCIPLE: This tracker observes aggregate patterns (response times,
activity levels, collaboration frequency) — NOT message content.
All insights are used to HELP employees, not monitor them.
"""

import logging
from datetime import datetime, timedelta
from collections import defaultdict
from typing import Optional

from digital_employee.database.crud import DatabaseCRUD

logger = logging.getLogger(__name__)


class WorkloadSignal:
    """Signal types for employee work pattern analysis."""
    EMAIL_SENT = "email_sent"
    EMAIL_RECEIVED = "email_received"
    TEAMS_MESSAGE = "teams_message"
    TEAMS_REACTION = "teams_reaction"
    MEETING_ATTENDED = "meeting_attended"
    MEETING_ORGANIZED = "meeting_organized"
    LATE_RESPONSE = "late_response"       # Response after-hours
    WEEKEND_ACTIVITY = "weekend_activity"
    TASK_COMPLETED = "task_completed"
    DEADLINE_MISSED = "deadline_missed"


class EmployeeTracker:
    """
    Tracks employee work patterns and health signals.

    This system is designed to:
    - Surface employees who may need support (overloaded, disengaged, blocked)
    - Identify collaboration patterns (isolated employees, over-dependents)
    - Help managers proactively address issues

    It is NOT designed to:
    - Track message content for surveillance
    - Create performance records for HR
    - Enable micromanagement

    All insights are suggestions for proactive support, not performance metrics.
    """

    # Activity thresholds for health assessment
    ACTIVITY_THRESHOLDS = {
        "low_activity_days": 3,      # No signal for 3 days = concerning
        "overwork_daily_hours": 10,  # More than 10h/day signals = potential overwork
        "weekend_signals_threshold": 5,  # More than 5 weekend signals/week
        "late_night_hour": 22,       # Activity after 10pm
    }

    def __init__(self, db: DatabaseCRUD):
        self.db = db

    # ─────────────────────────────────────────────
    # Employee Registry
    # ─────────────────────────────────────────────

    def register_employee(
        self,
        email: str,
        name: str,
        department: str = "",
        role: str = "",
        manager_email: str = "",
        team_members: list[str] = None,
    ) -> dict:
        """Register an employee for work pattern tracking."""
        employee = {
            "email": email,
            "name": name,
            "department": department,
            "role": role,
            "manager_email": manager_email,
            "team_members": team_members or [],
            "status": "active",
            "health_status": "nominal",  # nominal|watch|support_needed
            "last_activity_at": None,
            "signals_count_7d": 0,
            "meetings_count_7d": 0,
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
        }
        # Check if already exists
        existing = self.db.find("employees", {"email": email})
        if existing:
            return self.db.update("employees", existing[0]["id"], {
                "name": name, "department": department, "role": role,
                "manager_email": manager_email,
            })
        return self.db.create("employees", employee)

    # ─────────────────────────────────────────────
    # Signal Ingestion
    # ─────────────────────────────────────────────

    def record_signal(
        self,
        employee_email: str,
        signal_type: str,
        timestamp: datetime = None,
        metadata: dict = None,
    ):
        """
        Record an activity signal for an employee.
        Signals come from email, Teams, calendar — NOT message content.
        """
        if timestamp is None:
            timestamp = datetime.utcnow()

        signal = {
            "employee_email": employee_email,
            "signal_type": signal_type,
            "timestamp": timestamp.isoformat(),
            "hour_of_day": timestamp.hour,
            "day_of_week": timestamp.weekday(),  # 0=Monday, 6=Sunday
            "is_weekend": timestamp.weekday() >= 5,
            "is_late_night": timestamp.hour >= self.ACTIVITY_THRESHOLDS["late_night_hour"],
            "metadata": metadata or {},
        }

        self.db.create("employee_signals", signal)

        # Update employee's last activity
        employees = self.db.find("employees", {"email": employee_email})
        if employees:
            self.db.update("employees", employees[0]["id"], {
                "last_activity_at": timestamp.isoformat(),
                "updated_at": datetime.utcnow().isoformat(),
            })

    def ingest_email_signal(self, sender_email: str, timestamp: datetime = None):
        """Record that an employee sent an email."""
        self.record_signal(sender_email, WorkloadSignal.EMAIL_SENT, timestamp)

    def ingest_teams_signal(self, sender_email: str, timestamp: datetime = None, channel: str = ""):
        """Record Teams activity for an employee."""
        self.record_signal(
            sender_email, WorkloadSignal.TEAMS_MESSAGE, timestamp,
            metadata={"channel": channel}
        )

    def ingest_meeting_signal(
        self,
        employee_email: str,
        meeting_title: str,
        start_time: datetime,
        is_organizer: bool = False,
    ):
        """Record meeting attendance."""
        signal_type = WorkloadSignal.MEETING_ORGANIZED if is_organizer else WorkloadSignal.MEETING_ATTENDED
        self.record_signal(
            employee_email, signal_type, start_time,
            metadata={"meeting_title": meeting_title}
        )

    # ─────────────────────────────────────────────
    # Health Analysis
    # ─────────────────────────────────────────────

    def get_employee_signals(self, employee_email: str, days: int = 7) -> list[dict]:
        """Get recent signals for an employee."""
        all_signals = self.db.list("employee_signals")
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [
            s for s in all_signals
            if s.get("employee_email") == employee_email
            and datetime.fromisoformat(s["timestamp"]) > cutoff
        ]

    def analyze_employee_health(self, employee_email: str) -> dict:
        """
        Analyze work health signals for an employee.
        Returns insights about potential issues to surface to managers.
        """
        signals_7d = self.get_employee_signals(employee_email, days=7)
        signals_30d = self.get_employee_signals(employee_email, days=30)

        employees = self.db.find("employees", {"email": employee_email})
        employee = employees[0] if employees else {}

        # --- Compute metrics ---
        total_7d = len(signals_7d)
        weekend_signals = sum(1 for s in signals_7d if s.get("is_weekend"))
        late_night_signals = sum(1 for s in signals_7d if s.get("is_late_night"))
        meeting_signals = sum(1 for s in signals_7d if s["signal_type"] in
                              (WorkloadSignal.MEETING_ATTENDED, WorkloadSignal.MEETING_ORGANIZED))
        tasks_completed = sum(1 for s in signals_7d if s["signal_type"] == WorkloadSignal.TASK_COMPLETED)
        deadlines_missed = sum(1 for s in signals_7d if s["signal_type"] == WorkloadSignal.DEADLINE_MISSED)

        # Activity by day of week
        daily_counts = defaultdict(int)
        for s in signals_7d:
            day = datetime.fromisoformat(s["timestamp"]).strftime("%a")
            daily_counts[day] += 1

        # Last activity
        last_activity = employee.get("last_activity_at")
        days_since_activity = 999
        if last_activity:
            last_dt = datetime.fromisoformat(last_activity)
            days_since_activity = (datetime.utcnow() - last_dt).days

        # --- Assess health ---
        health_signals = []
        health_status = "nominal"

        if days_since_activity >= self.ACTIVITY_THRESHOLDS["low_activity_days"]:
            health_signals.append({
                "type": "low_activity",
                "severity": "medium",
                "description": f"No activity detected for {days_since_activity} days",
                "recommendation": "Check in to ensure they are not blocked or disengaged",
            })
            health_status = "watch"

        if weekend_signals >= self.ACTIVITY_THRESHOLDS["weekend_signals_threshold"]:
            health_signals.append({
                "type": "overwork_weekend",
                "severity": "medium",
                "description": f"Working weekends ({weekend_signals} signals this week)",
                "recommendation": "Discuss workload and sustainability",
            })
            health_status = "watch"

        if late_night_signals >= 3:
            health_signals.append({
                "type": "overwork_late_night",
                "severity": "high",
                "description": f"Frequent late-night activity ({late_night_signals} signals this week)",
                "recommendation": "Urgent: review workload and check for burnout risk",
            })
            health_status = "support_needed"

        if deadlines_missed >= 2:
            health_signals.append({
                "type": "deadline_issues",
                "severity": "high",
                "description": f"Multiple missed deadlines ({deadlines_missed} this week)",
                "recommendation": "Identify blockers and provide support",
            })
            health_status = "support_needed"

        if meeting_signals >= 20:  # More than 20 meeting signals per week
            health_signals.append({
                "type": "meeting_overload",
                "severity": "medium",
                "description": f"Very high meeting load ({meeting_signals} meetings this week)",
                "recommendation": "Review meeting necessity and consider protecting focus time",
            })

        # Update health status in DB
        if employees:
            self.db.update("employees", employees[0]["id"], {
                "health_status": health_status,
                "updated_at": datetime.utcnow().isoformat(),
            })

        return {
            "employee_email": employee_email,
            "employee_name": employee.get("name", employee_email),
            "health_status": health_status,
            "metrics_7d": {
                "total_signals": total_7d,
                "weekend_signals": weekend_signals,
                "late_night_signals": late_night_signals,
                "meetings": meeting_signals,
                "tasks_completed": tasks_completed,
                "deadlines_missed": deadlines_missed,
                "days_since_activity": days_since_activity,
                "activity_by_day": dict(daily_counts),
            },
            "health_signals": health_signals,
            "needs_attention": len(health_signals) > 0,
        }

    def get_team_health_overview(self, manager_email: str = None) -> list[dict]:
        """Get health overview for all employees (or a specific team)."""
        if manager_email:
            employees = self.db.find("employees", {"manager_email": manager_email})
        else:
            employees = self.db.list("employees")

        results = []
        for emp in employees:
            if emp.get("status") != "active":
                continue
            health = self.analyze_employee_health(emp["email"])
            if health["needs_attention"]:
                results.append(health)

        return sorted(results, key=lambda e: {
            "support_needed": 0, "watch": 1, "nominal": 2
        }.get(e["health_status"], 3))

    def get_disengaged_employees(self, days_inactive: int = 5) -> list[dict]:
        """Find employees showing low activity signals."""
        all_employees = self.db.list("employees")
        disengaged = []
        now = datetime.utcnow()

        for emp in all_employees:
            if emp.get("status") != "active":
                continue
            last_activity = emp.get("last_activity_at")
            if not last_activity:
                disengaged.append({**emp, "days_inactive": 999})
                continue
            days = (now - datetime.fromisoformat(last_activity)).days
            if days >= days_inactive:
                disengaged.append({**emp, "days_inactive": days})

        return sorted(disengaged, key=lambda e: e.get("days_inactive", 0), reverse=True)

    def generate_team_digest(self) -> dict:
        """Generate a team health summary."""
        all_employees = self.db.list("employees")
        active_employees = [e for e in all_employees if e.get("status") == "active"]

        needs_attention = self.get_team_health_overview()
        disengaged = self.get_disengaged_employees(days_inactive=5)

        return {
            "total_employees": len(active_employees),
            "employees_needing_attention": len(needs_attention),
            "attention_details": [
                {
                    "name": e["employee_name"],
                    "email": e["employee_email"],
                    "status": e["health_status"],
                    "top_signal": e["health_signals"][0]["description"] if e["health_signals"] else "Unknown",
                }
                for e in needs_attention[:10]
            ],
            "potentially_disengaged": len(disengaged),
            "disengaged_details": [
                {
                    "name": e.get("name", e["email"]),
                    "email": e["email"],
                    "days_inactive": e.get("days_inactive", 0),
                }
                for e in disengaged[:5]
            ],
        }
