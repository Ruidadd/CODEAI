"""
Pydantic models for the Digital Employee REST API.
"""

from datetime import datetime
from typing import Any, Optional
from pydantic import BaseModel, Field


# ─────────────────────────────────────────────
# Request Models
# ─────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "main"


class EmailWebhookPayload(BaseModel):
    """Microsoft Graph change notification payload."""
    value: list[dict]


class ProcessEmailRequest(BaseModel):
    message_id: str
    auto_respond: bool = False


class ProcessMeetingRequest(BaseModel):
    meeting_id: str
    notes: Optional[str] = None
    transcript: Optional[str] = None


class CreateProjectRequest(BaseModel):
    name: str
    owner_email: str
    description: str = ""
    priority: str = "medium"
    deadline: Optional[datetime] = None
    team_members: list[str] = []
    tags: list[str] = []


class UpdateProjectRequest(BaseModel):
    status: Optional[str] = None
    update_note: str = ""
    updated_by: str = ""


class AddMilestoneRequest(BaseModel):
    title: str
    due_date: datetime
    owner_email: str = ""
    description: str = ""


class CreateContractRequest(BaseModel):
    title: str
    contract_type: str
    counterparty: str
    owner_email: str
    start_date: datetime
    end_date: Optional[datetime] = None
    value: float = 0.0
    currency: str = "USD"
    auto_renewal: bool = False
    renewal_notice_days: int = 30
    signatories: list[str] = []
    tags: list[str] = []
    notes: str = ""


class RegisterEmployeeRequest(BaseModel):
    email: str
    name: str
    department: str = ""
    role: str = ""
    manager_email: str = ""
    team_members: list[str] = []


class GenerateFollowupRequest(BaseModel):
    item_type: str
    item_name: str
    recipient_name: str
    last_status: str
    days_since_update: int
    relationship_context: str = "colleague"


class StatusReportRequest(BaseModel):
    period: str = "weekly"
    send_email: bool = False
    recipients: list[str] = []


# ─────────────────────────────────────────────
# Response Models
# ─────────────────────────────────────────────

class ChatResponse(BaseModel):
    response: str
    thread_id: str


class AgentBriefingResponse(BaseModel):
    known_people: int
    tracked_projects: int
    tracked_contracts: int
    tracked_meetings: int
    pending_followups: int
    overdue_followups: int
    recent_signals: int
    recent_insights: int


class DigestResponse(BaseModel):
    projects: dict
    meetings: dict
    contracts: dict
    team: dict
    generated_at: str


class HealthResponse(BaseModel):
    status: str
    agent_name: str
    agent_email: str
    scheduler_running: bool
    jobs: list[dict]
    db_stats: dict


class JobStatusResponse(BaseModel):
    jobs: list[dict]
    scheduler_running: bool
