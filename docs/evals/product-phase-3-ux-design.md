---
eval-for: product-phase-3
date: 2026-04-06
last-run: never
---

# Eval — Product Phase 3 UX Design

## What This Eval Covers

The UX design decisions for the Super Auto Pets pack builder: interaction model, lobby system, publish model, API shape, data constraints, and internal consistency. Checks that the spec is complete enough for downstream phases to build from without ambiguity.

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
| 1 | Frontmatter phase number matches filename | `phase: product-3` in frontmatter; file is `product-phase-3-ux-design.md` |
| 2 | Decisions table has no empty cells | All rows have exactly 3 cells (Decision, Choice, Rationale) |
| 3 | Slot counts marked as human-verified | Key Architectural Signals row says "human verified against in-game pack builder and native export format" |
| 4 | Conflict resolution is first-come first-served | Real-Time Collaboration section says server processes actions in order; rejected actions show error toast only to acting user |
| 5 | Rejected actions NOT in history feed | Spec explicitly states rejected actions do not appear in the live history feed |
| 6 | Lobby slug = pack ID | Decisions table has "Lobby slug = pack ID — One ID serves as both lobby identifier and pack DB record" |
| 7 | Private lobby defined | Decisions table and Lobby System section describe private lobbies as non-listed lobbies using the same slug model |
| 8 | Publish model described | Publish Flow section covers freeze, collaborator listing, public URL, fork |
| 9 | Fork described | Publish Flow section covers fork creating a new draft; fork available on published pack page |
| 10 | Save to my account described | Lobby System section covers upsert behaviour — first press creates, subsequent presses update |
| 11 | Collaborators listed on published pack | Decisions table and Publish Flow section state collaborators are captured at publish time |
| 12 | Max collaborators stated | Lobby System section states 8 max; full lobby shows error message |
| 13 | Mascot pet described | Decisions table, lobby card wireframe, and header wireframe all reference mascot pet |
| 14 | Import/Export section present | Section documents SAP native JSON format: Title, Minion, Minions (60 enumIds), Spells (18 enumIds) |
| 15 | Picker pool defined | Decisions table states "all rollable pets from all available packs" |
| 16 | Pet detail sheet described | Section covers image, stats, stacked ability levels, related perks, related toys, Add/Remove button |
| 17 | Perk cross-referencing flagged as pipeline dependency | Detail sheet section notes perk descriptions require a future pipeline phase |
| 18 | Error states table present | Section covers tier full, WebSocket disconnected, server rejection, lobby not found, auth required |
| 19 | Unauthenticated landing state described | Section states unauthenticated users see a landing/login page; cannot access lobby browser |
| 20 | Leave lobby behaviour defined | Lobby System section states closing the tab disconnects; no explicit leave button |
| 21 | Active lobbies defined | Lobby System section defines "active" as lobbies with at least one connection in the last hour |
| 22 | Lobby expiry clears all state | Lobby auto-expiry section states lobby and all its state are deleted after 1 hour of zero connections |
| 23 | No localStorage references | localStorage is not mentioned as a persistence mechanism anywhere in the doc |
| 24 | API shape includes POST endpoints | POST /api/lobbies and POST /api/packs both present |
| 25 | API shape includes GET /api/perks | Endpoint present; rollable filter noted on GET /api/foods |
| 26 | History feed is scrollable | Feed section states feed is scrollable within its window |
| 27 | History feed uses color not position | Feed section states each user's entries shown in their assigned color; no left/right split |
| 28 | Upvote/downvote in v1 scope | Decisions table has "Upvote / downvote — In scope for v1" |
| 29 | Comments deferred to v2 | Decisions table and Phase 4 Directive both say comments are v2 |
| 30 | ASCII diagrams use 6 tiers | Neither diagram references Tier 7 |

## Pass Criteria

All 30 checks must pass. Any failure means the eval fails and the phase doc must be corrected before the phase is considered complete.

## When to Re-run

- Before Phase 4 begins (Feature Scope)
- Any time the phase doc is modified

## Notes

- Perk cross-referencing and perk descriptions are explicitly flagged as a dependency on a future pipeline phase. This is a known gap, not an eval failure.
- WebSocket message format is intentionally deferred to Dev Phase 2 (API Layer). Not a failure.
- Auth method is intentionally deferred to Phase 5 (DB decisions). Not a failure.
