#!/usr/bin/env python3
"""Bar Raiser — CEO/CTO adversarial plan reviewer (enhanced).

UserPromptSubmit hook. For plan-class prompts, runs an eval_judge gauntlet:
- existence/rebuild check (does the plan rebuild already-shipped work?)
- business value score (block if <7/10)
- simpler-path test (is there a 20-line helper or config change?)
- prompt execution coverage (every distinct requirement must be addressable;
  cardinality rule: every/all/each + countable noun → coverage must be ≥0.90)

3-tier LLM fallback:
  1) sagent backend  (http://localhost:8042/api/sagent/ctx/chat)
  2) Anthropic API   (key from ~/.sagent/secrets.json or $ANTHROPIC_API_KEY)
  3) Ollama          (http://localhost:11434/api/chat)
  → fail-open if all three are unreachable.

Per-project context auto-discovery (first hit wins):
  ~/.sagent/supervisor_enforcement.json override (per-project)
  $CWD/services/code_agent/CONTEXT.md
  $CWD/CONTEXT.md
  $CWD/CLAUDE.md
  ~/.sagestack/CONTEXT.md
  (then legacy default ~/projects/sagent/services/code_agent/CONTEXT.md)

Exit codes:
  0 → allow (approve, warn, or every backend unreachable)
  2 → block (verdict=block OR business_value_score < 7 OR coverage < 0.90)
"""

from __future__ import annotations

import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.request

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLAN_KEYWORDS = {
    "build", "create", "implement", "add", "make",
    "set up", "install", "write", "develop",
}
PLAN_TASK_CLASSES = {"plan", "debug_hard"}

SUPERVISOR_CFG = pathlib.Path.home() / ".sagent" / "supervisor_enforcement.json"
SECRETS_PATH = pathlib.Path.home() / ".sagent" / "secrets.json"

CONTEXT_PATH_DEFAULT = (
    pathlib.Path.home() / "projects" / "sagent" / "services" / "code_agent" / "CONTEXT.md"
)

API_URL = "http://localhost:8042/api/sagent/ctx/chat"
ANTHROPIC_URL = "https://api.anthropic.com/v1/messages"
OLLAMA_URL = "http://localhost:11434/api/chat"

TIMEOUT_S = 4
ANTHROPIC_TIMEOUT_S = 8
OLLAMA_TIMEOUT_S = 8
CONTEXT_LINES = 80

MIN_BUSINESS_SCORE = 7
MIN_PROMPT_COVERAGE = 0.90

