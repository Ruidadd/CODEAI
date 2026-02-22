"""
Project tracker — monitors project health, milestones, and status.
Proactively surfaces at-risk projects and triggers follow-up actions.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from digital_employee.database.crud import DatabaseCRUD

logger = logging.getLogger(__name__)


class ProjectStatus:
    ON_TRACK = "on_track"
    AT_RISK = "at_risk"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DELAYED = "delayed"


class ProjectTracker:
    """
    Tracks all active projects, their milestones, owners, and health signals.
    Generates follow-up actions when projects go silent or hit risk indicators.
    """

    # Days without update before escalating
    STALE_THRESHOLD_DAYS = {
        "critical": 1,
        "high": 3,
        "medium": 7,
        "low": 14,
    }

    def __init__(self, db: DatabaseCRUD):
        self.db = db

    # ─────────────────────────────────────────────
    # Project CRUD
    # ─────────────────────────────────────────────

    def create_project(
        self,
        name: str,
        owner_email: str,
        description: str = "",
        priority: str = "medium",
        deadline: Optional[datetime] = None,
        team_members: list[str] = None,
        tags: list[str] = None,
    ) -> dict:
        """Register a new project to track."""
        project = {
            "name": name,
            "owner_email": owner_email,
            "description": description,
            "priority": priority,
            "status": ProjectStatus.ON_TRACK,
            "deadline": deadline.isoformat() if deadline else None,
            "team_members": team_members or [],
            "tags": tags or [],
            "created_at": datetime.utcnow().isoformat(),
            "last_update_at": datetime.utcnow().isoformat(),
            "milestones": [],
            "updates": [],
            "health_score": 100,  # 0-100
        }
        saved = self.db.create("projects", project)
        logger.info(f"Project created: {name} (owner: {owner_email})")
        return saved

    def update_project_status(
        self,
        project_id: str,
        status: str,
        update_note: str = "",
        updated_by: str = "",
    ) -> dict:
        """Update project status with an optional note."""
        update = {
            "status": status,
            "last_update_at": datetime.utcnow().isoformat(),
        }
        if update_note:
            note_entry = {
                "content": update_note,
                "author": updated_by,
                "timestamp": datetime.utcnow().isoformat(),
            }
            project = self.db.get("projects", project_id)
            updates = project.get("updates", [])
            updates.append(note_entry)
            update["updates"] = updates

        return self.db.update("projects", project_id, update)

    def add_milestone(
        self,
        project_id: str,
        title: str,
        due_date: datetime,
        owner_email: str = "",
        description: str = "",
    ) -> dict:
        """Add a milestone to a project."""
        project = self.db.get("projects", project_id)
        milestones = project.get("milestones", [])
        milestone = {
            "id": f"ms_{len(milestones) + 1}",
            "title": title,
            "due_date": due_date.isoformat(),
            "owner_email": owner_email,
            "description": description,
            "status": "pending",
            "completed_at": None,
        }
        milestones.append(milestone)
        return self.db.update("projects", project_id, {"milestones": milestones})

    # ─────────────────────────────────────────────
    # Health Analysis
    # ─────────────────────────────────────────────

    def get_all_projects(self) -> list[dict]:
        return self.db.list("projects")

    def get_stale_projects(self) -> list[dict]:
        """Return projects that haven't been updated within their priority threshold."""
        all_projects = self.get_all_projects()
        stale = []
        now = datetime.utcnow()

        for project in all_projects:
            if project.get("status") in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
                continue

            priority = project.get("priority", "medium")
            threshold_days = self.STALE_THRESHOLD_DAYS.get(priority, 7)
            last_update = project.get("last_update_at")

            if last_update:
                last_dt = datetime.fromisoformat(last_update)
                days_stale = (now - last_dt).days
                if days_stale >= threshold_days:
                    project["days_stale"] = days_stale
                    project["threshold_days"] = threshold_days
                    stale.append(project)

        return sorted(stale, key=lambda p: p.get("days_stale", 0), reverse=True)

    def get_at_risk_projects(self) -> list[dict]:
        """Return projects with upcoming deadlines or overdue milestones."""
        all_projects = self.get_all_projects()
        at_risk = []
        now = datetime.utcnow()

        for project in all_projects:
            if project.get("status") in (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED):
                continue

            risk_reasons = []

            # Check overall deadline
            deadline_str = project.get("deadline")
            if deadline_str:
                deadline_dt = datetime.fromisoformat(deadline_str)
                days_to_deadline = (deadline_dt - now).days
                if days_to_deadline < 0:
                    risk_reasons.append(f"OVERDUE by {abs(days_to_deadline)} days")
                elif days_to_deadline <= 7:
                    risk_reasons.append(f"Due in {days_to_deadline} days")
                elif days_to_deadline <= 14:
                    risk_reasons.append(f"Approaching deadline ({days_to_deadline} days)")

            # Check milestones
            for milestone in project.get("milestones", []):
                if milestone.get("status") == "completed":
                    continue
                ms_due = milestone.get("due_date")
                if ms_due:
                    ms_dt = datetime.fromisoformat(ms_due)
                    ms_days = (ms_dt - now).days
                    if ms_days < 0:
                        risk_reasons.append(f"Milestone '{milestone['title']}' overdue by {abs(ms_days)} days")
                    elif ms_days <= 3:
                        risk_reasons.append(f"Milestone '{milestone['title']}' due in {ms_days} days")

            # Blocked status
            if project.get("status") == ProjectStatus.BLOCKED:
                risk_reasons.append("Project is blocked")

            if risk_reasons:
                project["risk_reasons"] = risk_reasons
                at_risk.append(project)

        return at_risk

    def calculate_health_score(self, project: dict) -> int:
        """
        Calculate a 0-100 health score for a project.
        100 = perfectly healthy, 0 = critical issue.
        """
        score = 100
        now = datetime.utcnow()

        # Staleness penalty
        last_update = project.get("last_update_at")
        if last_update:
            days_stale = (now - datetime.fromisoformat(last_update)).days
            score -= min(days_stale * 5, 30)  # -5 per stale day, max -30

        # Status penalty
        status_penalty = {
            ProjectStatus.ON_TRACK: 0,
            ProjectStatus.AT_RISK: -20,
            ProjectStatus.BLOCKED: -40,
            ProjectStatus.DELAYED: -25,
        }
        score += status_penalty.get(project.get("status", ""), 0)

        # Deadline proximity penalty
        deadline_str = project.get("deadline")
        if deadline_str:
            deadline_dt = datetime.fromisoformat(deadline_str)
            days_left = (deadline_dt - now).days
            if days_left < 0:
                score -= 40  # Overdue
            elif days_left <= 7:
                score -= 20
            elif days_left <= 14:
                score -= 10

        # Overdue milestones penalty
        for milestone in project.get("milestones", []):
            if milestone.get("status") == "completed":
                continue
            ms_due = milestone.get("due_date")
            if ms_due and datetime.fromisoformat(ms_due) < now:
                score -= 10

        return max(0, min(100, score))

    # ─────────────────────────────────────────────
    # Signals from external sources
    # ─────────────────────────────────────────────

    def ingest_email_signal(self, project_name: str, email_data: dict):
        """Record that a project was mentioned in an email."""
        projects = self.db.find("projects", {"name": project_name})
        if projects:
            project_id = projects[0]["id"]
            self.db.update("projects", project_id, {
                "last_update_at": datetime.utcnow().isoformat(),
            })
            logger.debug(f"Project '{project_name}' updated via email signal")

    def ingest_teams_signal(self, project_name: str, message_data: dict):
        """Record that a project was mentioned in Teams."""
        projects = self.db.find("projects", {"name": project_name})
        if projects:
            project_id = projects[0]["id"]
            self.db.update("projects", project_id, {
                "last_update_at": datetime.utcnow().isoformat(),
            })

    def generate_project_digest(self) -> dict:
        """Generate a summary of all project health."""
        all_projects = self.get_all_projects()
        stale = self.get_stale_projects()
        at_risk = self.get_at_risk_projects()

        return {
            "total_active": len([p for p in all_projects if p.get("status") not in
                                 (ProjectStatus.COMPLETED, ProjectStatus.CANCELLED)]),
            "on_track": len([p for p in all_projects if p.get("status") == ProjectStatus.ON_TRACK]),
            "at_risk": [{"id": p["id"], "name": p["name"], "reasons": p.get("risk_reasons", [])}
                        for p in at_risk],
            "stale": [{"id": p["id"], "name": p["name"], "days_stale": p.get("days_stale", 0),
                       "owner_email": p["owner_email"]}
                      for p in stale],
            "blocked": [{"id": p["id"], "name": p["name"]}
                        for p in all_projects if p.get("status") == ProjectStatus.BLOCKED],
            "completed_recently": [
                {"id": p["id"], "name": p["name"]}
                for p in all_projects
                if p.get("status") == ProjectStatus.COMPLETED
                and p.get("last_update_at")
                and (datetime.utcnow() - datetime.fromisoformat(p["last_update_at"])).days <= 7
            ],
        }
