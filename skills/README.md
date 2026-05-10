# ~/.aistack/skills — General-Purpose Skill Library

20 skills curated from the sagent/OpenClaw ecosystem. Each works on **any codebase** without sagent backend dependencies.

| # | Skill | Description |
|---|-------|-------------|
| 1 | **auto-architect** | Architecture-doc-to-deployment pipeline: reads `.xlsx/.docx/.md/.pdf`, builds a dependency DAG, installs in topological order, manages API key vault with fallback chains |
| 2 | **auto-handoff** | File-watcher that auto-routes changes to the right skill: frontend errors → Frontend Helper, security configs → Network Security, code files → Local LLM review |
| 3 | **browser-explore** | Interactive browser automation decision tree: Playwright MCP for DOM-native exploration, agent-browser CLI for one-liners, Playwright test runner for committed E2E suites |
| 4 | **code-coach** | Watches code changes and delivers actionable improvement tips (patterns, DRY, security, naming, git hygiene) via macOS notifications or Slack/Discord webhook |
| 5 | **engineering-governance** | Unified pre-commit / pre-merge / pre-deploy gate CLI. Codifies FAANG-level rules: migration parity, schema drift, secret scan, PR size, ADR requirements, runbook checks |
| 6 | **engineering-policies** | Policy registry (`modules/policies/`) that surfaces top-5 relevant rules at task kickoff. Agents must cite policy IDs; violations emit events; bypasses require reason + expiry |
| 7 | **file-scavenger** | Finds obsolete files across a project or system (orphaned node_modules, stale venvs, extracted archives, dead code) and presents them for review — never auto-deletes |
| 8 | **frontend-helper** | Next.js 14 / React 18 / TypeScript / Tailwind error translator. Paste terminal output, ask questions, or scan a project directory for common frontend issues |
| 9 | **github** | `gh` CLI patterns for PRs, issues, CI runs, and advanced API queries. Covers checking CI status, viewing failed logs, JSON output with `--jq`, and multi-repo operations |
| 10 | **llm-fallback** | Chains LLM providers (Claude → OpenAI → Groq → Ollama → LM Studio) so when one fails the next picks up. Check status, test the chain, configure chain order |
| 11 | **local-llm-connector** | Auto-detects and connects to self-hosted LLMs (Ollama, LM Studio, LocalAI, any OpenAI-compatible). Lists models, runs code gen, exposes a unified proxy on a single port |
| 12 | **migration-health** | SQL migration inventory audit: gaps in numbering, duplicates, missing `down/` siblings, ghosts (applied but deleted), and checksum drift. Works with or without a live DB |
| 13 | **model-usage** | Summarizes per-model LLM cost from CodexBar's local cost logs. Current model, full breakdown, JSON output. macOS only (requires `codexbar` CLI) |
| 14 | **nano-pdf** | Natural-language PDF editing via the `nano-pdf` CLI. Edit specific pages with a plain-English instruction; always sanity-check output before sending |
| 15 | **network-security** | Port scanner + firewall checker + continuous connection monitor. Quick scan, deep scan (all 65535 ports), exposure assessment, CVE cross-reference. Read-only unless user approves |
| 16 | **notion** | Notion REST API patterns for pages, databases (data sources), and blocks. Full CRUD with `curl` examples. Covers the 2025-09-03 API version (databases → data sources rename) |
| 17 | **skill-creator** | Step-by-step guide for designing, structuring, and packaging new agent skills. Covers naming, progressive-disclosure design, scripts/references/assets layout, and packaging |
| 18 | **software-advisor** | CVE + EOL scanner for system packages, language runtimes, and project dependencies. Sorted by severity (CRITICAL → LOW), with migration commands for every finding |
| 19 | **summarize** | Fast CLI to summarize URLs, local files, YouTube links, and podcasts via `summarize` CLI. Supports multiple LLM providers, transcript extraction, and configurable length |
| 20 | **task-orchestrator** | Multi-step workflow engine: parallel/sequential/batched execution, exponential retry, dependency graphs, webhook/cron/REST triggers, and Excel/CSV/JSON/ClickUp input sources |

## Selection criteria

All 20 skills pass the following test: they work on **any codebase** without the sagent FastAPI backend, sagent MCP tools, or project-specific business logic.

Excluded categories:
- Skills wrapping sagent-only MCP tools (`mcp__sagent__*`)
- Device-specific skills (Apple Notes, Bear, camsnap, openhue, etc.)
- Thin CLI wrappers for single-person workflows (food-order, gifgrep, joke-generator)
- Project-specific business logic (trackers/HRMS, erp_pos, grill-kitchen)

## Usage

These skills are loaded by any Claude Code session that has `~/.aistack/skills/` in its skill path. Install into a specific project by copying the skill folder or referencing via marketplace.
