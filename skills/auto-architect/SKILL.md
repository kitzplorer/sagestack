---
version: 1.0.0
name: auto-architect
description: "Autonomous architecture-to-deployment pipeline. Reads architecture docs (.xlsx, .docx, .md, .pdf) from a folder, extracts technology requirements, plans dependency installation order using topological sort on dependency graphs, monitors system resources (CPU, RAM, disk) to schedule work, manages multi-provider API keys with automatic failback chains, bridges to any IDE via Language Server Protocol, auto-triggers testing/security/advisor agents after implementation, and communicates with all other skills via an event bus (MCP culture). Use when the user wants to install a full tech stack from architecture docs, manage API keys, orchestrate coding agents, or automate the build-test-secure pipeline."
metadata:
  {
    "openclaw":
      {
        "emoji": "🏗️",
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
          ],
        "os": ["darwin", "linux"],
      },
  }
---

# Auto-Architect: Autonomous Architecture-to-Deployment Pipeline

Reads architecture documents, extracts technology requirements, builds a dependency graph, and installs everything in topologically-sorted order while monitoring system resources. Orchestrates coding agents, manages API keys with fallback chains, and auto-triggers post-implementation agents.

## Core Rules

- NEVER install anything without showing the plan to the user first.
- ALWAYS check system resources before starting heavy operations.
- ALWAYS use the dependency graph to determine correct installation order.
- NEVER store API keys in plaintext — use the encrypted key vault.
- When an agent fails, escalate to human with full context, never silently retry forever.
- Respect the LLM Architecture Bible commandments when making architecture decisions.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    AUTO-ARCHITECT                        │
│                                                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │  Doc     │  │ Resource │  │  API Key │             │
│  │  Reader  │→ │ Monitor  │→ │  Vault   │             │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘             │
│       │              │              │                   │
│       ▼              ▼              ▼                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐             │
│  │ Dep Graph│  │ Installer│  │ Agent    │             │
│  │ (Topo   │→ │ (Plan +  │→ │ Bus     │             │
│  │  Sort)  │  │  Execute)│  │ (Events)│             │
│  └─────────┘  └──────────┘  └────┬─────┘             │
│                                   │                    │
│       ┌───────────────────────────┼───────────┐       │
│       ▼              ▼            ▼            ▼       │
│  ┌─────────┐  ┌──────────┐ ┌─────────┐ ┌──────────┐ │
│  │ Coding  │  │ Testing  │ │Security │ │ Software │ │
│  │ Agent   │  │ Agent    │ │ Agent   │ │ Advisor  │ │
│  └─────────┘  └──────────┘ └─────────┘ └──────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Workflows

### 1. Full Architecture Scan & Install

Place architecture documents in `~/.openclaw/architecture/` (or any folder), then:

> Scan my architecture docs and install everything needed

The system will:

1. Parse all `.xlsx`, `.docx`, `.md`, `.pdf` files in the folder
2. Extract technology names, versions, ports, and dependencies
3. Build a directed acyclic graph (DAG) of dependencies
4. Topologically sort the DAG for correct install order
5. Check current system state (what's already installed)
6. Show the installation plan with estimated resource usage
7. After user approval, install in dependency order
8. Verify each installation before proceeding to the next
9. Report results and trigger security scan

### 2. Add New Software from Excel

> Install the new tools from my updated tech stack spreadsheet

The orchestrator watches for file changes in the architecture folder. When a new `.xlsx` is detected:

1. Diff against the previous known state
2. Extract only NEW entries
3. Build incremental dependency graph
4. Plan installation considering PC load
5. Execute when resources are available

### 3. API Key Management

> Add my Claude API key with OpenAI and Groq as fallbacks

The vault stores encrypted keys with priority chains:

- Primary key used first
- On failure (rate limit, quota, timeout), automatically rotates to next
- Tracks usage, costs, and remaining quota per key
- Alerts when approaching limits

### 4. Autonomous Coding Pipeline

> Implement the auth service from the architecture doc

The coding agent:

1. Reads architecture requirements for the specific component
2. Connects to the active IDE (VS Code, Cursor, Windsurf, or terminal)
3. Generates code following architecture principles
4. Runs in error-correction loop (max 5 iterations)
5. Consults historical error patterns before attempting fixes
6. Escalates to human when stuck (not after 50 retries — after 3 meaningful attempts)
7. On completion, triggers: test agent, security scan, software advisor

### 5. Resource-Aware Scheduling

> The system should install Docker, Node, and Python but my laptop is at 80% CPU

The resource monitor:

- Checks CPU%, RAM%, disk I/O before each operation
- Queues heavy operations (Docker builds, npm install) when load is high
- Runs lightweight tasks (config, env setup) immediately
- Respects user-configurable thresholds

## Event Bus (MCP Culture)

All agents communicate via a publish-subscribe event bus:

```
Event: INSTALL_COMPLETE {tool: "docker", version: "24.0"}
  → Security Agent: scan Docker config
  → Software Advisor: check for known CVEs
  → File Scavenger: index new files

Event: CODE_COMPLETE {service: "auth-service", files: [...]}
  → Testing Agent: run pytest on auth-service
  → Security Agent: scan for vulnerabilities
  → File Scavenger: check for leftover temp files

Event: ERROR_DETECTED {agent: "coding", error: "...", attempts: 3}
  → Human Escalation: show context, ask for guidance
```

## Configuration

Environment variables in `~/.openclaw/.env`:

```bash
# Architecture docs folder
ARCH_DOCS_PATH=~/.openclaw/architecture/

# Resource thresholds (0-100)
MAX_CPU_PERCENT=75
MAX_RAM_PERCENT=80
MAX_DISK_PERCENT=90

# API Key Vault (auto-encrypted)
KEY_VAULT_PATH=~/.openclaw/vault/keys.enc

# Agent settings
MAX_CODING_RETRIES=5
ESCALATION_AFTER_ATTEMPTS=3
HUMAN_TIMEOUT_SECONDS=300

# Auto-trigger agents after events
AUTO_TRIGGER_TESTS=true
AUTO_TRIGGER_SECURITY=true
AUTO_TRIGGER_ADVISOR=true
AUTO_TRIGGER_SCAVENGER=true
```
