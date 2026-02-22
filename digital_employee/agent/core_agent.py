"""
Core AI Agent powered by Claude (Anthropic).
This is the brain of the Digital Employee — it processes signals,
makes decisions, and generates actions.
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any, Optional

import anthropic

from digital_employee.agent.memory import AgentMemory
from digital_employee.agent.prompts import (
    DIGITAL_EMPLOYEE_SYSTEM_PROMPT,
    EMAIL_ANALYSIS_PROMPT,
    TEAMS_MESSAGE_ANALYSIS_PROMPT,
    MEETING_FOLLOWUP_PROMPT,
    STATUS_REPORT_PROMPT,
    PROACTIVE_INQUIRY_PROMPT,
)

logger = logging.getLogger(__name__)


class DigitalEmployeeAgent:
    """
    The core AI agent that powers the Digital Employee.
    Uses Claude to analyze inputs and generate actions.
    """

    def __init__(self, config: dict):
        self.config = config
        self.client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
        self.model = config.get("claude_model", "claude-opus-4-6")
        self.memory = AgentMemory()
        self.identity = config.get("employee_identity", {})
        logger.info(f"Digital Employee Agent initialized: {self.identity.get('name', 'Unknown')}")

    # ─────────────────────────────────────────────
    # Core Claude API Wrapper
    # ─────────────────────────────────────────────

    def _call_claude(
        self,
        prompt: str,
        system: str = None,
        thread_id: str = None,
        expect_json: bool = False,
        max_tokens: int = 4096,
    ) -> str:
        """Make a call to the Claude API with optional conversation history."""
        messages = []

        if thread_id:
            messages = self.memory.conversations.get_claude_format(thread_id)

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                system=system or DIGITAL_EMPLOYEE_SYSTEM_PROMPT,
                messages=messages,
            )
            result = response.content[0].text

            if thread_id:
                self.memory.conversations.add_message(thread_id, "user", prompt)
                self.memory.conversations.add_message(thread_id, "assistant", result)

            if expect_json:
                # Extract JSON from response
                result = self._extract_json(result)

            return result

        except anthropic.APIError as e:
            logger.error(f"Claude API error: {e}")
            raise

    def _extract_json(self, text: str) -> dict:
        """Extract JSON object from Claude's response text."""
        # Try direct JSON parse
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Try to find JSON block
        import re
        patterns = [
            r'```json\s*([\s\S]+?)\s*```',
            r'```\s*([\s\S]+?)\s*```',
            r'\{[\s\S]+\}',
        ]
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                try:
                    candidate = match.group(1) if '```' in pattern else match.group(0)
                    return json.loads(candidate)
                except json.JSONDecodeError:
                    continue

        logger.warning(f"Could not extract JSON from response: {text[:200]}")
        return {"raw_response": text}

    # ─────────────────────────────────────────────
    # Email Processing
    # ─────────────────────────────────────────────

    def analyze_email(self, email_data: dict) -> dict:
        """
        Analyze an incoming email and determine if/how to respond.
        Returns structured analysis with suggested actions.
        """
        email_content = f"""
From: {email_data.get('sender_name')} <{email_data.get('sender_email')}>
To: {email_data.get('recipient')}
Subject: {email_data.get('subject')}
Date: {email_data.get('received_at')}
Body:
{email_data.get('body', '')}
        """

        prompt = EMAIL_ANALYSIS_PROMPT.format(email_content=email_content)
        analysis = self._call_claude(prompt, expect_json=True)

        # Update entity memory
        sender = email_data.get('sender_email', '')
        if sender:
            self.memory.entities.upsert_person(sender, {
                "name": email_data.get('sender_name', ''),
                "last_email_subject": email_data.get('subject', ''),
            })
            self.memory.work_context.add_signal(
                "email_received", sender,
                {"subject": email_data.get('subject'), "intent": analysis.get("intent")}
            )

        # Register follow-up if needed
        if analysis.get("follow_up_needed"):
            self.memory.work_context.add_followup({
                "id": str(uuid.uuid4()),
                "type": "email_followup",
                "entity": sender,
                "subject": email_data.get('subject'),
                "due_by": analysis.get("follow_up_deadline"),
                "action": f"Follow up on: {email_data.get('subject')}",
                "context": analysis.get("summary"),
            })

        return analysis

    def draft_email_response(
        self,
        original_email: dict,
        analysis: dict,
        additional_context: str = ""
    ) -> dict:
        """Draft an email response based on analysis."""
        thread_id = f"email_{original_email.get('message_id', uuid.uuid4())}"

        context = f"""
You need to respond to this email as {self.identity.get('name', 'the Digital Employee')}.

Original Email:
From: {original_email.get('sender_name')} <{original_email.get('sender_email')}>
Subject: {original_email.get('subject')}
Body: {original_email.get('body', '')[:1000]}

Analysis: {json.dumps(analysis, ensure_ascii=False)}
Additional Context: {additional_context}

Generate a professional email response as JSON:
{{
  "subject": "Re: {original_email.get('subject')}",
  "body": "email body here",
  "tone": "professional|friendly|formal",
  "cc": [],
  "attachments_needed": []
}}
        """

        return self._call_claude(context, thread_id=thread_id, expect_json=True)

    # ─────────────────────────────────────────────
    # Teams Processing
    # ─────────────────────────────────────────────

    def analyze_teams_messages(self, channel_name: str, messages: list[dict]) -> dict:
        """Analyze a batch of Teams messages for insights and action items."""
        messages_text = "\n".join([
            f"[{m.get('timestamp', '')}] {m.get('sender_name', 'Unknown')}: {m.get('content', '')}"
            for m in messages
        ])

        prompt = TEAMS_MESSAGE_ANALYSIS_PROMPT.format(
            channel_name=channel_name,
            messages=messages_text
        )

        analysis = self._call_claude(prompt, expect_json=True)

        # Record signals for participants
        for participant in analysis.get("key_participants", []):
            self.memory.work_context.add_signal(
                "teams_activity", participant,
                {"channel": channel_name, "sentiment": analysis.get("sentiment")}
            )

        # Register follow-ups for action items
        for item in analysis.get("action_items", []):
            if item.get("owner"):
                self.memory.work_context.add_followup({
                    "id": str(uuid.uuid4()),
                    "type": "teams_action_item",
                    "entity": item["owner"],
                    "action": item.get("task", ""),
                    "due_by": item.get("deadline"),
                    "context": f"From Teams channel: {channel_name}",
                })

        return analysis

    def generate_teams_message(self, channel: str, purpose: str, context: dict) -> str:
        """Generate a Teams message for a specific purpose."""
        prompt = f"""
Generate a professional Microsoft Teams message for the following:
Channel/Recipient: {channel}
Purpose: {purpose}
Context: {json.dumps(context, ensure_ascii=False)}

The message should be:
- Concise (under 200 words)
- Action-oriented
- Appropriate for Teams format (can use @mentions, bullet points)
- Natural and not robotic-sounding

Return just the message text, no JSON wrapper.
        """
        return self._call_claude(prompt)

    # ─────────────────────────────────────────────
    # Meeting Processing
    # ─────────────────────────────────────────────

    def process_meeting(self, meeting_data: dict) -> dict:
        """
        Process a meeting and generate follow-up actions.
        Input can be meeting notes, transcript, or calendar event data.
        """
        prompt = MEETING_FOLLOWUP_PROMPT.format(
            meeting_title=meeting_data.get("title", "Meeting"),
            meeting_date=meeting_data.get("date", "Unknown"),
            participants=", ".join(meeting_data.get("participants", [])),
            content=meeting_data.get("notes", meeting_data.get("transcript", "No notes available"))
        )

        result = self._call_claude(prompt, expect_json=True)

        # Store meeting in memory
        meeting_id = meeting_data.get("id", str(uuid.uuid4()))
        self.memory.entities.upsert_meeting(meeting_id, {
            "title": meeting_data.get("title"),
            "date": meeting_data.get("date"),
            "participants": meeting_data.get("participants", []),
            "action_items_count": len(result.get("action_items", [])),
            "processed_at": datetime.utcnow().isoformat(),
        })

        # Register follow-ups for each action item
        for item in result.get("action_items", []):
            self.memory.work_context.add_followup({
                "id": str(uuid.uuid4()),
                "type": "meeting_action_item",
                "entity": item.get("owner", ""),
                "action": item.get("task", ""),
                "due_by": item.get("deadline"),
                "priority": item.get("priority", "medium"),
                "context": f"Action item from: {meeting_data.get('title')}",
                "meeting_id": meeting_id,
            })

        return result

    # ─────────────────────────────────────────────
    # Proactive Follow-Up Generation
    # ─────────────────────────────────────────────

    def generate_proactive_inquiry(
        self,
        item_type: str,
        item_name: str,
        recipient_name: str,
        last_status: str,
        days_since_update: int,
        relationship_context: str = "colleague"
    ) -> dict:
        """Generate a proactive follow-up inquiry."""
        prompt = PROACTIVE_INQUIRY_PROMPT.format(
            item_type=item_type,
            item_name=item_name,
            last_status=last_status,
            days_since_update=days_since_update,
            recipient_name=recipient_name,
            relationship_context=relationship_context
        )

        return self._call_claude(prompt, expect_json=True)

    def check_and_generate_followups(self) -> list[dict]:
        """
        Check all pending follow-ups and generate inquiry messages
        for items that are overdue or need attention.
        """
        overdue = self.memory.work_context.get_overdue_followups()
        generated = []

        for followup in overdue:
            entity = followup.get("entity", "")
            person = self.memory.entities.get_person(entity)
            recipient_name = person.get("name", entity) if person else entity

            days_overdue = 0
            if followup.get("due_by"):
                due_dt = datetime.fromisoformat(followup["due_by"])
                days_overdue = (datetime.utcnow() - due_dt).days

            inquiry = self.generate_proactive_inquiry(
                item_type=followup.get("type", "task"),
                item_name=followup.get("action", ""),
                recipient_name=recipient_name,
                last_status=followup.get("context", "pending"),
                days_since_update=days_overdue,
            )

            inquiry["followup_id"] = followup.get("id")
            inquiry["recipient"] = entity
            generated.append(inquiry)

        return generated

    # ─────────────────────────────────────────────
    # Status Reports
    # ─────────────────────────────────────────────

    def generate_status_report(
        self,
        projects: list[dict],
        meetings: list[dict],
        contracts: list[dict],
        employee_signals: list[dict],
        period: str = "weekly"
    ) -> dict:
        """Generate a comprehensive executive status report."""
        prompt = STATUS_REPORT_PROMPT.format(
            period=period,
            projects_data=json.dumps(projects, ensure_ascii=False, default=str),
            meetings_data=json.dumps(meetings, ensure_ascii=False, default=str),
            contracts_data=json.dumps(contracts, ensure_ascii=False, default=str),
            employee_data=json.dumps(employee_signals, ensure_ascii=False, default=str),
        )

        return self._call_claude(prompt, expect_json=True, max_tokens=8192)

    # ─────────────────────────────────────────────
    # General Conversation
    # ─────────────────────────────────────────────

    def chat(self, user_message: str, thread_id: str = "main") -> str:
        """
        General chat interface for the digital employee.
        Used for direct interaction via UI or Teams.
        """
        briefing = self.memory.get_briefing()
        context_prefix = f"""
Current Date: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
Agent Identity: {self.identity.get('name', 'Digital Employee')} ({self.identity.get('email', '')})
Memory State: {json.dumps(briefing)}

User Message:
        """
        return self._call_claude(context_prefix + user_message, thread_id=thread_id)

    def get_briefing(self) -> dict:
        """Return current agent state briefing."""
        return self.memory.get_briefing()
