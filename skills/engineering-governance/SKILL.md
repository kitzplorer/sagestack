---
name: Engineering Governance
version: 1.0.0
multi_project: true
description: "Unified 'is this change ready?' gate. Codifies FAANG-level rules and enforces them at three phases: pre-commit, pre-merge, pre-deploy. Use for /governance check, /governance explain <gate>, /governance skip <gate>."
---
# Engineering Governance

Unified "is this change ready?" gate. Codifies FAANG-level rules and enforces
them at three phases: **pre-commit**, **pre-merge**, **pre-deploy**.

Not a wiki. A **CLI** that exits 1 when rules are violated, and tells you
exactly how to fix it.

## The problem

Rules exist. They live in CLAUDE.md, LESSONS_LEARNED.md, ADRs, pre-commit hooks,
CI scripts — scattered across a project and lost between projects. Nobody reads
all of them. Nobody enforces all of them.

The governance module collapses the rules into one engine with one entry point.
Every project installs it via `modules/governance/` and gets the same standard.

## Usage

Install in a project:

```bash
cp -r /path/to/reference/modules/governance <your-project>/modules/
cp -r /path/to/reference/modules/schema-guard <your-project>/modules/
# Wire pre-commit
cat modules/governance/templates/pre-commit-hooks.yaml >> .pre-commit-config.yaml
pre-commit install
# Wire CI
cp modules/governance/templates/.github/governance.yml .github/workflows/
# Bootstrap: generate ADR folder, runbooks dir, initial baseline
python3 modules/governance/cli.py bootstrap
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

## Gate matrix (abridged)

| Gate | Phase | What it blocks |
|---|---|---|
| `migration.parity` | pre-commit | up-migrations without a `down/` sibling |
| `migration.no-collision` | pre-commit | duplicate migration numbers |
| `migration.additive-first` | pre-commit | DROP / rename without ADR reference |
| `schema.drift` | pre-merge | code references to columns/tables not in DB |
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
| `runbook.present` | pre-deploy | user-visible change without a runbook |
| `feature-flag.for-risk` | pre-merge | changes to auth/billing without a flag |
| `slo.unchanged` | pre-deploy | canary p95/error-rate budget exceeded |

## DO (always)

- Every up-migration ships with a `down/` sibling (or `IRREVERSIBLE:` marker + ADR link).
- Additive-first: new columns/tables are backwards-compatible; destructive changes require ADR + dual-write.
- Every risky change ships behind a feature flag with a named rollback command.
- Measure before optimizing. Baseline metric + target in the plan.
- Small commits, small PRs. > 1000 LOC needs a split or approval footer.
- Conventional commit messages: `feat(module):`, `fix(module):`, `chore:`, `refactor:`, `docs:`, `test:`, `ci:`, `perf:`.
- Read code before writing. Re-use before creating.
- Delete aggressively. The lowest tech debt is no code.
- Write the regression test before fixing the bug.
- Provider ABCs for every external dependency (depend on interfaces, not concretions).

## DON'T (ever)

- `--no-verify` commits.
- `git push --force` to shared branches.
- DROP / rename in a shipping migration without dual-write window.
- Mock what should be integration-tested.
- Amend a pushed commit.
- Add a dependency without approval.
- Ship a feature without a rollback plan.
- "I'll circle back" — cleanup that isn't in this PR never lands.
- Optimize without baseline numbers.
- Edit a file without reading it first.
- Skip writing a runbook for a user-visible change.
- Allow a ghost migration (applied in DB, file gone) to persist > 24h.

## Related skills

- **migration-health** — inventory + applied-vs-disk check. Used by `migration.*` gates.
- **software-advisor** — dep CVE checks. Used by `dep.security` gate.
