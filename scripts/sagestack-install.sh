#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  sagestack-install.sh — Phase 3 universal sagestack installer
#
#  Installs the sagent sagestack on any macOS 12+ or Ubuntu 22+ machine.
#  Configures Claude Code, Claude Desktop, Cursor, Windsurf, Zed, and shell.
#
#  Usage:
#    curl -fsSL https://raw.githubusercontent.com/kitzplorer/sagent/main/scripts/sagestack-install.sh | bash
#    bash sagestack-install.sh --dry-run
#    bash sagestack-install.sh --backend http://my-sagent:8042
#
#  Idempotent: re-running is safe — already-done steps are skipped.
#  Managed blocks: `# sagestack-managed-start` / `# sagestack-managed-end` markers
#  allow re-runs to update only the managed section of any file.
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

# ── Globals ────────────────────────────────────────────────────────────────
SAGESTACK_VERSION="0.1.0"
SAGESTACK_DIR="${HOME}/.sagestack"
SAGESTACK_HOOKS_DIR="${SAGESTACK_DIR}/hooks"
SAGESTACK_MCP_DIR="${SAGESTACK_DIR}/mcp"
SAGESTACK_REPO="${SAGESTACK_REPO:-https://github.com/kitzplorer/sagent}"
SAGENT_BACKEND="${SAGENT_BACKEND:-http://localhost:8042}"
DRY_RUN=0
HARNESS_GUARD_PATH="${SAGESTACK_HOOKS_DIR}/harness_guard.sh"
MCP_SCRIPT_PATH="${SAGESTACK_MCP_DIR}/sagent-mcp.py"

# ── Colours ────────────────────────────────────────────────────────────────
B='\033[1m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
hdr()  { printf "\n${B}${C}══ %s ══${N}\n" "$*"; }
ok()   { printf "${G}  ✓ %s${N}\n" "$*"; }
skip() { printf "${Y}  ↷ %s${N}\n" "$*"; }
err()  { printf "${R}  ✗ %s${N}\n" "$*" >&2; }
step() { printf "${B}  → %s${N}\n" "$*"; }
dry()  { printf "${Y}  [dry-run] %s${N}\n" "$*"; }

# ── Arg parsing ────────────────────────────────────────────────────────────
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   DRY_RUN=1; shift ;;
    --backend)   SAGENT_BACKEND="$2"; shift 2 ;;
    --repo)      SAGESTACK_REPO="$2"; shift 2 ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--backend URL] [--repo URL]"
      exit 0 ;;
    *) err "Unknown flag: $1"; exit 1 ;;
  esac
done

# ── Helpers ────────────────────────────────────────────────────────────────
run() {
  if [[ $DRY_RUN -eq 1 ]]; then
    dry "$*"
  else
    eval "$*"
  fi
}

cmd_exists() { command -v "$1" &>/dev/null; }

# Write a file atomically (tmp → mv). No-op in dry-run.
atomic_write() {
  local dest="$1"
  local content="$2"
  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would write $(echo "$content" | wc -l | tr -d ' ') lines → $dest"
    return
  fi
  local tmp="${dest}.sagestack.tmp"
  printf '%s' "$content" > "$tmp"
  mv "$tmp" "$dest"
}

# Ensure a managed block exists or is updated in a text file.
# Usage: upsert_managed_block <file> <block_content>
upsert_managed_block() {
  local file="$1"
  local block="$2"

  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would upsert managed block in $file"
    return
  fi

  local start_marker="# sagestack-managed-start"
  local end_marker="# sagestack-managed-end"

  if grep -qF "$start_marker" "$file" 2>/dev/null; then
    # Remove existing managed block then re-append
    local tmp="${file}.sagestack.tmp"
    python3 - "$file" "$start_marker" "$end_marker" <<'PYEOF'
import sys, pathlib
path, start, end = sys.argv[1], sys.argv[2], sys.argv[3]
lines = pathlib.Path(path).read_text().splitlines(keepends=True)
out, inside = [], False
for line in lines:
    if line.rstrip() == start:
        inside = True
    elif line.rstrip() == end:
        inside = False
    elif not inside:
        out.append(line)
pathlib.Path(path + ".sagestack.tmp").write_text("".join(out))
PYEOF
    mv "${file}.sagestack.tmp" "$file"
  fi

  printf '\n%s\n%s\n%s\n' "$start_marker" "$block" "$end_marker" >> "$file"
}

