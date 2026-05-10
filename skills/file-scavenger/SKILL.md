---
version: 1.0.0
name: file-scavenger
description: "Discovers obsolete, unused, and uninteracted files across the system or project. Identifies abandoned downloads, stale cache files, orphaned configs, unused dependencies, and forgotten temp files. Shows clear descriptions of what each file is and lets you decide what to do. Use when the user wants to clean up their system, find old files, or identify what can be safely removed."
metadata: { "openclaw": { "emoji": "🗑️", "os": ["darwin", "linux"] } }
---

# File Scavenger

Intelligent file discovery tool that finds obsolete, unused, and forgotten files across your system or projects. Unlike blind cleanup tools, it explains what each file is, why it thinks it's obsolete, and lets you decide what to do.

## Core Rules

- NEVER delete files automatically. Always present findings and ask what to do.
- For every file found, provide: path, size, last accessed date, what it is, and why it may be obsolete.
- Group findings by category for easier decision-making.
- Calculate total reclaimable space per category.
- Support dry-run mode (default) and interactive cleanup mode.
- Respect .gitignore patterns and never flag tracked git files as obsolete.

## Workflow

### 1. System-Wide Scan

Scan common locations for obsolete files:

```bash
bash skills/file-scavenger/scripts/system_scan.sh
```

Scans these locations:

**Downloads Folder:**

- Files not accessed in 90+ days
- Duplicate downloads (same name with (1), (2) suffixes)
- Installer files (.dmg, .pkg, .exe, .msi) already installed
- Archive files (.zip, .tar.gz, .rar) that were extracted

**Cache & Temp:**

- Browser caches over 1GB
- Package manager caches (npm, pip, brew, apt)
- Build caches (node_modules/.cache, **pycache**, .gradle)
- OS temp files older than 30 days
- Xcode derived data (macOS)

**Developer Artifacts:**

- Orphaned node_modules in abandoned projects
- Stale virtual environments (venv, .venv)
- Old Docker images and volumes
- Unused Homebrew formulas
- Stale git branches (local only, merged)

**Config Files:**

- Configs for uninstalled applications
- Duplicate/conflicting dotfiles
- Orphaned .env files in abandoned projects

### 2. Project Scan

Scan a specific project for cleanup opportunities:

```bash
bash skills/file-scavenger/scripts/project_scan.sh [project_path]
```

Without a path, scans the current directory. Finds:

**Unused Dependencies:**

- npm packages in package.json but not imported anywhere
- Python packages in requirements.txt but not imported
- Unused dev dependencies

**Dead Code Files:**

- Source files not imported/required by any other file
- Test files for deleted source files
- Stale migration files (if using a framework)

**Build Artifacts:**

- dist/ or build/ folders from old builds
- Source maps in production
- Coverage reports
- Old bundle analysis files

**Documentation:**

- Outdated README references to deleted files
- Stale TODO/FIXME comments older than 6 months
- Orphaned documentation for removed features

### 3. Interactive Cleanup

Run the scavenger in interactive mode:

```bash
bash skills/file-scavenger/scripts/interactive_cleanup.sh [path]
```

For each finding, presents:

```
┌─────────────────────────────────────────────────────┐
│ 📁 File: ~/Downloads/installer-v2.3.1.dmg          │
│ 📊 Size: 245 MB                                     │
│ 📅 Last Accessed: 2025-08-15 (198 days ago)         │
│ 🏷️  Category: Installer (already installed)          │
│                                                      │
│ ℹ️  This is a macOS installer package for AppName    │
│    v2.3.1. The app is currently installed at         │
│    /Applications/AppName.app (v2.3.1), so this       │
│    installer is no longer needed.                    │
│                                                      │
│ What would you like to do?                           │
│ 1) Delete                                            │
│ 2) Move to Trash                                     │
│ 3) Skip                                              │
│ 4) Skip all in this category                        │
└─────────────────────────────────────────────────────┘
```

### 4. Continuous Monitoring

