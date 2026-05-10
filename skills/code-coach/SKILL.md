---
name: Code Coach
version: 1.0.0
description: "Watches your code changes, identifies improvement areas, and pushes"
---
# Code Coach

Watches your code changes, identifies improvement areas, and pushes
notifications to help you grow as a developer. Like a senior dev
looking over your shoulder — but less awkward.

Sends actionable tips, links to short reads, and pattern improvements
via macOS notifications or webhook (WhatsApp/Slack/Discord).

## Usage

```bash
# Watch project for improvement opportunities
python3 skills/code-coach/scripts/code_coach.py watch /path/to/project

# Analyze a single file
python3 skills/code-coach/scripts/code_coach.py review /path/to/file.py

# Get today's learning tip
python3 skills/code-coach/scripts/code_coach.py tip

# Show your improvement stats
python3 skills/code-coach/scripts/code_coach.py stats

# Configure notification channels
python3 skills/code-coach/scripts/code_coach.py config
```

## What It Checks

- Code patterns (magic numbers, long functions, deep nesting)
- Security patterns (hardcoded secrets, SQL injection, XSS)
- Best practices (naming, DRY, error handling)
- Git patterns (commit sizes, branch hygiene)
- Sends relevant short reads (2-5 min articles) for each area

## Events Published

- `coach.tip.sent` — improvement tip delivered
- `coach.pattern.detected` — code pattern found

## How this is verified at L5

The skill invokes code analysis via `scripts/code_coach.py` which calls the sagent LLM router (ctx_route task_class=summarize_short) to generate coaching tips. L1: skill file exists with CLI entry points (watch, review, tip, stats). L3: invocation produces real coaching feedback and macOS/webhook notifications, not stubs. L5: matches sagent code-review patterns (pattern detection, security checks, DRY violations) and integrates with sagent event bus for telemetry; no external coaching peer applies.
