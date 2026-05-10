# browser-explore — Interactive Browser Automation

Triggered by: `/browser-explore`, `/browse`, `/e2e`

## When to use which tool

| Scenario | Tool | Why |
|---|---|---|
| Explore a page, debug UI, check state | **Playwright MCP** (`mcp__playwright__*`) | DOM-native, no screenshots, reads actual element state |
| Quick one-off navigation/screenshot | **agent-browser CLI** (`agent-browser open/click/eval`) | Zero-script startup, good for one-liners |
| Full automated E2E test suite | **Playwright test runner** (`npx playwright test`) | Assertions, retries, CI-friendly |
| AI-driven step-by-step persona test | **Playwright MCP** | Tools are discrete commands Claude calls one at a time |

## Tool 1: Playwright MCP (preferred for interactive work)

MCP server is registered as `playwright`. Claude calls these tools step by step — no script file needed.

### Core tools available

```
mcp__playwright__browser_navigate     → go to URL
mcp__playwright__browser_click        → click by selector or description
mcp__playwright__browser_type        → type into field
mcp__playwright__browser_snapshot    → get DOM accessibility tree (NOT a screenshot)
mcp__playwright__browser_evaluate   → run JS in page context, returns value
mcp__playwright__browser_console_messages → read console output
mcp__playwright__browser_network_requests → inspect XHR/fetch calls
mcp__playwright__browser_take_screenshot  → only when visual proof needed
mcp__playwright__browser_wait_for    → wait for selector or network idle
```

### Persona test pattern (DOM-first, no screenshots)

```
1. mcp__playwright__browser_navigate  url="http://localhost:8042/login"
2. mcp__playwright__browser_snapshot  → read DOM, find form fields
3. mcp__playwright__browser_type      selector="input[name=username]" text="kittu"
4. mcp__playwright__browser_click     selector="button[type=submit]"
5. mcp__playwright__browser_wait_for  selector=".dashboard" OR waitForLoadState="networkidle"
6. mcp__playwright__browser_evaluate  expression="document.title"  → assert
7. mcp__playwright__browser_console_messages → check for JS errors
```

**Never** use `browser_take_screenshot` as the primary assertion — read the DOM snapshot instead. Screenshots are for human review only.

### Console + network debugging

```
# Check for JS errors after action:
mcp__playwright__browser_console_messages

# See what API calls fired:
mcp__playwright__browser_network_requests

# Evaluate arbitrary JS:
mcp__playwright__browser_evaluate  expression="JSON.stringify(window.__SAGENT_STATE__)"
mcp__playwright__browser_evaluate  expression="document.querySelectorAll('.error').length"
```

## Tool 2: agent-browser CLI (one-liner exploration)

Good for: quick checks, opening URLs, grabbing screenshots from scripts.

```bash
# Install (one-time)
npm install -g agent-browser
agent-browser install          # downloads Chrome

# Basic commands
agent-browser open <url>       # navigate (keeps session warm)
agent-browser click <sel>      # CSS selector or natural language description
agent-browser type <sel> <text>
agent-browser eval "<js>"      # returns value
agent-browser screenshot <path>
agent-browser exists <sel>     # returns true/false
agent-browser console          # dump console messages

# Daemon mode (for many sequential commands — avoids repeated startup)
agent-browser daemon start
agent-browser open <url> --daemon
agent-browser eval "..." --daemon
agent-browser daemon stop
```

**Performance reality (measured on [host]):**
- Cold open: ~1–3s (no daemon), ~5–10s (daemon cold start)
- Warm open (no daemon): ~800ms–1.6s
- Playwright MCP navigate: ~300–800ms (session stays warm in MCP server)
- Playwright test runner cold: ~1.7s after first run

agent-browser is NOT consistently faster. Use it for ergonomics (shell scripts, one-liners), not for speed.

## Tool 3: Playwright test runner (E2E suites)

For committed test files in `portal/e2e/`:

```bash
npx playwright test portal/e2e/login.spec.ts --reporter=line
npx playwright test --ui          # interactive mode
npx playwright show-report        # open HTML report
```

Auth state is stored in `portal/e2e/.auth/` — don't re-login every test:
```typescript
// portal/e2e/dev-login.setup.ts handles auth once
// tests reuse stored state via storageState: 'portal/e2e/.auth/user.json'
```

## Combo pattern: explore with MCP, commit with test runner

```
Step 1 — Find the right selectors (MCP):
  mcp__playwright__browser_navigate + browser_snapshot

Step 2 — Verify behavior interactively (MCP):
  browser_click + browser_evaluate + browser_console_messages

Step 3 — Write the passing test (file):
  portal/e2e/<feature>.spec.ts

Step 4 — Run + commit:
  npx playwright test portal/e2e/<feature>.spec.ts
  git commit -m "test(e2e): ..."
```

## Anti-patterns

- Using `browser_take_screenshot` to "check" state → read DOM instead
- Writing a full Playwright script file for a one-off exploration → use MCP tools
- Using agent-browser in CI → use Playwright test runner
- Calling `agent-browser` inside an async FastAPI route → it's a blocking subprocess

## How this is verified at L5

```bash
# MCP server is registered
claude mcp list | grep "playwright.*Connected"

# agent-browser is installed
which agent-browser && agent-browser --version

# Playwright is present in portal
ls portal/node_modules/.bin/playwright

# At least one E2E spec exists
ls portal/e2e/*.spec.ts | wc -l  # ≥ 1
```
