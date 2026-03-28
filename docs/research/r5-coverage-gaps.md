# R5: Coverage Gap Analysis

## Extraction Capability Summary

| Field | GSAP | We Extract | Accuracy | Extraction Path | Status |
|-------|------|------------|----------|-----------------|--------|
| name | 581 | 672 | ~100% | MinionEnum + localization | **DONE** — display name from localization SharedTableData |
| attack | 581 | 554 | 98.7% | Cpp2IL ISIL (MinionConstants SetStats) | **DONE** — 7 minor mismatches |
| health | 581 | 554 | 97.7% | Cpp2IL ISIL (MinionConstants SetStats) | **DONE** — 12 minor mismatches |
| tier | 581 | 589 | 95.8% | Cpp2IL ISIL (StartGroup) | **FIXABLE** — token tier bug |
| trigger | 537 | 509 | 100% (via join) | groundedsap→abilityEnum join | **NEEDS NATIVE CODE** for standalone |
| level1/2/3 | 581 | 766 | 75.9% | Localization bundles (UnityPy) | **DONE** — icon strip + params needed |
| archetypes | 484 | 17 | 3.5% | Cpp2IL ISIL (SetArchetype*) | **GAP** — parser only catches simple cases |
| id | 580 | 672 | 100% | MinionEnum.cs | **DONE** |
| categories | 190 | 0 | — | Unknown — possibly ItemTemplate fields | **GAP** — not in any extracted data |
| custom tags | 576 | 0 | — | Unknown — likely community-curated | **GAP** — probably not in game files |

## Key Findings

1. **Pack membership**: The HTML grid doesn't show per-pack checkmarks. The "categories" field (F2P, Star, Unicorn, etc.) indicates pack exclusivity. 391 pets have no category = available in all packs.

2. **Archetypes are extractable** but our ISIL parser only captures 17/484. The SetArchetypeProducer/Consumer/Custom/Mvp calls ARE in the ISIL output — the parser just doesn't associate them with the right pets consistently. Fix: improve the ISIL parser to track archetype assignments more carefully.

3. **Trigger extraction without groundedsap**: The 34 Ghidra factory functions only cover 14 trigger types. Common triggers (Sell, Buy, Faint, Hurt) use a different code path — they're likely set by methods on TriggerBase subclasses rather than factory functions. Full standalone trigger extraction requires deeper Ghidra analysis or a different decompilation approach.

4. **"Custom" tags** (like "Buy/Sell, Shop Scaling", "Projectile, Sniping") are likely community-curated gameplay categorizations, not game data. Probably not extractable.

5. **Description quality**: 75.9% match. Main fixes: strip all {XxxIcon} placeholders, resolve {0} template params, add "Works N times" suffixes from TriggerLimit/Repeat fields.

## Priority Actions for Pipeline

1. **High**: Fix icon stripping in descriptions (easy regex fix)
2. **High**: Fix token tier assignment (handle StartTokenGroup)
3. **Medium**: Improve archetype extraction in ISIL parser
4. **Medium**: Build standalone trigger extraction (deeper Ghidra work)
5. **Low**: Resolve {0} template params and "Works N times" suffixes
6. **Low**: Investigate categories extraction path
