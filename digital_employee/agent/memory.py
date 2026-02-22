"""
Memory and context management for the Digital Employee agent.
Maintains conversation history, entity memory, and work context.
"""

import json
from datetime import datetime, timedelta
from typing import Any, Optional
from collections import defaultdict


class EntityMemory:
    """Tracks known entities: people, projects, contracts, meetings."""

    def __init__(self):
        self._people: dict[str, dict] = {}
        self._projects: dict[str, dict] = {}
        self._contracts: dict[str, dict] = {}
        self._meetings: dict[str, dict] = {}

    def upsert_person(self, email: str, data: dict):
        if email not in self._people:
            self._people[email] = {"first_seen": datetime.utcnow().isoformat(), "interactions": 0}
        self._people[email].update(data)
        self._people[email]["last_seen"] = datetime.utcnow().isoformat()
        self._people[email]["interactions"] = self._people[email].get("interactions", 0) + 1

    def upsert_project(self, project_id: str, data: dict):
        if project_id not in self._projects:
            self._projects[project_id] = {"created_at": datetime.utcnow().isoformat()}
        self._projects[project_id].update(data)
        self._projects[project_id]["updated_at"] = datetime.utcnow().isoformat()

    def upsert_contract(self, contract_id: str, data: dict):
        if contract_id not in self._contracts:
            self._contracts[contract_id] = {"created_at": datetime.utcnow().isoformat()}
        self._contracts[contract_id].update(data)
        self._contracts[contract_id]["updated_at"] = datetime.utcnow().isoformat()

    def upsert_meeting(self, meeting_id: str, data: dict):
        if meeting_id not in self._meetings:
            self._meetings[meeting_id] = {"created_at": datetime.utcnow().isoformat()}
        self._meetings[meeting_id].update(data)
        self._meetings[meeting_id]["updated_at"] = datetime.utcnow().isoformat()

    def get_person(self, email: str) -> Optional[dict]:
        return self._people.get(email)

    def get_project(self, project_id: str) -> Optional[dict]:
        return self._projects.get(project_id)

    def get_all_projects(self) -> dict:
        return self._projects.copy()

    def get_all_contracts(self) -> dict:
        return self._contracts.copy()

    def get_all_meetings(self) -> dict:
        return self._meetings.copy()

    def get_people_without_recent_contact(self, days: int = 7) -> list[str]:
        """Return emails of people we haven't interacted with recently."""
        cutoff = datetime.utcnow() - timedelta(days=days)
        result = []
        for email, data in self._people.items():
            last_seen = data.get("last_seen")
            if last_seen:
                last_dt = datetime.fromisoformat(last_seen)
                if last_dt < cutoff:
                    result.append(email)
        return result


class ConversationMemory:
    """Maintains rolling conversation history per contact."""

    def __init__(self, max_messages_per_thread: int = 20):
        self._threads: dict[str, list[dict]] = defaultdict(list)
        self._max = max_messages_per_thread

    def add_message(self, thread_id: str, role: str, content: str, metadata: dict = None):
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        self._threads[thread_id].append(msg)
        # Keep only recent messages
        if len(self._threads[thread_id]) > self._max:
            self._threads[thread_id] = self._threads[thread_id][-self._max:]

    def get_thread(self, thread_id: str) -> list[dict]:
        return self._threads.get(thread_id, [])

    def get_claude_format(self, thread_id: str) -> list[dict]:
        """Return messages in Claude API format."""
        return [
            {"role": m["role"], "content": m["content"]}
            for m in self._threads.get(thread_id, [])
            if m["role"] in ("user", "assistant")
        ]

    def summarize_thread(self, thread_id: str) -> str:
        """Return a text summary of the thread for context injection."""
        messages = self._threads.get(thread_id, [])
        if not messages:
            return "No prior conversation."
        lines = []
        for m in messages[-5:]:  # Last 5 messages
            ts = m["timestamp"][:10]
            lines.append(f"[{ts}] {m['role'].upper()}: {m['content'][:200]}")
        return "\n".join(lines)


class WorkContextMemory:
    """Tracks the agent's ongoing work context: pending tasks, signals, insights."""

    def __init__(self):
        self._pending_followups: list[dict] = []
        self._signals: list[dict] = []  # Observed behavioral signals
        self._insights: list[dict] = []  # AI-generated insights

    def add_followup(self, followup: dict):
        """Register a pending follow-up action."""
        followup["created_at"] = datetime.utcnow().isoformat()
        followup["status"] = "pending"
        self._pending_followups.append(followup)

    def complete_followup(self, followup_id: str):
        for f in self._pending_followups:
            if f.get("id") == followup_id:
                f["status"] = "completed"
                f["completed_at"] = datetime.utcnow().isoformat()
                break

    def get_pending_followups(self) -> list[dict]:
        return [f for f in self._pending_followups if f.get("status") == "pending"]

    def get_overdue_followups(self) -> list[dict]:
        now = datetime.utcnow()
        overdue = []
        for f in self._pending_followups:
            if f.get("status") != "pending":
                continue
            due = f.get("due_by")
            if due and datetime.fromisoformat(due) < now:
                overdue.append(f)
        return overdue

    def add_signal(self, signal_type: str, entity: str, data: dict):
        """Record an observed signal about a person or entity."""
        self._signals.append({
            "type": signal_type,
            "entity": entity,
            "data": data,
            "observed_at": datetime.utcnow().isoformat()
        })
        # Keep last 500 signals
        if len(self._signals) > 500:
            self._signals = self._signals[-500:]

    def get_signals_for(self, entity: str, days: int = 7) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(days=days)
        return [
            s for s in self._signals
            if s["entity"] == entity
            and datetime.fromisoformat(s["observed_at"]) > cutoff
        ]

    def add_insight(self, insight: dict):
        insight["generated_at"] = datetime.utcnow().isoformat()
        self._insights.append(insight)

    def get_recent_insights(self, hours: int = 24) -> list[dict]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        return [
            i for i in self._insights
            if datetime.fromisoformat(i["generated_at"]) > cutoff
        ]

    def export_state(self) -> dict:
        return {
            "pending_followups": len(self.get_pending_followups()),
            "overdue_followups": len(self.get_overdue_followups()),
            "recent_signals": len(self._signals[-50:]),
            "recent_insights": len(self.get_recent_insights())
        }


class AgentMemory:
    """Unified memory system for the Digital Employee agent."""

    def __init__(self):
        self.entities = EntityMemory()
        self.conversations = ConversationMemory()
        self.work_context = WorkContextMemory()

    def serialize(self) -> str:
        """Serialize memory state to JSON string for persistence."""
        return json.dumps({
            "entities": {
                "people": self.entities._people,
                "projects": self.entities._projects,
                "contracts": self.entities._contracts,
                "meetings": self.entities._meetings,
            },
            "work_context": self.work_context.export_state()
        }, default=str)

    def get_briefing(self) -> dict:
        """Return a high-level briefing of current state."""
        state = self.work_context.export_state()
        return {
            "known_people": len(self.entities._people),
            "tracked_projects": len(self.entities._projects),
            "tracked_contracts": len(self.entities._contracts),
            "tracked_meetings": len(self.entities._meetings),
            **state
        }