# Merge JSON using Python3 (safe on fresh machine — python3 is our only assumption).
# Usage: merge_json <file> <patch_json_string>
merge_json() {
  local file="$1"
  local patch="$2"

  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would merge JSON into $file"
    return
  fi

  python3 - "$file" "$patch" <<'PYEOF'
import sys, json, pathlib, copy

file_path = pathlib.Path(sys.argv[1])
patch = json.loads(sys.argv[2])

base = {}
if file_path.exists():
    try:
        base = json.loads(file_path.read_text())
    except json.JSONDecodeError:
        print(f"  [warn] Could not parse {file_path}, creating fresh copy", file=sys.stderr)

def deep_merge(target, source):
    for key, value in source.items():
        if key in target and isinstance(target[key], dict) and isinstance(value, dict):
            deep_merge(target[key], value)
        else:
            target[key] = value
    return target

merged = deep_merge(copy.deepcopy(base), patch)

tmp = str(file_path) + ".sagestack.tmp"
with open(tmp, "w") as f:
    json.dump(merged, f, indent=2)
    f.write("\n")

import os
os.replace(tmp, str(file_path))
print(f"  merged {len(patch)} top-level key(s) into {file_path}")
PYEOF
}

# ── Banner ──────────────────────────────────────────────────────────────────
echo ""
printf "${B}${C}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║        sagent sagestack installer  v${SAGESTACK_VERSION}                      ║"
if [[ $DRY_RUN -eq 1 ]]; then
echo "║                  *** DRY-RUN MODE ***                            ║"
fi
echo "╚══════════════════════════════════════════════════════════════════╝"
printf "${N}\n"

# ── Step 1: OS + arch detection ─────────────────────────────────────────────
hdr "1/10  Detecting environment"

OS="unknown"
ARCH="$(uname -m)"
case "$ARCH" in
  arm64|aarch64) ARCH="arm64" ;;
  x86_64|amd64)  ARCH="amd64" ;;
esac

case "$(uname -s)" in
  Darwin) OS="macos" ;;
  Linux)  OS="linux" ;;
  *)      err "Unsupported OS: $(uname -s)"; exit 1 ;;
esac

ok "OS: $OS  arch: $ARCH"

# ── Step 2: Tool detection ──────────────────────────────────────────────────
hdr "2/10  Detecting installed tools"

HAS_CLAUDE=0; HAS_CURSOR=0; HAS_WINDSURF=0; HAS_ZED=0; HAS_VSCODE=0
HAS_NODE=0; HAS_PYTHON3=0; HAS_BREW=0; HAS_GIT=0; HAS_GO=0

cmd_exists claude       && { HAS_CLAUDE=1;   ok "claude CLI found: $(command -v claude)"; } || skip "claude CLI not found"
cmd_exists cursor       && { HAS_CURSOR=1;   ok "cursor found"; }     || skip "cursor not found"
cmd_exists windsurf     && { HAS_WINDSURF=1; ok "windsurf found"; }   || skip "windsurf not found"
cmd_exists zed          && { HAS_ZED=1;      ok "zed found"; }        || skip "zed not found"
cmd_exists code         && { HAS_VSCODE=1;   ok "vscode (code) found"; } || skip "vscode not found"
cmd_exists node         && { HAS_NODE=1;     ok "node found: $(node --version)"; } || skip "node not found"
cmd_exists python3      && { HAS_PYTHON3=1;  ok "python3 found: $(python3 --version 2>&1)"; } || skip "python3 not found"
cmd_exists brew         && { HAS_BREW=1;     ok "brew found"; }       || skip "brew not found"
cmd_exists git          && { HAS_GIT=1;      ok "git found"; }        || skip "git not found"
cmd_exists go           && { HAS_GO=1;       ok "go found: $(go version 2>&1 | awk '{print $3}')"; } || skip "go not found"

