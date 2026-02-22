"""
Microsoft Teams integration via Microsoft Graph API.
Handles channel monitoring, message sending, and meeting data.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from digital_employee.integrations.ms_graph import MSGraphClient

logger = logging.getLogger(__name__)


class TeamsClient:
    """
    Manages Teams interactions for the digital employee.
    - Monitor channels for messages and updates
    - Send messages to channels and individuals (DMs)
    - Access meeting data and attendance
    - Track chat threads
    """

    def __init__(self, graph_client: MSGraphClient, user_email: str):
        self.graph = graph_client
        self.user_email = user_email
        self._user_id: Optional[str] = None

    def _get_user_id(self) -> str:
        """Get the Teams user ID for the digital employee."""
        if not self._user_id:
            user = self.graph.get(f"/users/{self.user_email}")
            self._user_id = user["id"]
        return self._user_id

    # ─────────────────────────────────────────────
    # Teams & Channels
    # ─────────────────────────────────────────────

    def list_joined_teams(self) -> list[dict]:
        """List all teams the digital employee has joined."""
        result = self.graph.get(f"/users/{self.user_email}/joinedTeams")
        teams = result.get("value", [])
        return [{"id": t["id"], "name": t["displayName"], "description": t.get("description", "")} for t in teams]

    def list_team_channels(self, team_id: str) -> list[dict]:
        """List all channels in a team."""
        result = self.graph.get(f"/teams/{team_id}/channels")
        channels = result.get("value", [])
        return [
            {
                "id": c["id"],
                "name": c["displayName"],
                "description": c.get("description", ""),
                "team_id": team_id,
            }
            for c in channels
        ]

    # ─────────────────────────────────────────────
    # Channel Messages
    # ─────────────────────────────────────────────

    def get_channel_messages(
        self,
        team_id: str,
        channel_id: str,
        top: int = 50,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """Get recent messages from a channel."""
        params = {"$top": top}
        if since:
            params["$filter"] = f"lastModifiedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}"

        messages = self.graph.paginate(
            f"/teams/{team_id}/channels/{channel_id}/messages",
            params=params,
            max_items=top,
        )
        return [self._normalize_channel_message(m) for m in messages if m.get("messageType") == "message"]

    def get_message_replies(self, team_id: str, channel_id: str, message_id: str) -> list[dict]:
        """Get replies to a specific channel message."""
        result = self.graph.get(
            f"/teams/{team_id}/channels/{channel_id}/messages/{message_id}/replies"
        )
        return [self._normalize_channel_message(m) for m in result.get("value", [])]

    def send_channel_message(
        self,
        team_id: str,
        channel_id: str,
        content: str,
        is_html: bool = False,
        reply_to_message_id: str = None,
    ) -> dict:
        """Send a message to a Teams channel."""
        body = {
            "body": {
                "contentType": "html" if is_html else "text",
                "content": content,
            }
        }

        if reply_to_message_id:
            path = f"/teams/{team_id}/channels/{channel_id}/messages/{reply_to_message_id}/replies"
        else:
            path = f"/teams/{team_id}/channels/{channel_id}/messages"

        result = self.graph.post(path, body)
        logger.info(f"Teams message sent to channel {channel_id}")
        return result

    # ─────────────────────────────────────────────
    # Direct Messages (Chats)
    # ─────────────────────────────────────────────

    def get_chats(self, chat_type: str = "oneOnOne") -> list[dict]:
        """
        Get chat conversations. chat_type: oneOnOne|group|meeting
        """
        result = self.graph.get(
            f"/users/{self.user_email}/chats",
            params={"$filter": f"chatType eq '{chat_type}'", "$expand": "members"}
        )
        return result.get("value", [])

    def get_chat_with_user(self, other_user_email: str) -> Optional[dict]:
        """Find existing 1:1 chat with a specific user."""
        chats = self.get_chats(chat_type="oneOnOne")
        for chat in chats:
            members = chat.get("members", [])
            member_emails = [m.get("email", "").lower() for m in members]
            if other_user_email.lower() in member_emails:
                return chat
        return None

    def create_chat(self, members: list[str]) -> dict:
        """Create a new group or 1:1 chat."""
        chat_type = "oneOnOne" if len(members) == 2 else "group"
        body = {
            "chatType": chat_type,
            "members": [
                {
                    "@odata.type": "#microsoft.graph.aadUserConversationMember",
                    "roles": ["owner"],
                    "user@odata.bind": f"https://graph.microsoft.com/v1.0/users('{email}')",
                }
                for email in members
            ],
        }
        return self.graph.post("/chats", body)

    def send_dm(self, chat_id: str, content: str, is_html: bool = False) -> dict:
        """Send a direct message in a chat."""
        body = {
            "body": {
                "contentType": "html" if is_html else "text",
                "content": content,
            }
        }
        result = self.graph.post(f"/chats/{chat_id}/messages", body)
        logger.info(f"DM sent to chat {chat_id}")
        return result

    def send_dm_to_user(self, user_email: str, content: str) -> dict:
        """Send a DM to a user, creating the chat if needed."""
        chat = self.get_chat_with_user(user_email)
        if not chat:
            chat = self.create_chat([self.user_email, user_email])
        return self.send_dm(chat["id"], content)

    def get_chat_messages(self, chat_id: str, top: int = 20) -> list[dict]:
        """Get recent messages from a DM chat."""
        result = self.graph.get(
            f"/chats/{chat_id}/messages",
            params={"$top": top, "$orderby": "createdDateTime DESC"}
        )
        return result.get("value", [])

    # ─────────────────────────────────────────────
    # Meetings & Calendar Events
    # ─────────────────────────────────────────────

    def get_online_meetings(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[dict]:
        """Get online meetings for the digital employee."""
        if not start:
            start = datetime.utcnow() - timedelta(days=7)
        if not end:
            end = datetime.utcnow() + timedelta(days=30)

        result = self.graph.get(
            f"/users/{self.user_email}/onlineMeetings",
            params={
                "$filter": (
                    f"startDateTime ge {start.strftime('%Y-%m-%dT%H:%M:%SZ')} and "
                    f"startDateTime le {end.strftime('%Y-%m-%dT%H:%M:%SZ')}"
                )
            }
        )
        return result.get("value", [])

    def get_meeting_attendance(self, meeting_id: str) -> list[dict]:
        """Get attendance report for a specific meeting."""
        try:
            result = self.graph.get(f"/me/onlineMeetings/{meeting_id}/attendanceReports")
            reports = result.get("value", [])
            if reports:
                latest_report_id = reports[0]["id"]
                detail = self.graph.get(
                    f"/me/onlineMeetings/{meeting_id}/attendanceReports/{latest_report_id}/attendanceRecords"
                )
                return detail.get("value", [])
        except Exception as e:
            logger.warning(f"Could not get attendance for meeting {meeting_id}: {e}")
        return []

    def get_calendar_events(
        self,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
        top: int = 50,
    ) -> list[dict]:
        """Get calendar events (including meetings)."""
        if not start:
            start = datetime.utcnow()
        if not end:
            end = datetime.utcnow() + timedelta(days=14)

        result = self.graph.get(
            f"/users/{self.user_email}/calendarView",
            params={
                "startDateTime": start.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "endDateTime": end.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "$top": top,
                "$orderby": "start/dateTime",
                "$select": "id,subject,start,end,attendees,organizer,bodyPreview,onlineMeeting,isOnlineMeeting",
            }
        )
        return result.get("value", [])

    # ─────────────────────────────────────────────
    # Presence & Activity Signals
    # ─────────────────────────────────────────────

    def get_user_presence(self, user_email: str) -> dict:
        """Get presence status for a user (Available, Busy, Away, etc.)."""
        try:
            result = self.graph.get(f"/users/{user_email}/presence")
            return {
                "availability": result.get("availability"),
                "activity": result.get("activity"),
                "status_message": result.get("statusMessage", {}).get("message", {}).get("content", ""),
            }
        except Exception as e:
            logger.warning(f"Could not get presence for {user_email}: {e}")
            return {}

    def get_multiple_user_presence(self, user_ids: list[str]) -> list[dict]:
        """Batch get presence for multiple users."""
        try:
            result = self.graph.post(
                "/communications/getPresencesByUserId",
                {"ids": user_ids}
            )
            return result.get("value", [])
        except Exception as e:
            logger.warning(f"Batch presence fetch failed: {e}")
            return []

    # ─────────────────────────────────────────────
    # Webhook Subscriptions
    # ─────────────────────────────────────────────

    def subscribe_to_channel(
        self,
        team_id: str,
        channel_id: str,
        notification_url: str,
    ) -> dict:
        """Subscribe to real-time channel message notifications."""
        return self.graph.subscribe_webhook(
            resource=f"/teams/{team_id}/channels/{channel_id}/messages",
            change_types=["created", "updated"],
            notification_url=notification_url,
        )

    def subscribe_to_chats(self, notification_url: str) -> dict:
        """Subscribe to all chat message notifications for the user."""
        return self.graph.subscribe_webhook(
            resource=f"/users/{self.user_email}/chats/getAllMessages",
            change_types=["created"],
            notification_url=notification_url,
        )

    # ─────────────────────────────────────────────
    # Normalization
    # ─────────────────────────────────────────────

    def _normalize_channel_message(self, raw: dict) -> dict:
        sender = raw.get("from", {})
        user = sender.get("user", {}) if sender else {}
        return {
            "id": raw.get("id"),
            "sender_name": user.get("displayName", "Unknown"),
            "sender_id": user.get("id"),
            "content": raw.get("body", {}).get("content", ""),
            "content_type": raw.get("body", {}).get("contentType", "text"),
            "timestamp": raw.get("createdDateTime"),
            "last_modified": raw.get("lastModifiedDateTime"),
            "message_type": raw.get("messageType"),
            "reactions": [r.get("reactionType") for r in raw.get("reactions", [])],
            "reply_count": len(raw.get("replies", [])),
        }
