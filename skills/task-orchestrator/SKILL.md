---
version: 1.0.0
name: task-orchestrator
description: "Automated task orchestration with parallel execution, retry strategies, escalation via WhatsApp, multi-input support (Excel, CSV, JSON, REST API, ClickUp), trigger system (webhooks, cron, WhatsApp commands, direct API), and dependency management. Use when the user wants to automate workflows, schedule task pipelines, or manage multi-step operations."
metadata:
  {
    "openclaw":
      {
        "emoji": "🎯",
        "requires": { "bins": ["python3"] },
        "install":
          [
            {
              "id": "brew-python",
              "kind": "brew",
              "formula": "python@3.12",
              "bins": ["python3"],
              "label": "Install Python 3.12 (brew)",
            },
            {
              "id": "apt-python",
              "kind": "apt",
              "package": "python3",
              "bins": ["python3"],
              "label": "Install Python 3 (apt)",
            },
          ],
      },
  }
---

# Task Orchestrator

Automated task orchestration engine for OpenClaw. Execute complex multi-step workflows with intelligent retry, parallel execution, human-in-the-loop escalation, and multiple trigger types.

## Quick Start

### 1. Install Python dependencies

```bash
pip3 install httpx pandas openpyxl apscheduler fastapi uvicorn
```

### 2. Run the orchestrator

The orchestrator lives at `skills/task-orchestrator/scripts/`. Use the launcher:

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py
```

## Architecture

```
                    ┌──────────────────┐
                    │  TRIGGER SYSTEM  │
                    │  (4 trigger types)│
                    └────────┬─────────┘
                             │
              ┌──────────────▼──────────────┐
              │     MULTI-INPUT HANDLER     │
              │ Excel│CSV│JSON│API│ClickUp  │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │    ADVANCED ORCHESTRATOR    │
              │ Parallel│Sequential│Batched │
              │ Dependencies│Groups│Retry   │
              └──────────────┬──────────────┘
                             │
              ┌──────────────▼──────────────┐
              │   OPENCLAW INTEGRATION     │
              │ WhatsApp Escalation│Status  │
              └─────────────────────────────┘
```

## Core Concepts

### Task Definition

Tasks can be defined inline, from JSON, from Excel, or from external systems:

```json
{
  "task_id": "scrape_data_001",
  "title": "Scrape Job Portals",
  "implementation_code": "import httpx; resp = httpx.get('https://api.example.com/jobs'); context.set_variable('jobs', resp.json())",
  "test_cases": [
    {
      "name": "verify_data",
      "check_function": "len(context.shared_state.get('jobs', [])) > 0",
      "expected_result": true,
      "failure_is_critical": true
    }
  ],
  "priority": 1,
  "retry_config": {
    "max_attempts": 3,
    "strategy": "EXPONENTIAL",
    "base_delay_seconds": 30,
    "escalate_after_attempts": 2
  }
}
```

### Execution Modes

- **SEQUENTIAL**: Tasks run one at a time, in order
- **PARALLEL**: Tasks run concurrently (configurable `max_concurrent`)
- **BATCHED**: Tasks run in groups of N

### Retry Strategies

- **EXPONENTIAL**: 30s → 60s → 120s (doubles each time)
- **LINEAR**: 30s → 60s → 90s (adds base delay each time)
- **NEW_APPROACH**: Uses alternative implementation code on retry

### Task Groups

Group tasks for execution control:

```json
{
  "groups": [
    {
      "group_id": "group_1",
      "name": "Data Collection",
      "tasks": ["task_1", "task_2", "task_3"],
      "execution_mode": "PARALLEL",
      "max_concurrent": 3
    },
    {
      "group_id": "group_2",
      "name": "Processing",
      "tasks": ["task_4", "task_5"],
      "execution_mode": "SEQUENTIAL"
    }
  ]
}
```

### Dependencies

```json
{
  "dependencies": {
    "task_4": { "depends_on": ["task_1", "task_2"], "wait_for_success": true },
    "task_5": { "depends_on": ["task_4"], "wait_for_success": true }
  }
}
```

## Trigger System (4 Types)

### 1. Webhook Triggers (Event-Based)

External systems POST to your endpoint to start workflows:

```bash
curl -X POST http://localhost:8000/webhooks/new-candidate \
  -H "Content-Type: application/json" \
  -d '{"candidate_id": "123", "name": "John Doe"}'
