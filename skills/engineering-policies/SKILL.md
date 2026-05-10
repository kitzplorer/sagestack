---
version: 1.0.0
name: engineering-policies
description: Fleet-wide engineering policies registry. Surfaces the top-5 relevant policies at task kickoff so every code-generation agent obeys the same rules. Install into any project via `marketplace_install engineering-policies`.
triggers:
  - "at session start before any non-trivial code edit"
  - "user says /policies, /policy, /rules, /scan-policies"
  - "agent is about to write or modify code in a fleet project"
events_published:
  - policy.violation.detected
  - policy.bypass.used
  - policy.new.added
---

# Engineering Policies Skill

**What**: 73-and-growing policy registry that every agent in Bala's fleet MUST consult before doing meaningful code work. Policies cover schema (4NF), code (5NF / BCNF / 3NF), security, frontend, backend, AI routing, governance, migrations, docs, ops.

**Why**: Rules drift. CLAUDE.md is 800 lines. Nobody reads all of it. This skill makes the top-5 relevant rules appear **exactly when they apply**.

## Install into a project

```bash
# From the target project root
cp -r ~/projects/hrms/modules/policies modules/
python3 modules/policies/cli.py list | head    # sanity check
python3 -m pytest modules/policies/tests/ -v   # 21/21 green
```

Or via the marketplace:

```python
from sagent.marketplace import install
install("engineering-policies", target_project="<project-name>")
```

## Usage from inside an agent turn

### 1. Task kickoff — ALWAYS

```bash
python3 modules/policies/cli.py search "<one-line intent>" --json
```

Returns top-5 policies with `id, name, category, severity, rule, rationale`. Load into context. Obey them.

### 2. When in doubt — explain

```bash
python3 modules/policies/cli.py explain SCHEMA-001
```

Full rule, rationale, pass/fail examples, enforcement phase, bypass policy.

### 3. Before commit — check

```bash
python3 modules/policies/cli.py check --phase pre-commit
```

Runs governance gates tagged with the policy IDs they enforce. Exit 0 = clean, 1 = violations.

### 4. When shipping a risky change

```bash
python3 modules/policies/cli.py check --phase pre-deploy
```

## Enforcement contract

Agents are **REQUIRED** to:

1. Run `search` at task kickoff with the task intent.
2. Load top-5 returned policies into working context.
3. Cite the policy ID when a decision is driven by it (e.g. "per SEC-005, adding confirm-token to this endpoint").
4. If a policy blocks the task, either comply OR open an ADR + file a time-boxed bypass via the governance CLI.

Agents are **FORBIDDEN** from:

1. Ignoring a returned CRITICAL or HIGH policy silently.
2. Bypassing a policy without writing a reason + expiry.
3. Editing `policies/*.yaml` to weaken a policy without user approval.

## Events

Wired into the sagent event bus when available:

- `policy.violation.detected` — emitted by `cli.py check` when a gate fails
- `policy.bypass.used` — emitted when governance `skip` creates a bypass
- `policy.new.added` — emitted when `reload` detects a new policy file

Subscribe on sagent:

```python
from sagent.events import subscribe
subscribe("policy.violation.detected", handler)
```

## Onboarding prompt

See `ONBOARD_PROMPT.md` for the recommended system-prompt addition. Copy it into CLAUDE.md for every fleet project.

## Source of truth

The canonical copy lives at `~/projects/hrms/modules/policies/`. All fleet projects install from there.

Changes flow:
1. Edit YAML in hrms/modules/policies/policies/<cat>/
2. `python3 modules/policies/cli.py reload`
3. Commit + push from hrms
4. Other projects pull via the marketplace (`marketplace_install engineering-policies --upgrade`)
