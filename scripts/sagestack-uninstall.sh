#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  sagestack-uninstall.sh — remove sagent sagestack managed config only
#
#  Only removes:
#   - The managed blocks (sagestack-managed-start/end) from text config files
#   - The ~/.sagestack/ directory (after explicit confirmation)
#
#  NEVER touches user config outside managed markers.
#  NEVER removes any tool (claude, node, brew, etc.)
# ═══════════════════════════════════════════════════════════════════════════
set -euo pipefail

DRY_RUN=0
NO_CONFIRM=0
SAGESTACK_DIR="${HOME}/.sagestack"

B='\033[1m'; G='\033[0;32m'; Y='\033[1;33m'; R='\033[0;31m'; C='\033[0;36m'; N='\033[0m'
hdr()  { printf "\n${B}${C}══ %s ══${N}\n" "$*"; }
ok()   { printf "${G}  ✓ %s${N}\n" "$*"; }
skip() { printf "${Y}  ↷ %s${N}\n" "$*"; }
step() { printf "${B}  → %s${N}\n" "$*"; }
dry()  { printf "${Y}  [dry-run] %s${N}\n" "$*"; }

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)   DRY_RUN=1; shift ;;
    --yes|-y)    NO_CONFIRM=1; shift ;;
    -h|--help)
      echo "Usage: $0 [--dry-run] [--yes]"
      echo ""
      echo "  --dry-run   Show what would be removed without doing it"
      echo "  --yes/-y    Skip confirmation prompt"
      exit 0 ;;
    *) echo "Unknown flag: $1"; exit 1 ;;
  esac
done

echo ""
printf "${B}${C}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║        sagent sagestack — uninstaller                              ║"
if [[ $DRY_RUN -eq 1 ]]; then
echo "║                  *** DRY-RUN MODE ***                            ║"
fi
echo "╚══════════════════════════════════════════════════════════════════╝"
printf "${N}\n"

# ── Confirm ───────────────────────────────────────────────────────────────────
if [[ $DRY_RUN -eq 0 && $NO_CONFIRM -eq 0 ]]; then
  printf "${Y}This will remove all sagestack managed config blocks and the ~/.sagestack/ directory.${N}\n"
  printf "User config outside managed markers will NOT be touched.\n\n"
  read -r -p "Continue? [y/N] " confirm
  [[ "${confirm,,}" == "y" ]] || { echo "Aborted."; exit 0; }
fi

# ── Helper: strip managed block from a text file ──────────────────────────────
strip_managed_block() {
  local file="$1"
  if [[ ! -f "$file" ]]; then
    skip "$file not found — skipped"
    return
  fi
  if ! grep -qF "# sagestack-managed-start" "$file" 2>/dev/null; then
    skip "$file — no managed block found"
    return
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would strip managed block from $file"
    return
  fi

  python3 - "$file" <<'PYEOF'
import sys, pathlib, os

path = pathlib.Path(sys.argv[1])
start = "# sagestack-managed-start"
end   = "# sagestack-managed-end"

lines = path.read_text().splitlines(keepends=True)
out, inside = [], False
for line in lines:
    stripped = line.rstrip()
    if stripped == start:
        inside = True
    elif stripped == end:
        inside = False
    elif not inside:
        out.append(line)

# Strip trailing blank lines left by removal
while out and out[-1].strip() == "":
    out.pop()
if out:
    out.append("\n")

tmp = str(path) + ".sagestack.tmp"
pathlib.Path(tmp).write_text("".join(out))
os.replace(tmp, str(path))
print(f"  stripped managed block from {path}")
PYEOF
  ok "Stripped managed block from $file"
}

# ── Helper: remove a JSON key path from a config file ────────────────────────
remove_json_key() {
  local file="$1"
  local key_path="$2"   # dot-separated path, e.g. "mcpServers.sagent"

  if [[ ! -f "$file" ]]; then
    skip "$file not found — skipped"
    return
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would remove JSON key '$key_path' from $file"
    return
  fi

  python3 - "$file" "$key_path" <<'PYEOF'
import sys, json, os, pathlib

file_path = pathlib.Path(sys.argv[1])
key_path  = sys.argv[2].split(".")

try:
    data = json.loads(file_path.read_text())
except (json.JSONDecodeError, FileNotFoundError) as e:
    print(f"  [skip] Could not parse {file_path}: {e}", file=sys.stderr)
    sys.exit(0)

# Navigate and delete the leaf key
node = data
for k in key_path[:-1]:
    if not isinstance(node, dict) or k not in node:
        print(f"  [skip] key path '{'.'.join(key_path)}' not found — nothing to remove")
        sys.exit(0)
    node = node[k]

leaf = key_path[-1]
if leaf in node:
    del node[leaf]
    print(f"  removed key '{'.'.join(key_path)}' from {file_path}")
else:
    print(f"  [skip] key '{'.'.join(key_path)}' not present")
    sys.exit(0)

tmp = str(file_path) + ".sagestack.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, str(file_path))
PYEOF
  ok "Removed JSON key '$key_path' from $file"
}