# Also check GUI apps on macOS
if [[ "$OS" == "macos" ]]; then
  [[ -d "/Applications/Cursor.app" ]]    && { HAS_CURSOR=1;   ok "Cursor.app found"; }
  [[ -d "/Applications/Windsurf.app" ]]  && { HAS_WINDSURF=1; ok "Windsurf.app found"; }
  [[ -d "/Applications/Zed.app" ]]       && { HAS_ZED=1;      ok "Zed.app found"; }
  [[ -d "/Applications/Cursor.app" ]] || [[ -d "$HOME/Applications/Cursor.app" ]] && HAS_CURSOR=1
fi

# python3 is hard-required after this point
if [[ $HAS_PYTHON3 -eq 0 ]]; then
  err "python3 is required but not found. Install it and re-run."
  exit 1
fi

# ── Step 3: Install dependencies ─────────────────────────────────────────────
hdr "3/10  Installing missing dependencies"

# Homebrew (macOS only)
if [[ "$OS" == "macos" && $HAS_BREW -eq 0 ]]; then
  step "Installing Homebrew..."
  run '/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
  # shellcheck disable=SC1091
  [[ -f "/opt/homebrew/bin/brew" ]] && eval "$(/opt/homebrew/bin/brew shellenv)" || true
  [[ -f "/usr/local/bin/brew" ]]    && eval "$(/usr/local/bin/brew shellenv)"    || true
  cmd_exists brew && { HAS_BREW=1; ok "Homebrew installed"; } || err "Homebrew install failed — continuing"
fi

# Node.js
if [[ $HAS_NODE -eq 0 ]]; then
  step "Installing Node.js..."
  if [[ "$OS" == "macos" && $HAS_BREW -eq 1 ]]; then
    run "brew install node" && { HAS_NODE=1; ok "Node.js installed via brew"; } || err "brew install node failed"
  elif [[ "$OS" == "linux" ]]; then
    # Use NodeSource LTS installer — works on Ubuntu/Debian without nvm
    run "curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash - && sudo apt-get install -y nodejs" \
      && { HAS_NODE=1; ok "Node.js installed via NodeSource"; } \
      || err "Node.js install failed — npm steps will be skipped"
  else
    err "Cannot install Node.js automatically on this platform. Install it manually and re-run."
  fi
fi

# git (needed for cloning hooks)
if [[ $HAS_GIT -eq 0 ]]; then
  step "Installing git..."
  if [[ "$OS" == "macos" && $HAS_BREW -eq 1 ]]; then
    run "brew install git" && { HAS_GIT=1; ok "git installed"; } || err "git install failed"
  elif [[ "$OS" == "linux" ]]; then
    run "sudo apt-get install -y git" && { HAS_GIT=1; ok "git installed"; } || err "git install failed"
  fi
fi

# ── Step 4: Install paseo ────────────────────────────────────────────────────
hdr "4/10  Installing paseo"

if [[ $HAS_NODE -eq 1 ]]; then
  if cmd_exists paseo; then
    skip "paseo already installed: $(paseo --version 2>/dev/null || echo 'unknown version')"
  else
    step "npm install -g @getpaseo/cli..."
    run "npm install -g @getpaseo/cli" && ok "paseo installed" || err "paseo install failed — non-fatal, continuing"
  fi
else
  skip "Node.js not available — skipping paseo install"
fi

# ── Step 5: Download claude-code-harness binary ─────────────────────────────
hdr "5/10  claude-code-harness binary"

HARNESS_BIN="${SAGESTACK_DIR}/bin/harness_guard"
if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "${SAGESTACK_DIR}/bin"
fi

if [[ -f "$HARNESS_BIN" ]]; then
  skip "harness_guard binary already present at $HARNESS_BIN"
else
  # Try GitHub releases first
  HARNESS_RELEASE_URL="${SAGESTACK_REPO}/releases/latest/download/harness_guard-${OS}-${ARCH}"
  step "Attempting download from GitHub releases..."
  if run "curl -fsSL -o '${HARNESS_BIN}.tmp' '${HARNESS_RELEASE_URL}' && mv '${HARNESS_BIN}.tmp' '${HARNESS_BIN}' && chmod +x '${HARNESS_BIN}'" 2>/dev/null; then
    ok "harness_guard downloaded from releases"
  elif [[ $HAS_GO -eq 1 ]]; then
    step "Binary not found in releases — building from source with go..."
    HARNESS_SRC="${SAGESTACK_DIR}/src/harness_guard"
    if [[ $DRY_RUN -eq 0 ]]; then mkdir -p "$HARNESS_SRC"; fi
    # Write a minimal harness guard in Go if no source exists yet
    if [[ ! -f "${HARNESS_SRC}/main.go" && $DRY_RUN -eq 0 ]]; then
      cat > "${HARNESS_SRC}/main.go" <<'GOEOF'
