# ═══════════════════════════════════════════════════════════════════════════
#  aistack-install.ps1 — Windows installer stub for sagent aistack
#
#  Requires: PowerShell 5.1+ or PowerShell Core 7+
#
#  Usage:
#    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#    .\aistack-install.ps1
#    .\aistack-install.ps1 -DryRun
#    .\aistack-install.ps1 -Backend "http://my-sagent:8042"
# ═══════════════════════════════════════════════════════════════════════════
param(
    [switch]$DryRun,
    [string]$Backend = "http://localhost:8042",
    [string]$WslDistro = "Ubuntu"
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Helpers ────────────────────────────────────────────────────────────────
function Write-Header($msg) {
    Write-Host "`n══ $msg ══" -ForegroundColor Cyan
}
function Write-Ok($msg) {
    Write-Host "  ✓ $msg" -ForegroundColor Green
}
function Write-Skip($msg) {
    Write-Host "  ↷ $msg" -ForegroundColor Yellow
}
function Write-Step($msg) {
    Write-Host "  → $msg" -ForegroundColor White
}
function Write-Err($msg) {
    Write-Host "  ✗ $msg" -ForegroundColor Red -BackgroundColor Black
}
function Write-Dry($msg) {
    Write-Host "  [dry-run] $msg" -ForegroundColor Yellow
}

function Invoke-Safe {
    param([scriptblock]$Block, [string]$Label = "")
    try { & $Block }
    catch { Write-Err "Failed${$(if ($Label) {" ($Label)"} else {''})}: $_" }
}

# ── Banner ─────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║       sagent aistack installer — Windows                         ║" -ForegroundColor Cyan
if ($DryRun) {
    Write-Host "║                  *** DRY-RUN MODE ***                            ║" -ForegroundColor Yellow
}
Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ── Step 1: Detect WSL2 ────────────────────────────────────────────────────
Write-Header "1/7  Detecting WSL2"

$hasWsl = $false
$wslAvailable = $false

try {
    $wslOutput = wsl --status 2>&1
    if ($LASTEXITCODE -eq 0 -or ($wslOutput -match "WSL")) {
        $wslAvailable = $true
    }
} catch {
    $wslAvailable = $false
}

# Check if the requested distro is installed
if ($wslAvailable) {
    try {
        $distros = wsl --list --quiet 2>&1
        if ($distros -match $WslDistro) {
            $hasWsl = $true
            Write-Ok "WSL2 found with distro: $WslDistro"
        } else {
            Write-Skip "WSL2 installed but distro '$WslDistro' not found. Available: $($distros -join ', ')"
        }
    } catch {
        Write-Skip "WSL2 status check failed: $_"
    }
} else {
    Write-Skip "WSL2 not detected"
}

# ── Step 2: Node.js via winget ─────────────────────────────────────────────
Write-Header "2/7  Checking Node.js"

$hasNode = $false
try {
    $nodeVersion = node --version 2>&1
    if ($LASTEXITCODE -eq 0) {
        $hasNode = $true
        Write-Ok "Node.js already installed: $nodeVersion"
    }
} catch {
    $hasNode = $false
}

if (-not $hasNode) {
    Write-Step "Installing Node.js via winget..."
    $hasWinget = $false
    try {
        winget --version | Out-Null
        $hasWinget = $true
    } catch {}

    if ($hasWinget) {
        if ($DryRun) {
            Write-Dry "winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements"
        } else {
            Invoke-Safe -Label "winget install Node.js" {
                winget install -e --id OpenJS.NodeJS.LTS `
                    --accept-source-agreements `
                    --accept-package-agreements `
                    --silent
                Write-Ok "Node.js installed via winget"
                $hasNode = $true
            }
        }
    } else {
        Write-Err "winget not found. Install Node.js manually from https://nodejs.org/en/download"
        Write-Host "  After installing, re-run this script." -ForegroundColor Yellow
    }
}

# ── Step 3: Claude Desktop MCP config ──────────────────────────────────────
Write-Header "3/7  Configuring Claude Desktop"

$claudeConfigDir = Join-Path $env:APPDATA "Claude"
$claudeConfigPath = Join-Path $claudeConfigDir "claude_desktop_config.json"

$mcpEntry = @{
    mcpServers = @{
        sagent = @{
            command = "python3"
            args    = @("$env:USERPROFILE\.aistack\mcp\sagent-mcp.py")
            env     = @{ SAGENT_BACKEND = $Backend }
        }
    }
}

if (Test-Path $claudeConfigDir) {
    if ($DryRun) {
        Write-Dry "Would merge sagent MCP entry into $claudeConfigPath"
    } else {
        # Load existing config or start fresh
        $existing = @{}
        if (Test-Path $claudeConfigPath) {
            try {
                $existing = Get-Content $claudeConfigPath -Raw | ConvertFrom-Json -AsHashtable
            } catch {
                Write-Skip "Could not parse existing config — will create fresh"
                $existing = @{}
            }
        }

        # Ensure mcpServers key exists
        if (-not $existing.ContainsKey("mcpServers")) {
            $existing["mcpServers"] = @{}
        }

        if ($existing["mcpServers"].ContainsKey("sagent")) {
            Write-Skip "sagent MCP entry already present in claude_desktop_config.json"
        } else {
            $existing["mcpServers"]["sagent"] = $mcpEntry.mcpServers.sagent

            # Atomic write via temp file
            $tmpPath = "$claudeConfigPath.aistack.tmp"
            $existing | ConvertTo-Json -Depth 10 | Set-Content -Path $tmpPath -Encoding UTF8
            Move-Item -Path $tmpPath -Destination $claudeConfigPath -Force
            Write-Ok "Claude Desktop configured: $claudeConfigPath"
        }
    }
} else {
    Write-Skip "Claude Desktop config dir not found ($claudeConfigDir)"
    Write-Host "  If you have Claude Desktop installed, re-run after it creates $claudeConfigDir" -ForegroundColor Yellow
}

# ── Step 3b: Configure VS Code (native Windows) ────────────────────────────
Write-Header "4/7  Configuring VS Code (native Windows)"

$vsCodeSettingsDir  = Join-Path $env:APPDATA "Code\User"
$vsCodeSettingsPath = Join-Path $vsCodeSettingsDir "settings.json"

if (Test-Path $vsCodeSettingsDir) {
    if ($DryRun) {
        Write-Dry "Would merge sagent MCP server into $vsCodeSettingsPath"
    } else {
        Invoke-Safe -Label "VS Code settings" {
            $vsSettings = @{}
            if (Test-Path $vsCodeSettingsPath) {
                try {
                    $vsSettings = Get-Content $vsCodeSettingsPath -Raw | ConvertFrom-Json -AsHashtable
                } catch {
                    Write-Skip "Could not parse VS Code settings.json — creating fresh merge"
                    $vsSettings = @{}
                }
            }

            # Ensure mcp.servers path exists
            if (-not $vsSettings.ContainsKey("mcp")) { $vsSettings["mcp"] = @{} }
            if (-not $vsSettings["mcp"].ContainsKey("servers")) { $vsSettings["mcp"]["servers"] = @{} }

            if ($vsSettings["mcp"]["servers"].ContainsKey("sagent")) {
                Write-Skip "sagent MCP server already present in VS Code settings.json"
            } else {
                $vsSettings["mcp"]["servers"]["sagent"] = @{
                    command = "python3"
                    args    = @("$env:USERPROFILE\.aistack\mcp\sagent-mcp.py")
                    env     = @{ SAGENT_BACKEND = $Backend }
                }

                $tmpPath = "$vsCodeSettingsPath.aistack.tmp"
                $vsSettings | ConvertTo-Json -Depth 10 | Set-Content -Path $tmpPath -Encoding UTF8
                Move-Item -Path $tmpPath -Destination $vsCodeSettingsPath -Force
                Write-Ok "VS Code configured: $vsCodeSettingsPath"
            }
        }
    }
} else {
    Write-Skip "VS Code settings dir not found ($vsCodeSettingsDir) — skipping"
}

# ── Step 3c: Configure Cursor (native Windows) ─────────────────────────────
Write-Header "5/7  Configuring Cursor (native Windows)"

$cursorConfigDir  = Join-Path $env:USERPROFILE ".cursor"
$cursorConfigPath = Join-Path $cursorConfigDir "mcp.json"

if ($DryRun) {
    Write-Dry "Would merge sagent into $cursorConfigPath"
} else {
    Invoke-Safe -Label "Cursor mcp.json" {
        # Create ~/.cursor if it doesn't exist
        if (-not (Test-Path $cursorConfigDir)) {
            New-Item -ItemType Directory -Path $cursorConfigDir -Force | Out-Null
        }

        $cursorCfg = @{}
        if (Test-Path $cursorConfigPath) {
            try {
                $cursorCfg = Get-Content $cursorConfigPath -Raw | ConvertFrom-Json -AsHashtable
            } catch {
                Write-Skip "Could not parse Cursor mcp.json — creating fresh merge"
                $cursorCfg = @{}
            }
        }

        if (-not $cursorCfg.ContainsKey("mcpServers")) { $cursorCfg["mcpServers"] = @{} }

        if ($cursorCfg["mcpServers"].ContainsKey("sagent")) {
            Write-Skip "sagent already present in Cursor mcp.json"
        } else {
            $cursorCfg["mcpServers"]["sagent"] = @{
                command = "python3"
                args    = @("$env:USERPROFILE\.aistack\mcp\sagent-mcp.py")
                env     = @{ SAGENT_BACKEND = $Backend }
            }

            $tmpPath = "$cursorConfigPath.aistack.tmp"
            $cursorCfg | ConvertTo-Json -Depth 10 | Set-Content -Path $tmpPath -Encoding UTF8
            Move-Item -Path $tmpPath -Destination $cursorConfigPath -Force
            Write-Ok "Cursor configured: $cursorConfigPath"
        }
    }
}

# ── Step 3d: Deploy Python aistack hook for Windows ────────────────────────
Write-Header "6/7  Installing Windows context_writer hook"

$hooksDir         = Join-Path $env:USERPROFILE ".aistack\hooks"
$hookScript       = Join-Path $hooksDir "context_writer.py"
$claudeSettingsDir  = Join-Path $env:USERPROFILE ".claude"
$claudeSettingsPath = Join-Path $claudeSettingsDir "settings.json"

if ($DryRun) {
    Write-Dry "Would write $hookScript and register UserPromptSubmit hook in $claudeSettingsPath"
} else {
    Invoke-Safe -Label "context_writer hook" {
        # Create hooks dir
        if (-not (Test-Path $hooksDir)) {
            New-Item -ItemType Directory -Path $hooksDir -Force | Out-Null
        }

        # Write the Python hook script (fail-open, reads stdin JSON, writes context.json)
        $hookContent = @'
#!/usr/bin/env python3
"""
aistack context_writer hook (Windows native)
Reads Claude Code UserPromptSubmit JSON from stdin,
writes %USERPROFILE%\.aistack\context.json — same schema as bash version.
Always exits 0 (fail-open).
"""
import json
import os
import sys
import tempfile
from pathlib import Path

def main():
    try:
        raw = sys.stdin.read()
        payload = json.loads(raw) if raw.strip() else {}
    except Exception:
        payload = {}

    try:
        context = {
            "prompt":     payload.get("prompt", ""),
            "session_id": payload.get("session_id", ""),
            "cwd":        payload.get("cwd", ""),
            "timestamp":  payload.get("timestamp", ""),
            "hook":       "UserPromptSubmit",
            "source":     "context_writer.py",
        }

        out_dir  = Path(os.environ.get("USERPROFILE", Path.home())) / ".aistack"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / "context.json"

        # Atomic write via temp file in same dir
        tmp = out_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(context, indent=2), encoding="utf-8")
        tmp.replace(out_path)
    except Exception:
        pass  # fail-open

    sys.exit(0)

if __name__ == "__main__":
    main()
'@
        Set-Content -Path $hookScript -Value $hookContent -Encoding UTF8
        Write-Ok "Hook written: $hookScript"

        # Register in Claude Code settings.json
        if (-not (Test-Path $claudeSettingsDir)) {
            New-Item -ItemType Directory -Path $claudeSettingsDir -Force | Out-Null
        }

        $claudeSettings = @{}
        if (Test-Path $claudeSettingsPath) {
            try {
                $claudeSettings = Get-Content $claudeSettingsPath -Raw | ConvertFrom-Json -AsHashtable
            } catch {
                Write-Skip "Could not parse Claude settings.json — creating fresh"
                $claudeSettings = @{}
            }
        }

        if (-not $claudeSettings.ContainsKey("hooks")) { $claudeSettings["hooks"] = @{} }
        if (-not $claudeSettings["hooks"].ContainsKey("UserPromptSubmit")) {
            $claudeSettings["hooks"]["UserPromptSubmit"] = @()
        }

        $hookCmd  = "python3 `"$env:USERPROFILE\.aistack\hooks\context_writer.py`""
        $existing = $claudeSettings["hooks"]["UserPromptSubmit"]
        $alreadyRegistered = $false
        foreach ($entry in $existing) {
            if ($entry -is [hashtable] -and $entry["hooks"]) {
                foreach ($h in $entry["hooks"]) {
                    if ($h -is [hashtable] -and $h["command"] -eq $hookCmd) {
                        $alreadyRegistered = $true
                        break
                    }
                }
            }
            if ($alreadyRegistered) { break }
        }

        if ($alreadyRegistered) {
            Write-Skip "context_writer hook already registered in Claude settings.json"
        } else {
            $hookEntry = @{
                matcher = ".*"
                hooks   = @(
                    @{
                        type    = "command"
                        command = $hookCmd
                    }
                )
            }
            $claudeSettings["hooks"]["UserPromptSubmit"] += $hookEntry

            $tmpPath = "$claudeSettingsPath.aistack.tmp"
            $claudeSettings | ConvertTo-Json -Depth 10 | Set-Content -Path $tmpPath -Encoding UTF8
            Move-Item -Path $tmpPath -Destination $claudeSettingsPath -Force
            Write-Ok "UserPromptSubmit hook registered in $claudeSettingsPath"
        }
    }
}

# ── Step 4: Delegate to WSL2 bash installer ─────────────────────────────────
Write-Header "7/7  Main installer (bash via WSL2)"

if ($hasWsl) {
    Write-Step "Running aistack-install.sh inside WSL2 ($WslDistro)..."

    $bashArgs = ""
    if ($DryRun) { $bashArgs += " --dry-run" }
    if ($Backend -ne "http://localhost:8042") { $bashArgs += " --backend '$Backend'" }

    $bashCmd = @"
set -euo pipefail
if command -v curl &>/dev/null; then
  bash <(curl -fsSL https://raw.githubusercontent.com/kitzplorer/sagent/main/scripts/aistack-install.sh)$bashArgs
else
  echo 'curl not found in WSL2. Install it: sudo apt-get install -y curl' >&2
  exit 1
fi
"@

    if ($DryRun) {
        Write-Dry "wsl -d $WslDistro -- bash -c '<installer script>$bashArgs'"
    } else {
        Invoke-Safe -Label "WSL2 bash installer" {
            wsl -d $WslDistro -- bash -c $bashCmd
        }
    }
    Write-Ok "WSL2 installer completed"
} else {
    # No WSL2 — print setup instructions
    Write-Host ""
    Write-Host "╔══════════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║  WSL2 is required for Claude Code on Windows.                    ║" -ForegroundColor Yellow
    Write-Host "╠══════════════════════════════════════════════════════════════════╣" -ForegroundColor Yellow
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "║  Install WSL2 (run in PowerShell as Administrator):              ║" -ForegroundColor Yellow
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "║    wsl --install                                                 ║" -ForegroundColor Cyan
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "║  Then restart your PC and re-run this installer.                 ║" -ForegroundColor Yellow
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "║  Manual WSL2 setup guide:                                        ║" -ForegroundColor Yellow
    Write-Host "║    https://learn.microsoft.com/windows/wsl/install               ║" -ForegroundColor Cyan
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "║  Once WSL2 is installed, run the bash installer directly:        ║" -ForegroundColor Yellow
    Write-Host "║    wsl -- bash <(curl -fsSL https://raw.githubusercontent.com/  ║" -ForegroundColor Cyan
    Write-Host "║      kitzplorer/sagent/main/scripts/aistack-install.sh)          ║" -ForegroundColor Cyan
    Write-Host "║                                                                  ║" -ForegroundColor Yellow
    Write-Host "╚══════════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
}

# ── Summary ────────────────────────────────────────────────────────────────
Write-Host ""
if ($DryRun) {
    Write-Host "Dry-run complete — no files were modified." -ForegroundColor Yellow
} else {
    Write-Host "aistack Windows setup complete." -ForegroundColor Green
    if ($hasWsl) {
        Write-Host "The full aistack is now configured inside WSL2 ($WslDistro)." -ForegroundColor Green
    }
}
Write-Host ""
