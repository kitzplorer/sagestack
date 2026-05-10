"""
llm.py — 3-tier LLM router
Priority: sagent backend (localhost:8042) → Anthropic API → Ollama → None
Zero pip dependencies: urllib.request, json, pathlib, os
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

SAGENT_URL = "http://localhost:8042/api/sagent/ctx/chat"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "llama3"
ANTHROPIC_MODEL = "claude-haiku-4-5"
TIMEOUT = 20  # seconds


def _secrets_key() -> str | None:
    """Read Anthropic key from ~/.sagent/secrets.json or env."""
    env_key = os.environ.get("ANTHROPIC_API_KEY")
    if env_key:
        return env_key
    secrets_path = Path.home() / ".sagent" / "secrets.json"
    if secrets_path.exists():
        try:
            data = json.loads(secrets_path.read_text())
            return data.get("ANTHROPIC_API_KEY") or data.get("anthropic_api_key")
        except (json.JSONDecodeError, OSError):
            pass
    return None


def _post(url: str, payload: dict, headers: dict | None = None) -> dict | None:
    body = json.dumps(payload).encode()
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=body, headers=req_headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read())
    except (urllib.error.URLError, json.JSONDecodeError, OSError):
        return None


def _try_sagent(prompt: str, task: str) -> str | None:
    payload = {
        "task": task,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = _post(SAGENT_URL, payload)
    if resp and isinstance(resp, dict):
        # sagent ctx/chat returns {"content": "..."} or {"message": "..."}
        return resp.get("content") or resp.get("message") or resp.get("text")
    return None


def _try_anthropic(prompt: str) -> str | None:
    key = _secrets_key()
    if not key:
        return None
    payload = {
        "model": ANTHROPIC_MODEL,
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
    }
    resp = _post(ANTHROPIC_URL, payload, headers)
    if resp and isinstance(resp, dict):
        content = resp.get("content", [])
        if content and isinstance(content, list):
            return content[0].get("text")
    return None


def _try_ollama(prompt: str) -> str | None:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
    }
    resp = _post(OLLAMA_URL, payload)
    if resp and isinstance(resp, dict):
        return resp.get("response")
    return None


def chat(prompt: str, task: str = "eval_judge") -> str | None:
    """
    Send prompt through the 3-tier fallback chain.
    Returns the text response or None if all tiers fail.
    """
    result = _try_sagent(prompt, task)
    if result:
        return result

    result = _try_anthropic(prompt)
    if result:
        return result

    result = _try_ollama(prompt)
    if result:
        return result

    return None


def available_tier() -> str:
    """Return which LLM tier is reachable (for status display)."""
    # Quick probe: try sagent
    try:
        payload = {"task": "lookup", "messages": [{"role": "user", "content": "ping"}]}
        body = json.dumps(payload).encode()
        req = urllib.request.Request(
            SAGENT_URL, data=body,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        urllib.request.urlopen(req, timeout=3)
        return "sagent"
    except Exception:
        pass

    # Try Anthropic key presence
    if _secrets_key():
        return "anthropic"

    # Try Ollama
    try:
        req = urllib.request.Request(
            "http://localhost:11434/api/tags", method="GET"
        )
        urllib.request.urlopen(req, timeout=3)
        return "ollama"
    except Exception:
        pass

    return "none"
