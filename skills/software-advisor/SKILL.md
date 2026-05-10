---
version: 1.0.0
name: software-advisor
description: "Monitors installed software for known security vulnerabilities, end-of-life status, and recommends when to migrate or update. Checks system packages, language runtimes, frameworks, and project dependencies against vulnerability databases. Use when the user asks about software security, outdated packages, CVEs, or whether they should update/replace a tool."
---

# Software Security Advisor

Proactively monitors installed software for security vulnerabilities, end-of-life (EOL) status,
and known issues. Tells you when it's time to update, migrate, or replace software.

## Core Rules

- All checks are read-only. Never update or uninstall without explicit user approval.
- Present findings sorted by severity: CRITICAL → HIGH → MEDIUM → LOW.
- Always provide migration/update paths, not just warnings.
- Check both system-level and project-level dependencies.
- Cross-reference multiple sources (NVD, vendor advisories, EOL databases).

## Workflow

### 1. Full System Audit

```bash
bash skills/software-advisor/scripts/audit_software.sh
```

Checks:
- OS version and patch status (macOS/Linux)
- System packages (brew/apt/dnf)
- Language runtimes (Node.js, Python, Ruby, Go, Java, Rust)
- Database servers (PostgreSQL, MySQL, Redis, MongoDB)
- Web servers (nginx, Apache, Caddy)
- Container runtimes (Docker, Podman)
- CLI tools (git, curl, openssl, ssh)

### 2. Quick Check (Specific Software)

```bash
bash skills/software-advisor/scripts/check_single.sh node
bash skills/software-advisor/scripts/check_single.sh openssl
bash skills/software-advisor/scripts/check_single.sh python3
```

### 3. EOL Check

```bash
bash skills/software-advisor/scripts/check_eol.sh
```

Checks EOL dates for Node.js, Python, Ruby, Go, Java, .NET, Ubuntu/Debian/macOS, database major versions, framework versions.

### 4. Dependency Vulnerability Scan

```bash
bash skills/software-advisor/scripts/scan_deps.sh [project_path]
```

Detects: `package.json`, `requirements.txt`, `Gemfile`, `go.mod`, `Cargo.toml`, `composer.json`

Runs: `npm audit`, `pip-audit`, `bundler-audit`, `govulncheck`, `cargo audit`

## Decision Framework

### CHANGE IMMEDIATELY (Critical)
- Actively exploited CVE (CVSS 9.0+)
- Past EOL with no security patches
- Known data breach vector in current version

### CHANGE SOON (High)
- EOL within 3 months
- CVEs CVSS 7.0–8.9 without patches
- Vendor recommends migration

### PLAN MIGRATION (Medium)
- EOL within 6–12 months
- Better alternatives with active development

### MONITOR (Low)
- Minor version updates available
- Non-security bug fixes pending

## Integration

- Works with **network-security** to correlate service versions with exposure
- Works with **file-scavenger** to identify abandoned project dependencies
- Works with **engineering-governance** for the `dep.security` gate