```

### 2. Scheduled Triggers (Cron-Based)

Run pipelines on a schedule:

```python
# Daily at 8 AM
schedule_config = {"hour": 8, "minute": 0, "timezone": "Asia/Kolkata"}

# Monday/Wednesday/Friday at 9 AM
schedule_config = {"hour": 9, "minute": 0, "day_of_week": "mon,wed,fri"}
```

### 3. WhatsApp Command Triggers

Send commands via WhatsApp to trigger pipelines:

```
RUN_PIPELINE
GET_STATUS
```

### 4. Direct API Triggers

Call the REST API directly:

```bash
curl -X POST http://localhost:8000/api/run-pipeline \
  -H "Content-Type: application/json" \
  -d '{"pipeline_name": "daily_recruitment"}'
```

## Input Sources

### JSON File

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py \
  --input tasks.json --mode json
```

### Excel File

Create an Excel file with sheets: Tasks, Templates, Groups.

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py \
  --input tasks.xlsx --mode excel
```

### CSV File

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py \
  --input tasks.csv --mode csv
```

### ClickUp

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py \
  --mode clickup --api-key pk_xxx --list-id 12345
```

### REST API

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py \
  --mode rest --api-url https://api.example.com/tasks
```

## Task Templates (Pre-Built)

4 built-in templates to reduce task definition time by ~83%:

1. **send_emails** - Bulk email sending with template support
2. **parse_csv** - CSV file parsing with validation
3. **api_call** - REST API calling with auth
4. **database_update** - Database updates with verification

Use templates in Excel:

| task_id | title       | use_template | recipient_source | email_subject   |
| ------- | ----------- | ------------ | ---------------- | --------------- |
| task_1  | Send Emails | send_emails  | candidates.csv   | New Opportunity |

## Escalation (Human-in-the-Loop)

When a task fails beyond retry threshold, the system sends a WhatsApp message:

```
🚨 Task Escalation Required

Task: Send Emails
Attempts: 2/3
Error: Connection timeout

1️⃣ RETRY_NEW - Try different approach
2️⃣ MANUAL_FIX - I'll handle it
3️⃣ SKIP - Skip this task
4️⃣ CANCEL - Stop everything

Reply with: 1, 2, 3, or 4
```

## Multi-Instance Support

Run the same pipeline for multiple clients simultaneously:

```python
orchestrator = MultiInstanceOrchestrator()
orchestrator.create_instance("client_a")
orchestrator.create_instance("client_b")
results = await orchestrator.run_all_instances(plan)
```

## Running the Server

Start the orchestrator as a FastAPI server with all triggers active:

```bash
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py --serve --port 8000
```

This starts:

- Webhook endpoints: `/webhooks/{trigger_id}`
- Direct API: `/api/run-pipeline`
- Scheduled triggers (background)
- WhatsApp command listener (via OpenClaw)
- Status endpoint: `GET /triggers`

## Monitoring

Check pipeline status:

```bash
curl http://localhost:8000/api/status
```

View execution logs:

```bash
curl http://localhost:8000/api/logs/{execution_id}
```

## Example: Daily Workflow Pipeline

```json
{
  "pipeline": "daily_operations",
  "groups": [
    {
      "name": "Data Collection",
      "execution_mode": "PARALLEL",
      "max_concurrent": 5,
      "tasks": ["scrape_portal_1", "scrape_portal_2", "scrape_portal_3"]
    },
    {
      "name": "Processing",
      "execution_mode": "SEQUENTIAL",
      "tasks": ["parse_data", "validate", "store"]
    },
    {
      "name": "Notifications",
      "execution_mode": "PARALLEL",
      "tasks": ["send_emails", "update_dashboard"]
    }
  ],
  "triggers": {
    "scheduled": { "hour": 8, "minute": 0 },
    "webhook": "/webhooks/new-data",
    "whatsapp": "RUN_DAILY"
  }
}
```

## Configuration

Set via environment variables or OpenClaw config:

```bash
ORCHESTRATOR_PORT=8000
ORCHESTRATOR_MAX_CONCURRENT=10
ORCHESTRATOR_DEFAULT_RETRY_STRATEGY=EXPONENTIAL
ORCHESTRATOR_BASE_DELAY=30
OPENCLAW_API_URL=http://localhost:3000
OPENCLAW_API_KEY=your_key
OPENCLAW_BOT_ID=your_bot_id
OPENCLAW_PHONE=+91XXXXXXXXXX
```
