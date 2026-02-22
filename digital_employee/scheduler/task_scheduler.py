"""
Background task scheduler for the Digital Employee.
Runs periodic jobs to monitor, collect signals, and trigger proactive follow-ups.
"""

import logging
from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)


class DigitalEmployeeScheduler:
    """
    Manages all scheduled tasks for the digital employee.

    Job Schedule:
    - Every 5 min:  Check inbox for new emails
    - Every 5 min:  Check Teams for new messages
    - Every 15 min: Process pending action items and generate follow-ups
    - Every 30 min: Update presence/activity signals
    - Every 1 hour: Check contract expiry alerts
    - Every 1 hour: Check stale projects and overdue milestones
    - Every day 8am: Generate morning briefing
    - Every day 6pm: Generate end-of-day status digest
    - Every Monday 9am: Weekly executive status report
    """

    def __init__(self, config: dict):
        self.config = config
        self._scheduler = BackgroundScheduler(timezone="UTC")
        self._job_registry: dict[str, Callable] = {}

    # ─────────────────────────────────────────────
    # Lifecycle
    # ─────────────────────────────────────────────

    def start(self):
        """Start the scheduler."""
        self._scheduler.start()
        logger.info("Digital Employee Scheduler started")

    def stop(self):
        """Stop the scheduler gracefully."""
        self._scheduler.shutdown(wait=True)
        logger.info("Digital Employee Scheduler stopped")

    def is_running(self) -> bool:
        return self._scheduler.running

    # ─────────────────────────────────────────────
    # Job Registration
    # ─────────────────────────────────────────────

    def register_email_monitor(self, handler: Callable, interval_minutes: int = 5):
        """Register email inbox monitoring job."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="email_monitor",
            name="Email Inbox Monitor",
            replace_existing=True,
            misfire_grace_time=60,
        )
        self._job_registry["email_monitor"] = handler
        logger.info(f"Email monitor registered (every {interval_minutes} min)")
        return job

    def register_teams_monitor(self, handler: Callable, interval_minutes: int = 5):
        """Register Teams channel monitoring job."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="teams_monitor",
            name="Teams Channel Monitor",
            replace_existing=True,
            misfire_grace_time=60,
        )
        self._job_registry["teams_monitor"] = handler
        logger.info(f"Teams monitor registered (every {interval_minutes} min)")
        return job

    def register_followup_processor(self, handler: Callable, interval_minutes: int = 15):
        """Register job to process pending follow-ups."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="followup_processor",
            name="Follow-up Processor",
            replace_existing=True,
            misfire_grace_time=120,
        )
        self._job_registry["followup_processor"] = handler
        logger.info(f"Follow-up processor registered (every {interval_minutes} min)")
        return job

    def register_contract_alert_checker(self, handler: Callable, interval_hours: int = 1):
        """Register contract expiry alert checker."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(hours=interval_hours),
            id="contract_alert_checker",
            name="Contract Alert Checker",
            replace_existing=True,
        )
        self._job_registry["contract_alert_checker"] = handler
        logger.info(f"Contract alert checker registered (every {interval_hours} hour)")
        return job

    def register_project_health_checker(self, handler: Callable, interval_hours: int = 1):
        """Register project health checker."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(hours=interval_hours),
            id="project_health_checker",
            name="Project Health Checker",
            replace_existing=True,
        )
        logger.info(f"Project health checker registered (every {interval_hours} hour)")
        return job

    def register_morning_briefing(self, handler: Callable, hour: int = 8, minute: int = 0):
        """Register daily morning briefing job."""
        job = self._scheduler.add_job(
            handler,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="morning_briefing",
            name="Morning Briefing",
            replace_existing=True,
        )
        logger.info(f"Morning briefing registered (daily at {hour:02d}:{minute:02d} UTC)")
        return job

    def register_eod_digest(self, handler: Callable, hour: int = 17, minute: int = 0):
        """Register end-of-day digest job."""
        job = self._scheduler.add_job(
            handler,
            trigger=CronTrigger(hour=hour, minute=minute),
            id="eod_digest",
            name="End of Day Digest",
            replace_existing=True,
        )
        logger.info(f"EOD digest registered (daily at {hour:02d}:{minute:02d} UTC)")
        return job

    def register_weekly_report(self, handler: Callable, day_of_week: str = "mon", hour: int = 9):
        """Register weekly executive status report."""
        job = self._scheduler.add_job(
            handler,
            trigger=CronTrigger(day_of_week=day_of_week, hour=hour),
            id="weekly_report",
            name="Weekly Executive Report",
            replace_existing=True,
        )
        logger.info(f"Weekly report registered ({day_of_week} at {hour:02d}:00 UTC)")
        return job

    def register_presence_monitor(self, handler: Callable, interval_minutes: int = 30):
        """Register employee presence/activity monitor."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(minutes=interval_minutes),
            id="presence_monitor",
            name="Presence & Activity Monitor",
            replace_existing=True,
        )
        logger.info(f"Presence monitor registered (every {interval_minutes} min)")
        return job

    def register_subscription_renewer(self, handler: Callable, interval_hours: int = 48):
        """Register webhook subscription renewal job."""
        job = self._scheduler.add_job(
            handler,
            trigger=IntervalTrigger(hours=interval_hours),
            id="subscription_renewer",
            name="Webhook Subscription Renewer",
            replace_existing=True,
        )
        logger.info(f"Subscription renewer registered (every {interval_hours} hours)")
        return job

    def run_job_now(self, job_id: str):
        """Trigger a job to run immediately."""
        job = self._scheduler.get_job(job_id)
        if job:
            job.func()
        else:
            handler = self._job_registry.get(job_id)
            if handler:
                handler()
            else:
                logger.warning(f"Job not found: {job_id}")

    def get_job_status(self) -> list[dict]:
        """Get status of all scheduled jobs."""
        jobs = []
        for job in self._scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": next_run.isoformat() if next_run else None,
                "trigger": str(job.trigger),
            })
        return jobs
