---
name: Frontend Helper
version: 1.0.0
description: "Frontend error translator and learning companion. Parses terminal/build output, identifies errors in plain English, and suggests fixes. Focused on Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS. Use when debugging frontend build errors, hydration issues, TypeScript errors, or asking frontend questions."
---
# Frontend Helper

Personal frontend error translator and learning companion.
Parses terminal/build output, identifies errors in plain English,
suggests fixes, and connects to LLM for deeper questions.

Focused on: Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS.

## Usage

```bash
# Paste terminal output, get help
python3 skills/frontend-helper/scripts/frontend_helper.py paste

# Ask a frontend question
python3 skills/frontend-helper/scripts/frontend_helper.py ask "what is hydration?"

# Scan a project for common issues
python3 skills/frontend-helper/scripts/frontend_helper.py scan /path/to/project

# Interactive mode (chat + paste)
python3 skills/frontend-helper/scripts/frontend_helper.py interactive
```

## Common Error Patterns

### Next.js Hydration Mismatch

```
Error: Hydration failed because the initial UI does not match what was rendered on the server.
```

**Fix**: Ensure server and client render identically. Common causes:
- Using `Math.random()` or `Date.now()` without `useMemo`
- Browser-only APIs (`window`, `localStorage`) accessed during SSR
- Conditional rendering based on `typeof window !== 'undefined'`

Solution: Use `useEffect` for client-only code, or `suppressHydrationWarning` for known mismatches.

### TypeScript Strict Mode Errors

```
Type 'string | undefined' is not assignable to type 'string'
```

**Fix**: Use optional chaining (`?.`), nullish coalescing (`??`), or add explicit type guards.

### React 18 Hook Rules

```
React Hook "useXxx" cannot be called inside a callback
```

**Fix**: Hooks must be called at the top level of a React function component, not inside callbacks, loops, or conditions.

### Next.js App Router: Server vs Client Components

- Default: Server Components (can't use hooks, browser APIs)
- Add `'use client'` directive at top of file to use hooks
- Don't import server-only code into client components

## Events Published

- `frontend.error.identified` — error parsed with fix suggestion
- `frontend.question.asked` — question routed to LLM
