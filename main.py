"""
Digital Employee — Main Application Entry Point

Starts the FastAPI server with all services initialized:
- AI Agent (Claude)
- Microsoft Graph integrations (Email, Teams)
- Business Trackers (Projects, Meetings, Contracts, Employees)
- Background Scheduler
- REST API
"""

import logging
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import Config
from digital_employee.agent.core_agent import DigitalEmployeeAgent
from digital_employee.api.routes import router
from digital_employee.database.crud import DatabaseCRUD
from digital_employee.integrations.email_client import EmailClient
from digital_employee.integrations.ms_graph import MSGraphClient
from digital_employee.integrations.teams_client import TeamsClient
from digital_employee.scheduler.task_scheduler import DigitalEmployeeScheduler
from digital_employee.trackers.contract_tracker import ContractTracker
from digital_employee.trackers.employee_tracker import EmployeeTracker
from digital_employee.trackers.meeting_tracker import MeetingTracker
from digital_employee.trackers.project_tracker import ProjectTracker
from digital_employee.utils.helpers import is_business_hours, sanitize_email_body

# ─────────────────────────────────────────────
# Logging Setup
# ─────────────────────────────────────────────

def setup_logging(level: str = "INFO"):
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[
            logging.StreamHandler(sys.stdout),
        ]
    )
    # Reduce noise from third-party libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)
    logging.getLogger("anthropic").setLevel(logging.WARNING)


logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────
# Application Factory
# ─────────────────────────────────────────────