// harness_guard — minimal stub. Replace with full source from sagestack repo.
package main

import (
	"fmt"
	"os"
)

func main() {
	// Exit 0 to not block tool calls until the real binary is deployed
	fmt.Fprintln(os.Stderr, "[harness_guard] stub — replace with full binary from "+
		"https://github.com/kitzplorer/sagent/releases")
	os.Exit(0)
}
GOEOF
    fi
    run "cd '${HARNESS_SRC}' && go mod init harness_guard 2>/dev/null; go build -o '${HARNESS_BIN}' ." \
      && ok "harness_guard built from source" \
      || err "Go build failed — guard binary skipped"
  else
    err "Could not obtain harness_guard binary (no releases + no go compiler). The hook will use the shell script fallback."
  fi
fi

# ── Step 6: Deploy hooks ─────────────────────────────────────────────────────
hdr "6/10  Deploying sagestack hooks"

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$SAGESTACK_HOOKS_DIR"
fi

# Write harness_guard.sh shell fallback
HARNESS_SH_CONTENT='#!/usr/bin/env bash
# harness_guard.sh — sagent sagestack pre-tool-use hook (shell fallback)
# Delegates to binary if available, else exits 0 (fail-open).
BINARY="${HOME}/.sagestack/bin/harness_guard"
if [[ -x "$BINARY" ]]; then
  exec "$BINARY" "$@"
fi
# Shell fallback: log the tool call and exit 0 (do not block)
LOGFILE="${HOME}/.sagestack/harness.log"
echo "$(date -Iseconds) tool_call tool=${TOOL_NAME:-unknown}" >> "$LOGFILE" 2>/dev/null || true
exit 0
'

if [[ -f "$HARNESS_GUARD_PATH" ]]; then
  skip "harness_guard.sh already present"
else
  atomic_write "$HARNESS_GUARD_PATH" "$HARNESS_SH_CONTENT"
  if [[ $DRY_RUN -eq 0 ]]; then chmod +x "$HARNESS_GUARD_PATH"; fi
  ok "harness_guard.sh deployed"
fi

# ── Step 7: Deploy sagent-mcp.py ─────────────────────────────────────────────
hdr "7/10  Deploying sagent-mcp.py"

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "$SAGESTACK_MCP_DIR"
fi

MCP_CONTENT='#!/usr/bin/env python3
"""
sagent-mcp.py — MCP stdio bridge for the sagent backend.
Proxies JSON-RPC MCP requests to SAGENT_BACKEND over HTTP.
"""
import os, sys, json, urllib.request, urllib.error

BACKEND = os.environ.get("SAGENT_BACKEND", "http://localhost:8042")
MCP_ENDPOINT = f"{BACKEND}/api/sagent/mcp"


def send_request(payload: dict) -> dict:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        MCP_ENDPOINT,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.URLError as e:
        return {"jsonrpc": "2.0", "id": payload.get("id"), "error": {"code": -32000, "message": str(e)}}


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as e:
            result = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": f"Parse error: {e}"}}
        else:
            result = send_request(payload)
        print(json.dumps(result), flush=True)


if __name__ == "__main__":
    main()
'

if [[ -f "$MCP_SCRIPT_PATH" ]]; then
  skip "sagent-mcp.py already present"
else
  atomic_write "$MCP_SCRIPT_PATH" "$MCP_CONTENT"
  if [[ $DRY_RUN -eq 0 ]]; then chmod +x "$MCP_SCRIPT_PATH"; fi
  ok "sagent-mcp.py deployed"
fi

# ── Step 8: Configure tools ──────────────────────────────────────────────────
hdr "8/10  Configuring tools"

# ── 8a: Claude Code — settings.json ─────────────────────────────────────────
CLAUDE_SETTINGS="${HOME}/.claude/settings.json"

