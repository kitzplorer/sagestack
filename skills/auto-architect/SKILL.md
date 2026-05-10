---
version: 1.0.0
name: auto-architect
description: "Autonomous architecture-to-deployment pipeline. Reads architecture docs (.xlsx, .docx, .md, .pdf), extracts technology requirements, plans dependency installation using topological sort, monitors system resources (CPU, RAM, disk), manages multi-provider API keys with fallback chains, bridges to IDEs via LSP, and auto-triggers testing/security agents. Use when the user wants to install a full tech stack from architecture docs, manage API keys, or automate the build-test-secure pipeline."
---

# Auto-Architect: Autonomous Architecture-to-Deployment Pipeline

Reads architecture documents, extracts technology requirements, builds a dependency graph, and installs everything in topologically-sorted order while monitoring system resources.

## Core Rules

- NEVER install anything without showing the plan to the user first.
- ALWAYS check system resources before starting heavy operations.
- ALWAYS use the dependency graph to determine correct installation order.
- NEVER store API keys in plaintext — use the encrypted key vault.
- When an agent fails, escalate to human with full context, never silently retry forever.

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

### 2. API Key Management

> Add my Claude API key with OpenAI and Groq as fallbacks

The vault stores encrypted keys with priority chains:
- Primary key used first
- On failure (rate limit, quota, timeout), automatically rotates to next
- Tracks usage, costs, and remaining quota per key
- Alerts when approaching limits

### 3. Resource-Aware Scheduling

The resource monitor:
- Checks CPU%, RAM%, disk I/O before each operation
- Queues heavy operations (Docker builds, npm install) when load is high
- Runs lightweight tasks (config, env setup) immediately

## Configuration

Environment variables in `~/.openclaw/.env`:

```bash
ARCH_DOCS_PATH=~/.openclaw/architecture/
MAX_CPU_PERCENT=75
MAX_RAM_PERCENT=80
MAX_DISK_PERCENT=90
KEY_VAULT_PATH=~/.openclaw/vault/keys.enc
MAX_CODING_RETRIES=5
ESCALATION_AFTER_ATTEMPTS=3
AUTO_TRIGGER_TESTS=true
AUTO_TRIGGER_SECURITY=true
```

## Event Bus

All agents communicate via publish-subscribe events:

```
Event: INSTALL_COMPLETE {tool: "docker", version: "24.0"}
  → Security Agent: scan Docker config
  → Software Advisor: check for known CVEs

Event: CODE_COMPLETE {service: "auth-service", files: [...]}
  → Testing Agent: run tests
  → Security Agent: scan for vulnerabilities

Event: ERROR_DETECTED {agent: "coding", error: "...", attempts: 3}
  → Human Escalation: show context, ask for guidance
```
