# Current Project State

> Keep this file up to date. Update it when starting or completing a phase.

## Active Phase

### Product Phase 2 — Data Extraction Pipeline ✅ COMPLETE

- Phase doc: `docs/phases/product-phase-2-data-extraction-pipeline.md`
- Scripts: `scripts/data-pipeline/`
- **Status: COMPLETE** — full game data extraction working

## What Exists

### Primary extraction: `scripts/data-pipeline/extract_web.py`

**This is the main script.** It extracts ALL game data from the live WebGL build with zero pre-existing files:

```bash
python3 scripts/data-pipeline/extract_web.py --output-dir data/extracted
```

**How it works:**
1. Launches SAP WebGL build from itch.io in headless Chromium via Playwright
2. Intercepts and saves `game.wasm` + `game.data` during download
3. Extracts `global-metadata.dat` (IL2CPP metadata) from `game.data`
4. Auto-downloads and runs Il2CppDumper to get function table indices + enum names
5. Verifies struct field offsets against known pet values (auto-discovers if changed)
6. Calls `GetReleasedMinions/Spells/Perks` directly through the WASM function table
7. Reads all object fields from WASM linear memory
8. Resolves enum IDs to human-readable names
9. Outputs `pets.json` (670), `spells.json` (195), `perks.json` (104)

**Dependencies:** `playwright` (pip), Chromium (installed by playwright), `dotnet` 6+ runtime

**Survives game updates automatically** — everything derived at runtime. Field offsets self-verified on each run.

### Secondary extraction: `scripts/data-pipeline/extract.py`

Static decompilation pipeline using Cpp2IL + Il2CppDumper on the Windows desktop build. **Mostly superseded** by `extract_web.py`, but still the only source for:
- **Trigger names** (e.g., "Faint", "Start of battle") — extracted from ISIL symbolic `CreateTrigger.X` calls
- **Ability descriptions** (e.g., "Give one random friend +1 attack") — from localization bundles + hardcoded `SetAbout` strings

Requires: Downloaded Windows game files, Cpp2IL binary, Il2CppDumper binary.

### Data extracted per item

| Field | Pets | Spells | Perks | Source |
|-------|------|--------|-------|--------|
| name | ✅ | ✅ | ✅ | Web extract |
| enumId | ✅ | ✅ | ✅ | Web extract |
| tier | ✅ | ✅ | — | Web extract |
| attack/health | ✅ | — | — | Web extract |
| price | ✅ | ✅ | — | Web extract |
| rollable | ✅ | ✅ | — | Web extract |
| archetypes | ✅ | ✅ | — | Web extract |
| packs | ✅ | ✅ | — | Web extract |
| abilities list | ✅ | — | ✅ | Web extract |
| roles | ✅ | — | — | Web extract |
| about (description) | partial | ✅ | — | Web extract |
| trigger name | ❌ | — | — | ISIL pipeline only |
| ability descriptions | ❌ | — | — | ISIL pipeline only |

### Supporting files

| File | Purpose | Status |
|------|---------|--------|
| `scripts/data-pipeline/extract_spells.py` | Spell extraction from ISIL | Superseded by web extract |
| `scripts/data-pipeline/extract_perks.py` | Perk extraction from ISIL | Superseded by web extract |
| `scripts/data-pipeline/trigger-map.json` | Pre-built trigger name map from groundedsap | Still used as fallback |
| `scripts/data-pipeline/check-version.py` | Desktop game version checker | Still useful |
| `scripts/data-pipeline/parse-isil-standalone.py` | Dev tool for ISIL parsing | Superseded |

### Validation results vs GroundedSAP (groundedsap.co.uk)

Web extraction matches or exceeds GroundedSAP on every metric:
- **670 pets** (vs GS 581) — we have more, including all 35 mythological creatures GS has
- **195 spells** (vs GS ~156)
- **104 perks** (vs GS ~98)
- 16 stat differences are game version differences (our data is from the live web build)
- Archetype differences exist because GS uses community-curated tags, we use the game's internal archetypes

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
