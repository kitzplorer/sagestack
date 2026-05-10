"""
collector.py — deterministic evidence collectors
Zero pip dependencies: subprocess, pathlib, re, json
"""
import json
import re
import subprocess
from pathlib import Path


def file_exists(path: str) -> dict:
    """L1 — path resolves on disk."""
    p = Path(path).expanduser()
    ok = p.exists()
    return {
        "collector": "file_exists",
        "path": str(p),
        "pass": ok,
        "detail": "exists" if ok else "not found",
    }


def grep_symbol(path: str, pattern: str, flags: int = re.IGNORECASE) -> dict:
    """L2 — pattern found in file content."""
    p = Path(path).expanduser()
    if not p.exists():
        return {"collector": "grep_symbol", "path": str(p), "pass": False, "detail": "file not found"}
    try:
        text = p.read_text(errors="replace")
    except OSError as exc:
        return {"collector": "grep_symbol", "path": str(p), "pass": False, "detail": str(exc)}
    matches = re.findall(pattern, text, flags)
    ok = len(matches) > 0
    return {
        "collector": "grep_symbol",
        "path": str(p),
        "pattern": pattern,
        "pass": ok,
        "match_count": len(matches),
        "detail": f"{len(matches)} match(es)" if ok else "pattern not found",
    }


def grep_dir(directory: str, pattern: str, glob: str = "**/*.py") -> dict:
    """L2 — pattern found anywhere under directory."""
    d = Path(directory).expanduser()
    if not d.is_dir():
        return {"collector": "grep_dir", "directory": str(d), "pass": False, "detail": "not a directory"}
    matched_files = []
    for f in d.glob(glob):
        try:
            if re.search(pattern, f.read_text(errors="replace"), re.IGNORECASE):
                matched_files.append(str(f))
        except OSError:
            pass
    ok = len(matched_files) > 0
    return {
        "collector": "grep_dir",
        "directory": str(d),
        "pattern": pattern,
        "pass": ok,
        "matched_files": matched_files[:10],
        "detail": f"{len(matched_files)} file(s)" if ok else "not found",
    }


def git_log_count(path: str, since: str = "30.days.ago") -> dict:
    """L3 — git commit activity proves the file is live (not a stub)."""
    p = Path(path).expanduser()
    try:
        result = subprocess.run(
            ["git", "log", "--oneline", f"--since={since}", "--", str(p)],
            capture_output=True, text=True, timeout=10,
            cwd=str(p.parent if p.is_file() else p),
        )
        lines = [l for l in result.stdout.strip().splitlines() if l]
        ok = len(lines) > 0
        return {
            "collector": "git_log_count",
            "path": str(p),
            "since": since,
            "pass": ok,
            "commit_count": len(lines),
            "detail": f"{len(lines)} commits in {since}" if ok else "no recent commits",
        }
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {"collector": "git_log_count", "path": str(p), "pass": False, "detail": str(exc)}


def test_pass(command: list[str], cwd: str | None = None) -> dict:
    """L3/L4 — run a test command and check it exits 0."""
    try:
        result = subprocess.run(
            command, capture_output=True, text=True, timeout=60,
            cwd=cwd,
        )
        ok = result.returncode == 0
        return {
            "collector": "test_pass",
            "command": command,
            "pass": ok,
            "returncode": result.returncode,
            "stdout_tail": result.stdout[-500:] if result.stdout else "",
            "stderr_tail": result.stderr[-500:] if result.stderr else "",
            "detail": "exit 0" if ok else f"exit {result.returncode}",
        }
    except subprocess.TimeoutExpired:
        return {"collector": "test_pass", "command": command, "pass": False, "detail": "timeout"}
    except FileNotFoundError as exc:
        return {"collector": "test_pass", "command": command, "pass": False, "detail": str(exc)}


def function_not_stub(path: str, fn_name: str) -> dict:
    """L3 — function body is not a known no-op stub pattern."""
    STUB_PATTERNS = [
        r"pass\s*$",
        r"return\s+None\s*$",
        r"return\s+\{\s*\}\s*$",
        r"\.\.\.(\s*#.*)?$",
        r"raise\s+NotImplementedError",
    ]
    p = Path(path).expanduser()
    if not p.exists():
        return {"collector": "function_not_stub", "path": str(p), "pass": False, "detail": "file not found"}
    text = p.read_text(errors="replace")
    # Find the function block (rough heuristic)
    fn_match = re.search(rf"def\s+{re.escape(fn_name)}\s*\(", text)
    if not fn_match:
        return {"collector": "function_not_stub", "path": str(p), "fn": fn_name, "pass": False, "detail": "function not found"}
    body = text[fn_match.start():][:500]
    for pat in STUB_PATTERNS:
        if re.search(pat, body, re.MULTILINE):
            return {
                "collector": "function_not_stub",
                "path": str(p),
                "fn": fn_name,
                "pass": False,
                "detail": f"stub pattern matched: {pat}",
            }
    return {"collector": "function_not_stub", "path": str(p), "fn": fn_name, "pass": True, "detail": "non-stub body"}


def run_all_for_file(file_path: str) -> list[dict]:
    """Convenience: run L1 + L2 collectors for a single file."""
    results = [file_exists(file_path)]
    p = Path(file_path).expanduser()
    if p.exists() and p.suffix == ".py":
        results.append(grep_symbol(file_path, r"def\s+\w+"))
    return results
