"""
ledger.py — SQLite claim store for ~/.aistack/supervisor/
DB: ~/.aistack/supervisor.db
Pure stdlib only: sqlite3, pathlib, json, datetime
"""
import json
import sqlite3
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
CREATE INDEX IF NOT EXISTS idx_claims_status   ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_file     ON claims(file_path);
CREATE INDEX IF NOT EXISTS idx_claims_tier     ON claims(tier);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(str(DB_PATH))
    con.row_factory = sqlite3.Row
    con.executescript(DDL)
    con.commit()
    return con


def add_claim(
    claim_text: str,
    claim_type: str = "generic",
    file_path: str | None = None,
) -> int:
    """Insert a new open claim. Returns the new row id."""
    now = _now()
    with _connect() as con:
        cur = con.execute(
            """
            INSERT INTO claims (file_path, claim_type, claim_text, status, created_at, updated_at)
            VALUES (?, ?, ?, 'open', ?, ?)
            """,
            (file_path, claim_type, claim_text, now, now),
        )
        return cur.lastrowid


def get_open_claims() -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM claims WHERE status = 'open' ORDER BY created_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_blocked_claims() -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM claims WHERE status = 'blocked' ORDER BY updated_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def get_by_file(file_path: str) -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM claims WHERE file_path = ? ORDER BY created_at DESC",
            (file_path,),
        ).fetchall()
    return [dict(r) for r in rows]


def update_verdict(
    claim_id: int,
    tier: int,
    verdict: str,
    evidence: list,
    gaps: list,
) -> None:
    status = "closed" if verdict == "pass" else "blocked" if tier < 2 else "open"
    with _connect() as con:
        con.execute(
            """
            UPDATE claims
            SET tier = ?, status = ?, evidence_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                tier,
                status,
                json.dumps({"verdict": verdict, "evidence": evidence, "gaps": gaps}),
                _now(),
                claim_id,
            ),
        )


def tier_counts() -> dict:
    with _connect() as con:
        rows = con.execute(
            "SELECT tier, COUNT(*) AS n FROM claims GROUP BY tier"
        ).fetchall()
    return {r["tier"]: r["n"] for r in rows}


def all_claims(limit: int = 200) -> list[dict]:
    with _connect() as con:
        rows = con.execute(
            "SELECT * FROM claims ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]
