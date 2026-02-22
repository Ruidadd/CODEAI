"""
Configuration management for the Digital Employee.
Loads settings from environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Config:
    # ── Anthropic / Claude ──────────────────────
    anthropic_api_key: str = field(default_factory=lambda: os.environ["ANTHROPIC_API_KEY"])
    claude_model: str = field(default_factory=lambda: os.getenv("CLAUDE_MODEL", "claude-opus-4-6"))

    # ── Microsoft Graph (Azure AD App) ──────────
    ms_tenant_id: str = field(default_factory=lambda: os.getenv("MS_TENANT_ID", ""))
    ms_client_id: str = field(default_factory=lambda: os.getenv("MS_CLIENT_ID", ""))
    ms_client_secret: str = field(default_factory=lambda: os.getenv("MS_CLIENT_SECRET", ""))

    # ── Digital Employee Identity ────────────────
    employee_name: str = field(default_factory=lambda: os.getenv("EMPLOYEE_NAME", "Alex"))
    employee_email: str = field(default_factory=lambda: os.getenv("EMPLOYEE_EMAIL", ""))
    employee_display_name: str = field(default_factory=lambda: os.getenv("EMPLOYEE_DISPLAY_NAME", "Alex (Digital Assistant)"))

    # ── Application ─────────────────────────────
    app_host: str = field(default_factory=lambda: os.getenv("APP_HOST", "0.0.0.0"))
    app_port: int = field(default_factory=lambda: int(os.getenv("APP_PORT", "8000")))
    webhook_base_url: str = field(default_factory=lambda: os.getenv("WEBHOOK_BASE_URL", ""))
    db_path: str = field(default_factory=lambda: os.getenv("DB_PATH", "digital_employee.db"))
    log_level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))

    # ── Scheduler Settings ───────────────────────
    email_check_interval_min: int = field(default_factory=lambda: int(os.getenv("EMAIL_CHECK_INTERVAL_MIN", "5")))
    teams_check_interval_min: int = field(default_factory=lambda: int(os.getenv("TEAMS_CHECK_INTERVAL_MIN", "5")))
    followup_interval_min: int = field(default_factory=lambda: int(os.getenv("FOLLOWUP_INTERVAL_MIN", "15")))
    morning_briefing_hour: int = field(default_factory=lambda: int(os.getenv("MORNING_BRIEFING_HOUR", "8")))
    eod_digest_hour: int = field(default_factory=lambda: int(os.getenv("EOD_DIGEST_HOUR", "17")))

    # ── Senior Stakeholders (recipients of reports) ──
    ceo_email: str = field(default_factory=lambda: os.getenv("CEO_EMAIL", ""))
    coo_email: str = field(default_factory=lambda: os.getenv("COO_EMAIL", ""))
    report_recipients: list = field(default_factory=lambda: [
        e.strip()
        for e in os.getenv("REPORT_RECIPIENTS", "").split(",")
        if e.strip()
    ])

    # ── Feature Flags ───────────────────────────
    enable_auto_respond: bool = field(default_factory=lambda: os.getenv("ENABLE_AUTO_RESPOND", "false").lower() == "true")
    enable_teams_monitoring: bool = field(default_factory=lambda: os.getenv("ENABLE_TEAMS_MONITORING", "true").lower() == "true")
    enable_employee_health: bool = field(default_factory=lambda: os.getenv("ENABLE_EMPLOYEE_HEALTH", "true").lower() == "true")

    def to_agent_config(self) -> dict:
        """Return config dict for the AI agent."""
        return {
            "anthropic_api_key": self.anthropic_api_key,
            "claude_model": self.claude_model,
            "employee_identity": {
                "name": self.employee_name,
                "email": self.employee_email,
                "display_name": self.employee_display_name,
            },
        }

    def to_graph_config(self) -> dict:
        """Return config dict for Microsoft Graph client."""
        return {
            "ms_tenant_id": self.ms_tenant_id,
            "ms_client_id": self.ms_client_id,
            "ms_client_secret": self.ms_client_secret,
            "employee_email": self.employee_email,
        }

    def validate(self):
        """Validate required configuration."""
        errors = []
        if not self.anthropic_api_key:
            errors.append("ANTHROPIC_API_KEY is required")
        if not self.employee_email:
            errors.append("EMPLOYEE_EMAIL is required")
        if errors:
            raise ValueError(f"Configuration errors: {'; '.join(errors)}")

    @classmethod
    def from_env(cls) -> "Config":
        """Load configuration from environment variables."""
        return cls()
