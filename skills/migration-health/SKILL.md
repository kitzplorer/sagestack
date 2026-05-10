---
name: Migration Health
version: 1.0.0
description: "Inventory-audit for file-based SQL migrations. Detects gaps in numbering, duplicate numbers, missing rollback siblings, orphan files, applied-vs-pending status, ghost migrations (applied but deleted), and checksum drift. Use when a migration 'doesn't work', before deploys, or as a pre-commit/CI gate."
---
# Migration Health

Inventory-audit for file-based SQL migrations. Answers the "are we missing
anything?" question that code-vs-schema drift tools don't cover:

- Gaps in numbering (e.g. jumped from 082 → 084, lost 083)
- Duplicate numbers (two people claimed the same slot)
- Missing `down/NNN_*.sql` rollback siblings
- Orphan down files in the root instead of `migrations/down/`
- **Applied vs pending** per version (needs DB + `schema_migrations` tracking table)
- **Ghosts**: version applied in DB but file deleted on disk
- **Checksum drift**: file edited after it was applied

Backed by the `schema-guard` portable module (lives in each project's
`modules/schema-guard/`). Auto-creates a tiny `schema_migrations` tracking
table on first run — no migration framework required.

## Usage

```bash
# File-only audit (no DB)
python3 modules/schema-guard/cli.py audit \
  --dir app/migrations

# Full audit (DB + files), auto-create tracking table
python3 modules/schema-guard/cli.py audit \
  --dir app/migrations \
  --db "$DATABASE_URL"

# Repairs
python3 modules/schema-guard/cli.py audit --dir ... \
  --fix-orphan-downs         # move misfiled *_down.sql from root → down/
  --generate-down-stubs      # placeholder rollbacks for each missing down

# CI gate (exit 1 on any issue)
python3 modules/schema-guard/cli.py audit --dir ... --fail-on-issues
```

## When to call

- **Pre-commit hook**: block unhealthy commits before they land.
- **CI**: fail PRs that add migrations without downs, or introduce number duplicates.
- **Nightly cron**: full audit on prod DB.
- **Pre-deploy check**: block deploy if any version is `pending` on prod or any `ghost` anywhere.
- **When a migration "doesn't work"**: call this first before opening a DB shell.

## Tracking table contract

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version     INTEGER PRIMARY KEY,
    name        TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    checksum    TEXT
);
```

Any migration runner should upsert into this table on every successful apply:

```sql
INSERT INTO schema_migrations (version, name, checksum)
VALUES (:v, :n, :c)
ON CONFLICT (version) DO UPDATE SET applied_at = NOW(), checksum = EXCLUDED.checksum;
```

Compatible with Alembic (`alembic_version`) and Django (`django_migrations`) via
a compatibility VIEW named `schema_migrations`.

## Relation to schema-guard `check`

- `check/fix/ci` answer: "does my code reference columns that don't exist in the DB?"
- `audit` answers: "is my migration inventory consistent — on disk and in the DB?"

Run both. They catch different failure classes.
