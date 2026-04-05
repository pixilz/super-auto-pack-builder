---
phase: product-phase-2
status: complete
started: 2026-03-27
completed: 2026-04-05
---

# Phase 2 — Data Extraction Pipeline

## Goal

Build a fully automated pipeline that extracts complete, accurate pet/food/ability data from SAP game files — no external data sources required, survives game updates without code changes.

## Result

**One script: `scripts/data-pipeline/extract_web.py`**

```bash
python3 scripts/data-pipeline/extract_web.py --output-dir data/extracted
```

Zero pre-existing files. ~3 minutes. Outputs `pets.json` (670), `spells.json` (195), `perks.json` (104). Designed for unattended cronjob operation with `--version-file` for update detection.

## How It Works

1. Playwright launches the SAP WebGL build from itch.io in headless Chromium
2. Route interception captures `game.wasm`, `game.data`, and localization `.bundle` files
3. `global-metadata.dat` (IL2CPP metadata) is extracted from `game.data`
4. Il2CppDumper (auto-downloaded if missing) runs on the WASM binary to produce:
   - `script.json` → WASM function table indices for game functions
   - `dump.cs` → enum name mappings (Archetype, Pack, TriggerEnum, AbilityEnum, etc.)
5. Field offsets are verified against known pet values (Ant=2/2, Beaver=3/2, etc.) and auto-discovered if layout changes
6. Game functions called directly through `mod.asm.__indirect_function_table`:
   - `GetReleasedMinions()` → all pet data
   - `GetReleasedSpells()` → all spell/food data
   - `GetReleasedPerks()` → all perk data
   - `GetAbilities()` → ability trigger data (TriggerBase.Enum)
7. Localization bundles parsed with UnityPy for ability descriptions and spell descriptions
8. All enum IDs resolved to human-readable names

## Data Extracted

| Field | Pets | Spells | Perks |
|-------|------|--------|-------|
| name, enumId | 670 (100%) | 195 (100%) | 104 (100%) |
| tier, attack, health, price | 670 (100%) | 195 (100%) | — |
| rollable, active | 670 (100%) | 195 (100%) | — |
| archetypes | 504 (75%) | 195 | — |
| packs | 560 (84%) | 195 | — |
| ability list | 651 (97%) | — | 104 (100%) |
| triggers | 629 (94%) | — | — |
| descriptions | 633 (94%) | 195 (100%) | — |

## Cronjob Setup

```bash
0 6 * * 1,4 python3 /path/to/extract_web.py \
  --output-dir /data/sap \
  --version-file /data/sap/.version \
  --timeout 90
```

- `--version-file`: SHA256 hash of `game.wasm`. Skips extraction if unchanged (~30s).
- `--check-only`: Detect update without extracting.
- Exit code 0 = success, 1 = failure.
- No manual intervention on game update — everything re-derived from the new binary.

## Dependencies

- `playwright` + Chromium: `pip install playwright && playwright install chromium`
- `dotnet` 6+ runtime (for Il2CppDumper)
- `UnityPy` (optional, for descriptions): `pip install UnityPy`

## Validation vs GroundedSAP

| Metric | Our Extract | GroundedSAP |
|--------|-------------|-------------|
| Total pets | **670** | 581 |
| Stats accuracy | 97.2% (16 game version diffs) | baseline |
| Triggers | 93.1% (naming format diffs) | baseline |
| Descriptions | 92.8% | baseline |
| Spells | **195** | ~156 |
| Perks | **104** | ~98 |

## Remaining Gaps

| Gap | Cause | Severity |
|-----|-------|----------|
| Trigger display names | Raw enum names (`ThisDied`) vs display (`Faint`) | Low — normalization map needed |
| ~40 missing descriptions | Token pets + localization gaps | Low — tokens say "No ability" |
| 16 stat diffs vs GS | Game version difference (ours is newer) | Not a bug |

## What Was Tried Before

The first approach used static decompilation (Cpp2IL + Il2CppDumper + Ghidra) on the Windows desktop build. This achieved ~97% accuracy for stats but missed 35 mythological pets (Chimera, Hydra, Phoenix, etc.) whose creation code couldn't be traced through IL2CPP. The WASM memory reading approach solved this by reading live game state after full initialization.

All files from the static approach have been removed from the repo. The history is in git if needed.

## What I Learned

- **IL2CPP WASM builds are easier to extract from than native x86-64** — the WASM function table gives direct callable access to game functions without needing to understand calling conventions
- **Unity WebGL builds serve everything from itch.io** — game.wasm, game.data, localization bundles all downloadable via Playwright route interception
- **C# Dictionary in IL2CPP isn't always a Dictionary** — `GetAbilities()` returns a `List<AbilityCollection>`, not a `Dictionary<AbilityEnum, AbilityCollection>` as the dump.cs signature suggests
- **Field offset verification is essential** — checking known values (Ant=2/2) on every run catches layout changes before they produce silently wrong data
- **Lazy initialization matters** — not all game objects are populated until accessed, which is why calling the game's own accessor functions (GetReleasedMinions) is more reliable than scanning memory directly
