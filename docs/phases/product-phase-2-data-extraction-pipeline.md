---
phase: product-phase-2
status: in-progress
started: 2026-03-27
completed:
---

# Phase 2 — Data Extraction Pipeline

## Goal

Build a fully automated pipeline that extracts complete, accurate pet/food/ability data from SAP game files — no external data sources required.

## Context

Phase 1 (Data Source & Discovery) revealed that pet data is hardcoded in `GameAssembly.dll` (IL2CPP compiled native code). We extracted stats, tiers, and ability enum references via Cpp2IL ISIL parsing, and ability descriptions from localization bundles. But ability triggers remain locked in native code lambda bodies.

We have a complete reference dataset from groundedsap.co.uk (581 pets, all fields). This serves as our validation target — the pipeline is "done" when its output matches groundedsap for the current patch, and can produce correct output for future patches without any external data.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Primary data validation source | groundedsap.co.uk | User-trusted, comprehensive, covers all packs including Custom |
| Binary decompilation tool | Ghidra (headless) | Successfully analyzed GameAssembly.dll; Cpp2IL couldn't reconstruct method bodies |
| Localization extraction | UnityPy + binary parsing | Extracted 5304 strings including ability descriptions from addressable bundles |
| Trigger extraction approach | Ghidra decompile + groundedsap cross-reference | Use known triggers to map factory functions, then validate the mapping is reusable |

## Deliverables

### Research (use groundedsap as Rosetta Stone)

- [ ] **R1: Stat validation** — Diff our extracted stats (attack, health, tier) against groundedsap for all 581 pets. Identify and fix parser bugs.
- [ ] **R2: Trigger factory mapping** — Cross-reference groundedsap's known triggers with our 34 Ghidra trigger factory functions. Build a verified factory_address → trigger_name lookup.
- [ ] **R3: Lambda-to-ability mapping** — Use the verified trigger mapping + ability descriptions to match each Ghidra lambda to its ability enum. This is the key missing link.
- [ ] **R4: Ability description validation** — Diff our localization-extracted descriptions against groundedsap's. Fix any extraction bugs.
- [ ] **R5: Coverage gap analysis** — Identify any data in groundedsap we still can't extract (packs, rollable status, categories, notes, etc.) and determine extraction paths.

### Pipeline (automate the extraction)

- [ ] **P1: Pet stat extractor** — Script that takes Cpp2IL ISIL output and produces pet stats JSON. Tested against groundedsap.
- [ ] **P2: Ability description extractor** — Script that extracts ability text from localization bundles. Tested against groundedsap.
- [ ] **P3: Trigger extractor** — Script that uses Ghidra headless to decompile trigger lambdas and extract trigger assignments. Tested against groundedsap.
- [ ] **P4: End-to-end pipeline** — Single script: game files in → complete pets.json out. Regression tested against groundedsap snapshot.

## Open Questions

- Can we extract food/spell data using the same approach? (SpellConstants mirrors MinionConstants)
- Can the pipeline run in Docker for reproducibility?
- How do we handle pets that exist in our extraction but not in groundedsap (removed/test pets)?
- Is there a faster alternative to full Ghidra analysis (~45 min) for the trigger extraction step?

## What I Learned

(To be filled as work progresses)

## Evals

| Eval | File | Result |
|---|---|---|
| Stat accuracy vs groundedsap | | |
| Trigger accuracy vs groundedsap | | |
| Description accuracy vs groundedsap | | |
| End-to-end pipeline output | | |

## Related

- `docs/phases/product-phase-1-data-source-and-discovery.md`
- `docs/game-file-map.md`
- `docs/learning/unity-il2cpp-data-extraction.md`
- `tmp/groundedsap-data.json` — reference dataset
- `tmp/ghidra-lambdas-decompiled.c` — 7203 decompiled lambda functions
- `tmp/ghidra-abilities-decompiled.c` — 22 decompiled ability creation functions
