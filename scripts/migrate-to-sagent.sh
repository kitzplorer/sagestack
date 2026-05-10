#!/usr/bin/env bash
# migrate-to-sagent.sh — Upgrade from sagestack (free tier) to full sagent
set -euo pipefail

SAGENT_BACKEND="${1:-https://sagent.nishtechnologies.com}"
SETTINGS="$HOME/.claude/settings.json"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

echo "=== Migrating sagestack → sagent ==="
echo "Backend: $SAGENT_BACKEND"

# 1. Verify sagestack is installed
if [[ ! -d "$HOME/.sagestack" ]]; then
  echo "Error: ~/.sagestack not found. Install sagestack first: curl -fsSL $SAGENT_BACKEND/install.sh | bash"
  exit 1
fi

# 2. Install/detect sagent backend
if command -v sagent &>/dev/null; then
  echo "✓ sagent already installed"
else
  echo "Installing sagent backend..."
  curl -fsSL "$SAGENT_BACKEND/api/install" | bash || true
fi

# 3. Backup ~/.claude/settings.json
if [[ -f "$SETTINGS" ]]; then
  cp "$SETTINGS" "${SETTINGS}.bak.${TIMESTAMP}"
  echo "✓ Backed up settings to ${SETTINGS}.bak.${TIMESTAMP}"
fi

# 4. Update MCP: rename sagestack → sagestack-fallback, add sagent
python3 - <<PYEOF
import json, pathlib, sys
p = pathlib.Path("$SETTINGS")
if not p.exists():
    sys.exit(0)
cfg = json.loads(p.read_text())
mcp = cfg.setdefault("mcpServers", {})
# Rename sagestack entry to fallback
if "sagestack" in mcp and "sagestack-fallback" not in mcp:
    mcp["sagestack-fallback"] = mcp.pop("sagestack")
    print("✓ sagestack MCP kept as fallback")
# Add full sagent entry
mcp["sagent"] = {
    "command": "python3",
    "args": [str(pathlib.Path.home() / ".sagent" / "mcp" / "sagent-mcp.py")],
    "env": {"SAGENT_BACKEND": "$SAGENT_BACKEND"}
}
p.write_text(json.dumps(cfg, indent=2))
print("✓ sagent MCP added to settings.json")
PYEOF

# 5. Copy config
if [[ -f "$HOME/.sagestack/config.json" ]]; then
  mkdir -p "$HOME/.sagent"
  cp "$HOME/.sagestack/config.json" "$HOME/.sagent/config.json"
  echo "✓ Config carried over to ~/.sagent/"
fi

echo ""
echo "=== Migration complete ==="
echo "  sagent MCP: active"
echo "  sagestack MCP: kept as fallback"
echo "  Restart Claude Code to pick up changes."
echo ""
echo "  Open $SAGENT_BACKEND to sign in and unlock all 81 skills."
