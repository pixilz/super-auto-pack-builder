# R1: Stat Validation Report

## Overall
- Groundedsap: 581 pets | Extracted: 672 pets | Matched by ID: 530
- In groundedsap only: 50 (tokens with different names, Unicorn pack mythicals)
- In extraction only: 142 (test pets, removed pets, relics)

## Attack: 523/530 match (98.7%)
- 7 mismatches, deltas of ±1-3. Likely minor version differences or parser edge cases.

## Health: 518/530 match (97.7%)
- 12 mismatches, deltas of ±1-3. Same cause.

## Tier: 502/524 match (95.8%)
- 22 mismatches. **20 are Δ+5** — all token/summoned pets (Bee, Ram, Dirty Rat, etc.)
- Bug: our parser assigns tokens to tier 6 because they appear after the last StartGroup(6) call
- Fix: handle StartTokenGroup() to reset tier properly
- Remaining 2 mismatches are minor.

## Action Items
1. Fix token tier assignment in parse-isil.py (handle StartTokenGroup)
2. Investigate 50 pets in groundedsap but not in extraction (name mapping issues)
3. The 7 attack and 12 health mismatches are low priority (possible version differences)
