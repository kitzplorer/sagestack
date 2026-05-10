---
version: 1.0.0
name: network-security
description: "Continuous network security monitoring. Scans open ports, detects vulnerabilities, monitors active connections, checks firewall status, and provides real-time security alerts. Use when the user wants to check ports, scan for vulnerabilities, monitor network exposure, or harden their server setup."
---

# Network Security Scanner

Comprehensive network security monitoring. Continuously checks open ports,
detects vulnerabilities, monitors connections, and alerts on security issues.

## Core Rules

- Require explicit approval before any state-changing action (closing ports, changing firewall rules).
- All scans are read-only unless the user explicitly requests remediation.
- Format all findings with severity levels: CRITICAL, HIGH, MEDIUM, LOW, INFO.
- Provide actionable remediation steps for every finding.

## Workflow

### 1. Quick Security Scan (Default)

```bash
bash skills/network-security/scripts/quick_scan.sh
```

Checks: all listening ports + processes, firewall status, active connections, known dangerous ports, exposed admin panels/DBs.

### 2. Deep Port Scan

```bash
bash skills/network-security/scripts/deep_scan.sh [target_ip]
```

Without target, scans localhost. Checks all 65535 TCP ports, common UDP ports, service version detection, SSL/TLS certificate validation.

### 3. Continuous Monitoring Mode

```bash
bash skills/network-security/scripts/monitor.sh start   # start background monitor
bash skills/network-security/scripts/monitor.sh stop
bash skills/network-security/scripts/monitor.sh status  # view monitoring log
```

Monitors every 60s for: new ports opening, new inbound connections, firewall rule changes, failed auth attempts.

### 4. Server Exposure Assessment

```bash
bash skills/network-security/scripts/exposure_check.sh [port]
```

Checks: external accessibility, rate limiting, HTTPS/TLS, CORS headers, auth on sensitive endpoints, input validation, error message leakage.

### 5. Vulnerability Database Check

```bash
bash skills/network-security/scripts/vuln_check.sh
```

Cross-references running service versions against NVD, checks default credentials, misconfiguration patterns.

## Dangerous Ports Reference

| Port  | Service        | Risk                   |
| ----- | -------------- | ---------------------- |
| 3306  | MySQL          | Data theft             |
| 5432  | PostgreSQL     | Data theft             |
| 6379  | Redis          | Unauthenticated access |
| 27017 | MongoDB        | Data theft             |
| 9200  | Elasticsearch  | Data leak              |
| 2375  | Docker API     | Full host compromise   |
| 5900  | VNC            | Screen capture         |
| 8080  | Dev servers    | Unprotected access     |
| 11211 | Memcached      | DDoS amplification     |

## Server Hardening Checklist

1. **Firewall**: Only required ports open
2. **TLS**: HTTPS on all public-facing endpoints
3. **Auth**: Token or key-based authentication on all API endpoints
4. **Rate Limiting**: Max requests per IP per minute
5. **Input Validation**: Sanitize all incoming request data
6. **Logging**: Log all access attempts with IP and timestamp
7. **IP Allowlisting**: Restrict access to known IPs if possible
8. **Reverse Proxy**: Use nginx/caddy in front of the application
9. **Process Isolation**: Run services as non-root user
10. **Updates**: Keep all services patched

## Integration

- Works with **software-advisor** to correlate service versions with CVEs
- Works with **healthcheck** for overall system security posture
