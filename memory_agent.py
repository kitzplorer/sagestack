#!/usr/bin/env python3
"""Aistack Memory Agent — Cross-LLM session continuity.

Writes a concise session summary to CONTEXT.md so the next LLM
(Claude, Cursor, Windsurf, Zed, etc.) knows what happened without
reading a wall of chat history.

Zero dependencies — stdlib only. Works on any project with a .git/ root.

3-tier LLM fallback for smart summaries:
  1) Anthropic API  (ANTHROPIC_API_KEY env or ~/.sagent/secrets.json)
  2) Ollama         (localhost:11434, llama3 / mistral / llama2)
  3) git log        (pure template, always works)

Usage:
  python3 memory_agent.py                          # auto from git + LLM
  python3 memory_agent.py --llm "Cursor"           # label which LLM ran
  python3 memory_agent.py --summary "fixed X, Y"   # manual summary
  python3 memory_agent.py --init                   # create CONTEXT.md
  python3 memory_agent.py --project /path/to/repo  # explicit project root
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Root + path discovery
# ---------------------------------------------------------------------------

def _find_project_root(start: Path | None = None) -> Path:
    """Walk up from start (or cwd) until we find a .git directory."""
    cwd = (start or Path(os.getcwd())).resolve()
    for candidate in [cwd, *cwd.parents]:
        if (candidate / ".git").exists():
            return candidate
    return cwd  # fallback: cwd itself


def _find_context_file(project_root: Path) -> Path:
    """Return the best CONTEXT.md path for this project."""
    candidates = [
        project_root / "services" / "code_agent" / "CONTEXT.md",
        project_root / "CONTEXT.md",
        Path.home() / ".sagestack" / "CONTEXT.md",
    ]
    for c in candidates:
        if c.exists():
            return c
    return project_root / "CONTEXT.md"  # default (may not exist yet)


def _find_memory_md() -> Path | None:
    """Locate the Claude project memory file for this repo, if any."""
    # Claude stores per-project memory under ~/.claude/projects/<encoded-path>/memory/
    cwd_str = str(Path(os.getcwd()).resolve())
    encoded = cwd_str.replace("/", "-").lstrip("-")
    base = Path.home() / ".claude" / "projects" / encoded / "memory" / "MEMORY.md"
    if base.parent.exists():
        return base
    # Fallback: scan for any memory dir that matches the project name
    project_name = _find_project_root().name
    claude_projects = Path.home() / ".claude" / "projects"
    if claude_projects.exists():
        for d in claude_projects.iterdir():
            if project_name in d.name and (d / "memory" / "MEMORY.md").exists():
                return d / "memory" / "MEMORY.md"
    return None


# ---------------------------------------------------------------------------
# Git helpers
# ---------------------------------------------------------------------------

def _run(cmd: str, cwd: Path) -> str:
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, cwd=str(cwd))
        return r.stdout.strip()
    except Exception:
        return ""


def get_recent_changes(project_root: Path) -> dict:
    branch = _run("git branch --show-current", project_root)
    commits = _run("git log --oneline -8 --no-merges", project_root)
    stat = _run("git diff --stat HEAD~3 HEAD 2>/dev/null", project_root) or \
           _run("git diff --stat HEAD 2>/dev/null", project_root)
    changed = _run("git diff --name-only HEAD~3 HEAD 2>/dev/null", project_root) or \
              _run("git diff --name-only HEAD 2>/dev/null", project_root)
    return {"branch": branch, "commits": commits, "stat": stat, "changed_files": changed}


# ---------------------------------------------------------------------------
# LLM fallback chain
# ---------------------------------------------------------------------------

def _build_summary_prompt(changes: dict, existing_context: str, llm_label: str) -> str:
    ctx_snippet = (existing_context or "")[:400]
    return (
        f"You are a project memory agent. The developer just finished a session using {llm_label}.\n"
        "Write a concise session summary in 4-6 bullet points.\n"
        "Rules:\n"
        "- Each bullet starts with an action verb (Fixed, Added, Changed, Deleted, Refactored)\n"
        "- Be specific and technical (mention file names, function names)\n"
        "- Total under 150 words\n"
        "- Plain text, no markdown headers\n\n"
        f"Recent git activity:\n{changes.get('commits', 'none')}\n\n"
        f"Files changed:\n{changes.get('changed_files', 'none')}\n\n"
        f"Existing context (last 400 chars):\n{ctx_snippet}\n\n"
        "Write ONLY the bullet points, nothing else."
    )


def _try_anthropic(prompt: str) -> str | None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        try:
            secrets = json.loads((Path.home() / ".sagent" / "secrets.json").read_text())
            api_key = secrets.get("ANTHROPIC_API_KEY", "")
        except Exception:
            pass
    if not api_key:
        return None

    payload = json.dumps({
        "model": "claude-haiku-4-5",
        "max_tokens": 400,
        "messages": [{"role": "user", "content": prompt}],
    }).encode()
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return data["content"][0]["text"].strip()
    except Exception:
        return None


def _try_ollama(prompt: str) -> str | None:
    for model in ("llama3", "mistral", "llama2"):
        payload = json.dumps({
            "model": model,
            "prompt": prompt,
            "stream": False,
        }).encode()
        req = urllib.request.Request(
            "http://localhost:11434/api/generate",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode())
            text = data.get("response", "").strip()
            if text:
                return text
        except Exception:
            continue
    return None


def _template_summary(changes: dict) -> str:
    commits = changes.get("commits", "no commits")
    files = changes.get("changed_files", "unknown files")
    lines = ["- Session completed (no LLM summary available)"]
    for line in commits.splitlines()[:4]:
        if line.strip():
            lines.append(f"- {line.strip()}")
    if files:
        top = files.splitlines()[:3]
        lines.append(f"- Modified: {', '.join(top)}")
    return "\n".join(lines)


def get_summary(changes: dict, existing_context: str, llm_label: str) -> str:
    prompt = _build_summary_prompt(changes, existing_context, llm_label)
    result = _try_anthropic(prompt)
    if result:
        print("✓ Summary via Anthropic API")
        return result
    result = _try_ollama(prompt)
    if result:
        print("✓ Summary via Ollama")
        return result
    print("Using git log template (no LLM available)")
    return _template_summary(changes)


# ---------------------------------------------------------------------------
# Read / write context
# ---------------------------------------------------------------------------

def read_context(path: Path) -> str:
    try:
        return path.read_text(errors="replace")
    except Exception:
        return ""


def write_session_entry(context_path: Path, summary: str, llm_label: str) -> None:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n\n## Last Session ({now}, {llm_label})\n{summary}"

    content = read_context(context_path)
    if "## Last Session" in content:
        lines = content.splitlines(keepends=True)
        out, in_block = [], False
        for line in lines:
            if line.startswith("## Last Session"):
                in_block = True
                continue
            if in_block and line.startswith("## "):
                in_block = False
            if not in_block:
                out.append(line)
        content = "".join(out).rstrip()

    context_path.write_text(content + entry, encoding="utf-8")
    print(f"✓ CONTEXT.md updated ({context_path})")


def update_memory_md(memory_path: Path | None, summary: str, llm_label: str) -> None:
    if not memory_path:
        return
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    entry = f"\n## Last Session ({now}, {llm_label})\n{summary}\n"

    content = read_context(memory_path) if memory_path.exists() else ""
    if "## Last Session" in content:
        lines = content.splitlines(keepends=True)
        out, in_block = [], False
        for line in lines:
            if line.startswith("## Last Session"):
                in_block = True
                continue
            if in_block and line.startswith("## "):
                in_block = False
            if not in_block:
                out.append(line)
        content = "".join(out).rstrip()

    memory_path.write_text(content + entry, encoding="utf-8")
    print(f"✓ MEMORY.md updated ({memory_path})")


# ---------------------------------------------------------------------------
# Init
# ---------------------------------------------------------------------------

INITIAL_CONTEXT = """\
# Project — Cross-LLM Session Context

