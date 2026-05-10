---
version: 1.0.0
name: software-advisor
description: "Monitors installed software for known security vulnerabilities, end-of-life status, and recommends when to migrate or update. Checks system packages, language runtimes, frameworks, and dependencies against vulnerability databases. Use when the user asks about software security, outdated packages, CVEs, or whether they should update/replace a tool."
metadata: { "openclaw": { "emoji": "🔍", "os": ["darwin", "linux"] } }
---

# Software Security Advisor

Proactively monitors installed software for security vulnerabilities, end-of-life (EOL) status, and known issues. Tells you when it's time to update, migrate, or replace software before it becomes a liability.

## Core Rules

- All checks are read-only. Never update or uninstall software without explicit user approval.
- Present findings sorted by severity: CRITICAL → HIGH → MEDIUM → LOW.
- Always provide migration/update paths, not just warnings.
- Check both system-level and project-level dependencies.
- Cross-reference multiple sources (NVD, vendor advisories, EOL databases).

## Workflow

### 1. Full System Audit

Run a comprehensive software security audit:

```bash
bash skills/software-advisor/scripts/audit_software.sh
```

This checks:

**System-Level Software:**

- OS version and patch status (macOS/Linux)
- System packages (brew/apt/dnf/pacman)
- Language runtimes (Node.js, Python, Ruby, Go, Java, Rust)
- Database servers (PostgreSQL, MySQL, Redis, MongoDB, SQLite)
- Web servers (nginx, Apache, Caddy)
- Container runtimes (Docker, Podman)
- CLI tools (git, curl, openssl, ssh)

**Project-Level Dependencies:**

- npm/pnpm/yarn packages (via `npm audit` / `pnpm audit`)
- Python packages (via `pip-audit` or `safety`)
- Ruby gems (via `bundler-audit`)
- Go modules (via `govulncheck`)
- Rust crates (via `cargo audit`)

### 2. Quick Check (Specific Software)

Check a specific tool or package:

```bash
bash skills/software-advisor/scripts/check_single.sh <software_name>
```

Example:

```bash
bash skills/software-advisor/scripts/check_single.sh node
bash skills/software-advisor/scripts/check_single.sh openssl
bash skills/software-advisor/scripts/check_single.sh python3
```

### 3. EOL (End-of-Life) Check

Check which installed software is past its end-of-life date:

```bash
bash skills/software-advisor/scripts/check_eol.sh
```

Checks against known EOL dates for:

- Node.js (LTS schedule)
- Python (release cycle)
- Ruby, Go, Java, .NET
- Ubuntu/Debian/RHEL/macOS versions
- Database major versions
- Framework versions (React, Angular, Vue, Django, Rails, etc.)

### 4. Dependency Vulnerability Scan

Scan project dependencies for known vulnerabilities:

```bash
bash skills/software-advisor/scripts/scan_deps.sh [project_path]
```

Without a path, scans the current directory. Detects:

- package.json / pnpm-lock.yaml / yarn.lock (Node.js)
- requirements.txt / Pipfile / pyproject.toml (Python)
- Gemfile / Gemfile.lock (Ruby)
- go.mod / go.sum (Go)
- Cargo.toml / Cargo.lock (Rust)
- composer.json (PHP)

### 5. Continuous Monitoring

Schedule periodic checks via OpenClaw cron:

```bash
# Daily dependency scan
openclaw cron add --name "software-advisor:daily-scan" \
  --schedule "0 6 * * *" \
  --command "bash skills/software-advisor/scripts/audit_software.sh --quiet"

# Weekly EOL check
openclaw cron add --name "software-advisor:weekly-eol" \
  --schedule "0 9 * * 1" \
  --command "bash skills/software-advisor/scripts/check_eol.sh"
```

## Report Format

```
═══════════════════════════════════════════
  SOFTWARE SECURITY ADVISORY REPORT
  Host: hostname | Date: YYYY-MM-DD HH:MM
═══════════════════════════════════════════

SUMMARY
  Software Checked: 47
  Critical Vulnerabilities: 2
  Software Past EOL: 3
  Updates Available: 12
  Overall Risk: HIGH

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 CRITICAL - IMMEDIATE ACTION REQUIRED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  openssl 1.1.1w
    Status: END OF LIFE (Sep 2023)
    CVEs: CVE-2024-XXXXX (RCE, CVSS 9.8)
    Risk: Remote code execution possible
    Action: Upgrade to openssl 3.3+
    Command: brew upgrade openssl@3

  log4j 2.14.1 (in project: /app)
    Status: VULNERABLE
    CVEs: CVE-2021-44228 (Log4Shell, CVSS 10.0)
    Risk: Remote code execution via JNDI injection
    Action: Upgrade to log4j 2.21+
    Command: Update pom.xml dependency

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚠️  HIGH - UPDATE RECOMMENDED
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Node.js 18.19.0
    Status: Maintenance LTS (EOL Apr 2025)
    Action: Migrate to Node.js 22 LTS
    Command: nvm install 22 && nvm alias default 22

  Python 3.9.18
    Status: Security-only updates (EOL Oct 2025)
    Action: Migrate to Python 3.12+
    Command: brew install python@3.12

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ℹ️  INFO - SOFTWARE STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  ✅ git 2.44.0          Current, no known issues
  ✅ nginx 1.25.4        Current, no known issues
  ✅ PostgreSQL 16.2     Current LTS, no known issues
  ⚠️  Redis 7.0.15       Update available: 7.2.4
  ⚠️  Docker 25.0.3      Update available: 26.0.0

MIGRATION RECOMMENDATIONS
  1. [URGENT] Replace openssl 1.1.1 → 3.3
  2. [SOON]   Migrate Node.js 18 → 22
  3. [PLAN]   Migrate Python 3.9 → 3.12
═══════════════════════════════════════════
```

## Decision Framework: When to Change Software

The advisor uses this framework to determine urgency:

### 🚨 CHANGE IMMEDIATELY (Critical)

- Software has an actively exploited CVE (CVSS 9.0+)
- Software is past EOL with no security patches
- Known data breach vector in current version
- Vendor has issued an emergency advisory

### ⚠️ CHANGE SOON (High)

- Software enters EOL within 3 months
- CVEs with CVSS 7.0-8.9 without patches
- Vendor recommends migration
- Performance/compatibility issues with current stack

### 📋 PLAN MIGRATION (Medium)

- Software enters EOL within 6-12 months
- Better alternatives exist with active development
- Current version lacks critical features needed
- Community support declining

### ℹ️ MONITOR (Low)

- Minor version updates available
- Non-security bug fixes pending
- Newer versions available but current is stable
- Feature enhancements in newer versions

## Integration with Other Skills

- Works with **healthcheck** skill for overall system security posture
- Works with **network-security** skill to correlate service versions with exposure
- Works with **file-scavenger** to identify abandoned project dependencies
