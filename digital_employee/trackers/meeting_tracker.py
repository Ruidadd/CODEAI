"""
Meeting tracker — processes meetings, extracts action items,
and ensures follow-through on commitments.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from digital_employee.database.crud import DatabaseCRUD

logger = logging.getLogger(__name__)


class MeetingTracker:
    """
    Manages the full lifecycle of meetings:
    1. Register upcoming meetings from calendar
    2. Process meeting notes/transcripts after the meeting
    3. Track action items to completion
    4. Follow up with participants on their commitments
    """

    def __init__(self, db: DatabaseCRUD):
        self.db = db

    # ─────────────────────────────────────────────
    # Meeting Registration
    # ─────────────────────────────────────────────

    def register_meeting(
        self,
        title: str,
        start_time: datetime,
        end_time: datetime,
        organizer_email: str,
        participants: list[str],
        meeting_id: str = None,
        teams_meeting_url: str = None,
        description: str = "",
    ) -> dict:
        """Register an upcoming meeting to track."""
        meeting = {
            "external_id": meeting_id,
            "title": title,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "organizer_email": organizer_email,
            "participants": participants,
            "teams_url": teams_meeting_url,
            "description": description,
            "status": "scheduled",  # scheduled|completed|cancelled
            "notes": "",
            "transcript": "",
            "action_items": [],
            "decisions": [],
            "follow_up_sent": False,
            "created_at": datetime.utcnow().isoformat(),
            "processed_at": None,
        }
        saved = self.db.create("meetings", meeting)
        logger.info(f"Meeting registered: {title} at {start_time}")
        return saved

    def sync_from_calendar_event(self, calendar_event: dict) -> dict:
        """Create or update a meeting record from a calendar event."""
        # Extract participants from attendees
        participants = [
            a.get("emailAddress", {}).get("address", "")
            for a in calendar_event.get("attendees", [])
        ]

        start_str = calendar_event.get("start", {}).get("dateTime", "")
        end_str = calendar_event.get("end", {}).get("dateTime", "")

        start_dt = datetime.fromisoformat(start_str.replace("Z", "+00:00")) if start_str else datetime.utcnow()
        end_dt = datetime.fromisoformat(end_str.replace("Z", "+00:00")) if end_str else datetime.utcnow()

        # Check if meeting already exists
        existing = self.db.find("meetings", {"external_id": calendar_event.get("id")})
        if existing:
            return self.db.update("meetings", existing[0]["id"], {
                "title": calendar_event.get("subject", "Meeting"),
                "start_time": start_dt.isoformat(),
                "participants": participants,
            })

        return self.register_meeting(
            title=calendar_event.get("subject", "Meeting"),
            start_time=start_dt,
            end_time=end_dt,
            organizer_email=calendar_event.get("organizer", {}).get("emailAddress", {}).get("address", ""),
            participants=participants,
            meeting_id=calendar_event.get("id"),
            teams_meeting_url=calendar_event.get("onlineMeeting", {}).get("joinUrl"),
            description=calendar_event.get("bodyPreview", ""),
        )

    # ─────────────────────────────────────────────
    # Post-Meeting Processing
    # ─────────────────────────────────────────────

    def record_meeting_notes(self, meeting_id: str, notes: str, recorded_by: str = "") -> dict:
        """Record meeting notes after the meeting."""
        return self.db.update("meetings", meeting_id, {
            "notes": notes,
            "notes_recorded_by": recorded_by,
            "notes_recorded_at": datetime.utcnow().isoformat(),
        })

    def record_transcript(self, meeting_id: str, transcript: str) -> dict:
        """Record meeting transcript (from Teams auto-transcription)."""
        return self.db.update("meetings", meeting_id, {
            "transcript": transcript,
            "transcript_recorded_at": datetime.utcnow().isoformat(),
        })

    def mark_meeting_completed(self, meeting_id: str) -> dict:
        """Mark a meeting as completed (triggers follow-up processing)."""
        return self.db.update("meetings", meeting_id, {
            "status": "completed",
            "completed_at": datetime.utcnow().isoformat(),
        })

    def store_processed_results(self, meeting_id: str, ai_results: dict) -> dict:
        """Store the AI-processed results (action items, decisions, etc.)."""
        update = {
            "action_items": ai_results.get("action_items", []),
            "decisions": ai_results.get("decisions", []),
            "open_questions": ai_results.get("open_questions", []),
            "summary": ai_results.get("summary", ""),
            "next_meeting_agenda": ai_results.get("next_meeting", []),
            "processed_at": datetime.utcnow().isoformat(),
            "status": "completed",
        }
        return self.db.update("meetings", meeting_id, update)

    # ─────────────────────────────────────────────
    # Action Item Management
    # ─────────────────────────────────────────────

    def complete_action_item(
        self,
        meeting_id: str,
        action_item_index: int,
        completed_by: str = "",
    ) -> dict:
        """Mark a specific action item as complete."""
        meeting = self.db.get("meetings", meeting_id)
        action_items = meeting.get("action_items", [])

        if 0 <= action_item_index < len(action_items):
            action_items[action_item_index]["status"] = "completed"
            action_items[action_item_index]["completed_at"] = datetime.utcnow().isoformat()
            action_items[action_item_index]["completed_by"] = completed_by

        return self.db.update("meetings", meeting_id, {"action_items": action_items})

    def get_overdue_action_items(self) -> list[dict]:
        """Get all overdue action items across all meetings."""
        all_meetings = self.db.list("meetings")
        overdue = []
        now = datetime.utcnow()

        for meeting in all_meetings:
            for idx, item in enumerate(meeting.get("action_items", [])):
                if item.get("status") == "completed":
                    continue
                deadline_str = item.get("deadline")
                if deadline_str:
                    try:
                        deadline_dt = datetime.fromisoformat(deadline_str)
                        if deadline_dt < now:
                            days_overdue = (now - deadline_dt).days
                            overdue.append({
                                **item,
                                "meeting_id": meeting["id"],
                                "meeting_title": meeting.get("title"),
                                "days_overdue": days_overdue,
                                "action_item_index": idx,
                            })
                    except ValueError:
                        pass

        return sorted(overdue, key=lambda x: x.get("days_overdue", 0), reverse=True)

    def get_upcoming_action_deadlines(self, within_days: int = 3) -> list[dict]:
        """Get action items due within the next N days."""
        all_meetings = self.db.list("meetings")
        upcoming = []
        now = datetime.utcnow()
        cutoff = now + timedelta(days=within_days)

        for meeting in all_meetings:
            for item in meeting.get("action_items", []):
                if item.get("status") == "completed":
                    continue
                deadline_str = item.get("deadline")
                if deadline_str:
                    try:
                        deadline_dt = datetime.fromisoformat(deadline_str)
                        if now <= deadline_dt <= cutoff:
                            upcoming.append({
                                **item,
                                "meeting_id": meeting["id"],
                                "meeting_title": meeting.get("title"),
                                "days_until_due": (deadline_dt - now).days,
                            })
                    except ValueError:
                        pass

        return sorted(upcoming, key=lambda x: x.get("days_until_due", 999))

    # ─────────────────────────────────────────────
    # Query Helpers
    # ─────────────────────────────────────────────

    def get_upcoming_meetings(self, within_hours: int = 48) -> list[dict]:
        """Get meetings scheduled in the next N hours."""
        all_meetings = self.db.list("meetings")
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=within_hours)

        upcoming = []
        for meeting in all_meetings:
            if meeting.get("status") != "scheduled":
                continue
            start_str = meeting.get("start_time")
            if start_str:
                start_dt = datetime.fromisoformat(start_str)
                if now <= start_dt <= cutoff:
                    upcoming.append(meeting)

        return sorted(upcoming, key=lambda m: m.get("start_time", ""))

    def get_meetings_needing_followup(self) -> list[dict]:
        """Get completed meetings that haven't had follow-up sent yet."""
        all_meetings = self.db.list("meetings")
        return [
            m for m in all_meetings
            if m.get("status") == "completed"
            and not m.get("follow_up_sent")
            and m.get("action_items")
        ]

    def mark_followup_sent(self, meeting_id: str):
        """Mark that follow-up has been sent for a meeting."""
        self.db.update("meetings", meeting_id, {
            "follow_up_sent": True,
            "follow_up_sent_at": datetime.utcnow().isoformat(),
        })

    def generate_meetings_digest(self) -> dict:
        """Generate a summary of meeting action item status."""
        overdue = self.get_overdue_action_items()
        upcoming_deadlines = self.get_upcoming_action_deadlines(within_days=3)
        needing_followup = self.get_meetings_needing_followup()

        return {
            "overdue_action_items": len(overdue),
            "overdue_details": overdue[:10],  # Top 10
            "upcoming_deadlines": len(upcoming_deadlines),
            "upcoming_deadline_details": upcoming_deadlines[:10],
            "meetings_needing_followup": len(needing_followup),
        }
