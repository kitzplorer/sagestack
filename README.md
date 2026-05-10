# aistack

One-command AI coding stack — supervisor, bar raiser, skills, and cross-IDE MCP wiring.

Works on any macOS 12+ or Ubuntu 22+ machine. No cloud account required beyond your API key.

## What you get

| Component | What it does |
|---|---|
| **bar raiser** | Blocks plans that rebuild existing work, score <7/10 business value, or miss requirements |
| **supervisor** | Claim lifecycle ledger — L1→L5 verification for every file you touch |
| **20 curated skills** | `/design-review`, `/code-coach`, `/task-orchestrator`, `/github`, and 16 more |
| **memory agent** | Writes session summaries to CONTEXT.md so any LLM picks up where you left off |
| **cross-IDE MCP** | Wires sagent MCP into Claude Code, Cursor, Windsurf, Zed, Claude Desktop |

## Install (macOS / Linux)

```bash
curl -fsSL https://raw.githubusercontent.com/[org]/aistack/main/scripts/aistack-install.sh | bash
```

## Install (Windows — native or WSL2)

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\scripts\aistack-install.ps1
```

## What gets installed

```
~/.aistack/
  hooks/           # bar_raiser.py, supervisor hooks
  supervisor/      # standalone L1-L5 claim verifier
  skills/          # 20 general-purpose slash commands
  mcp/             # sagent-mcp.py bridge
  memory_agent.py  # cross-LLM session memory
  signals.db       # SQLite MCP cache (offline resilience)
  context.json     # cross-tool handoff state
```

## Dry run

```bash
bash scripts/aistack-install.sh --dry-run
```

## Uninstall

```bash
bash scripts/aistack-uninstall.sh
```

## Configuration

Copy `templates/aistack.config.example.json` to `~/.aistack/config.json` and set:

```json
{
  "backend": "http://localhost:8042",
  "anthropic_api_key": "sk-ant-...",
  "ollama_url": "http://localhost:11434"
}
```

## Bar raiser

Blocks Claude Code plans automatically via `UserPromptSubmit` hook. Checks:
- Would this rebuild already-shipped work?
- Business value score ≥ 7/10
- Prompt execution coverage ≥ 90%
- Cardinality rule: "every/all X" claims must cover ≥ 90% of actual X population

LLM chain: your sagent backend → Anthropic API → Ollama → fail-open.

## Supervisor CLI

```bash
python3 ~/.aistack/supervisor/supervisor.py status
python3 ~/.aistack/supervisor/supervisor.py sweep
python3 ~/.aistack/supervisor/supervisor.py verify --target path/to/file.py
python3 ~/.aistack/supervisor/supervisor.py blocked
```

## Memory agent

```bash
# Auto-run (wired via Stop hook):
python3 ~/.aistack/memory_agent.py

# Manual after Cursor session:
python3 ~/.aistack/memory_agent.py --llm "Cursor" --summary "fixed auth bug, added tests"

# Init a new project:
python3 ~/.aistack/memory_agent.py --init --project /path/to/repo
```

## License

MIT
