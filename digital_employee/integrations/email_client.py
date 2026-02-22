"""
Email integration via Microsoft Graph API.
Handles reading, sending, and monitoring the digital employee's mailbox.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

from digital_employee.integrations.ms_graph import MSGraphClient

logger = logging.getLogger(__name__)


class EmailClient:
    """
    Manages the digital employee's email via Microsoft Graph (Outlook/Exchange).
    Supports reading, sending, replying, flagging, and webhook subscriptions.
    """

    def __init__(self, graph_client: MSGraphClient, user_email: str):
        self.graph = graph_client
        self.user_email = user_email
        self._base = f"/users/{user_email}"

    # ─────────────────────────────────────────────
    # Reading Emails
    # ─────────────────────────────────────────────

    def get_inbox_messages(
        self,
        top: int = 50,
        unread_only: bool = False,
        since: Optional[datetime] = None,
    ) -> list[dict]:
        """Fetch messages from the inbox."""
        params = {
            "$top": top,
            "$orderby": "receivedDateTime DESC",
            "$select": (
                "id,subject,from,toRecipients,ccRecipients,receivedDateTime,"
                "isRead,importance,hasAttachments,bodyPreview,body,conversationId"
            ),
        }

        filters = []
        if unread_only:
            filters.append("isRead eq false")
        if since:
            filters.append(f"receivedDateTime ge {since.strftime('%Y-%m-%dT%H:%M:%SZ')}")
        if filters:
            params["$filter"] = " and ".join(filters)

        result = self.graph.get(f"{self._base}/mailFolders/inbox/messages", params=params)
        messages = result.get("value", [])
        return [self._normalize_message(m) for m in messages]

    def get_message(self, message_id: str) -> dict:
        """Get a specific message by ID."""
        msg = self.graph.get(
            f"{self._base}/messages/{message_id}",
            params={"$select": "id,subject,from,toRecipients,ccRecipients,receivedDateTime,isRead,importance,body,conversationId"}
        )
        return self._normalize_message(msg)

    def get_conversation_thread(self, conversation_id: str) -> list[dict]:
        """Get all messages in a conversation thread."""
        messages = self.graph.paginate(
            f"{self._base}/messages",
            params={
                "$filter": f"conversationId eq '{conversation_id}'",
                "$orderby": "receivedDateTime ASC",
                "$select": "id,subject,from,toRecipients,receivedDateTime,body,bodyPreview",
            }
        )
        return [self._normalize_message(m) for m in messages]

    def search_messages(self, query: str, top: int = 20) -> list[dict]:
        """Search messages by keyword."""
        result = self.graph.get(
            f"{self._base}/messages",
            params={"$search": f'"{query}"', "$top": top}
        )
        return [self._normalize_message(m) for m in result.get("value", [])]

    def get_flagged_messages(self) -> list[dict]:
        """Get flagged/important messages."""
        result = self.graph.get(
            f"{self._base}/messages",
            params={
                "$filter": "flag/flagStatus eq 'flagged'",
                "$orderby": "receivedDateTime DESC",
                "$top": 50,
            }
        )
        return [self._normalize_message(m) for m in result.get("value", [])]

    # ─────────────────────────────────────────────
    # Sending Emails
    # ─────────────────────────────────────────────

    def send_email(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] = None,
        bcc: list[str] = None,
        reply_to_message_id: str = None,
        importance: str = "normal",
        is_html: bool = False,
    ) -> bool:
        """Send an email from the digital employee's account."""
        message = {
            "subject": subject,
            "importance": importance,
            "body": {
                "contentType": "HTML" if is_html else "Text",
                "content": body,
            },
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        }

        if cc:
            message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
        if bcc:
            message["bccRecipients"] = [{"emailAddress": {"address": addr}} for addr in bcc]

        if reply_to_message_id:
            # Reply to existing message
            self.graph.post(
                f"{self._base}/messages/{reply_to_message_id}/reply",
                {"message": message, "comment": body}
            )
        else:
            self.graph.post(f"{self._base}/sendMail", {"message": message})

        logger.info(f"Email sent to {to}: {subject}")
        return True

    def forward_email(self, message_id: str, to: list[str], comment: str = "") -> bool:
        """Forward an email to new recipients."""
        self.graph.post(
            f"{self._base}/messages/{message_id}/forward",
            {
                "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
                "comment": comment,
            }
        )
        return True

    def save_draft(
        self,
        to: list[str],
        subject: str,
        body: str,
        cc: list[str] = None,
    ) -> dict:
        """Save an email as draft for review before sending."""
        message = {
            "subject": subject,
            "body": {"contentType": "Text", "content": body},
            "toRecipients": [{"emailAddress": {"address": addr}} for addr in to],
        }
        if cc:
            message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]

        draft = self.graph.post(f"{self._base}/messages", message)
        logger.info(f"Draft saved: {subject}")
        return draft

    # ─────────────────────────────────────────────
    # Email Management
    # ─────────────────────────────────────────────

    def mark_as_read(self, message_id: str):
        self.graph.patch(f"{self._base}/messages/{message_id}", {"isRead": True})

    def flag_message(self, message_id: str, flag_status: str = "flagged"):
        """Flag/unflag a message. flag_status: flagged|notFlagged|complete"""
        self.graph.patch(
            f"{self._base}/messages/{message_id}",
            {"flag": {"flagStatus": flag_status}}
        )

    def move_to_folder(self, message_id: str, folder_id: str):
        self.graph.post(
            f"{self._base}/messages/{message_id}/move",
            {"destinationId": folder_id}
        )

    def create_folder(self, folder_name: str, parent_folder_id: str = None) -> dict:
        """Create a mail folder for organizing tracked items."""
        path = f"{self._base}/mailFolders"
        if parent_folder_id:
            path = f"{self._base}/mailFolders/{parent_folder_id}/childFolders"
        return self.graph.post(path, {"displayName": folder_name})

    # ─────────────────────────────────────────────
    # Webhook Subscriptions
    # ─────────────────────────────────────────────

    def subscribe_to_inbox(self, notification_url: str) -> dict:
        """Subscribe to real-time inbox notifications via webhook."""
        return self.graph.subscribe_webhook(
            resource=f"users/{self.user_email}/mailFolders/inbox/messages",
            change_types=["created"],
            notification_url=notification_url,
        )

    # ─────────────────────────────────────────────
    # Normalization
    # ─────────────────────────────────────────────

    def _normalize_message(self, raw: dict) -> dict:
        """Convert raw Graph API message to a cleaner format."""
        sender = raw.get("from", {}).get("emailAddress", {})
        to_recipients = [
            r["emailAddress"]["address"]
            for r in raw.get("toRecipients", [])
        ]
        cc_recipients = [
            r["emailAddress"]["address"]
            for r in raw.get("ccRecipients", [])
        ]

        return {
            "id": raw.get("id"),
            "conversation_id": raw.get("conversationId"),
            "subject": raw.get("subject", "(No Subject)"),
            "sender_name": sender.get("name", ""),
            "sender_email": sender.get("address", ""),
            "to": to_recipients,
            "cc": cc_recipients,
            "received_at": raw.get("receivedDateTime"),
            "is_read": raw.get("isRead", False),
            "importance": raw.get("importance", "normal"),
            "has_attachments": raw.get("hasAttachments", False),
            "preview": raw.get("bodyPreview", ""),
            "body": raw.get("body", {}).get("content", ""),
            "body_type": raw.get("body", {}).get("contentType", "text"),
        }
