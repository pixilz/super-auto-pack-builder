---
phase: setup-phase-3
status: in-progress
started: 2026-03-25
completed:
---

# Setup Phase 3 — Linting

## Goal

Lock in the package manager, Node version, and linting setup for the entire monorepo before any packages are created.

## Context

Linting and formatting standards need to be in place before code is written — retrofitting them is painful and creates noisy diffs. The package manager and Node version are foundational decisions that affect every package in the monorepo. This phase gates all development phases.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Runtime | Node LTS (22) | Stable, well-supported, lower friction than Bun while learning other new things |
| Package manager | pnpm via corepack | Fast, excellent monorepo workspace support, corepack enforces it automatically |

## Deliverables

- [x] Decide on package manager (npm / pnpm / yarn) and lock it in (#3)
- [x] Decide on Node version and lock it in (`engines` field in package.json) (#4)
- [ ] Set up ESLint across the monorepo (#5)
- [ ] Set up Stylelint across the monorepo (#6)
- [ ] Set up TypeScript type checking (`tsc --noEmit`) (#7)
- [ ] Set up Markdownlint across the monorepo (#8)
- [ ] Set up Hadolint for Dockerfiles (#9)
- [ ] Verify all linting enforced consistently (#10)

## Open Questions

- Which package manager? (pnpm is common for monorepos due to workspace support and performance)
- Which Node version? (LTS is the safe default)
- DB linting (SQLFluff / Squawk) — revisit after database is chosen in Product Phase 5

## Blocked By

**Dev Phase 0 — Docker** must complete first. Claude runs inside yolobox (a Docker container inside WSL), so all tooling must be installed inside the project Docker image — not on WSL or Windows directly. Installing linting tools before the Dockerfile exists would mean doing it twice. Dev Phase 0 was moved up as a prerequisite for this phase.

## What I Learned

_To be filled in._

## Evals

| Eval | File | Result |
|---|---|---|
| — | — | — |

## Related

- [Setup Phase 2](setup-phase-2-task-management.md)
