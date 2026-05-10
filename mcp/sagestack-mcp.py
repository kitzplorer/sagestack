#!/usr/bin/env python3
"""Sagestack MCP bridge — exposes sagent tools to Claude Code and other IDE agents.

Reads SAGENT_BACKEND env var (default: http://localhost:8042).
Proxies tool calls to the backend with SQLite caching for offline resilience.

Install: configured automatically by sagestack-install.sh
"""
from __future__ import annotations

import json
import os
import sqlite3
import sys
import urllib.error
import urllib.request
from pathlib import Path

BACKEND = os.environ.get("SAGENT_BACKEND", "http://localhost:8042")
CACHE_DB = Path.home() / ".sagestack" / "signals.db"
TIMEOUT = 3.0


class _Cache:
    def __init__(self) -> None:
        self._db = sqlite3.connect(str(CACHE_DB), check_same_thread=False)
        self._db.execute(
            "CREATE TABLE IF NOT EXISTS cache (key TEXT PRIMARY KEY, value TEXT, ts INTEGER DEFAULT (strftime('%s','now')))"
        )
        self._db.commit()

    def get(self, key: str):
        row = self._db.execute("SELECT value FROM cache WHERE key=?", (key,)).fetchone()
        return json.loads(row[0]) if row else None

    def set(self, key: str, value) -> None:
        self._db.execute("INSERT OR REPLACE INTO cache(key,value) VALUES(?,?)", (key, json.dumps(value)))
        self._db.commit()


_cache = _Cache()


def _call(path: str, method: str = "GET", body=None):
    url = f"{BACKEND}/api/sagent/{path.lstrip('/')}"
    try:
        req = urllib.request.Request(url, method=method)
        if body:
            req.add_header("Content-Type", "application/json")
            req.data = json.dumps(body).encode()
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            result = json.loads(r.read().decode())
        _cache.set(path, result)
        return result
    except Exception:
        cached = _cache.get(path)
        if cached is not None:
            return cached
        return {"error": "backend unreachable", "cached": False}


def _tool(name: str, description: str, input_schema: dict):
    return {"name": name, "description": description, "inputSchema": input_schema}


MIGRATE_SCRIPT = Path(__file__).parent.parent / "scripts" / "migrate-to-sagent.sh"


def _migrate_to_sagent(args: dict) -> dict:
    """Run migrate-to-sagent.sh, optionally with a custom backend URL."""
    import subprocess
    backend = args.get("backend", "https://sagent.nishtechnologies.com")
    script = str(MIGRATE_SCRIPT)
    if not MIGRATE_SCRIPT.exists():
        return {"error": f"migrate script not found at {script}"}
    try:
        result = subprocess.run(
            ["bash", script, backend],
            capture_output=True, text=True, timeout=120
        )
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"error": "migration script timed out after 120s"}
    except Exception as exc:
        return {"error": str(exc)}


TOOLS = [
    _tool("ctx_status", "Get the current context and enrichment signals", {"type": "object", "properties": {}}),
    _tool("list_machines", "List all registered machines in the fabric", {"type": "object", "properties": {}}),
    _tool("list_bugs", "List open bugs", {"type": "object", "properties": {"limit": {"type": "integer"}, "severity": {"type": "string"}}}),
    _tool("list_plans", "List current plans", {"type": "object", "properties": {}}),
    _tool("list_actions", "List available MCP actions", {"type": "object", "properties": {}}),
    _tool("manual_steps", "List pending manual operator steps", {"type": "object", "properties": {}}),
    _tool("rag_query", "Semantic search over the codebase", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
    _tool("llm_cost", "Show LLM cost breakdown for last 7 days", {"type": "object", "properties": {}}),
    _tool("recall", "Recall from project memory", {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}),
    _tool(
        "migrate_to_sagent",
        "Upgrade from sagestack (free tier) to the full sagent platform. "
        "Renames the sagestack MCP entry to sagestack-fallback, installs the sagent MCP, "
        "and copies config to ~/.sagent/. Pass backend to override the default sagent URL.",
        {
            "type": "object",
            "properties": {
                "backend": {
                    "type": "string",
                    "description": "sagent backend URL (default: https://sagent.nishtechnologies.com)",
                }
            },
        },
    ),
]

TOOL_MAP = {
    "ctx_status": lambda _: _call("ctx/status"),
    "list_machines": lambda _: _call("machines/"),
    "list_bugs": lambda args: _call(f"bugs/?limit={args.get('limit', 20)}&severity={args.get('severity', '')}"),
    "list_plans": lambda _: _call("plans/"),
    "list_actions": lambda _: _call("actions/"),
    "manual_steps": lambda _: _call("manual-steps/"),
    "rag_query": lambda args: _call(f"rag/query?q={urllib.parse.quote(args['query'])}"),
    "llm_cost": lambda _: _call("ctx/cost"),
    "recall": lambda args: _call("memory/recall", "POST", {"query": args["query"]}),
    "migrate_to_sagent": _migrate_to_sagent,
}


def _handle(msg: dict) -> dict:
    method = msg.get("method", "")
    msg_id = msg.get("id")

    if method == "initialize":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "sagestack-mcp", "version": "1.0.0"},
        }}

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": msg_id, "result": {"tools": TOOLS}}

    if method == "tools/call":
        name = msg["params"]["name"]
        args = msg["params"].get("arguments", {})
        fn = TOOL_MAP.get(name)
        result = fn(args) if fn else {"error": f"unknown tool: {name}"}
        return {"jsonrpc": "2.0", "id": msg_id, "result": {
            "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
        }}

    return {"jsonrpc": "2.0", "id": msg_id, "error": {"code": -32601, "message": "Method not found"}}


def main() -> None:
    import urllib.parse
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = _handle(msg)
        sys.stdout.write(json.dumps(response) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
