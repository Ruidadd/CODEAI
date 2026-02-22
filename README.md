# Digital Employee

An AI-powered organizational assistant that acts like a senior executive coordinator (CEO/COO Chief of Staff). It has its own email, Microsoft Teams presence, and calendar — and autonomously tracks every project, meeting, contract, and employee work status.

## What It Does

```
📧 Email        → Reads, analyzes, and responds to emails
💬 Teams        → Monitors channels, tracks discussions, sends DMs
📅 Calendar     → Registers meetings, extracts action items
📊 Projects     → Tracks milestones, surfaces at-risk items
📝 Meetings     → Extracts action items, sends follow-ups
📄 Contracts    → Monitors expiry, alerts on pending signatures
👥 Team Health  → Observes work patterns, flags burnout risk
🤖 AI Agent     → Powered by Claude — generates all inquiries & reports
```

## Architecture

```
digital_employee/
├── agent/
│   ├── core_agent.py        # Claude-powered AI brain
│   ├── memory.py            # Entity, conversation & work context memory
│   └── prompts.py           # System prompts for all tasks
├── integrations/
│   ├── ms_graph.py          # Microsoft Graph API base client (OAuth2)
│   ├── email_client.py      # Email: read, send, reply, webhook
│   └── teams_client.py      # Teams: channels, DMs, presence, meetings
├── trackers/
│   ├── project_tracker.py   # Project health & milestone tracking
│   ├── meeting_tracker.py   # Meeting lifecycle & action items
│   ├── contract_tracker.py  # Contract expiry & signature pipeline
│   └── employee_tracker.py  # Work pattern signals & team health
├── scheduler/
│   └── task_scheduler.py    # Background job scheduler (APScheduler)
├── api/
│   ├── routes.py            # FastAPI REST endpoints
│   └── models.py            # Pydantic request/response models
├── database/
│   └── crud.py              # SQLite-backed document store
└── utils/
    └── helpers.py           # Shared utilities
```

## Scheduled Jobs

| Job | Frequency | Purpose |
|-----|-----------|---------|
| Email Monitor | Every 5 min | Read and analyze new emails |
| Teams Monitor | Every 5 min | Monitor channel messages |
| Follow-up Processor | Every 15 min | Send overdue follow-up messages |
| Contract Alerts | Every 1 hour | Alert on expiring contracts |
| Project Health Check | Every 1 hour | Follow up on stale projects |
| Morning Briefing | Daily 8am UTC | Send status digest to executives |
| EOD Digest | Daily 5pm UTC | Summarize pending/overdue items |
| Weekly Report | Monday 9am UTC | Full executive status report |

## Setup

### 1. Prerequisites

- Python 3.11+
- An Anthropic API key
- A Microsoft Azure AD app registration (for email/Teams)
- A public HTTPS URL for webhooks (use [ngrok](https://ngrok.com) for local dev)

### 2. Azure AD App Registration

1. Go to [Azure Portal](https://portal.azure.com) → Azure Active Directory → App registrations
2. Create a new app registration
3. Add **Application permissions** (not delegated):
   - `Mail.Read`, `Mail.Send`, `Mail.ReadWrite`
   - `ChannelMessage.Read.All`, `ChatMessage.Read`
   - `Calendars.Read`, `OnlineMeetings.Read.All`
   - `Presence.Read.All`, `User.Read.All`
4. Grant admin consent
5. Create a client secret
6. Note your Tenant ID, Client ID, and Client Secret

### 3. Install and Configure

```bash
pip install -r requirements.txt

cp .env.example .env
# Edit .env with your credentials
```

### 4. Run

```bash
python main.py
# API docs: http://localhost:8000/docs
```

### 5. Run Tests

```bash
pytest tests/ -v
```

## API Reference

### Chat
```
POST /api/v1/chat
```

### Projects
```
GET  /api/v1/projects
POST /api/v1/projects
PATCH /api/v1/projects/{id}
GET  /api/v1/projects/at-risk
```

### Meetings
```
POST /api/v1/meetings/process
GET  /api/v1/meetings/upcoming
GET  /api/v1/meetings/overdue-actions
```

### Contracts
```
GET  /api/v1/contracts
POST /api/v1/contracts
GET  /api/v1/contracts/expiring
GET  /api/v1/contracts/pending-signatures
```

### Employees
```
GET  /api/v1/employees
POST /api/v1/employees
GET  /api/v1/employees/health
GET  /api/v1/employees/{email}/health
```

### Reports
```
GET  /api/v1/digest
POST /api/v1/reports/status
POST /api/v1/followups/process-overdue
```

### Webhooks
```
POST /api/v1/webhooks/email
POST /api/v1/webhooks/teams
```

## Privacy and Ethics

The employee tracker observes **aggregate work patterns** (activity levels, response times), not message content. All insights are designed to help employees, not surveil them:

- No message content is stored for employee profiling
- Signals surface employees who may need support (overloaded, blocked, disengaged)
- Insights are framed as check-in recommendations, not performance records
- The system should be disclosed to employees

## How Invisible Collection Works

1. **Passive Observation**: Reads incoming emails/Teams messages and extracts entities (project names, deadlines, people)
2. **Calendar Integration**: Automatically registers meetings and processes them after completion
3. **Proactive Inquiry**: When signals go quiet (e.g., no project update for 7+ days), generates a natural follow-up

Follow-ups are generated by Claude to sound specific and contextual — not automated or robotic.
