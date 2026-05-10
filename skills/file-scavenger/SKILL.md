---
version: 1.0.0
name: file-scavenger
description: "Discovers obsolete, unused, and uninteracted files across the system or project. Identifies abandoned downloads, stale cache files, orphaned configs, unused dependencies, and forgotten temp files. Shows clear descriptions of what each file is and lets you decide what to do. Use when the user wants to clean up their system, find old files, or identify what can be safely removed."
---

# File Scavenger

Intelligent file discovery tool that finds obsolete, unused, and forgotten files.
Unlike blind cleanup tools, it explains what each file is, why it may be obsolete,
and lets you decide what to do.

## Core Rules

- NEVER delete files automatically. Always present findings and ask what to do.
- For every file: path, size, last accessed date, what it is, why it may be obsolete.
- Group findings by category for easier decision-making.
- Calculate total reclaimable space per category.
- Support dry-run mode (default) and interactive cleanup mode.
- Respect .gitignore patterns and never flag tracked git files as obsolete.

## Workflow

### 1. System-Wide Scan

```bash
bash skills/file-scavenger/scripts/system_scan.sh
```

Finds:
- **Downloads**: Files not accessed in 90+ days, duplicate downloads, installer .dmg/.pkg already installed, extracted archives
- **Cache & Temp**: Browser caches over 1GB, npm/pip/brew caches, build caches (`node_modules/.cache`, `__pycache__`), Xcode derived data
- **Developer Artifacts**: Orphaned `node_modules`, stale virtual environments, old Docker images, unused Homebrew formulas, stale local git branches
- **Config Files**: Configs for uninstalled applications, orphaned `.env` files

### 2. Project Scan

```bash
bash skills/file-scavenger/scripts/project_scan.sh [project_path]
```

Finds:
- **Unused Dependencies**: npm packages in package.json but not imported; Python packages in requirements.txt but not imported
- **Dead Code Files**: Source files not imported by any other file; test files for deleted source files
- **Build Artifacts**: Old `dist/`, `build/`, coverage reports, bundle analysis files
- **Documentation**: Outdated README references to deleted files; orphaned docs for removed features

### 3. Interactive Cleanup

```bash
bash skills/file-scavenger/scripts/interactive_cleanup.sh
```

Walks through each finding and asks: keep / delete / move to archive.

## Output Format

```
═══════════════════════════════════
  FILE SCAVENGER REPORT
  Scanned: /Users/you | Date: 2026-05-10
═══════════════════════════════════

DOWNLOADS (reclaimable: 4.2 GB)
  ├── Installer.dmg   1.2 GB  last accessed: 8 months ago
  │   → macOS installer, likely already installed
  └── archive.zip     800 MB  last accessed: 1 year ago
      → Contains: project files, was extracted to ~/project/

CACHES (reclaimable: 12 GB)
  ├── npm cache       8.5 GB  → Safe to delete: npm re-downloads on demand
  └── pip cache       3.2 GB  → Safe to delete: pip re-downloads on demand

ORPHANED node_modules (reclaimable: 6.1 GB)
  └── ~/abandoned-project/node_modules
      → No git activity in 14 months; parent folder has no package.json
═══════════════════════════════════
TOTAL RECLAIMABLE: 22.3 GB
```