> **READ THIS before planning or writing any code.**
> Auto-updated at the end of each session by `memory_agent.py`.

---

## What this project is

(Fill in after first session.)

## How to run

(Fill in after first session.)

## Key constraints

(Fill in after first session.)

---

## Session Log

"""


def init_context(context_path: Path, overwrite: bool = False) -> None:
    if context_path.exists() and not overwrite:
        print(f"CONTEXT.md already exists at {context_path} (use --force to overwrite)")
        return
    context_path.parent.mkdir(parents=True, exist_ok=True)
    context_path.write_text(INITIAL_CONTEXT, encoding="utf-8")
    print(f"✓ Initialized {context_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description="Aistack Memory Agent")
    ap.add_argument("--llm", default="Claude", help="LLM label (e.g. Cursor, Windsurf)")
    ap.add_argument("--summary", default="", help="Manual summary text")
    ap.add_argument("--init", action="store_true", help="Create CONTEXT.md if missing")
    ap.add_argument("--force", action="store_true", help="Overwrite CONTEXT.md (with --init)")
    ap.add_argument("--project", default="", help="Explicit project root path")
    args = ap.parse_args()

    project_root = Path(args.project).resolve() if args.project else _find_project_root()
    context_path = _find_context_file(project_root)

    if args.init:
        init_context(context_path, overwrite=args.force)
        return

    if not context_path.exists():
        print("CONTEXT.md missing — initialising...")
        init_context(context_path)

    if args.summary:
        summary = args.summary
        print("Using manual summary.")
    else:
        changes = get_recent_changes(project_root)
        print(f"Generating summary for {project_root.name}...")
        summary = get_summary(changes, read_context(context_path), args.llm)

    write_session_entry(context_path, summary, args.llm)
    update_memory_md(_find_memory_md(), summary, args.llm)
    print(f"\nSession memory:\n{summary}\n")


if __name__ == "__main__":
    main()
