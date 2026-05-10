#!/usr/bin/env python3
"""
hooks/on_user_prompt_submit.py
Claude Code UserPromptSubmit hook — logs incoming prompt as a pending claim.

Wire in ~/.claude/settings.json:
  "hooks": {
    "UserPromptSubmit": [
      {"type": "command", "command": "python3 ~/.aistack/supervisor/hooks/on_user_prompt_submit.py"}
    ]
  }

Input: JSON on stdin (Claude Code hook envelope)
Output: nothing (stdout/stderr only; exit 0 always — fail-open)
"""
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".aistack" / "supervisor.db"
DDL = """
CREATE TABLE IF NOT EXISTS claims (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    file_path    TEXT,
    claim_type   TEXT NOT NULL,
    claim_text   TEXT NOT NULL,
    tier         INTEGER DEFAULT 0,
    status       TEXT NOT NULL DEFAULT 'open',
    evidence_json TEXT,
    created_at   TEXT NOT NULL,
    updated_at   TEXT NOT NULL
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.executescript(DDL)
    con.commit()
    return con


def _extract_prompt(data: dict) -> str | None:
    # Claude Code hook envelope: {"prompt": "...", ...}
    # Also check nested structures
    if "prompt" in data:
        return str(data["prompt"])
    if "message" in data:
        return str(data["message"])
    return None


def main() -> None:
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return
        data = json.loads(raw)
    except (json.JSONDecodeError, OSError):
        return  # fail-open

    prompt = _extract_prompt(data)
    if not prompt or len(prompt.strip()) < 10:
        return

    # Only log prompts that look like implementation promises / claims
    keywords = ("implement", "add", "fix", "create", "build", "ensure", "make sure",
                 "deploy", "migrate", "update", "refactor", "write", "enable")
    lowered = prompt.lower()
    if not any(kw in lowered for kw in keywords):
        return

    claim_text = prompt[:500].replace("\n", " ").strip()

    try:
        con = _ensure_db()
        now = _now()
        con.execute(
            """
            INSERT INTO claims (claim_type, claim_text, status, created_at, updated_at)
            VALUES ('prompt', ?, 'open', ?, ?)
            """,
            (claim_text, now, now),
        )
        con.commit()
        con.close()
    except (sqlite3.Error, OSError):
        pass  # fail-open always


if __name__ == "__main__":
    main()