def create_app(config: Config) -> FastAPI:
    """Create and configure the FastAPI application."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Application lifespan: startup and shutdown."""
        logger.info("=" * 60)
        logger.info(f"Starting Digital Employee: {config.employee_display_name}")
        logger.info(f"Email: {config.employee_email}")
        logger.info("=" * 60)

        # ── Initialize Database ────────────────────
        db = DatabaseCRUD(db_path=config.db_path)
        logger.info(f"Database initialized: {config.db_path}")

        # ── Initialize Trackers ────────────────────
        project_tracker = ProjectTracker(db=db)
        meeting_tracker = MeetingTracker(db=db)
        contract_tracker = ContractTracker(db=db)
        employee_tracker = EmployeeTracker(db=db)

        # ── Initialize AI Agent ────────────────────
        agent = DigitalEmployeeAgent(config=config.to_agent_config())
        logger.info("AI Agent (Claude) initialized")

        # ── Initialize MS Graph Integrations ──────
        ms_enabled = bool(config.ms_tenant_id and config.ms_client_id and config.ms_client_secret)
        graph_client = None
        email_client = None
        teams_client = None

        if ms_enabled:
            graph_client = MSGraphClient(config=config.to_graph_config())
            email_client = EmailClient(graph_client=graph_client, user_email=config.employee_email)
            teams_client = TeamsClient(graph_client=graph_client, user_email=config.employee_email)
            logger.info("Microsoft Graph integrations initialized")

            # Set up webhooks if webhook URL is configured
            if config.webhook_base_url:
                _setup_webhooks(config, email_client, teams_client)
        else:
            logger.warning("Microsoft Graph not configured — email/Teams integration disabled")

        # ── Initialize Scheduler ───────────────────
        scheduler = DigitalEmployeeScheduler(config=config.to_agent_config())

        services = {
            "agent": agent,
            "db": db,
            "graph_client": graph_client,
            "email_client": email_client,
            "teams_client": teams_client,
            "project_tracker": project_tracker,
            "meeting_tracker": meeting_tracker,
            "contract_tracker": contract_tracker,
            "employee_tracker": employee_tracker,
            "scheduler": scheduler,
        }

        # Register scheduler jobs
        _register_scheduler_jobs(services, config)
        scheduler.start()

        # Store services in app state for dependency injection
        app.state.services = services

        logger.info("Digital Employee is ready and monitoring")
        logger.info(f"API docs: http://{config.app_host}:{config.app_port}/docs")

        yield  # Application is running

        # ── Shutdown ───────────────────────────────
        logger.info("Shutting down Digital Employee...")
        scheduler.stop()
        if graph_client:
            graph_client.close()
        logger.info("Digital Employee stopped.")

    app = FastAPI(
        title="Digital Employee",
        description=(
            "An AI-powered organizational assistant that tracks projects, meetings, "
            "contracts, and team health — proactively following up like a CEO/COO."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(router, prefix="/api/v1")
    return app


# ─────────────────────────────────────────────
# Webhook Setup
# ─────────────────────────────────────────────

def _setup_webhooks(config: Config, email_client: EmailClient, teams_client: TeamsClient):
    """Set up Microsoft Graph webhooks for real-time notifications."""
    base_url = config.webhook_base_url.rstrip("/")

    try:
        sub = email_client.subscribe_to_inbox(
            notification_url=f"{base_url}/api/v1/webhooks/email"
        )
        logger.info(f"Email webhook subscription created: {sub.get('id')}")
    except Exception as e:
        logger.warning(f"Failed to create email webhook: {e} (will use polling instead)")

    if config.enable_teams_monitoring:
        try:
            sub = teams_client.subscribe_to_chats(
                notification_url=f"{base_url}/api/v1/webhooks/teams"
            )
            logger.info(f"Teams webhook subscription created: {sub.get('id')}")
        except Exception as e:
            logger.warning(f"Failed to create Teams webhook: {e} (will use polling instead)")


# ─────────────────────────────────────────────
# Scheduler Jobs
# ─────────────────────────────────────────────

def _register_scheduler_jobs(services: dict, config: Config):
    """Register all background jobs with the scheduler."""
    scheduler = services["scheduler"]
    agent = services["agent"]
    email_client = services["email_client"]
    teams_client = services["teams_client"]
    project_tracker = services["project_tracker"]
    meeting_tracker = services["meeting_tracker"]
    contract_tracker = services["contract_tracker"]
    employee_tracker = services["employee_tracker"]

    # ── Email Monitor ──────────────────────────
    if email_client:
        def check_email():
            """Poll inbox for new emails and process them."""
            try:
                since = datetime.utcnow() - timedelta(minutes=config.email_check_interval_min + 1)
                messages = email_client.get_inbox_messages(unread_only=True, since=since, top=20)
                logger.debug(f"Email check: {len(messages)} new messages")
                for msg in messages:
                    analysis = agent.analyze_email(msg)
                    employee_tracker.ingest_email_signal(msg.get("sender_email", ""))
                    logger.info(f"Email processed: '{msg['subject']}' [{analysis.get('urgency', 'medium')}]")
                    email_client.mark_as_read(msg["id"])
            except Exception as e:
                logger.error(f"Email check failed: {e}", exc_info=True)

        scheduler.register_email_monitor(check_email, interval_minutes=config.email_check_interval_min)

    # ── Teams Monitor ──────────────────────────
    if teams_client and config.enable_teams_monitoring:
        def check_teams():
            """Poll Teams channels for recent messages."""
            try:
                teams = teams_client.list_joined_teams()
                since = datetime.utcnow() - timedelta(minutes=config.teams_check_interval_min + 1)
                for team in teams[:5]:  # Limit to 5 teams
                    channels = teams_client.list_team_channels(team["id"])
                    for channel in channels[:3]:  # Limit to 3 channels per team
                        messages = teams_client.get_channel_messages(
                            team["id"], channel["id"], top=20, since=since
                        )
                        if messages:
                            channel_name = f"{team['name']} > {channel['name']}"
                            analysis = agent.analyze_teams_messages(channel_name, messages)
                            for participant in analysis.get("key_participants", []):
                                employee_tracker.ingest_teams_signal(
                                    participant, channel=channel_name
                                )
                            logger.debug(f"Teams: {channel_name} — {len(messages)} messages analyzed")
            except Exception as e:
                logger.error(f"Teams check failed: {e}", exc_info=True)

        scheduler.register_teams_monitor(check_teams, interval_minutes=config.teams_check_interval_min)

    # ── Follow-up Processor ────────────────────
    def process_followups():
        """Check for overdue follow-ups and send inquiries."""
        try:
            if not is_business_hours():
                return  # Don't send follow-ups outside business hours

            inquiries = agent.check_and_generate_followups()
            for inquiry in inquiries:
                recipient = inquiry.get("recipient", "")
                if not recipient:
                    continue
                channel = inquiry.get("channel", "email")
                try:
                    if channel == "email" and email_client:
                        email_client.send_email(
                            to=[recipient],
                            subject=inquiry.get("subject", "Follow-up"),
                            body=inquiry.get("body", ""),
                        )
                    elif channel in ("teams_dm",) and teams_client:
                        teams_client.send_dm_to_user(recipient, inquiry.get("body", ""))
                    logger.info(f"Follow-up sent to {recipient}: {inquiry.get('subject', '')}")
                except Exception as e:
                    logger.error(f"Failed to send follow-up to {recipient}: {e}")
        except Exception as e:
            logger.error(f"Follow-up processor failed: {e}", exc_info=True)

    scheduler.register_followup_processor(process_followups, interval_minutes=config.followup_interval_min)

    # ── Contract Alert Checker ─────────────────
    def check_contract_alerts():
        """Send expiry alerts for contracts."""
        try:
            alerts_due = contract_tracker.get_alerts_due()
            for contract in alerts_due:
                threshold = contract.get("alert_threshold_days", 30)
                owner = contract.get("owner_email", "")
                if owner and email_client:
                    days_left = contract.get("days_until_expiry", threshold)
                    urgency_msg = "URGENT: " if threshold <= 7 else ""
                    body = (
                        f"{urgency_msg}Contract Alert\n\n"
                        f"Contract: {contract['title']}\n"
                        f"Counterparty: {contract.get('counterparty', 'Unknown')}\n"
                        f"Expiry: {contract.get('end_date', 'Unknown')}\n"
                        f"Days Remaining: {days_left}\n"
                        f"Auto-renewal: {'Yes' if contract.get('auto_renewal') else 'No'}\n\n"
                        f"Please review this contract and take appropriate action."
                    )
                    email_client.send_email(
                        to=[owner],
                        subject=f"{urgency_msg}Contract Expiring in {days_left} Days: {contract['title']}",
                        body=body,
                    )
                    contract_tracker.mark_alert_sent(contract["id"], threshold)
                    logger.info(f"Contract alert sent: {contract['title']} ({days_left} days)")
        except Exception as e:
            logger.error(f"Contract alert check failed: {e}", exc_info=True)

    scheduler.register_contract_alert_checker(check_contract_alerts, interval_hours=1)

    # ── Project Health Checker ─────────────────
    def check_project_health():
        """Check for stale or at-risk projects."""
        try:
            stale = project_tracker.get_stale_projects()
            if stale and email_client:
                for project in stale[:5]:  # Process top 5 stale projects
                    owner = project.get("owner_email", "")
                    if owner:
                        inquiry = agent.generate_proactive_inquiry(
                            item_type="project",
                            item_name=project["name"],
                            recipient_name=project.get("owner_email", ""),
                            last_status=project.get("status", "unknown"),
                            days_since_update=project.get("days_stale", 0),
                        )
                        email_client.send_email(
                            to=[owner],
                            subject=inquiry.get("subject", f"Project Update: {project['name']}"),
                            body=inquiry.get("body", ""),
                        )
                        logger.info(f"Project status inquiry sent: {project['name']}")
        except Exception as e:
            logger.error(f"Project health check failed: {e}", exc_info=True)

    scheduler.register_project_health_checker(check_project_health, interval_hours=1)

    # ── Morning Briefing ───────────────────────
    def morning_briefing():
        """Generate and send morning briefing to stakeholders."""
        try:
            project_digest = project_tracker.generate_project_digest()
            meeting_digest = meeting_tracker.generate_meetings_digest()
            contract_digest = contract_tracker.generate_contracts_digest()
            team_digest = employee_tracker.generate_team_digest()

            # Build briefing text
            lines = [
                f"Good morning! Here is your daily briefing from {config.employee_display_name}.",
                f"Date: {datetime.utcnow().strftime('%A, %B %d, %Y')}",
                "",
                "── PROJECTS ──",
                f"Active: {project_digest.get('total_active', 0)} | "
                f"At Risk: {len(project_digest.get('at_risk', []))} | "
                f"Blocked: {len(project_digest.get('blocked', []))}",
            ]

            if project_digest.get("at_risk"):
                lines.append("⚠ At-Risk Projects:")
                for p in project_digest["at_risk"][:3]:
                    lines.append(f"  • {p['name']}: {', '.join(p.get('reasons', []))[:100]}")

            lines.extend([
                "",
                "── MEETINGS ──",
                f"Overdue Action Items: {meeting_digest.get('overdue_action_items', 0)} | "
                f"Due This Week: {meeting_digest.get('upcoming_deadlines', 0)}",
                "",
                "── CONTRACTS ──",
                f"Expiring Soon: {contract_digest.get('expiring_within_30_days', 0)} | "
                f"Pending Signatures: {contract_digest.get('pending_signatures', 0)}",
                "",
                "── TEAM ──",
                f"Employees Needing Attention: {team_digest.get('employees_needing_attention', 0)}",
            ])

            briefing_text = "\n".join(lines)
            logger.info("Morning briefing generated")

            # Send to stakeholders
            recipients = [r for r in [config.ceo_email, config.coo_email] + config.report_recipients if r]
            if recipients and email_client:
                email_client.send_email(
                    to=recipients,
                    subject=f"Morning Briefing — {datetime.utcnow().strftime('%B %d, %Y')}",
                    body=briefing_text,
                )
                logger.info(f"Morning briefing sent to {recipients}")

        except Exception as e:
            logger.error(f"Morning briefing failed: {e}", exc_info=True)

    scheduler.register_morning_briefing(morning_briefing, hour=config.morning_briefing_hour)

    # ── EOD Digest ─────────────────────────────
    def eod_digest():
        """Send end-of-day status digest."""
        try:
            pending = agent.memory.work_context.get_pending_followups()
            overdue = agent.memory.work_context.get_overdue_followups()

            if not pending and not overdue:
                return

            lines = [
                f"End of Day Summary — {datetime.utcnow().strftime('%B %d, %Y')}",
                f"From: {config.employee_display_name}",
                "",
                f"Pending Follow-ups: {len(pending)}",
                f"Overdue Follow-ups: {len(overdue)}",
            ]

            if overdue:
                lines.append("\nOverdue Items:")
                for item in overdue[:5]:
                    lines.append(f"  • {item.get('action', 'Unknown')} — {item.get('entity', 'Unknown')}")

            digest_text = "\n".join(lines)
            recipients = [r for r in [config.ceo_email, config.coo_email] + config.report_recipients if r]

            if recipients and email_client:
                email_client.send_email(
                    to=recipients,
                    subject=f"EOD Digest — {datetime.utcnow().strftime('%B %d, %Y')}",
                    body=digest_text,
                )

        except Exception as e:
            logger.error(f"EOD digest failed: {e}", exc_info=True)

    scheduler.register_eod_digest(eod_digest, hour=config.eod_digest_hour)

    # ── Weekly Report ──────────────────────────
    def weekly_report():
        """Generate and send the weekly executive status report."""
        try:
            report = agent.generate_status_report(
                projects=project_tracker.get_all_projects(),
                meetings=meeting_tracker.db.list("meetings"),
                contracts=contract_tracker.db.list("contracts"),
                employee_signals=employee_tracker.get_team_health_overview(),
                period="weekly",
            )

            summary = report.get("executive_summary", "Weekly report available.")
            recommended = report.get("recommended_actions", [])
            rec_text = "\n".join([
                f"• [{a.get('priority', 'medium').upper()}] {a.get('action', '')} — {a.get('owner', 'TBD')} by {a.get('deadline', 'TBD')}"
                for a in recommended[:10]
            ])

            body = f"""Weekly Executive Status Report
From: {config.employee_display_name}
Week of: {datetime.utcnow().strftime('%B %d, %Y')}

EXECUTIVE SUMMARY
{summary}

TOP RECOMMENDED ACTIONS
{rec_text}

Review the full report at: http://{config.app_host}:{config.app_port}/api/v1/digest
"""
            recipients = [r for r in [config.ceo_email, config.coo_email] + config.report_recipients if r]
            if recipients and email_client:
                email_client.send_email(
                    to=recipients,
                    subject=f"Weekly Status Report — Week of {datetime.utcnow().strftime('%B %d')}",
                    body=body,
                )
                logger.info(f"Weekly report sent to {recipients}")

        except Exception as e:
            logger.error(f"Weekly report failed: {e}", exc_info=True)

    scheduler.register_weekly_report(weekly_report, day_of_week="mon", hour=9)

    logger.info("All scheduler jobs registered")


# ─────────────────────────────────────────────
# Entry Point
# ─────────────────────────────────────────────

if __name__ == "__main__":
    config = Config.from_env()
    setup_logging(config.log_level)

    try:
        config.validate()
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        sys.exit(1)

    app = create_app(config)

    uvicorn.run(
        app,
        host=config.app_host,
        port=config.app_port,
        log_level=config.log_level.lower(),
        access_log=True,
    )