merge_claude_code_settings() {
  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would merge Claude Code settings into $CLAUDE_SETTINGS"
    return
  fi

  mkdir -p "$(dirname "$CLAUDE_SETTINGS")"
  [[ -f "$CLAUDE_SETTINGS" ]] || echo '{}' > "$CLAUDE_SETTINGS"

  python3 - "$CLAUDE_SETTINGS" "$HARNESS_GUARD_PATH" "$MCP_SCRIPT_PATH" "$SAGENT_BACKEND" <<'PYEOF'
import sys, json, os, copy

settings_path = sys.argv[1]
harness_path  = sys.argv[2]
mcp_path      = sys.argv[3]
backend       = sys.argv[4]

try:
    settings = json.loads(open(settings_path).read())
except (json.JSONDecodeError, FileNotFoundError):
    settings = {}

# ── Merge PreToolUse hook ──
hooks = settings.setdefault("hooks", {})
pre_tool_use = hooks.setdefault("PreToolUse", [])

hook_entry = {
    "matcher": "Bash|Write|Edit",
    "hooks": [{"type": "command", "command": harness_path}]
}

already_has_hook = any(
    any(h.get("command") == harness_path for h in entry.get("hooks", []))
    for entry in pre_tool_use
    if isinstance(entry, dict)
)

if not already_has_hook:
    pre_tool_use.append(hook_entry)
    print("  added PreToolUse hook entry")
else:
    print("  PreToolUse hook already present — skipped")

# ── Merge MCP server ──
mcp_servers = settings.setdefault("mcpServers", {})

if "sagent" not in mcp_servers:
    mcp_servers["sagent"] = {
        "command": "python3",
        "args": [mcp_path],
        "env": {"SAGENT_BACKEND": backend}
    }
    print("  added sagent MCP server")
else:
    print("  sagent MCP server already present — skipped")

# Atomic write
tmp = settings_path + ".sagestack.tmp"
with open(tmp, "w") as f:
    json.dump(settings, f, indent=2)
    f.write("\n")
os.replace(tmp, settings_path)
print(f"  wrote {settings_path}")
PYEOF
}

if [[ $HAS_CLAUDE -eq 1 ]] || [[ -d "${HOME}/.claude" ]]; then
  step "Merging Claude Code settings..."
  merge_claude_code_settings && ok "Claude Code configured"
else
  skip "Claude Code not found — skipping settings merge"
fi

