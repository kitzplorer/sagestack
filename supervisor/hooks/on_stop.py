#!/usr/bin/env python3
"""
hooks/on_stop.py
Claude Code Stop hook — sweeps pending claims from this session and grades them.

Wire in ~/.claude/settings.json:
  "hooks": {
    "Stop": [
      {"type": "command", "command": "python3 ~/.aistack/supervisor/hooks/on_stop.py"}
    ]
  }

Input: JSON on stdin (Claude Code hook envelope, may be empty)
Output: nothing — exit 0 always (fail-open)
"""
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path.home() / ".aistack" / "supervisor.db"
SUPERVISOR_DIR = Path(__file__).resolve().parents[1]

# Inline minimal versions so this hook is self-contained ─────────────────────

def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    return con


def _get_open_claims() -> list[dict]:
    if not DB_PATH.exists():
        return []
    try:
        con = _connect()
        rows = con.execute(
            "SELECT * FROM claims WHERE status = 'open' ORDER BY created_at DESC LIMIT 50"
        ).fetchall()
        con.close()
        return [dict(r) for r in rows]
    except sqlite3.Error:
        return []


def _grade_claim(claim_text: str) -> dict:
    """Minimal inline grader — L1 by default since we have no file context."""
    return {
        "tier": 1,
        "verdict": "partial",
        "passed": [],
        "gaps": ["No file context — promote to L3 via `supervisor sweep`"],
    }


def _update_verdict(claim_id: int, tier: int, verdict: str, gaps: list) -> None:
    try:
        con = _connect()
        con.execute(
            """
            UPDATE claims SET tier=?, status=?, evidence_json=?, updated_at=?
            WHERE id=?
            """,
            (
                tier,
                "open",  # keep open — sweep will fully grade
                json.dumps({"verdict": verdict, "gaps": gaps}),
                _now(),
                claim_id,
            ),
        )
        con.commit()
        con.close()
    except sqlite3.Error:
        pass


def _try_llm_grade(claim_text: str) -> str | None:
    """Quick Ollama probe — no-op if unavailable."""
    payload = json.dumps({
        "model": "llama3",
        "prompt": f"One-line verdict on this implementation claim (L1-L5 depth): {claim_text[:300]}",
        "stream": False,
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = json.loads(resp.read())
            return data.get("response", "")
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def main() -> None:
    # Read stdin (may be empty or JSON)
    try:
        raw = sys.stdin.read()
    except OSError:
        raw = ""

    claims = _get_open_claims()
    if not claims:
        return

    # Grade recent open claims (cap at 10 to keep hook fast)
    swept = 0
    for c in claims[:10]:
        llm_note = _try_llm_grade(c["claim_text"])
        gaps = ["Run `supervisor sweep` for full L3+ verification"]
        if llm_note:
            gaps.insert(0, f"LLM note: {llm_note[:200]}")
        _update_verdict(c["id"], tier=1, verdict="partial", gaps=gaps)
        swept += 1

    # Log summary to stderr (visible in hook debug output)
    if swept:
        print(f"[supervisor/on_stop] swept {swept} claims → run `python3 ~/.aistack/supervisor/supervisor.py sweep` for full grades", file=sys.stderr)


if __name__ == "__main__":
    main()
