---
version: 1.0.0
name: network-security
description: "Continuous network security monitoring for OpenClaw deployments. Scans open ports, detects vulnerabilities, monitors active connections, checks firewall status, and provides real-time security alerts when the machine is exposed as a server. Use when the user wants to check ports, scan for vulnerabilities, monitor network exposure, or harden their server setup for incoming requests."
metadata: { "openclaw": { "emoji": "🛡️", "os": ["darwin", "linux"] } }
---

# Network Security Scanner

Comprehensive network security monitoring for machines running OpenClaw as a server. Continuously checks open ports, detects vulnerabilities, monitors connections, and alerts on security issues.

## Core Rules

- Require explicit approval before any state-changing action (closing ports, changing firewall rules).
- All scans are read-only unless the user explicitly requests remediation.
- Never expose scan results to external services without user consent.
- Format all findings with severity levels: CRITICAL, HIGH, MEDIUM, LOW, INFO.
- Provide actionable remediation steps for every finding.

## Workflow

### 1. Quick Security Scan (Default)

Run a fast scan of the current machine's security posture:

```bash
bash skills/network-security/scripts/quick_scan.sh
```

This checks:

- All listening ports and their associated processes
- Firewall status (macOS Application Firewall + pf, or Linux ufw/iptables/nftables)
- Active network connections and their states
- Known dangerous ports (exposed databases, admin panels, debug ports)
- OpenClaw gateway bind address safety

### 2. Deep Port Scan

Thorough scan of all ports with service detection:

```bash
bash skills/network-security/scripts/deep_scan.sh [target_ip]
```

Without a target, scans localhost. Checks:

- All 65535 TCP ports
- Common UDP ports (53, 67, 68, 123, 161, 500, 5353)
- Service version detection on open ports
- Banner grabbing for service identification
- SSL/TLS certificate validation on HTTPS ports

### 3. Continuous Monitoring Mode

Start background monitoring that alerts on changes:

```bash
bash skills/network-security/scripts/monitor.sh start
```

Monitors every 60 seconds for:

- New ports opening
- New inbound connections from unknown IPs
- Firewall rule changes
- Unusual outbound connections
- Failed authentication attempts (SSH, HTTP)

Stop monitoring:

```bash
bash skills/network-security/scripts/monitor.sh stop
```

View monitoring log:

```bash
bash skills/network-security/scripts/monitor.sh status
```

### 4. Server Exposure Assessment

When running OpenClaw as a server accepting GET/POST requests:

```bash
bash skills/network-security/scripts/exposure_check.sh [port]
```

Checks:

- Is the port accessible from external networks?
- Are there rate limiting protections?
- Is HTTPS/TLS configured?
- Are CORS headers properly set?
- Is authentication required on sensitive endpoints?
- Are request size limits configured?
- Is input validation in place?
- Are error messages leaking internal info?

### 5. Vulnerability Database Check

Cross-reference running services against known CVEs:

```bash
bash skills/network-security/scripts/vuln_check.sh
```

Checks:

- Running service versions against NVD (National Vulnerability Database)
- Known exploits for detected service versions
- Default credentials on common services
- Misconfiguration patterns

## Dangerous Ports Reference

These ports should NEVER be exposed to public networks without strong authentication:

| Port  | Service        | Risk                   |
| ----- | -------------- | ---------------------- |
| 22    | SSH            | Brute force attacks    |
| 3306  | MySQL          | Data theft             |
| 5432  | PostgreSQL     | Data theft             |
| 6379  | Redis          | Unauthenticated access |
| 27017 | MongoDB        | Data theft             |
| 9200  | Elasticsearch  | Data leak              |
| 2375  | Docker API     | Full host compromise   |
| 5900  | VNC            | Screen capture         |
| 8080  | Dev servers    | Unprotected access     |
| 3000  | Dev frameworks | Debug endpoints        |
| 9090  | Various admin  | Admin access           |
| 11211 | Memcached      | DDoS amplification     |

## Hardening Checklist (for server mode)

When running OpenClaw as a server, ensure:

1. **Firewall**: Only required ports open (offer to configure)
2. **TLS**: HTTPS on all public-facing endpoints
3. **Auth**: Token or key-based authentication on all API endpoints
4. **Rate Limiting**: Max requests per IP per minute
5. **Input Validation**: Sanitize all incoming request data
6. **Logging**: Log all access attempts with IP and timestamp
7. **IP Allowlisting**: Restrict access to known IPs if possible
8. **Reverse Proxy**: Use nginx/caddy in front of the application
9. **Process Isolation**: Run services as non-root user
10. **Updates**: Keep all services patched

## Report Format

All scans output a structured report:

```
═══════════════════════════════════════
  OPENCLAW NETWORK SECURITY REPORT
  Host: hostname | Date: YYYY-MM-DD HH:MM
═══════════════════════════════════════

SUMMARY
  Open Ports: 5
  Critical Issues: 1
  Warnings: 3
  Score: 65/100

CRITICAL FINDINGS
  [CRITICAL] Port 6379 (Redis) exposed without authentication
    → Remediation: Set requirepass in redis.conf or close port

HIGH FINDINGS
  [HIGH] SSH allows password authentication
    → Remediation: Set PasswordAuthentication no in sshd_config

MEDIUM FINDINGS
  [MEDIUM] Port 3000 (Node.js) accessible externally
    → Remediation: Bind to 127.0.0.1 or add firewall rule

OPEN PORTS
  Port 22   → SSH (OpenSSH 9.6)     [FILTERED]
  Port 80   → HTTP (nginx 1.25)     [OPEN]
  Port 443  → HTTPS (nginx 1.25)    [OPEN]
  Port 3000 → Node.js               [OPEN - WARNING]
  Port 6379 → Redis 7.2             [OPEN - CRITICAL]

FIREWALL STATUS
  macOS Application Firewall: ENABLED
  pf (Packet Filter): DISABLED
  → Recommendation: Enable pf with deny-by-default policy

ACTIVE CONNECTIONS
  5 established, 2 listening, 0 suspicious
═══════════════════════════════════════
```

## Integration with OpenClaw Cron

Schedule periodic scans via OpenClaw:

```bash
# Quick scan every hour
openclaw cron add --name "network-security:hourly-scan" \
  --schedule "0 * * * *" \
  --command "bash skills/network-security/scripts/quick_scan.sh"

# Deep scan daily at 2 AM
openclaw cron add --name "network-security:daily-deep" \
  --schedule "0 2 * * *" \
  --command "bash skills/network-security/scripts/deep_scan.sh"
```

## Responding to Threats

When a critical issue is detected:

1. Alert the user immediately via their active channel
2. Provide the exact command to remediate
3. Offer to remediate with explicit approval
4. Log the finding for audit trail
5. Re-scan after remediation to verify

For continuous monitoring alerts, the system will:

- Send a message via the active OpenClaw channel
- Include severity, port/service, source IP, and recommended action
- Never auto-remediate without explicit user approval
