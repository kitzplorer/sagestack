# ~/.sagestack/supervisor — Standalone Verification Harness

Portable AI-stack supervisor. Runs on any machine with Python 3.10+.  
No FastAPI, no sagent imports, no pip dependencies beyond stdlib.

---

## Install

```bash
# Already at ~/.sagestack/supervisor/ — nothing to pip-install.
# Make the CLI executable:
chmod +x ~/.sagestack/supervisor/supervisor.py
```

---

## Usage

```bash
# Show open claims, tier distribution, LLM tier
python3 ~/.sagestack/supervisor/supervisor.py status

# Re-evaluate all open claims (file-level collectors)
python3 ~/.sagestack/supervisor/supervisor.py sweep

# Add LLM eval during sweep
python3 ~/.sagestack/supervisor/supervisor.py sweep --llm

# Verify claims for one file
python3 ~/.sagestack/supervisor/supervisor.py verify --target path/to/file.py

# List blocking claims only
python3 ~/.sagestack/supervisor/supervisor.py blocked

# Add a claim manually
python3 ~/.sagestack/supervisor/supervisor.py add --text "implement auth gate" --file services/auth.py --type security
```

---

## Verification Tiers

| Tier | Name | Proves |
|------|------|--------|
| L1 | Declaration | Label/file exists |
| L2 | Wiring | Symbol/import present |
| L3 | Behavior | Non-stub implementation (default required) |
| L4 | Outcome | Measurable runtime result |
| L5 | Peak Standard | Beats named benchmark |

Default required: **L3**.

---

## Hook Wiring (Claude Code)

Add to `~/.claude/settings.json`:

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "type": "command",
        "command": "python3 /Users/YOU/.sagestack/supervisor/hooks/on_user_prompt_submit.py"
      }
    ],
    "Stop": [
      {
        "type": "command",
        "command": "python3 /Users/YOU/.sagestack/supervisor/hooks/on_stop.py"
      }
    ]
  }
}
```

Replace `YOU` with your username. The hooks are fail-open — they never block Claude.

---

## LLM Tier Fallback

`llm.py` tries in order:
1. **sagent** — `POST http://localhost:8042/api/sagent/ctx/chat`
2. **Anthropic** — key from `~/.sagent/secrets.json` or `$ANTHROPIC_API_KEY`, uses `claude-haiku-4-5`
3. **Ollama** — `POST http://localhost:11434/api/generate` with `llama3`
4. **None** — all grades proceed without LLM (deterministic collectors only)

---

## DB Schema

SQLite at `~/.sagestack/supervisor.db`:

```sql
claims(id, file_path, claim_type, claim_text, tier, status, evidence_json, created_at, updated_at)
```

Status values: `open` | `closed` | `blocked`

---

## Files

```
~/.sagestack/supervisor/
  supervisor.py          CLI entrypoint
  ledger.py              SQLite claim store
  collector.py           Evidence collectors (file_exists, grep_symbol, git_log_count, test_pass)
  grader.py              L1-L5 verdict engine
  llm.py                 3-tier LLM router
  hooks/
    on_user_prompt_submit.py   UserPromptSubmit hook
    on_stop.py                 Stop hook (sweeps session claims)
  README.md              This file
```
