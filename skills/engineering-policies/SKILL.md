---
version: 1.0.0
name: engineering-policies
description: Fleet-wide engineering policies registry. Surfaces the top-5 relevant policies at task kickoff so every code-generation agent obeys the same rules. Use when starting a non-trivial code edit, or when the user says /policies, /policy, /rules.
triggers:
  - "at session start before any non-trivial code edit"
  - "user says /policies, /policy, /rules, /scan-policies"
  - "agent is about to write or modify code in a project"
events_published:
  - policy.violation.detected
  - policy.bypass.used
  - policy.new.added
---

# Engineering Policies Skill

**What**: Policy registry that every agent MUST consult before doing meaningful code work. Policies cover schema, code quality, security, frontend, backend, AI routing, governance, migrations, docs, ops.

**Why**: Rules drift. CLAUDE.md gets long. Nobody reads all of it. This skill makes the top-5 relevant rules appear **exactly when they apply**.

## Install into a project

```bash
# From the target project root
cp -r /path/to/reference/modules/policies modules/
python3 modules/policies/cli.py list | head    # sanity check
python3 -m pytest modules/policies/tests/ -v
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

Exit 0 = clean, 1 = violations.

### 4. When shipping a risky change

```bash
python3 modules/policies/cli.py check --phase pre-deploy
```

## Enforcement contract

Agents are **REQUIRED** to:

1. Run `search` at task kickoff with the task intent.
2. Load top-5 returned policies into working context.
3. Cite the policy ID when a decision is driven by it (e.g. "per SEC-005, adding confirm-token to this endpoint").
4. If a policy blocks the task, either comply OR open an ADR + file a time-boxed bypass.

Agents are **FORBIDDEN** from:

1. Ignoring a returned CRITICAL or HIGH policy silently.
2. Bypassing a policy without writing a reason + expiry.
3. Editing `policies/*.yaml` to weaken a policy without user approval.

## Policy file format

```yaml
# policies/security/SEC-005.yaml
id: SEC-005
name: confirm-token-on-state-change
category: security
severity: HIGH
rule: "Every endpoint that changes persistent state must require a confirm-token or CSRF header."
rationale: "Prevents CSRF attacks on form submissions."
enforcement_phase: pre-commit
bypass_policy: "ADR required + expires within 7 days"
```

## Source of truth

The canonical policy set lives in `modules/policies/policies/<category>/`. Changes flow:
1. Edit YAML in `modules/policies/policies/<cat>/`
2. `python3 modules/policies/cli.py reload`
3. Commit + push
4. Other projects pull via copy or package manager
