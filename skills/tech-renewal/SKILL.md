---
version: 1.0.0
name: tech-renewal
description: "Monitors installed technologies for end-of-life, trending replacements, compatibility issues, and migration urgency. Compares your stack against industry trends (npm downloads, GitHub stars, Stack Overflow activity). Recommends migration paths with compatibility scoring. Use when the user asks about outdated tech, trending alternatives, migration planning, or wants recurring tech health reports."
---

# Tech Renewal Bot

Proactively tracks which tech in your stack is outdated, what's trending as a
replacement, whether it's compatible with your architecture, and when to plan
migration.

## Core Rules

- Never auto-migrate. Only recommend. Human decides.
- Back claims with data (EOL dates, download trends, CVE counts).
- Compatibility scoring considers YOUR architecture, not generic advice.
- Monthly reports include actionable items, not just info dumps.

## Workflows

### 1. Full Stack Renewal Check

> What in my tech stack is outdated?

### 2. Single Tech Check

> Is FastAPI still the best choice for our backend?

### 3. Trending Alternatives

> What's trending to replace Redis for caching?

### 4. Migration Feasibility

> Should we migrate from PostgreSQL 14 to 16? What's involved?

### 5. Monthly Report Setup

> Send me a tech renewal report every month

## Report Format

```
TECH RENEWAL REPORT — 2026-05-10
Project: <your-project>

CRITICAL (act now):
  PostgreSQL 14 → EOL Oct 2026 (7 months)
  Action: Upgrade to 16. Estimated effort: 2-4 hours.

WARNING (plan within 6 months):
  Node.js 20 → LTS ends Apr 2026
  Trending replacement: Node.js 22 (LTS until Apr 2027)
  Compatible: YES

TRENDING:
  Bun gaining traction (2x npm downloads YoY)
  — NOT recommended yet: ecosystem gaps for typical stacks

STABLE (no action needed):
  FastAPI, Redis 7, Docker, Tailwind CSS
```

## Data Sources

- EOL dates: endoflife.date API
- Download trends: npm registry, PyPI stats
- GitHub stars: GitHub API (MoM growth)
- CVE counts: NVD API
- Stack Overflow activity: SO tags API

## Integration

- Works with **software-advisor** for CVE detail on flagged packages
- Works with **migration-health** when DB version migrations are planned
