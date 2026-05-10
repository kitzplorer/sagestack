---
name: Frontend Helper
version: 1.0.0
description: "Personal frontend error translator and learning companion."
---
# Frontend Helper

Personal frontend error translator and learning companion.
Parses terminal/build output, identifies errors in plain English,
suggests fixes, and connects to LLM for deeper questions.

Focused on: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS.

## Usage

```bash
# Paste terminal output, get help
python3 skills/frontend-helper/scripts/frontend_helper.py paste

# Ask a frontend question
python3 skills/frontend-helper/scripts/frontend_helper.py ask "what is hydration?"

# Scan a project for common issues
python3 skills/frontend-helper/scripts/frontend_helper.py scan /path/to/project

# Interactive mode (chat + paste)
python3 skills/frontend-helper/scripts/frontend_helper.py interactive
```

## Events Published

- `frontend.error.identified` — error parsed with fix suggestion
- `frontend.question.asked` — question routed to LLM

## How this is verified at L5

The skill invokes error parsing via `scripts/frontend_helper.py` which calls the sagent LLM router for translations and pattern matching. L1: skill file exists with CLI entry points. L3: invocation of `frontend_helper.py` produces real terminal output parsing, not stub text. L5: matches sagent-internal error taxonomy (Next.js 14 hydration, React 18 hooks, TypeScript strict errors) used across the fleet; no external peer benchmark applies.