# ── Helper: remove the PreToolUse harness hook entry from Claude settings ─────
remove_claude_hook() {
  local file="${HOME}/.claude/settings.json"
  if [[ ! -f "$file" ]]; then
    skip "~/.claude/settings.json not found"
    return
  fi

  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would remove sagestack PreToolUse hook from $file"
    return
  fi

  python3 - "$file" "${SAGESTACK_DIR}/hooks/harness_guard.sh" <<'PYEOF'
import sys, json, os, pathlib

file_path    = pathlib.Path(sys.argv[1])
harness_path = sys.argv[2]

try:
    data = json.loads(file_path.read_text())
except (json.JSONDecodeError, FileNotFoundError):
    sys.exit(0)

hooks = data.get("hooks", {})
pre_tool_use = hooks.get("PreToolUse", [])

before = len(pre_tool_use)
pre_tool_use[:] = [
    entry for entry in pre_tool_use
    if not any(h.get("command") == harness_path for h in entry.get("hooks", []))
]
after = len(pre_tool_use)

if before == after:
    print("  [skip] sagestack hook entry not found in PreToolUse")
    sys.exit(0)

hooks["PreToolUse"] = pre_tool_use
if not pre_tool_use:
    del hooks["PreToolUse"]
if not hooks:
    del data["hooks"]

tmp = str(file_path) + ".sagestack.tmp"
with open(tmp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
os.replace(tmp, str(file_path))
print(f"  removed sagestack PreToolUse hook from {file_path}")
PYEOF
  ok "Removed sagestack hook from ~/.claude/settings.json"
}

# ── 1: Text config files — strip managed blocks ───────────────────────────────
hdr "Stripping managed blocks from shell config"

for rc in "${HOME}/.zshrc" "${HOME}/.bashrc" "${HOME}/.bash_profile" "${HOME}/.profile"; do
  [[ -f "$rc" ]] && strip_managed_block "$rc" || true
done

hdr "Stripping managed blocks from Windsurf config"
strip_managed_block "${HOME}/.windsurf/rules" || true

# ── 2: JSON config files — remove sagent keys ────────────────────────────────
hdr "Removing sagent MCP entries from tool JSON configs"

remove_claude_hook

CLAUDE_SETTINGS="${HOME}/.claude/settings.json"
remove_json_key "$CLAUDE_SETTINGS" "mcpServers.sagent"

# Claude Desktop
OS="$(uname -s)"
case "$OS" in
  Darwin)
    CLAUDE_DESKTOP="${HOME}/Library/Application Support/Claude/claude_desktop_config.json"
    ;;
  Linux)
    CLAUDE_DESKTOP="${HOME}/.config/Claude/claude_desktop_config.json"
    ;;
  *)
    CLAUDE_DESKTOP=""
    ;;
esac
[[ -n "$CLAUDE_DESKTOP" ]] && remove_json_key "$CLAUDE_DESKTOP" "mcpServers.sagent" || true

# Cursor
remove_json_key "${HOME}/.cursor/mcp.json" "mcpServers.sagent" || true

# Zed
remove_json_key "${HOME}/.config/zed/settings.json" "assistant.mcp_servers.sagent" || true

# ── 3: Remove ~/.sagestack/ directory ──────────────────────────────────────────
hdr "Removing ~/.sagestack/ directory"

if [[ -d "$SAGESTACK_DIR" ]]; then
  if [[ $DRY_RUN -eq 1 ]]; then
    dry "Would remove $SAGESTACK_DIR"
  else
    step "Removing $SAGESTACK_DIR..."
    rm -rf "$SAGESTACK_DIR"
    ok "Removed $SAGESTACK_DIR"
  fi
else
  skip "$SAGESTACK_DIR not found — already clean"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ $DRY_RUN -eq 1 ]]; then
  printf "${Y}Dry-run complete — nothing was modified.${N}\n\n"
else
  printf "${G}sagestack uninstalled. Your tools and user config are untouched.${N}\n\n"
fi
