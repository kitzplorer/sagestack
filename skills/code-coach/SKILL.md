---
name: Code Coach
version: 1.0.0
description: "Watches your code changes, identifies improvement areas, and pushes notifications to help you grow as a developer. Analyzes code patterns, security issues, naming, DRY violations, and git hygiene. Use when the user wants to watch a project for improvement opportunities, review a file, or get a daily learning tip."
---
# Code Coach

Watches your code changes, identifies improvement areas, and delivers
actionable tips. Like a senior dev looking over your shoulder — but less awkward.

Sends tips via macOS notifications or webhook (Slack/Discord/custom).

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

## Configuration

Set your notification channel in config:

```bash
COACH_NOTIFY_CHANNEL=slack   # or: macos, discord, webhook
COACH_WEBHOOK_URL=https://hooks.slack.com/services/...
COACH_WATCH_EXTENSIONS=.py,.ts,.tsx,.js,.go,.rs
COACH_MIN_SEVERITY=medium    # low, medium, high
```

## Events Published

- `coach.tip.sent` — improvement tip delivered
- `coach.pattern.detected` — code pattern found with fix suggestion
