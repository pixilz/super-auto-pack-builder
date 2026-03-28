---
phase: product-phase-1
status: in-progress
started: 2026-03-27
completed:
---

# Phase 1 — Data Source and Discovery

## Goal

Determine what game data is available from decompiled Super Auto Pets files and define a strategy for extracting and structuring it.

## Context

All site data comes directly from decompiled game files — no third-party data sources. This phase answers two intertwined questions: what data do we want to expose, and what data is actually available? These questions are iterative — what we want informs what we look for, and what we find informs what's possible.

This phase must complete before any development phases that depend on game data (API layer, frontend, etc.).

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Game client | Steam (Windows) | Local file access required; itch.io WebGL version has no extractable local files |
| Primary data source for pet/food data | Team Wood Games network API (`api.teamwood.games`) | Pet/food data is not bundled locally; game fetches JSON from servers at runtime |
| Asset extraction tool | UnityPy (Python) | Works on Unity Addressable bundles; scriptable; cross-platform |
| Game logic extraction | IL2CPP pipeline (Il2CppDumper + ILSpy) | Game uses IL2CPP backend (not Mono); `GameAssembly.dll` confirmed |
| Pack scope | Turtle, Puppy, Star, Golden | Static packs only; Weekly Pack excluded (no unique pets — it's a rotating subset of existing pets) |
| Localization | English only for v1 | Reduce scope; localization bundles exist and can be added later |
| Mechanics data | Yes, extract from IL2CPP | Gold/XP/shop constants are in game logic, not the API |

## Deliverables

- [x] Data pipeline strategy doc — `docs/data-pipeline-strategy.md`
- [x] Data schema spec doc — `docs/data-schema-spec.md`

## Open Questions (resolved)

- **What decompiler?** UnityPy for asset bundles; Il2CppDumper + ILSpy for game logic (IL2CPP build)
- **What format does decompiled output come in?** JSON from network API; PNG/WAV from asset bundles; C# stubs from Il2CppDumper
- **What game data is available?** Pets (stats, 3-level abilities, packs, probabilities), foods, statuses, turn config, game mechanics constants, sprites, localization strings
- **What data do we want to expose?** Pets, foods, statuses, turns, mechanics — see schema spec

## Unresolved (carry into Dev Phase 1)

- Exact API path and request headers (requires mitmproxy capture of a live game session)
- Whether pet sprites are in local bundles or fetched from CDN at runtime
- Full numeric ID → slug mapping (requires live API response)
- Weekly Pack: confirm no unique pets (current understanding is Weekly is a rotating subset)

## What I Learned

- SAP is a Unity IL2CPP build — standard ILSpy/dnSpy approach doesn't work directly; need Il2CppDumper first
- Pet/food data is not in local Unity asset bundles; it's fetched from `api.teamwood.games` at runtime
- Local bundles contain: mascot pose data (MonoBehaviour), backgrounds, sounds, localization strings, and `Changes.json` (patch diff)
- The Addressables catalog (`catalog.json`) is the map of what's in which bundle — essential for understanding the asset layout
- IL2CPP metadata (`global-metadata.dat`) is human-readable enough for `strings` extraction; found the API URL format there
- `Changes.json` uses internal numeric pet IDs — requires ID mapping in the pipeline
- Pack names in the internal API differ from display names (e.g. `StandardPack` = Turtle Pack)

## Evals

| Eval | File | Result |
|---|---|---|
| | | |

## Related

- [Dev Phase 1 — Game File Pipeline](dev-phase-1-game-file-pipeline.md)
