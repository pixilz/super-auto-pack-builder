---
eval-for: product-phase-3
date: 2026-04-06
last-run: never
---

# Eval — Product Phase 3 UX Design

## What This Eval Covers

The UX design decisions for the Super Auto Pets pack builder: interaction model, API shape, data constraints, and open questions. Checks that the spec is internally consistent, complete, and does not contradict itself.

## Why This Eval Exists

A UX spec with contradictions or unresolved downstream-blocking questions will cause downstream phases to stall or make wrong architectural decisions. This eval ensures the spec is clean before Phase 4 begins.

## How to Run

Read `docs/phases/product-phase-3-ux-design.md` in full and verify each check below. Output results to `tmp/eval-product-phase-3-ux-YYYY-MM-DD.txt`.

```bash
# No commands needed — this is a document review eval
```

## Checks

| # | Check | Expected |
|---|---|---|
| 1 | Frontmatter phase number matches filename | Phase is `product-3` in frontmatter and doc is `product-phase-3-ux-design.md` |
| 2 | Decisions table has no empty cells | All rows have exactly 3 cells (Decision, Choice, Rationale) |
| 3 | "Key Architectural Signals" table: tier signal is clarified | Row says "Pack summary shows all 6 tiers simultaneously; tier tabs filter the picker panel only" — not "no tier selection UI" |
| 4 | Open question #1 removed | "What happens when two users select the same pet slot simultaneously?" is NOT in Open Questions (answered inline as "last write wins") |
| 5 | Pack lifecycle is in Open Questions | "What is the 'pack' lifecycle?" is present and flagged as downstream-blocking |
| 6 | v1 scope: perks excluded | Decisions table has "Pets + food only; perks excluded" |
| 7 | API shape documented | GET /api/packs/:id, GET /api/pets, GET /api/foods, WS /ws/pack/:id all present |
| 8 | 10 pets + 3 food per tier is marked verified | Key Architectural Signals table has "verified by user" annotation |
| 9 | No duplicate "Real-Time Collaboration" sections | Exactly one instance of the heading |
| 10 | ASCII diagram uses 6 tiers | Not 7 |
| 11 | Empty state described | Fresh pack has all 6 tiers visible with "0/10 pets", "0/3 food" |
| 12 | Home screen / pack list called out as out of scope | Section states packs are only accessible via share URL, no pack list |
| 13 | PUT /api/packs/:id note flags it as placeholder | Dev Phase 2 note added warning that WS patch ops replace full-document PUTs |
| 14 | Live history feed described | Section covers desktop sidebar, mobile slide-out, entry format, max 50 entries |
| 15 | Lobby system described | Home screen with create/join, lobby card shows name/creator/people/time, auto-expiry 1hr |
| 16 | URL share coexists with lobby | "Share URL instead" link present at bottom of lobby screen |
| 17 | Username IS display name | User account section states username = display name, no separate display name field |
| 18 | Lobby recovery mechanism | Returning user with localStorage pack state offered to recreate lobby with their saved pack |

## Pass Criteria

All 18 checks must pass. Any failure means the eval fails and the phase doc must be corrected before the phase is considered complete.

## When to Re-run

- Before Phase 4 begins (Feature Scope)
- Any time the phase doc is modified

## Notes

- Pack lifecycle is the single biggest open question. It is downstream-blocking for Phase 5 (DB) and Phase 6 (Hosting). Phase 4 must resolve it or explicitly defer it.
