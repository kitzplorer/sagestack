---
name: Auto-Handoff
version: 1.0.0
description: "Watches for code changes and tasks, automatically routes them to the right skill or agent. Use when the user wants to watch a directory and automatically trigger the right workflow on file save — e.g. frontend errors to Frontend Helper, package changes to dependency installer, security configs to Network Security."
---
# Auto-Handoff

Watches a directory for file changes (save events), analyzes what changed,
and routes to the appropriate skill automatically.

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

## Routing Rules (customizable)

```yaml
rules:
  - match: "*.tsx,*.jsx,*.css"
    skill: frontend-helper
  - match: "*.yml,*.yaml"
    skill: auto-architect
    condition: "path contains 'architecture'"
  - match: "package.json,requirements.txt,Cargo.toml"
    skill: software-advisor
  - match: "*.py,*.ts,*.go,*.rs"
    skill: code-coach
  - match: "nginx.conf,sshd_config,firewall*"
    skill: network-security
```

## Events Published

- `handoff.task.routed` — task sent to a skill
- `handoff.task.completed` — skill finished processing
- `handoff.error` — routing or execution error
