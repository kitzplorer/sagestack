---
name: Auto-Handoff
version: 1.0.0
description: "Watches for code changes and tasks, automatically routes them to the right"
---
# Auto-Handoff

Watches for code changes and tasks, automatically routes them to the right
bot/skill. Even small pieces of work get handed off immediately.

## How It Works

1. Watches a directory for file changes (save events)
2. Analyzes what changed (new file? error? config? test?)
3. Routes to the appropriate skill:
   - Frontend errors → Frontend Helper
   - Architecture docs → Auto-Architect Scanner
   - Package changes → Dependency Installer
   - Security config → Network Security
   - Code files → Local LLM for review/completion
4. Reports progress via events and notifications

## Usage

```bash
# Start watching a project
python3 skills/auto-handoff/scripts/auto_handoff.py watch /path/to/project

# One-time analysis of a file
python3 skills/auto-handoff/scripts/auto_handoff.py analyze /path/to/file

# Show routing rules
python3 skills/auto-handoff/scripts/auto_handoff.py rules

# Status of running handoffs
python3 skills/auto-handoff/scripts/auto_handoff.py status
```

## Events Published

- `handoff.task.routed` — task sent to a skill
- `handoff.task.completed` — skill finished processing
- `handoff.error` — routing or execution error