Schedule periodic scans to prevent file accumulation:

```bash
# Weekly system scan
openclaw cron add --name "file-scavenger:weekly-scan" \
  --schedule "0 10 * * 6" \
  --command "bash skills/file-scavenger/scripts/system_scan.sh --quiet"
```

## Report Format

```
═══════════════════════════════════════════
  FILE SCAVENGER REPORT
  Scanned: /Users/username | YYYY-MM-DD
═══════════════════════════════════════════

SUMMARY
  Files Found: 847
  Total Reclaimable: 23.4 GB
  Categories: 6

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 DOWNLOADS (12.1 GB reclaimable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Installers (Already Installed) — 4.2 GB
  ├─ installer-v2.3.1.dmg         245 MB  198 days  macOS installer, app installed
  ├─ setup-3.0.exe                180 MB  342 days  Windows installer (wrong OS)
  └─ ... (8 more files)

  Extracted Archives — 3.1 GB
  ├─ project-backup.zip           1.2 GB  90 days   ZIP, extracted to ./project-backup/
  ├─ dataset-2024.tar.gz          900 MB  156 days  Tarball, contents in ./dataset/
  └─ ... (5 more files)

  Old Downloads — 4.8 GB
  ├─ report-draft-v1.pdf          2.3 MB  280 days  PDF document, untouched
  ├─ photo-dump.zip               1.5 GB  365 days  Not accessed in a year
  └─ ... (42 more files)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗂️  DEVELOPER ARTIFACTS (8.7 GB reclaimable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Orphaned node_modules — 6.2 GB
  ├─ ~/old-project/node_modules/        1.8 GB  No package.json changes in 8 months
  ├─ ~/experiments/test-app/node_modules/ 900 MB  Project has no recent git commits
  └─ ... (4 more directories)

  Stale Virtual Environments — 1.5 GB
  ├─ ~/projects/ml-test/.venv/    800 MB  Last activated 6 months ago
  └─ ~/scripts/.venv/             700 MB  No Python files in parent directory

  Docker Artifacts — 1.0 GB
  ├─ 5 dangling images            600 MB  Not referenced by any container
  └─ 3 unused volumes             400 MB  No container attached

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚙️  CACHE & TEMP (2.6 GB reclaimable)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Package Manager Caches — 1.8 GB
  ├─ npm cache                    800 MB  Safe to clear (npm cache clean)
  ├─ pip cache                    500 MB  Safe to clear (pip cache purge)
  └─ brew cache                   500 MB  Safe to clear (brew cleanup)

  Build Caches — 800 MB
  ├─ Xcode DerivedData            500 MB  Can be rebuilt
  └─ Gradle cache                 300 MB  Can be rebuilt

ACTIONS AVAILABLE
  1) Review each file interactively
  2) Auto-delete files older than [N] days
  3) Delete by category
  4) Export list to CSV for review
  5) Skip (no changes)
═══════════════════════════════════════════
```

## File Identification

The scavenger identifies files using multiple signals:

1. **File extension** → What type of file (installer, archive, document, code)
2. **File header/magic bytes** → Actual content type verification
3. **Parent directory** → Context (Downloads, node_modules, cache, temp)
4. **Last access time** → How long since anyone used it
5. **Last modification time** → How long since it was changed
6. **Associated application** → Is the parent app still installed?
7. **Git status** → Is it tracked, ignored, or orphaned?
8. **Import analysis** → For code: is it referenced by other files?
9. **Size** → Prioritize large files for maximum space recovery

## Safety Guarantees

- **Never deletes without asking**. Every action requires explicit user approval.
- **Trash over delete**. Default action moves to Trash/Recycle Bin (recoverable).
- **Skip active projects**. Projects with recent git commits or file modifications are marked safe.
- **Respect .gitignore**. Tracked files are never flagged.
- **Explain everything**. Every file gets a human-readable explanation of what it is and why it was flagged.
- **Dry-run default**. The scavenger always starts in report mode, never cleanup mode.
