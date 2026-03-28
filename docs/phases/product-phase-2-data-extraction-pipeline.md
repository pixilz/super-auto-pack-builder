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

### SAP ability architecture has two trigger layers
The game separates **activation triggers** (Sell, Buy, Faint — when the ability fires) from **effect triggers** (Start of battle — when effects execute). Lambda code configures effect triggers via `SetTrigger()` with factory functions. Activation triggers are determined by which `TriggerBase` subclass is instantiated — the TYPE itself encodes the trigger, not an enum field. Extracting activation triggers requires cracking IL2CPP type reference → class name mapping.

### Metadata tokens in IL2CPP are not memory addresses
Static data (DAT_ values) in IL2CPP binaries contain runtime metadata tokens (0x6000XXXX format), not direct pointers. These need to be resolved via the `CodeGenModule.methodPointers` array using a base offset derived from the module's method table. The base offset (46074 for Assembly-CSharp) must be discovered empirically.

### Init flags as fingerprints
Each lambda function has a unique static initialization flag (`DAT_183aXXXXX == '\0'` pattern). These flags appear identically in both Cpp2IL ISIL and Ghidra decompiled output, making them reliable cross-reference fingerprints (785/785 correct matches).

### groundedsap.co.uk as Rosetta Stone
Using a known-good external dataset to JOIN with extracted data (petID → abilityEnum + petID → trigger = abilityEnum → trigger) produces 100% accuracy with zero conflicts. This "Rosetta Stone" approach lets us validate and supplement binary extraction without needing to crack every native code path.

## Research Results

| Research | Finding | Accuracy |
|---|---|---|
| R1: Stat validation | Attack 98.7%, Health 97.7%, Tier 99.4% (token tier bug fixed) | High |
| R2: Trigger factories | 36 factories map to 14 TriggerEnum values, but these are EFFECT triggers | N/A |
| R3: Lambda-to-ability | Solved via Rosetta Stone join — 509 mappings, 0 conflicts | 100% |
| R4: Descriptions | 71.4% match — gaps are icon placeholders, {0} params, "Works N times" suffixes | Medium |
| R5: Coverage gaps | All fields extractable except activation triggers and community-curated tags | See matrix |

## Accuracy Without External Data

| Field | Accuracy |
|-------|----------|
| Name | 99.1% |
| Attack | 98.7% |
| Health | 97.7% |
| Tier | 99.4% |
| Archetype | 89.6% |
| Description | ~71% |
| **Trigger** | **0%** |
| **Overall (excl. triggers)** | **97.1%** |

## Evals

| Eval | File | Result |
|---|---|---|
| Stat accuracy vs groundedsap | `tmp/r1-stat-validation.json` | 98.7% atk, 97.7% hp, 99.4% tier |
| Trigger accuracy (with map) | `tmp/r2-ability-trigger-map.json` | 100% (509 abilities) |
| Description accuracy | `tmp/r4-description-validation.json` | 71.4% |
| End-to-end pipeline | `scripts/data-pipeline/extract.py` | Runs, 672 pets output |

## Related

- `docs/phases/product-phase-1-data-source-and-discovery.md`
- `docs/game-file-map.md`
- `docs/learning/unity-il2cpp-data-extraction.md`
- `scripts/data-pipeline/extract.py` — extraction pipeline
- `scripts/data-pipeline/check-version.py` — version checker
- `scripts/data-pipeline/trigger-map.json` — 509 ability→trigger mappings (Rosetta Stone)
