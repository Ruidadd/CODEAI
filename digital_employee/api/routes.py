"""
FastAPI routes for the Digital Employee REST API.
Provides endpoints for:
- Chat interface
- Email/Teams webhooks
- Manual triggers
- Project/Meeting/Contract/Employee management
- Status reports and digests
"""

import json
import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status

from digital_employee.api.models import (
    AddMilestoneRequest,
    AgentBriefingResponse,
    ChatRequest,
    ChatResponse,
    CreateContractRequest,
    CreateProjectRequest,
    DigestResponse,
    EmailWebhookPayload,
    GenerateFollowupRequest,
    HealthResponse,
    ProcessEmailRequest,
    ProcessMeetingRequest,
    RegisterEmployeeRequest,
    StatusReportRequest,
    UpdateProjectRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_services(request: Request):
    """Dependency injection to get app services."""
    return request.app.state.services


# ─────────────────────────────────────────────
# Health & Status
# ─────────────────────────────────────────────

@router.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check(services=Depends(get_services)):
    """Check the health and status of the digital employee."""
    agent = services["agent"]
    scheduler = services["scheduler"]
    db = services["db"]

    identity = agent.identity
    return HealthResponse(
        status="running",
        agent_name=identity.get("name", "Digital Employee"),
        agent_email=identity.get("email", ""),
        scheduler_running=scheduler.is_running(),
        jobs=scheduler.get_job_status(),
        db_stats=db.get_stats(),
    )


@router.get("/briefing", response_model=AgentBriefingResponse, tags=["System"])
async def get_briefing(services=Depends(get_services)):
    """Get the agent's current memory and work context briefing."""
    agent = services["agent"]
    briefing = agent.get_briefing()
    return AgentBriefingResponse(**briefing)


# ─────────────────────────────────────────────
# Chat Interface
# ─────────────────────────────────────────────

@router.post("/chat", response_model=ChatResponse, tags=["Chat"])
async def chat(request: ChatRequest, services=Depends(get_services)):
    """Chat directly with the digital employee."""
    agent = services["agent"]
    response = agent.chat(request.message, thread_id=request.thread_id)
    return ChatResponse(response=response, thread_id=request.thread_id)


# ─────────────────────────────────────────────
# Email Webhooks & Processing
# ─────────────────────────────────────────────

@router.post("/webhooks/email", tags=["Webhooks"])
async def email_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Receive Microsoft Graph email change notifications."""
    # MS Graph sends a validation token on first subscription
    validation_token = request.query_params.get("validationToken")
    if validation_token:
        return validation_token

    body = await request.json()
    notifications = body.get("value", [])

    for notification in notifications:
        resource_data = notification.get("resourceData", {})
        message_id = resource_data.get("id")
        if message_id:
            background_tasks.add_task(
                _process_email_background,
                services=services,
                message_id=message_id,
            )

    return {"status": "accepted"}


@router.post("/emails/process", tags=["Email"])
async def process_email(
    req: ProcessEmailRequest,
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Manually trigger processing of a specific email."""
    background_tasks.add_task(
        _process_email_background,
        services=services,
        message_id=req.message_id,
        auto_respond=req.auto_respond,
    )
    return {"status": "processing", "message_id": req.message_id}


async def _process_email_background(services: dict, message_id: str, auto_respond: bool = False):
    """Background task: fetch, analyze, and optionally respond to an email."""
    try:
        email_client = services["email_client"]
        agent = services["agent"]
        employee_tracker = services["employee_tracker"]

        email = email_client.get_message(message_id)
        analysis = agent.analyze_email(email)

        logger.info(
            f"Email analyzed: '{email['subject']}' "
            f"intent={analysis.get('intent')} urgency={analysis.get('urgency')}"
        )

        # Record signal for sender
        employee_tracker.ingest_email_signal(
            email.get("sender_email", ""),
            timestamp=datetime.fromisoformat(email["received_at"]) if email.get("received_at") else None,
        )

        # Auto-respond if requested and action is needed
        if auto_respond and analysis.get("intent") == "action_required":
            draft = agent.draft_email_response(email, analysis)
            if draft.get("body"):
                email_client.send_email(
                    to=[email["sender_email"]],
                    subject=draft["subject"],
                    body=draft["body"],
                    reply_to_message_id=message_id,
                )
                logger.info(f"Auto-response sent for email: {email['subject']}")

        # Mark as read
        email_client.mark_as_read(message_id)

    except Exception as e:
        logger.error(f"Error processing email {message_id}: {e}", exc_info=True)


# ─────────────────────────────────────────────
# Teams Webhooks & Processing
# ─────────────────────────────────────────────

@router.post("/webhooks/teams", tags=["Webhooks"])
async def teams_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Receive Microsoft Graph Teams change notifications."""
    validation_token = request.query_params.get("validationToken")
    if validation_token:
        return validation_token

    body = await request.json()
    notifications = body.get("value", [])

    for notification in notifications:
        resource = notification.get("resource", "")
        resource_data = notification.get("resourceData", {})
        background_tasks.add_task(
            _process_teams_notification,
            services=services,
            resource=resource,
            resource_data=resource_data,
        )

    return {"status": "accepted"}


async def _process_teams_notification(services: dict, resource: str, resource_data: dict):
    """Background task: process a Teams notification."""
    try:
        teams_client = services["teams_client"]
        agent = services["agent"]
        employee_tracker = services["employee_tracker"]

        message_id = resource_data.get("id", "")
        logger.info(f"Processing Teams notification for resource: {resource}")

        # Extract team/channel from resource path if present
        # e.g. /teams/{teamId}/channels/{channelId}/messages/{messageId}
        parts = resource.split("/")
        if "teams" in parts and "channels" in parts:
            team_idx = parts.index("teams")
            channel_idx = parts.index("channels")
            if team_idx + 1 < len(parts) and channel_idx + 1 < len(parts):
                team_id = parts[team_idx + 1]
                channel_id = parts[channel_idx + 1]
                messages = teams_client.get_channel_messages(team_id, channel_id, top=10)
                if messages:
                    channel_name = f"teams/{team_id}/{channel_id}"
                    analysis = agent.analyze_teams_messages(channel_name, messages)
                    logger.info(f"Teams channel analyzed: {len(messages)} messages, "
                                f"sentiment={analysis.get('sentiment')}")

                    # Record signals for active participants
                    for participant in analysis.get("key_participants", []):
                        employee_tracker.ingest_teams_signal(participant, channel=channel_name)

    except Exception as e:
        logger.error(f"Error processing Teams notification: {e}", exc_info=True)


# ─────────────────────────────────────────────
# Meetings
# ─────────────────────────────────────────────

@router.post("/meetings/process", tags=["Meetings"])
async def process_meeting(
    req: ProcessMeetingRequest,
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Process a completed meeting to extract action items and generate follow-ups."""
    meeting_tracker = services["meeting_tracker"]
    agent = services["agent"]

    meeting = meeting_tracker.db.get("meetings", req.meeting_id)
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")

    if req.notes:
        meeting_tracker.record_meeting_notes(req.meeting_id, req.notes)
        meeting["notes"] = req.notes
    if req.transcript:
        meeting_tracker.record_transcript(req.meeting_id, req.transcript)
        meeting["transcript"] = req.transcript

    background_tasks.add_task(
        _process_meeting_background,
        services=services,
        meeting=meeting,
    )
    return {"status": "processing", "meeting_id": req.meeting_id}


async def _process_meeting_background(services: dict, meeting: dict):
    """Background task: AI-process a meeting."""
    try:
        agent = services["agent"]
        meeting_tracker = services["meeting_tracker"]
        email_client = services["email_client"]

        result = agent.process_meeting(meeting)
        meeting_tracker.store_processed_results(meeting["id"], result)

        # Send follow-up emails to participants
        follow_up_emails = result.get("follow_up_emails", [])
        for follow_up in follow_up_emails:
            try:
                email_client.send_email(
                    to=[follow_up["recipient"]],
                    subject=follow_up["subject"],
                    body=follow_up["body"],
                )
                logger.info(f"Meeting follow-up sent to {follow_up['recipient']}")
            except Exception as e:
                logger.error(f"Failed to send follow-up to {follow_up['recipient']}: {e}")

        meeting_tracker.mark_followup_sent(meeting["id"])
        logger.info(f"Meeting '{meeting.get('title')}' processed: "
                    f"{len(result.get('action_items', []))} action items extracted")

    except Exception as e:
        logger.error(f"Error processing meeting {meeting.get('id')}: {e}", exc_info=True)


@router.get("/meetings/upcoming", tags=["Meetings"])
async def get_upcoming_meetings(hours: int = 48, services=Depends(get_services)):
    """Get upcoming meetings in the next N hours."""
    meeting_tracker = services["meeting_tracker"]
    return meeting_tracker.get_upcoming_meetings(within_hours=hours)


@router.get("/meetings/overdue-actions", tags=["Meetings"])
async def get_overdue_action_items(services=Depends(get_services)):
    """Get all overdue action items from meetings."""
    meeting_tracker = services["meeting_tracker"]
    return meeting_tracker.get_overdue_action_items()


# ─────────────────────────────────────────────
# Projects
# ─────────────────────────────────────────────

@router.get("/projects", tags=["Projects"])
async def list_projects(services=Depends(get_services)):
    return services["project_tracker"].get_all_projects()


@router.post("/projects", tags=["Projects"])
async def create_project(req: CreateProjectRequest, services=Depends(get_services)):
    return services["project_tracker"].create_project(
        name=req.name,
        owner_email=req.owner_email,
        description=req.description,
        priority=req.priority,
        deadline=req.deadline,
        team_members=req.team_members,
        tags=req.tags,
    )


@router.patch("/projects/{project_id}", tags=["Projects"])
async def update_project(
    project_id: str,
    req: UpdateProjectRequest,
    services=Depends(get_services),
):
    result = services["project_tracker"].update_project_status(
        project_id=project_id,
        status=req.status,
        update_note=req.update_note,
        updated_by=req.updated_by,
    )
    if not result:
        raise HTTPException(status_code=404, detail="Project not found")
    return result


@router.post("/projects/{project_id}/milestones", tags=["Projects"])
async def add_milestone(
    project_id: str,
    req: AddMilestoneRequest,
    services=Depends(get_services),
):
    return services["project_tracker"].add_milestone(
        project_id=project_id,
        title=req.title,
        due_date=req.due_date,
        owner_email=req.owner_email,
        description=req.description,
    )


@router.get("/projects/at-risk", tags=["Projects"])
async def get_at_risk_projects(services=Depends(get_services)):
    return services["project_tracker"].get_at_risk_projects()


# ─────────────────────────────────────────────
# Contracts
# ─────────────────────────────────────────────

@router.get("/contracts", tags=["Contracts"])
async def list_contracts(services=Depends(get_services)):
    return services["contract_tracker"].db.list("contracts")


@router.post("/contracts", tags=["Contracts"])
async def create_contract(req: CreateContractRequest, services=Depends(get_services)):
    return services["contract_tracker"].create_contract(
        title=req.title,
        contract_type=req.contract_type,
        counterparty=req.counterparty,
        owner_email=req.owner_email,
        start_date=req.start_date,
        end_date=req.end_date,
        value=req.value,
        currency=req.currency,
        auto_renewal=req.auto_renewal,
        renewal_notice_days=req.renewal_notice_days,
        signatories=req.signatories,
        tags=req.tags,
        notes=req.notes,
    )


@router.get("/contracts/expiring", tags=["Contracts"])
async def get_expiring_contracts(days: int = 30, services=Depends(get_services)):
    return services["contract_tracker"].get_contracts_expiring_within(days)


@router.get("/contracts/pending-signatures", tags=["Contracts"])
async def get_pending_signatures(services=Depends(get_services)):
    return services["contract_tracker"].get_pending_signatures()


# ─────────────────────────────────────────────
# Employees
# ─────────────────────────────────────────────

@router.get("/employees", tags=["Employees"])
async def list_employees(services=Depends(get_services)):
    return services["employee_tracker"].db.list("employees")


@router.post("/employees", tags=["Employees"])
async def register_employee(req: RegisterEmployeeRequest, services=Depends(get_services)):
    return services["employee_tracker"].register_employee(
        email=req.email,
        name=req.name,
        department=req.department,
        role=req.role,
        manager_email=req.manager_email,
        team_members=req.team_members,
    )


@router.get("/employees/health", tags=["Employees"])
async def get_team_health(manager_email: str = None, services=Depends(get_services)):
    return services["employee_tracker"].get_team_health_overview(manager_email=manager_email)


@router.get("/employees/{email}/health", tags=["Employees"])
async def get_employee_health(email: str, services=Depends(get_services)):
    return services["employee_tracker"].analyze_employee_health(email)


# ─────────────────────────────────────────────
# Follow-ups & Reports
# ─────────────────────────────────────────────

@router.post("/followups/generate", tags=["Follow-ups"])
async def generate_followup(req: GenerateFollowupRequest, services=Depends(get_services)):
    """Generate a proactive follow-up message."""
    agent = services["agent"]
    return agent.generate_proactive_inquiry(
        item_type=req.item_type,
        item_name=req.item_name,
        recipient_name=req.recipient_name,
        last_status=req.last_status,
        days_since_update=req.days_since_update,
        relationship_context=req.relationship_context,
    )


@router.post("/followups/process-overdue", tags=["Follow-ups"])
async def process_overdue_followups(
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Trigger processing of all overdue follow-ups."""
    background_tasks.add_task(_process_overdue_followups, services=services)
    return {"status": "triggered"}


async def _process_overdue_followups(services: dict):
    """Generate and send overdue follow-up messages."""
    agent = services["agent"]
    email_client = services["email_client"]
    teams_client = services["teams_client"]

    inquiries = agent.check_and_generate_followups()
    sent_count = 0

    for inquiry in inquiries:
        try:
            channel = inquiry.get("channel", "email")
            recipient = inquiry.get("recipient", "")

            if channel == "email" and recipient:
                email_client.send_email(
                    to=[recipient],
                    subject=inquiry.get("subject", "Follow-up"),
                    body=inquiry.get("body", ""),
                )
                sent_count += 1
            elif channel in ("teams_dm", "teams_channel") and recipient:
                teams_client.send_dm_to_user(recipient, inquiry.get("body", ""))
                sent_count += 1

        except Exception as e:
            logger.error(f"Failed to send follow-up to {inquiry.get('recipient')}: {e}")

    logger.info(f"Processed {len(inquiries)} overdue follow-ups, sent {sent_count}")


@router.get("/digest", response_model=DigestResponse, tags=["Reports"])
async def get_digest(services=Depends(get_services)):
    """Get a comprehensive digest of all tracked items."""
    return DigestResponse(
        projects=services["project_tracker"].generate_project_digest(),
        meetings=services["meeting_tracker"].generate_meetings_digest(),
        contracts=services["contract_tracker"].generate_contracts_digest(),
        team=services["employee_tracker"].generate_team_digest(),
        generated_at=datetime.utcnow().isoformat(),
    )


@router.post("/reports/status", tags=["Reports"])
async def generate_status_report(
    req: StatusReportRequest,
    background_tasks: BackgroundTasks,
    services=Depends(get_services),
):
    """Generate and optionally email the executive status report."""
    background_tasks.add_task(
        _generate_and_send_status_report,
        services=services,
        period=req.period,
        send_email=req.send_email,
        recipients=req.recipients,
    )
    return {"status": "generating", "period": req.period}


async def _generate_and_send_status_report(
    services: dict,
    period: str,
    send_email: bool,
    recipients: list[str],
):
    """Background task: generate and optionally email status report."""
    try:
        agent = services["agent"]
        project_tracker = services["project_tracker"]
        meeting_tracker = services["meeting_tracker"]
        contract_tracker = services["contract_tracker"]
        employee_tracker = services["employee_tracker"]
        email_client = services.get("email_client")

        report = agent.generate_status_report(
            projects=project_tracker.get_all_projects(),
            meetings=meeting_tracker.db.list("meetings"),
            contracts=contract_tracker.db.list("contracts"),
            employee_signals=employee_tracker.get_team_health_overview(),
            period=period,
        )

        logger.info(f"Status report generated for period: {period}")

        if send_email and recipients and email_client:
            summary = report.get("executive_summary", "Status report available.")
            recommended = report.get("recommended_actions", [])
            rec_text = "\n".join([
                f"• [{a.get('priority', 'medium').upper()}] {a.get('action', '')} — {a.get('owner', 'TBD')} by {a.get('deadline', 'TBD')}"
                for a in recommended[:10]
            ])

            body = f"""Executive Status Report — {period.title()}
Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}

EXECUTIVE SUMMARY
{summary}

RECOMMENDED ACTIONS
{rec_text}

Full report is available in the Digital Employee dashboard.
"""
            email_client.send_email(
                to=recipients,
                subject=f"Digital Employee Status Report — {period.title()} {datetime.utcnow().strftime('%Y-%m-%d')}",
                body=body,
            )
            logger.info(f"Status report emailed to {recipients}")

    except Exception as e:
        logger.error(f"Error generating status report: {e}", exc_info=True)


# ─────────────────────────────────────────────
# Scheduler Control
# ─────────────────────────────────────────────

@router.get("/scheduler/jobs", tags=["Scheduler"])
async def get_scheduler_jobs(services=Depends(get_services)):
    return services["scheduler"].get_job_status()


@router.post("/scheduler/run/{job_id}", tags=["Scheduler"])
async def run_job_now(job_id: str, background_tasks: BackgroundTasks, services=Depends(get_services)):
    """Manually trigger a scheduler job to run immediately."""
    background_tasks.add_task(services["scheduler"].run_job_now, job_id)
    return {"status": "triggered", "job_id": job_id}