# Cardinality detection: "every/all/each/entire/full" + countable noun
_CARDINALITY_RE = re.compile(
    r"\b(every|all|each|entire|full)\s+([a-zA-Z][a-zA-Z\-_/]+s?)\b",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Project / context discovery
# ---------------------------------------------------------------------------

def _detect_project() -> str | None:
    """Return project name from cwd, matching keys in supervisor_enforcement.json."""
    cwd = pathlib.Path(os.getcwd()).resolve()
    home = pathlib.Path.home()
    for parent in [cwd, *cwd.parents]:
        if parent.parent == home / "projects":
            return parent.name
    try:
        rel = cwd.relative_to(home / "projects")
        return rel.parts[0] if rel.parts else None
    except ValueError:
        return None


def _get_context_path() -> pathlib.Path:
    """Auto-discover the most relevant CONTEXT/CLAUDE file."""
    cwd = pathlib.Path(os.getcwd()).resolve()
    project = _detect_project()

    # 1) explicit per-project override in supervisor_enforcement.json
    if SUPERVISOR_CFG.exists():
        try:
            cfg = json.loads(SUPERVISOR_CFG.read_text())
            if project and "projects" in cfg:
                p = cfg["projects"].get(project, {}).get("context_md_path")
                if p:
                    resolved = pathlib.Path(p).expanduser()
                    if resolved.exists():
                        return resolved
            p = cfg.get("context_md_path")
            if p:
                resolved = pathlib.Path(p).expanduser()
                if resolved.exists():
                    return resolved
        except Exception:
            pass

    # 2) auto-discovery cascade
    candidates = [
        cwd / "services" / "code_agent" / "CONTEXT.md",
        cwd / "CONTEXT.md",
        cwd / "CLAUDE.md",
        pathlib.Path.home() / ".sagestack" / "CONTEXT.md",
    ]
    for c in candidates:
        if c.exists():
            return c

    # 3) last-resort default
    return CONTEXT_PATH_DEFAULT


def _read_context_excerpt() -> str:
    path = _get_context_path()
    try:
        lines = path.read_text(errors="replace").splitlines()
        return "\n".join(lines[:CONTEXT_LINES])
    except Exception:
        return "(CONTEXT.md unavailable)"


def _is_plan_prompt(prompt: str) -> bool:
    lower = prompt.lower()
    if any(cls in lower for cls in PLAN_TASK_CLASSES):
        return True
    return any(kw in lower for kw in PLAN_KEYWORDS)


# ---------------------------------------------------------------------------
# Requirement enumeration & cardinality (stdlib-only inline impl)
# ---------------------------------------------------------------------------

def _enumerate_requirements(prompt: str) -> list[str]:
    """Pull out distinct requirements from the user's plan.

    Heuristics:
      - numbered list items (`1.`, `2)`)
      - bulleted items (`-`, `*`, `•`)
      - sentences containing imperative verbs (build/add/fix/...)
    """
    reqs: list[str] = []
    seen: set[str] = set()

    for line in prompt.splitlines():
        s = line.strip()
        if not s:
            continue
        if re.match(r"^(\d+[\.\)]|[-*•])\s+", s):
            cleaned = re.sub(r"^(\d+[\.\)]|[-*•])\s+", "", s).strip()
            if cleaned and cleaned.lower() not in seen:
                reqs.append(cleaned)
                seen.add(cleaned.lower())

    if not reqs:
        # fall back to imperative sentence split
        for sent in re.split(r"(?<=[.!?])\s+", prompt):
            s = sent.strip()
            if not s:
                continue
            if re.search(
                r"\b(build|create|implement|add|fix|make|update|refactor|"
                r"port|enable|wire|verify|ensure|migrate|delete|remove)\b",
                s,
                re.IGNORECASE,
            ):
                if s.lower() not in seen:
                    reqs.append(s)
                    seen.add(s.lower())

    return reqs


def _detect_cardinality_targets(prompt: str) -> list[tuple[str, str]]:
    """Return list of (quantifier, noun) for every/all/each + countable-noun phrases."""
    out = []
    for m in _CARDINALITY_RE.finditer(prompt):
        out.append((m.group(1).lower(), m.group(2).lower()))
    return out


# ---------------------------------------------------------------------------
# Gauntlet prompt
# ---------------------------------------------------------------------------

def _build_bar_raiser_prompt(
    user_prompt: str,
    context_excerpt: str,
    project: str | None,
    requirements: list[str],
    cardinality: list[tuple[str, str]],
) -> str:
    proj_label = f" ({project})" if project else ""
    req_block = "\n".join(f"  - {r}" for r in requirements) or "  (none enumerated)"
    card_block = (
        "\n".join(f"  - {q} {n}" for q, n in cardinality) or "  (no cardinality phrases)"
    )

    return (
        f"You are the strictest Bar Raiser / CEO reviewer for a software project{proj_label}. "
        "Your default is to challenge and raise the bar — not to approve.\n\n"
        "## Existing codebase context (CONTEXT excerpt):\n"
        f"{context_excerpt}\n\n"
        "## User's proposed plan (verbatim):\n"
        f"{user_prompt}\n\n"
        "## Enumerated requirements (from plan):\n"
        f"{req_block}\n\n"
        "## Cardinality phrases detected (every/all/each + noun):\n"
        f"{card_block}\n\n"
        "## Mandatory gauntlet — answer each in JSON below:\n"
        "1. **Existence check** — does the plan rebuild already-shipped work in the context?\n"
        "2. **Move-the-needle** — does this measurably move performance, reliability, "
        "user experience, or cost? Score business_value 0-10.\n"
        "3. **Simpler-path** — is there a 20-line helper, a config flag, or an existing "
        "library that achieves 80% of the value at 20% the effort?\n"
        "4. **Standard-raising** — rewrite vague acceptance criteria to be measurable "
        "(e.g. 'loads quickly' → 'TTI < 2s p95').\n"
        "5. **Assumption challenges** — list 3 assumptions the plan makes; flag risks.\n"
        "6. **Prompt execution coverage** — for each enumerated requirement, mark "
        "EXECUTABLE (the plan covers it) or MISSING (the plan ignores it). "
        "If ANY requirement is MISSING → coverage < 1.0.\n"
        "7. **Cardinality rule** — for any 'every / all / each + countable noun', the "
        "plan must address the FULL population, not a sample. If unclear → PARTIAL. "
        "If changed/total < 0.90 → coverage drops below threshold.\n"
        "8. **Kill / Pivot / Keep** — final call.\n\n"
        "Reply with ONLY valid JSON (no markdown fences, no prose outside the JSON):\n"
        "{\n"
        '  "verdict": "approve" | "warn" | "block",\n'
        '  "reason": "<one sentence>",\n'
        '  "existing_items": ["<thing already shipped>", ...],\n'
        '  "business_value_score": 0-10,\n'
        '  "simpler_alternative": "<sentence or null>",\n'
        '  "raised_acceptance_criteria": ["<measurable criterion>", ...],\n'
        '  "assumption_challenges": ["<assumption — risk>", ...],\n'
        '  "prompt_coverage": 0.0-1.0,\n'
        '  "missing_requirements": ["<requirement text>", ...],\n'
        '  "cardinality_concerns": ["<phrase> — risk", ...],\n'
        '  "kill_or_keep": "kill" | "pivot" | "keep"\n'
        "}\n\n"
        "Rules of thumb:\n"
        "- approve: clearly net-new, measurable, addresses 100% of requirements.\n"
        "- warn: partial overlap with existing work, OR cardinality unclear, OR coverage 0.90-0.99.\n"
        "- block: rebuilds shipped work, OR business_value < 7, OR coverage < 0.90, "
        "OR a 'every/all' phrase is plainly under-scoped."
    )


# ---------------------------------------------------------------------------
# 3-tier LLM fallback
# ---------------------------------------------------------------------------

def _http_post_json(url: str, payload: dict, headers: dict, timeout: float) -> str | None:
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read().decode(errors="replace")
    except Exception:
        return None


def _try_sagent(bar_raiser_prompt: str) -> str | None:
    body = _http_post_json(
        API_URL,
        {
            "task": "eval_judge",
            "messages": [{"role": "user", "content": bar_raiser_prompt}],
        },
        {"Content-Type": "application/json"},
        TIMEOUT_S,
    )
    if not body:
        return None
    try:
        data = json.loads(body)
        content = data.get("content") or data.get("response") or body
        if isinstance(content, list):
            content = " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        return str(content)
    except Exception:
        return body


def _load_anthropic_key() -> str | None:
    k = os.environ.get("ANTHROPIC_API_KEY")
    if k:
        return k
    if not SECRETS_PATH.exists():
        return None
    try:
        d = json.loads(SECRETS_PATH.read_text())
    except Exception:
        return None
    for key in ("ANTHROPIC_API_KEY", "anthropic_api_key", "anthropic", "claude_api_key"):
        v = d.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
        if isinstance(v, dict):
            inner = v.get("api_key") or v.get("key")
            if inner:
                return str(inner).strip()
    return None


def _try_anthropic(bar_raiser_prompt: str) -> str | None:
    key = _load_anthropic_key()
    if not key:
        return None
    body = _http_post_json(
        ANTHROPIC_URL,
        {
            "model": os.environ.get("SAGENT_BAR_RAISER_MODEL", "claude-haiku-4-5"),
            "max_tokens": 1024,
            "messages": [{"role": "user", "content": bar_raiser_prompt}],
        },
        {
            "Content-Type": "application/json",
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
        },
        ANTHROPIC_TIMEOUT_S,
    )
    if not body:
        return None
    try:
        data = json.loads(body)
        content = data.get("content")
        if isinstance(content, list):
            return " ".join(b.get("text", "") for b in content if isinstance(b, dict))
        return str(content) if content else None
    except Exception:
        return None


def _try_ollama(bar_raiser_prompt: str) -> str | None:
    body = _http_post_json(
        OLLAMA_URL,
        {
            "model": os.environ.get("SAGENT_OLLAMA_MODEL", "llama3.1"),
            "stream": False,
            "messages": [{"role": "user", "content": bar_raiser_prompt}],
        },
        {"Content-Type": "application/json"},
        OLLAMA_TIMEOUT_S,
    )
    if not body:
        return None
    try:
        data = json.loads(body)
        msg = data.get("message") or {}
        return msg.get("content") or data.get("response")
    except Exception:
        return None


def _llm_review(bar_raiser_prompt: str) -> tuple[dict | None, str]:
    """Return (parsed_json, source). Falls through three tiers; None if all fail."""
    for label, fn in (
        ("sagent", _try_sagent),
        ("anthropic", _try_anthropic),
        ("ollama", _try_ollama),
    ):
        raw = fn(bar_raiser_prompt)
        if not raw:
            continue
        text = raw.strip()
        if "```json" in text:
            text = text.split("```json", 1)[1].split("```", 1)[0].strip()
        elif text.startswith("```"):
            text = text.strip("`").strip()
            if text.lower().startswith("json"):
                text = text[4:].strip()
        m = re.search(r"\{.*\}", text, re.DOTALL)
        if not m:
            continue
        try:
            return json.loads(m.group(0)), label
        except Exception:
            continue
    return None, "none"


# ---------------------------------------------------------------------------
# Decision logic
# ---------------------------------------------------------------------------

def _final_verdict(result: dict) -> tuple[str, list[str]]:
    """Apply local hard gates on top of LLM verdict. Return (verdict, reasons)."""
    verdict = str(result.get("verdict", "approve")).lower()
    reasons: list[str] = []

    score = result.get("business_value_score")
    try:
        score_val = int(score) if score is not None else None
    except Exception:
        score_val = None
    if score_val is not None and score_val < MIN_BUSINESS_SCORE:
        verdict = "block"
        reasons.append(
            f"business_value_score {score_val}/10 < minimum {MIN_BUSINESS_SCORE}"
        )

    cov = result.get("prompt_coverage")
    try:
        cov_val = float(cov) if cov is not None else None
    except Exception:
        cov_val = None
    if cov_val is not None and cov_val < MIN_PROMPT_COVERAGE:
        verdict = "block"
        reasons.append(
            f"prompt_coverage {cov_val:.0%} < required {MIN_PROMPT_COVERAGE:.0%}"
        )

    return verdict, reasons


def main() -> None:
    raw = sys.stdin.read()
    try:
        data = json.loads(raw)
        prompt = data.get("prompt", raw)
    except Exception:
        prompt = raw

    prompt_str = str(prompt)
    if not _is_plan_prompt(prompt_str):
        sys.exit(0)

    project = _detect_project()
    context_excerpt = _read_context_excerpt()
    requirements = _enumerate_requirements(prompt_str)
    cardinality = _detect_cardinality_targets(prompt_str)

    bar_raiser_prompt = _build_bar_raiser_prompt(
        prompt_str, context_excerpt, project, requirements, cardinality
    )

    start = time.monotonic()
    result, source = _llm_review(bar_raiser_prompt)
    elapsed = time.monotonic() - start

    prefix = f"[bar_raiser{f'/{project}' if project else ''}]"

    if result is None:
        # fail-open: every tier unreachable
        sys.exit(0)

    verdict, hard_reasons = _final_verdict(result)
    reason = result.get("reason", "")
    existing_items = result.get("existing_items") or []
    missing = result.get("missing_requirements") or []
    simpler = result.get("simpler_alternative")
    score = result.get("business_value_score")
    cov = result.get("prompt_coverage")

    if verdict == "block":
        full_reason = reason
        if hard_reasons:
            full_reason = (full_reason + " | " if full_reason else "") + "; ".join(hard_reasons)
        print(f"{prefix} BLOCK: {full_reason}", file=sys.stderr)
        if existing_items:
            print(f"{prefix} Already exists:", file=sys.stderr)
            for item in existing_items:
                print(f"  - {item}", file=sys.stderr)
        if missing:
            print(f"{prefix} Missing requirements:", file=sys.stderr)
            for item in missing:
                print(f"  - {item}", file=sys.stderr)
        if simpler:
            print(f"{prefix} Simpler path: {simpler}", file=sys.stderr)
        if score is not None:
            print(
                f"{prefix} business_value_score={score} coverage={cov} "
                f"(via {source}, {elapsed:.1f}s)",
                file=sys.stderr,
            )
        sys.exit(2)

    if verdict == "warn":
        print(f"{prefix} WARN: {reason}", file=sys.stderr)
        if existing_items:
            print(f"{prefix} Overlapping items:", file=sys.stderr)
            for item in existing_items:
                print(f"  - {item}", file=sys.stderr)
        if missing:
            print(f"{prefix} Possibly unaddressed:", file=sys.stderr)
            for item in missing:
                print(f"  - {item}", file=sys.stderr)
        if simpler:
            print(f"{prefix} Simpler path: {simpler}", file=sys.stderr)
        sys.exit(0)

    sys.exit(0)


if __name__ == "__main__":
    main()