# ── 8b: Claude Desktop — claude_desktop_config.json ─────────────────────────
configure_claude_desktop() {
  local cfg_path="$1"
  if [[ ! -f "$cfg_path" && $DRY_RUN -eq 0 ]]; then
    mkdir -p "$(dirname "$cfg_path")"
    echo '{}' > "$cfg_path"
  fi

  local patch
  patch=$(python3 -c "
import json, sys
p = {
  'mcpServers': {
    'sagent': {
      'command': 'python3',
      'args': ['${MCP_SCRIPT_PATH}'],
      'env': {'SAGENT_BACKEND': '${SAGENT_BACKEND}'}
    }
  }
}
print(json.dumps(p))
")
  merge_json "$cfg_path" "$patch"
  ok "Claude Desktop configured: $cfg_path"
}

if [[ "$OS" == "macos" ]]; then
  CLAUDE_DESKTOP_CFG="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
  if [[ -d "${HOME}/Library/Application Support/Claude" ]] || [[ $DRY_RUN -eq 1 ]]; then
    step "Configuring Claude Desktop..."
    configure_claude_desktop "$CLAUDE_DESKTOP_CFG"
  else
    skip "Claude Desktop app not found (~/Library/Application Support/Claude missing)"
  fi
elif [[ "$OS" == "linux" ]]; then
  CLAUDE_DESKTOP_CFG="${HOME}/.config/Claude/claude_desktop_config.json"
  if [[ -d "${HOME}/.config/Claude" ]] || [[ $DRY_RUN -eq 1 ]]; then
    step "Configuring Claude Desktop (Linux)..."
    configure_claude_desktop "$CLAUDE_DESKTOP_CFG"
  else
    skip "Claude Desktop (Linux) config dir not found"
  fi
fi

# ── 8c: Cursor — mcp.json ────────────────────────────────────────────────────
configure_cursor() {
  local cursor_cfg="${HOME}/.cursor/mcp.json"
  if [[ $DRY_RUN -eq 0 ]]; then mkdir -p "${HOME}/.cursor"; fi

  local patch
  patch=$(python3 -c "
import json
p = {
  'mcpServers': {
    'sagent': {
      'command': 'python3',
      'args': ['${MCP_SCRIPT_PATH}'],
      'env': {'SAGENT_BACKEND': '${SAGENT_BACKEND}'}
    }
  }
}
print(json.dumps(p))
")
  merge_json "$cursor_cfg" "$patch"
  ok "Cursor configured: $cursor_cfg"
}

if [[ $HAS_CURSOR -eq 1 ]]; then
  step "Configuring Cursor..."
  configure_cursor
else
  skip "Cursor not found"
fi

# ── 8d: Windsurf — .windsurfrules ────────────────────────────────────────────
if [[ $HAS_WINDSURF -eq 1 ]]; then
  step "Configuring Windsurf..."
  WINDSURF_RULES_DIR="${HOME}/.windsurf"
  WINDSURF_RULES="${WINDSURF_RULES_DIR}/rules"
  if [[ $DRY_RUN -eq 0 ]]; then mkdir -p "$WINDSURF_RULES_DIR"; fi

  WINDSURF_BLOCK="# sagent MCP bridge
mcp_server sagent python3 ${MCP_SCRIPT_PATH}
env SAGENT_BACKEND=${SAGENT_BACKEND}"

  if [[ -f "$WINDSURF_RULES" ]] && grep -qF "sagestack-managed-start" "$WINDSURF_RULES" 2>/dev/null; then
    skip "Windsurf rules managed block already present"
  else
    upsert_managed_block "$WINDSURF_RULES" "$WINDSURF_BLOCK"
    ok "Windsurf .windsurfrules updated"
  fi
else
  skip "Windsurf not found"
fi

# ── 8e: Zed — settings.json ──────────────────────────────────────────────────
configure_zed() {
  local zed_cfg="${HOME}/.config/zed/settings.json"
  if [[ $DRY_RUN -eq 0 ]]; then mkdir -p "${HOME}/.config/zed"; fi

  local patch
  patch=$(python3 -c "
import json
p = {
  'assistant': {
    'mcp_servers': {
      'sagent': {
        'command': 'python3',
        'args': ['${MCP_SCRIPT_PATH}'],
        'env': {'SAGENT_BACKEND': '${SAGENT_BACKEND}'}
      }
    }
  }
}
print(json.dumps(p))
")
  merge_json "$zed_cfg" "$patch"
  ok "Zed configured: $zed_cfg"
}

if [[ $HAS_ZED -eq 1 ]]; then
  step "Configuring Zed..."
  configure_zed
else
  skip "Zed not found"
fi

# ── 8f: Shell — ~/.zshrc ─────────────────────────────────────────────────────
configure_shell() {
  local rc_file="$1"
  if [[ ! -f "$rc_file" && $DRY_RUN -eq 0 ]]; then touch "$rc_file"; fi

  local shell_block="export SAGESTACK_DIR=\"\${HOME}/.sagestack\"
export PATH=\"\${SAGESTACK_DIR}/bin:\${PATH}\"
export SAGENT_BACKEND=\"${SAGENT_BACKEND}\""

  if grep -qF "sagestack-managed-start" "$rc_file" 2>/dev/null; then
    skip "Shell managed block already in $rc_file — updating..."
  fi
  upsert_managed_block "$rc_file" "$shell_block"
  ok "Shell configured: $rc_file"
}

SHELL_RC=""
if [[ -n "${ZSH_VERSION:-}" ]] || [[ "$SHELL" == */zsh ]]; then
  SHELL_RC="${HOME}/.zshrc"
elif [[ -n "${BASH_VERSION:-}" ]] || [[ "$SHELL" == */bash ]]; then
  SHELL_RC="${HOME}/.bashrc"
fi

if [[ -n "$SHELL_RC" ]]; then
  step "Configuring shell ($SHELL_RC)..."
  configure_shell "$SHELL_RC"
else
  skip "Shell not detected (not zsh or bash) — skipping shell config"
fi

# ── Step 9: Initialize ~/.sagestack/ structure ──────────────────────────────────
hdr "9/10  Initializing ~/.sagestack/ directory structure"

if [[ $DRY_RUN -eq 0 ]]; then
  mkdir -p "${SAGESTACK_DIR}/bin" "${SAGESTACK_DIR}/hooks" "${SAGESTACK_DIR}/mcp" \
            "${SAGESTACK_DIR}/logs" "${SAGESTACK_DIR}/data"
fi

# signals.db stub (SQLite)
SIGNALS_DB="${SAGESTACK_DIR}/data/signals.db"
if [[ ! -f "$SIGNALS_DB" ]]; then
  if [[ $DRY_RUN -eq 0 ]]; then
    python3 -c "
import sqlite3, pathlib
db = sqlite3.connect('${SIGNALS_DB}')
db.execute('''CREATE TABLE IF NOT EXISTS signals (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (datetime(\"now\")),
  source TEXT,
  event TEXT,
  payload TEXT
)''')
db.commit()
db.close()
print('  signals.db initialised')
"
  else
    dry "Would create signals.db at $SIGNALS_DB"
  fi
  ok "signals.db created"
else
  skip "signals.db already exists"
fi

# context.json stub
CONTEXT_JSON="${SAGESTACK_DIR}/context.json"
if [[ ! -f "$CONTEXT_JSON" ]]; then
  CONTEXT_CONTENT=$(python3 -c "
import json, datetime
print(json.dumps({
  'version': '${SAGESTACK_VERSION}',
  'installed_at': datetime.datetime.utcnow().isoformat() + 'Z',
  'backend': '${SAGENT_BACKEND}',
  'os': '${OS}',
  'arch': '${ARCH}'
}, indent=2))
")
  atomic_write "$CONTEXT_JSON" "$CONTEXT_CONTENT"
  ok "context.json created"
else
  skip "context.json already exists"
fi

# Version file
VERSION_CONTENT="SAGESTACK_VERSION=${SAGESTACK_VERSION}
INSTALLED_AT=$(date -u +%Y-%m-%dT%H:%M:%SZ)
OS=${OS}
ARCH=${ARCH}
SAGENT_BACKEND=${SAGENT_BACKEND}
"
atomic_write "${SAGESTACK_DIR}/.version" "$VERSION_CONTENT"
ok ".version written"

# ── Step 10: Summary ─────────────────────────────────────────────────────────
hdr "10/10  Installation summary"

echo ""
printf "${B}Installed:${N}\n"
printf "  ${G}~/.sagestack/${N}                     sagestack home directory\n"
printf "  ${G}%s${N}  MCP bridge\n" "$MCP_SCRIPT_PATH"
printf "  ${G}%s${N}  pre-tool hook\n" "$HARNESS_GUARD_PATH"

echo ""
printf "${B}Configured:${N}\n"
[[ $HAS_CLAUDE -eq 1 ]] || [[ -d "${HOME}/.claude" ]] && printf "  ${G}Claude Code${N}  (%s)\n" "$CLAUDE_SETTINGS"
[[ "$OS" == "macos" ]] && printf "  ${G}Claude Desktop${N}\n"
[[ $HAS_CURSOR -eq 1 ]]   && printf "  ${G}Cursor${N}\n"
[[ $HAS_WINDSURF -eq 1 ]] && printf "  ${G}Windsurf${N}\n"
[[ $HAS_ZED -eq 1 ]]      && printf "  ${G}Zed${N}\n"
[[ -n "$SHELL_RC" ]]       && printf "  ${G}Shell${N}  (%s)\n" "$SHELL_RC"

echo ""
printf "${B}Next steps:${N}\n"
printf "  1. Reload your shell:  ${C}source %s${N}\n" "${SHELL_RC:-~/.zshrc}"
printf "  2. Verify:             ${C}cat ~/.sagestack/.version${N}\n"
printf "  3. Start backend:      ${C}cd ~/projects/sagent/services && python3 -m uvicorn code_agent.server:app --host 0.0.0.0 --port 8042${N}\n"
printf "  4. Uninstall:          ${C}bash sagestack-uninstall.sh${N}\n"
echo ""

if [[ $DRY_RUN -eq 1 ]]; then
  printf "${Y}Dry-run complete — no files were modified.${N}\n\n"
else
  printf "${G}sagestack v${SAGESTACK_VERSION} installed successfully.${N}\n\n"
fi
