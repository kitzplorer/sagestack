---
name: Engineering Governance
version: 1.0.0
multi_project: true
description: "Unified 'is this change ready?' gate. Codifies FAANG-level rules and enforces"
---
# Engineering Governance

Unified "is this change ready?" gate. Codifies FAANG-level rules and enforces
them at three phases: **pre-commit**, **pre-merge**, **pre-deploy**.

Not a wiki. A **CLI** that exits 1 when rules are violated, and tells you
exactly how to fix it.

## The problem

Rules exist. They live in CLAUDE.md, LESSONS_LEARNED.md, FAANG_GAP_ANALYSIS.md,
ADRs, pre-commit hooks, CI scripts — scattered across a project and lost between
projects. Nobody reads all of them. Nobody enforces all of them.

The governance module collapses the rules into one engine with one entry point.
Every project in the fleet installs it via `modules/governance/` and gets the
same standard.

## Usage

Install in a project (copy or git-submodule the portable module):

```bash
cp -r /path/to/hrms/modules/governance <your-project>/modules/
```

Then:

```bash
# Pre-commit — runs on every staged diff (fast checks only)
python3 modules/governance/cli.py pre-commit

# Pre-merge — runs in CI on every PR (fuller)
python3 modules/governance/cli.py pre-merge

# Pre-deploy — runs before production push (strictest)
python3 modules/governance/cli.py pre-deploy --env prod

# Explain why a gate exists and how to fix it
python3 modules/governance/cli.py explain migration.parity

# Time-boxed bypass (requires reason + expiry — tracked for postmortem)
python3 modules/governance/cli.py skip migration.parity \
  --reason "ADR-012: one-time seed migration" --expires 2026-05-01

# Show do/don't rules for a topic
python3 modules/governance/cli.py rules migrations
```

## Gate matrix (abridged — see `rules/CHECKLIST.md` in each project)

| Gate | Phase | What it blocks |
|---|---|---|
| `migration.parity` | pre-commit | up-migrations without a `down/` sibling |
| `migration.no-collision` | pre-commit | duplicate migration numbers |
| `migration.additive-first` | pre-commit | DROP / rename without ADR reference |
| `schema.drift` | pre-merge | code references to columns/tables that don't exist in DB |
| `tests.coverage` | pre-merge | coverage drop below threshold |
| `tests.no-new-failures` | pre-merge | any new test failure |
| `types.strict` | pre-commit | pyright strict violations on touched files |
| `secrets` | pre-commit | secret patterns in diff |
| `commit.format` | commit-msg | non-conventional commit messages |
| `branch.protection` | pre-commit | direct commits to `main`/`dev` |
| `pr.size` | pre-merge | > 1000 LOC without split-approval |
| `pr.adr-required` | pre-merge | arch-level change without ADR |
| `dep.security` | pre-merge | deps with high/critical CVEs |
| `dep.no-new-without-approval` | pre-commit | new dep without approval footer |
| `change.classify` | pre-merge | sagent executor classifies as "degrading" |
| `runbook.present` | pre-deploy | user-visible change without a runbook |
| `feature-flag.for-risk` | pre-merge | changes to auth/payroll/billing without a flag |
| `slo.unchanged` | pre-deploy | canary p95/error-rate budget exceeded |

## DO (always)

- Every up-migration ships with a `down/` sibling (or an explicit `IRREVERSIBLE:` marker with ADR link).
- Additive-first: new columns/tables are backwards-compatible; destructive changes require ADR + dual-write.
- Every risky change ships behind a feature flag with a named rollback command.
- Measure before optimizing. Baseline metric + target in the plan.
- Small commits, small PRs. > 1000 LOC needs a split or approval footer.
- Conventional commit messages: `feat(module):`, `fix(module):`, `chore:`, `refactor:`, `docs:`, `test:`, `ci:`, `perf:`.
- Read code before writing. Re-use before creating.
- Delete aggressively. The lowest tech debt is no code.
- Write the regression test before fixing the bug.
- Provider ABCs for every external dependency (3NF code: depend on interfaces, not concretions).
- One engine per concern across the fleet (5NF: no parallel reinventions).

## DON'T (ever)

- `--no-verify` commits.
- `git push --force` to shared branches.
- DROP / rename in a shipping migration without dual-write window.
- Mock what should be integration-tested ("we got burned last quarter" is the rule's origin).
- Amend a pushed commit.
- Add a dependency without approval.
- Ship a feature without a rollback plan.
- "I'll circle back" — cleanup that isn't in this PR never lands.
- Optimize without baseline numbers.
- Edit a file without reading it first.
- Skip writing a runbook for a user-visible change.
- Let a degrading change merge to main.
- Allow a ghost migration (applied in DB, file gone) to persist > 24h.

## Events published

- `governance.gate.failed` — `{project, gate, phase, file_or_symbol, fix_hint}`
- `governance.bypass.used` — `{project, gate, reason, expires_at, actor}`
- `governance.adr.new` — `{project, path, title}`
- `governance.runbook.new` — `{project, path, title, linked_endpoint}`

Consume these via sagent's existing telemetry — they show up on the governance
dashboard alongside migration health, schema drift, and cost tracking.

## Installation in a new project

```bash
# From the target project
cp -r /path/to/reference/modules/governance ./modules/
cp -r /path/to/reference/modules/schema-guard ./modules/
# Wire pre-commit
cat modules/governance/templates/pre-commit-hooks.yaml >> .pre-commit-config.yaml
pre-commit install
# Wire CI
cp modules/governance/templates/.github/governance.yml .github/workflows/
# First-run bootstrap: generate ADR folder, runbooks dir, initial baseline
python3 modules/governance/cli.py bootstrap
```

## Running in other projects

This skill is marked `multi_project: true` — it can run from any repo on the
fabric, not just sagent.

```bash
# From HRMS, nishops, or any other repo:
/engineering-governance check

# Equivalent CLI invocation:
python3 modules/governance/cli.py pre-commit
```

The skill resolves its modules path relative to the current git repo root.
`skill_context.resolve_skills_path()` walks the resolution order:

1. `<repo>/skills/` — if this skill is installed locally
2. `<repo>/.claude/skills/`
3. `~/.claude/skills/` — global install (sagent-wide)
4. `~/.openclaw/skills/` — legacy fallback

Install it into any project with one click from `/dashboard/widgets/marketplace`
or via the CLI:

```bash
POST /api/sagent/marketplace/install
{"skill_name": "engineering-governance", "target_project": "hrms"}
```

## Related skills

- **migration-health** — inventory + applied-vs-disk check. Used by `migration.*` gates.
- **schema-guard** — code-vs-DB drift check. Used by `schema.drift` gate.
- **review.executor** — progressive/neutral/degrading classifier. Used by `change.classify` gate.

## How this is verified at L5

The skill invokes gate logic via `modules/governance/cli.py` which loads and runs rule engines for each phase (pre-commit/pre-merge/pre-deploy). L1: skill file exists; modules/governance/ present with CHECKLIST.md rule catalog. L3: invocation of `cli.py pre-commit` against staged diff produces real gate verdicts (exit 0/1), not stubs. L5: matches FAANG governance standards (Google internal code review, meta infra gates, GitHub no-verify blocks); gates are sourced from project CLAUDE.md and reference ADRs / runbooks that live in the repo.
