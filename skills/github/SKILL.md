---
version: 1.0.0
name: github
description: "Interact with GitHub using the `gh` CLI. Use `gh issue`, `gh pr`, `gh run`, and `gh api` for issues, PRs, CI runs, and advanced queries."
---

# GitHub Skill

Use the `gh` CLI to interact with GitHub. Always specify `--repo owner/repo` when not in a git directory, or use URLs directly.

## Install

```bash
brew install gh    # macOS
# or: apt install gh (Debian/Ubuntu)
gh auth login
```

## Pull Requests

```bash
# Check CI status on a PR
gh pr checks 55 --repo owner/repo

# List recent workflow runs
gh run list --repo owner/repo --limit 10

# View a run and see which steps failed
gh run view <run-id> --repo owner/repo

# View logs for failed steps only
gh run view <run-id> --repo owner/repo --log-failed

# Create a PR
gh pr create --title "feat: add thing" --body "$(cat <<'EOF'
## Summary
- Added thing

## Test plan
- [ ] Run tests
EOF
)"

# Merge a PR
gh pr merge 55 --squash --delete-branch
```

## Issues

```bash
# List open issues
gh issue list --repo owner/repo --label bug

# Create an issue
gh issue create --title "Bug: ..." --body "Steps to reproduce..."

# Close an issue
gh issue close 42 --comment "Fixed in #55"
```

## API for Advanced Queries

```bash
# Get PR with specific fields
gh api repos/owner/repo/pulls/55 --jq '.title, .state, .user.login'

# List PR review comments
gh api repos/owner/repo/pulls/55/comments --jq '.[].body'
```

## JSON Output

Most commands support `--json` for structured output with `--jq` filtering:

```bash
gh issue list --repo owner/repo --json number,title --jq '.[] | "\(.number): \(.title)"'
gh pr list --json number,title,headRefName --jq '.[] | select(.headRefName | startswith("feat/"))'
```

## Common workflows

```bash
# See what's failing in CI for current branch
gh run list --branch $(git branch --show-current) --limit 5
gh run view $(gh run list --branch $(git branch --show-current) --limit 1 --json databaseId --jq '.[0].databaseId') --log-failed

# Check if PR is mergeable
gh pr view --json mergeable,mergeStateStatus
```
