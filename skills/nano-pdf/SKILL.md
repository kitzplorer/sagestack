---
version: 1.0.0
name: nano-pdf
description: Edit PDFs with natural-language instructions using the nano-pdf CLI. Use when the user wants to edit, annotate, or modify a PDF by describing the change in plain English.
homepage: https://pypi.org/project/nano-pdf/
---

# nano-pdf

Use `nano-pdf` to apply edits to a specific page in a PDF using a natural-language instruction.

## Install

```bash
uv tool install nano-pdf
# or: pip install nano-pdf
```

## Quick start

```bash
nano-pdf edit deck.pdf 1 "Change the title to 'Q3 Results' and fix the typo in the subtitle"
```

## Notes

- Page numbers are 0-based or 1-based depending on the tool version/config; if the result looks off by one, retry with the other.
- Always sanity-check the output PDF before sending it out.
- The edit is applied via LLM + PDF manipulation — works best on text-based PDFs, not scanned images.

## Common use cases

```bash
# Fix a typo on page 3
nano-pdf edit report.pdf 3 "Fix the typo 'accomodation' → 'accommodation'"

# Update a date
nano-pdf edit contract.pdf 1 "Change the date from January 1, 2025 to March 15, 2026"

# Replace a section heading
nano-pdf edit proposal.pdf 2 "Change the section heading 'Phase 1' to 'Discovery Phase'"
```
