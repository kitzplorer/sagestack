#!/usr/bin/env python3
"""Supervisor lifecycle hooks for Claude Code harness (enhanced).

Hooks:
  on_user_prompt_submit  — extract claim targets + plan promises (UserPromptSubmit)
  on_post_tool_use       — verify a claim + ghost-declaration check (PostToolUse)
  on_stop                — run a sweep and write a brief report (Stop)
  on_cron_hourly         — escalate BLOCKED claims (cron, called externally)

Each function is importable standalone. CLI form:

  python3 supervisor_hooks.py <hook_name> [json_payload]

Stdout must be JSON; non-zero exit suppresses the hook result silently.

Stdlib-only (json, pathlib, urllib.request, sqlite3, subprocess, os, sys, re).
"""
from __future__ import annotations

import json
import logging
import os
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

_BACKEND = os.environ.get("SAGENT_BACKEND", "http://localhost:8042")

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def _post(path: str, payload: dict, timeout: float = 1.5) -> dict:
    try:
        data = json.dumps(payload).encode()
        req = urllib.request.Request(
            f"{_BACKEND}{path}",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


def _get(path: str, timeout: float = 1.0) -> dict | list:
    try:
        with urllib.request.urlopen(f"{_BACKEND}{path}", timeout=timeout) as resp:
            return json.loads(resp.read())
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Plan / promise detection (ported from HRMS on_plan_submit, genericized)
# ---------------------------------------------------------------------------

_PLAN_SIGNALS = re.compile(
    r"(plan:|wave\s+\d|implement\s|requisition|batch\s+\d|deliverable)",
    re.IGNORECASE,
)
_NUMBERED_ITEM = re.compile(r"^\s*\d+[\.\)]\s+\S")
_BULLET_ITEM = re.compile(r"^\s*[-*•]\s+\S")


def _looks_like_plan(text: str) -> bool:
    if _PLAN_SIGNALS.search(text):
        return True
    lines = text.splitlines()
    numbered = sum(1 for line in lines if _NUMBERED_ITEM.match(line))
    bulleted = sum(1 for line in lines if _BULLET_ITEM.match(line))
    return (numbered + bulleted) >= 3


def _extract_promises(text: str) -> list[str]:
    """Pull out numbered / bulleted items as promise strings."""
    promises: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if _NUMBERED_ITEM.match(s) or _BULLET_ITEM.match(s):
            cleaned = re.sub(r"^(\d+[\.\)]|[-*•])\s+", "", s).strip()
            if cleaned:
                promises.append(cleaned)
    return promises


# ---------------------------------------------------------------------------
# Hook 1: on_user_prompt_submit
# ---------------------------------------------------------------------------

def on_user_prompt_submit(prompt: str) -> dict:
    """Extract claim targets + plan promises (UserPromptSubmit hook)."""
    targets: list[str] = []
    patterns = [
        r"verify\s+[`'\"]?([^\s`'\"]+)[`'\"]?",
        r"check\s+[`'\"]?([^\s`'\"]+\.py)[`'\"]?",
        r"services/code_agent/[^\s`'\"]+",
        r"modules/[^\s`'\"]+",
        r"app/[^\s`'\"]+\.py",
    ]
    for pat in patterns:
        for m in re.findall(pat, prompt, re.IGNORECASE):
            candidate = m.strip().strip("`'\"")
            if candidate and candidate not in targets:
                targets.append(candidate)

    # Plan-style prompts: enumerate promises and seed via backend (best-effort)
    promises: list[str] = []
    seeded = 0
    if _looks_like_plan(prompt):
        promises = _extract_promises(prompt)
        if promises:
            try:
                resp = _post(
                    "/api/sagent/supervisor/seed_promises",
                    {"promises": promises, "source": "<user_prompt>"},
                    timeout=1.5,
                )
                if isinstance(resp, dict):
                    seeded = int(resp.get("seeded", 0) or 0)
            except Exception:
                pass

    return {
        "hook": "on_user_prompt_submit",
        "claims": targets,
        "count": len(targets),
        "promises": promises,
        "promises_seeded": seeded,
    }


# ---------------------------------------------------------------------------
# Hook 2: on_post_tool_use (with ghost-declaration check, ported & genericized)
# ---------------------------------------------------------------------------

# (declaration_marker, [acceptable implementation markers])
_GHOST_RULES: list[tuple[str, list[str]]] = [
    ("aicp: true", ["useWidgetAI", "enableAI", "aiHandler", "onAIClick"]),
    ("wctp: true", ["onClick", "href=", "clickThroughUrl", "router.push", "onRowClick"]),
    ("cctp: true", ["onClick", "onBarClick", "onSliceClick", "onPointClick"]),
    ("wcp: true",  ["onClick", "href=", "router.push"]),
]


def _check_ghost_declarations(files: list[str]) -> int:
    """Count tsx/jsx files declaring a contract without an implementation marker."""
    ghost = 0
    for f in files:
        if not f or not (f.endswith(".tsx") or f.endswith(".jsx")):
            continue
        try:
            content = Path(f).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for declaration, required_impls in _GHOST_RULES:
            if declaration in content and not any(impl in content for impl in required_impls):
                ghost += 1
    return ghost


def _resolve_files(output: Any) -> list[str]:
    files: list[str] = []
    if isinstance(output, dict):
        files = list(output.get("files_changed") or [])
        if not files:
            fp = (
                (output.get("tool_input") or {}).get("file_path")
                or output.get("file_path")
                or output.get("path")
            )
            if fp:
                files = [fp]
    elif isinstance(output, str):
        for m in re.findall(r"((?:services/code_agent|app|modules|src)/[^\s'\"]+\.(?:py|tsx?|jsx?))", output):
            files.append(m)
    return [f for f in files if f]


def on_post_tool_use(tool_name: str, output: Any) -> dict:
    """After Write/Edit/Bash: L1 verify + ghost-declaration audit (PostToolUse)."""
    if tool_name not in ("Write", "Edit", "Bash"):
        return {"hook": "on_post_tool_use", "skipped": True, "tool": tool_name}

    files = _resolve_files(output)
    target = files[0] if files else ""

    if not target:
        return {"hook": "on_post_tool_use", "skipped": True, "reason": "no_target"}

    verify = _post("/api/sagent/supervisor/verify", {"target": target, "depth": "L1"})
    ghost = _check_ghost_declarations(files)

    return {
        "hook": "on_post_tool_use",
        "tool": tool_name,
        "target": target,
        "files_checked": files,
        "verify": verify,
        "ghost_declarations": ghost,
        "quality_ok": ghost == 0,
    }


# ---------------------------------------------------------------------------
# Hook 3: on_stop
# ---------------------------------------------------------------------------

def on_stop() -> dict:
    """On session stop, run a sweep + return status snapshot (Stop hook)."""
    report = _post("/api/sagent/supervisor/sweep", {})
    status = _get("/api/sagent/supervisor/status")
    return {"hook": "on_stop", "sweep": report, "status": status}


# ---------------------------------------------------------------------------
# Hook 4: on_cron_hourly
# ---------------------------------------------------------------------------

def on_cron_hourly() -> dict:
    """Escalate BLOCKED claims — hourly cron target."""
    blocked = _get("/api/sagent/supervisor/blocked")
    count = len(blocked) if isinstance(blocked, list) else 0
    if count:
        logger.warning("supervisor cron: %d BLOCKED claims", count)
    return {
        "hook": "on_cron_hourly",
        "blocked_count": count,
        "blocked": blocked if isinstance(blocked, list) else [],
    }


# ---------------------------------------------------------------------------
# CLI dispatch
# ---------------------------------------------------------------------------

_HOOKS = {
    "on_user_prompt_submit": on_user_prompt_submit,
    "on_post_tool_use": on_post_tool_use,
    "on_stop": on_stop,
    "on_cron_hourly": on_cron_hourly,
}


def main() -> None:
    args = sys.argv[1:]
    if not args:
        print(json.dumps({"error": "usage: supervisor_hooks.py <hook_name> [json_payload]"}))
        sys.exit(1)

    hook_name = args[0]
    fn = _HOOKS.get(hook_name)
    if fn is None:
        print(json.dumps({"error": f"unknown hook: {hook_name}", "available": list(_HOOKS)}))
        sys.exit(1)

    payload: dict = {}
    if len(args) > 1:
        try:
            payload = json.loads(args[1])
        except json.JSONDecodeError:
            pass
    else:
        # Allow JSON via stdin if no positional payload
        try:
            if not sys.stdin.isatty():
                raw = sys.stdin.read()
                if raw.strip():
                    payload = json.loads(raw)
        except Exception:
            pass

    try:
        if hook_name == "on_user_prompt_submit":
            result = fn(payload.get("prompt") or payload.get("user_prompt") or "")
        elif hook_name == "on_post_tool_use":
            result = fn(payload.get("tool_name", ""), payload.get("output", payload))
        else:
            result = fn()
    except Exception as exc:
        result = {"hook": hook_name, "error": str(exc)}

    print(json.dumps(result))


if __name__ == "__main__":
    main()
