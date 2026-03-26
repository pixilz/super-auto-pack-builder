# Super Auto Pets — Root CLAUDE.md

## What This Project Is

A data wiki and tooling site for Super Auto Pets, built from decompiled game files. Monorepo, self-hosted, full stack + DevOps.

**This is a learning-first project.** Shipping matters, but skill growth and documented knowledge matter more. Every phase must produce documented learning, not just working code.

Read `project.md` for the full charter before asking questions about scope or priorities.

---

## Core Principles for AI

### Build IN, not pile ON

- Extend and integrate with what exists. Do not add layers or abstractions unless they solve a concrete, current problem.
- Do not refactor surrounding code when fixing a bug.
- Do not add error handling for scenarios that cannot happen.
- Do not add features, docstrings, or comments to code you did not change.
- When uncertain about scope, stop and ask — do not assume or expand.

### Evals and tests gate every phase

- No phase is complete without passing evals.
- Evals are structured, specific checks — not informal review. See eval standards below.
- Regressions must be caught immediately. Evals are the mechanism.

### Context discipline

- **At the start of every conversation, read `CURRENT.md`** to understand the active phase and open tasks.
- Before starting a phase, read: `project.md`, the relevant `docs/phases/` doc (if it exists), and any relevant `docs/learning/` notes.
- When working in a package, read its `CLAUDE.md` before making changes.
- Prune context aggressively — keep it relevant to the current phase.
- Do not carry assumptions from a previous phase into a new one without re-reading the phase doc.

---

## Folder Conventions

| Folder | Purpose |
|--------|---------|
| `docs/phases/` | Phase result documents — permanent record of decisions |
| `docs/learning/` | Learning notes written as resume material |
| `docs/templates/` | Templates for phase docs, learning notes, and evals |
| `docs/evals/` | Eval documents |
| `.claude/skills/` | Claude Code skills (slash commands + auto-invocable) |
| `human_references/` | Human-written reference material — read-only for AI |

---

## Phase Doc Naming

Phase docs live in `docs/phases/` with a category prefix to avoid collisions:

```text
docs/phases/setup-phase-<n>-<slug>.md
docs/phases/product-phase-<n>-<slug>.md
docs/phases/dev-phase-<n>-<slug>.md
docs/phases/lt-phase-<n>-<slug>.md
```

Examples:

- `docs/phases/setup-phase-1-docs-standards-ai-skills.md`
- `docs/phases/product-phase-6-hosting-decision.md`
- `docs/phases/dev-phase-2-api-layer.md`

Each phase doc has a frontmatter status block. See `docs/templates/phase-doc.md`.

---

## Learning Note Naming

Learning notes live in `docs/learning/` with descriptive slugs:

```text
docs/learning/<topic-slug>.md
```

Examples:

- `docs/learning/drizzle-orm-basics.md`
- `docs/learning/docker-multistage-builds.md`

See `docs/templates/learning-note.md`.

---

## Eval Standards

Evals validate AI output. They are structured, testable checks — not informal review.

**What an eval must cover:**

- Specific, unambiguous claims about the output (not vague impressions)
- Explicit pass/fail criteria for each check
- Coverage of the main decisions or risks in that phase
- Instructions for how to run it

**When evals run:**

- At the end of every phase, before marking it complete
- When a significant implementation decision changes mid-phase

**Eval naming:**

```text
docs/evals/<phase-slug>-<concern>.md
```

Example: `docs/evals/product-phase-6-cost-model.md`

See `docs/templates/eval.md` for the full template and structure.

---

## Available Slash Commands

| Command | What it does |
|---------|-------------|
| `/new-phase-doc` | Create a new phase doc from template |
| `/start-phase` | Create GitHub issues for a phase and assign them to the milestone |
| `/add-learning-note` | Create a new learning note from template |
| `/close-issue` | Close a GitHub issue and update CURRENT.md |
| `/mark-phase-complete` | Mark a phase doc as complete |
| `/new-eval` | Create a new eval from template |

---

## Package-Level CLAUDE.md Files

Each package in the monorepo will have its own `CLAUDE.md` encoding package-specific conventions (language standards, test patterns, linting rules, etc.). When working in a package, always read its `CLAUDE.md` first. This file only covers repo-wide concerns.
