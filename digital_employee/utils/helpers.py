"""
Utility helpers for the Digital Employee system.
"""

import re
import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def extract_entities_from_text(text: str, known_projects: list[str], known_employees: list[str]) -> dict:
    """
    Extract known entity mentions from unstructured text.
    Used for passive signal collection from emails and Teams messages.
    """
    text_lower = text.lower()
    found_projects = [p for p in known_projects if p.lower() in text_lower]
    found_employees = [e for e in known_employees if e.lower() in text_lower]

    # Extract dates/deadlines
    date_patterns = [
        r'\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b',
        r'\b(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}\b',
        r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
        r'\b(end of week|eow|end of month|eom|next week|tomorrow|today)\b',
    ]
    dates_mentioned = []
    for pattern in date_patterns:
        matches = re.findall(pattern, text_lower)
        dates_mentioned.extend(matches)

    # Extract urgency signals
    urgency_keywords = {
        "critical": ["urgent", "asap", "immediately", "critical", "emergency", "blocker"],
        "high": ["important", "priority", "soon", "today", "deadline"],
        "low": ["fyi", "no rush", "when you have time", "low priority"],
    }
    urgency = "medium"
    for level, keywords in urgency_keywords.items():
        if any(kw in text_lower for kw in keywords):
            urgency = level
            break

    return {
        "projects": found_projects,
        "employees": found_employees,
        "dates_mentioned": dates_mentioned,
        "urgency": urgency,
    }


def parse_deadline_from_text(text: str) -> Optional[datetime]:
    """
    Try to parse a deadline from natural language text.
    Returns None if no parseable deadline found.
    """
    text_lower = text.lower()
    now = datetime.utcnow()

    # Relative dates
    if "today" in text_lower:
        return now.replace(hour=17, minute=0, second=0, microsecond=0)
    if "tomorrow" in text_lower:
        return (now + timedelta(days=1)).replace(hour=17, minute=0, second=0, microsecond=0)
    if "end of week" in text_lower or "eow" in text_lower:
        days_until_friday = (4 - now.weekday()) % 7
        return (now + timedelta(days=days_until_friday)).replace(hour=17, minute=0, second=0, microsecond=0)
    if "next week" in text_lower:
        return (now + timedelta(days=7)).replace(hour=17, minute=0, second=0, microsecond=0)
    if "end of month" in text_lower or "eom" in text_lower:
        next_month = now.replace(day=1) + timedelta(days=32)
        return next_month.replace(day=1) - timedelta(days=1)

    return None


def format_duration(seconds: float) -> str:
    """Format a duration in seconds to a human-readable string."""
    if seconds < 60:
        return f"{int(seconds)}s"
    elif seconds < 3600:
        return f"{int(seconds / 60)}m"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        minutes = int((seconds % 3600) / 60)
        return f"{hours}h {minutes}m"
    else:
        days = int(seconds / 86400)
        return f"{days}d"


def sanitize_email_body(body: str, max_length: int = 2000) -> str:
    """
    Clean an email body for AI processing.
    Removes HTML tags, normalizes whitespace, truncates if needed.
    """
    # Remove HTML tags
    clean = re.sub(r'<[^>]+>', '', body)
    # Normalize whitespace
    clean = re.sub(r'\s+', ' ', clean).strip()
    # Remove email signatures (common patterns)
    signature_patterns = [
        r'--\s*\n.*',
        r'Sent from my iPhone.*',
        r'Sent from my Android.*',
        r'Get Outlook for.*',
    ]
    for pattern in signature_patterns:
        clean = re.sub(pattern, '', clean, flags=re.DOTALL | re.IGNORECASE)
    # Truncate
    if len(clean) > max_length:
        clean = clean[:max_length] + "... [truncated]"
    return clean.strip()


def batch_list(items: list, batch_size: int) -> list[list]:
    """Split a list into batches of specified size."""
    return [items[i:i + batch_size] for i in range(0, len(items), batch_size)]


def days_until(target: datetime) -> int:
    """Calculate days until a target date."""
    delta = target - datetime.utcnow()
    return max(0, delta.days)


def is_business_hours(dt: datetime = None, start_hour: int = 8, end_hour: int = 18) -> bool:
    """Check if a datetime falls within business hours (Mon-Fri)."""
    if dt is None:
        dt = datetime.utcnow()
    return dt.weekday() < 5 and start_hour <= dt.hour < end_hour
