# Current Project State

> Keep this file up to date. Update it when starting or completing a phase.

## Active Phase

### Product Phase 2 — Data Extraction Pipeline

- Phase doc: `docs/phases/product-phase-2-data-extraction-pipeline.md`
- Scripts: `scripts/data-pipeline/`
- Status: Pipeline works (97.1% accuracy without external data, 100% trigger accuracy with trigger map)
- Remaining: standalone trigger extraction (activation triggers locked in IL2CPP type metadata)

## Recently Completed

| Phase | Doc |
|-------|-----|
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
