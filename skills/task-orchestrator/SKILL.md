---
version: 1.0.0
name: task-orchestrator
description: "Automated task orchestration with parallel execution, retry strategies, escalation, multi-input support (Excel, CSV, JSON, REST API, ClickUp), trigger system (webhooks, cron, direct API), and dependency management. Use when the user wants to automate workflows, schedule task pipelines, or manage multi-step operations."
---

# Task Orchestrator

Automated task orchestration engine. Execute complex multi-step workflows with
intelligent retry, parallel execution, human-in-the-loop escalation, and
multiple trigger types.

## Quick Start

```bash
pip3 install httpx pandas openpyxl apscheduler fastapi uvicorn
python3 skills/task-orchestrator/scripts/orchestrator_launcher.py
```

## Core Concepts

### Task Definition

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

- **EXPONENTIAL**: 30s → 60s → 120s
- **LINEAR**: 30s → 60s → 90s
- **NEW_APPROACH**: Uses alternative implementation code on retry

### Task Groups + Dependencies

```json
{
  "groups": [
    {"group_id": "g1", "tasks": ["t1", "t2"], "execution_mode": "PARALLEL", "max_concurrent": 3},
    {"group_id": "g2", "tasks": ["t3"], "execution_mode": "SEQUENTIAL"}
  ],
  "dependencies": {
    "t3": {"depends_on": ["t1", "t2"], "wait_for_success": true}
  }
}
```

## Trigger System

### Webhook Triggers

```bash
curl -X POST http://localhost:8000/webhooks/new-event \
  -H "Content-Type: application/json" \
  -d '{"id": "123"}'
```

### Scheduled Triggers (Cron)

```python
schedule_config = {"hour": 8, "minute": 0, "timezone": "UTC"}
```

### Direct API

```bash
curl -X POST http://localhost:8000/api/run-pipeline \
  -d '{"pipeline_name": "daily_ops"}'
```

## Input Sources

```bash
# JSON
python3 orchestrator_launcher.py --input tasks.json --mode json

# Excel (sheets: Tasks, Templates, Groups)
python3 orchestrator_launcher.py --input tasks.xlsx --mode excel

# CSV
python3 orchestrator_launcher.py --input tasks.csv --mode csv

# ClickUp
python3 orchestrator_launcher.py --mode clickup --api-key pk_xxx --list-id 12345

# REST API
python3 orchestrator_launcher.py --mode rest --api-url https://api.example.com/tasks
```

## Running as a Server

```bash
python3 orchestrator_launcher.py --serve --port 8000
```

Endpoints:
- `POST /webhooks/{trigger_id}` — webhook triggers
- `POST /api/run-pipeline` — direct API trigger
- `GET /api/status` — pipeline status
- `GET /api/logs/{execution_id}` — execution logs
- `GET /triggers` — list all triggers

## Configuration

```bash
ORCHESTRATOR_PORT=8000
ORCHESTRATOR_MAX_CONCURRENT=10
ORCHESTRATOR_DEFAULT_RETRY_STRATEGY=EXPONENTIAL
ORCHESTRATOR_BASE_DELAY=30
```
