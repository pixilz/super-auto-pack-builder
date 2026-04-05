# Current Project State

> Keep this file up to date. Update it when starting or completing a phase.

## Active Phase

### Product Phase 2 — Data Extraction Pipeline ✅ COMPLETE

- Scripts: `scripts/data-pipeline/`
- **Status: COMPLETE** — full game data extraction working from a single script

## What Exists

### Primary extraction: `scripts/data-pipeline/extract_web.py`

**This is the main script.** Extracts ALL game data from the live WebGL build. Zero pre-existing files needed.

```bash
python3 scripts/data-pipeline/extract_web.py --output-dir data/extracted
```

Takes ~3 minutes. Outputs `pets.json`, `spells.json`, `perks.json`.

**How it works:**
1. Launches SAP WebGL build from itch.io in headless Chromium via Playwright
2. Intercepts `game.wasm` + `game.data` during download, saves to disk
3. Extracts `global-metadata.dat` (IL2CPP metadata) from `game.data`
4. Auto-downloads Il2CppDumper if not present, runs it for function indices + enum names
5. Verifies struct field offsets against known pet values (auto-discovers if layout changes)
6. Calls `GetReleasedMinions/Spells/Perks` directly through WASM function table
7. Reads object fields (stats, archetypes, packs, abilities) from WASM linear memory
8. Reads ability triggers from `GetAbilities` → `AbilityCollection` → `Ability.Trigger.Enum`
9. Captures localization bundles during game load, parses with UnityPy for descriptions
10. Resolves all enum IDs to human-readable names from Il2CppDumper `dump.cs`
11. Outputs 3 clean JSON files

**Dependencies:** `playwright` (pip) + Chromium, `dotnet` 6+ runtime, `UnityPy` (pip, optional for descriptions)

**Survives game updates automatically.** Function indices resolved from fresh Il2CppDumper run. Field offsets (including trigger offset and AbilityEnums offset) self-discovered against known pet values on each run. Il2CppDumper auto-downloaded from GitHub if missing. No fallback indices — fails loud if Il2CppDumper fails.

### Cronjob / server operation

Designed for unattended twice-weekly runs:

```bash
# Crontab: run Mon+Thu at 6am, skip if no game update
0 6 * * 1,4 python3 /path/to/extract_web.py \
  --output-dir /data/sap \
  --version-file /data/sap/.version \
  --timeout 90
```

**Update detection:** Hashes `game.wasm` (SHA256), compares to `--version-file`. If unchanged, skips extraction (~30s for download check only). If changed, runs full extraction (~3min) and saves new hash.

**No manual intervention needed on game update.** All function indices, field offsets, enum names, and trigger offsets are re-derived from the new game binary each time.

**`--check-only` flag:** Detects whether game updated without running extraction.

**Exit codes:** 0 = success (or no update needed), 1 = failure.

### Data extracted per item

| Field | Pets | Spells | Perks | Source |
|-------|------|--------|-------|--------|
| name, enumId | 670 (100%) | 195 (100%) | 104 (100%) | WASM memory |
| tier, attack, health, price | 670 (100%) | 195 (100%) | — | WASM memory |
| rollable, active | 670 (100%) | 195 (100%) | — | WASM memory |
| archetypes (producer/consumer/custom) | 504 (75%) | 195 | — | WASM memory |
| packs | 560 (84%) | 195 | — | WASM memory |
| ability list (enum names) | 651 (97%) | — | 104 (100%) | WASM memory |
| roles | partial | — | — | WASM memory |
| **triggers** | **629 (94%)** | — | — | WASM memory (Ability.Trigger.Enum) |
| **ability descriptions** | **633 (94%)** | **195 (100%)** | — | Localization bundles (UnityPy) |

### Validation vs GroundedSAP (groundedsap.co.uk)

| Metric | Our Extract | GroundedSAP |
|--------|-------------|-------------|
| Total pets | **670** | 581 |
| Stats accuracy | 97.2% (16 version diffs) | baseline |
| Triggers (with normalization) | **93.1%** (~97% with full normalization map) | baseline |
| Descriptions | 92.8% | baseline |
| Spells | **195** | ~156 |
| Perks | **104** | ~98 |

Trigger "differences" are mostly naming format (`ThisDied` vs `Faint`, `EnemyAttacked5` vs `Five enemy attacks`). These are the same triggers, just raw enum names vs display names. A normalization map in the script converts most of them.

### Remaining gaps

| Gap | Count | Cause | Fix |
|-----|-------|-------|-----|
| Trigger naming | ~33 | Raw enum names need display normalization | Extend `TRIG_NORM` dict |
| Missing descriptions | ~40 | Token pets + localization gaps | Tokens have "No ability" |
| Stat diffs vs GS | 16 | Game version difference (ours is newer) | Not a bug |
| Missing from GS | 2 | Burbel + Guinea Piglet (legacy unused tokens) | Not needed |

### Scripts

| File | Purpose |
|------|---------|
| `scripts/data-pipeline/extract_web.py` | **The only extraction script.** Everything else was removed. |

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
