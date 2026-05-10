---
version: 1.0.0
name: skill-creator
description: Create or update AgentSkills. Use when designing, structuring, or packaging skills with scripts, references, and assets. Guides through: understanding the skill, planning reusable contents, initializing, editing, packaging, and iterating.
---

# Skill Creator

Guidance for creating effective agent skills.

## About Skills

Skills are modular, self-contained packages that extend an agent's capabilities by providing
specialized knowledge, workflows, and tools. They transform a general-purpose agent into
a specialist equipped with procedural knowledge the model alone doesn't have.

### What Skills Provide

1. Specialized workflows — Multi-step procedures for specific domains
2. Tool integrations — Instructions for working with specific file formats or APIs
3. Domain expertise — Project-specific schemas, business logic
4. Bundled resources — Scripts, references, and assets

## Core Principles

### Concise is Key

The context window is a public good. Only add context the agent doesn't already have.
Challenge each piece: "Does the agent need this?" and "Does this paragraph justify its token cost?"

Prefer concise examples over verbose explanations.

### Anatomy of a Skill

```
skill-name/
├── SKILL.md (required)
│   ├── YAML frontmatter: name + description (required)
│   └── Markdown instructions (required)
└── Bundled Resources (optional)
    ├── scripts/          - Executable code (Python/Bash/etc.)
    ├── references/       - Documentation loaded into context as needed
    └── assets/           - Files used in output (templates, icons, fonts)
```

#### Frontmatter

Only two fields matter for triggering:
- `name`: The skill name
- `description`: Primary triggering mechanism — include what the skill does AND when to use it.

#### Bundled Resources

- **scripts/**: Executable code for tasks that would otherwise be rewritten repeatedly
- **references/**: Domain docs, schemas, API specs — loaded only when needed
- **assets/**: Templates, images, boilerplate — not loaded into context, just used in output

## Skill Creation Process

1. **Understand** — Gather concrete usage examples. Ask: "What would a user say to trigger this?"
2. **Plan** — Identify reusable scripts, references, and assets from the examples
3. **Initialize** — `scripts/init_skill.py <skill-name> --path skills/ [--resources scripts,references]`
4. **Edit** — Write SKILL.md body + implement bundled resources. Test scripts by running them.
5. **Package** — `scripts/package_skill.py <path/to/skill-folder>` (validates + creates .skill zip)
6. **Iterate** — Use on real tasks, notice struggles, update

## Skill Naming

- Lowercase letters, digits, hyphens only; hyphen-case
- Under 64 characters
- Prefer short verb-led phrases: `gh-address-comments`, `pdf-rotate`
- Namespace by tool when it improves clarity

## Progressive Disclosure

Keep SKILL.md body under 500 lines. Use references/ for detail:

```markdown
# PDF Processing

## Quick start
[core workflow]

## Advanced features
- **Form filling**: See [FORMS.md](references/FORMS.md)
- **Tracked changes**: See [REDLINING.md](references/REDLINING.md)
```

## What NOT to include in a skill

- README.md, INSTALLATION_GUIDE.md, CHANGELOG.md
- Information the agent already knows
- Auxiliary context about the skill creation process itself
