---
phase: setup-phase-1
status: complete
started: 2026-03-25
completed: 2026-03-25
---

# Phase 1 — Documentation Standards and AI Skills

## Goal

Establish the documentation system, templates, naming conventions, eval standards, and AI slash commands that every subsequent phase will depend on.

## Context

This is the first pre-dev setup phase and a prerequisite for all other phases. Without consistent templates and conventions, phase docs become inconsistent and lose value as a reference. Without eval standards, AI output cannot be reliably validated. Without slash commands, the overhead of following conventions correctly is too high to sustain.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Phase doc naming | `<category>-phase-<n>-<slug>.md` | Avoids collisions across setup/product/dev/lt categories |
| Learning note naming | `<topic-slug>.md` in `docs/learning/` | Flat structure, easy to glob and reference |
| Eval naming | `<phase-slug>-<concern>.md` in `docs/evals/` | Ties evals to phases, supports multiple evals per phase |
| Slash command storage | `.claude/commands/` | Claude Code convention for project-scoped commands |
| Eval status field | `not-run` / `passed` / `failed` | Matches phase doc status pattern; makes state explicit |

## Deliverables

- [x] `docs/templates/phase-doc.md`
- [x] `docs/templates/learning-note.md`
- [x] `docs/templates/eval.md`
- [x] `CLAUDE.md` at repo root
- [x] `.claude/commands/new-phase-doc.md`
- [x] `.claude/commands/add-learning-note.md`
- [x] `.claude/commands/mark-phase-complete.md`
- [x] `.claude/commands/new-eval.md`

## Open Questions

- GitHub MCP server configuration: needs a personal access token scoped to this repo. Token scope to determine during Setup 2.
- Should learning notes support tags for cross-referencing? The template has a `tags` field but no tooling uses it yet.

## What I Learned

Setting up conventions before any code exists forces you to think about what information you actually need to capture vs. what feels comprehensive but becomes noise. The eval template in particular required deciding upfront what "done" means — which is harder than it sounds when the work is discovery-based (product phases) vs. implementation-based (dev phases).

The slash command pattern in Claude Code (markdown files in `.claude/commands/`) is simple but effective — it encodes process knowledge in a form that's version-controlled alongside the code.

## Evals

No evals for this phase — the deliverables are structural (templates, conventions, commands) and are validated by inspection.

## Related

- `project.md` — full project charter
- `docs/templates/phase-doc.md` — template used for all future phase docs
- `CLAUDE.md` — root AI conventions
