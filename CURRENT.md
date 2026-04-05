# Current Project State

> Keep this file up to date. Update it when starting or completing a phase.

## Active Phase

None — ready for next phase. See `project.md` for the phase roadmap.

Next up is likely **Product Phase 2 — UX Design** (wireframes, mobile-first decisions).

## Data Extraction (completed)

**One script: `scripts/data-pipeline/extract_web.py`**

Extracts all game data (670 pets, 195 spells, 104 perks) from the live WebGL build on itch.io. Zero pre-existing files needed, survives game updates, designed for unattended cronjob.

Full details: `docs/phases/product-phase-2-data-extraction-pipeline.md`

## Recently Completed

| Phase | Doc |
|-------|-----|
| Product Phase 2 — Data Extraction Pipeline | `docs/phases/product-phase-2-data-extraction-pipeline.md` |
| Product Phase 1 — Data Source and Discovery | `docs/phases/product-phase-1-data-source-and-discovery.md` |
| Setup Phase 4 — Testing Infrastructure | `docs/phases/setup-phase-4-testing-infrastructure.md` |
| Setup Phase 3 — Linting | `docs/phases/setup-phase-3-linting.md` |
| Dev Phase 0 — Docker | `docs/phases/dev-phase-0-docker.md` |
| Setup Phase 2 — Task Management | `docs/phases/setup-phase-2-task-management.md` |
| Setup Phase 1 — Documentation Standards & AI Skills | `docs/phases/setup-phase-1-docs-standards-ai-skills.md` |

## Blocking Decisions

None.

## Environment Notes

- All commands (pnpm, linters, etc.) run inside the container: `docker compose run app <cmd>`
- Do NOT run pnpm or Node directly on the host machine
- `extract_web.py` runs on the HOST (needs Playwright/Chromium, not Docker)
