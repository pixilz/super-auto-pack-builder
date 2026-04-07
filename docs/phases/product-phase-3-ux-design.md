---
phase: product-3
status: in-progress
started: 2026-04-06
completed:
---

# Product Phase 3 — UX Design

## Goal

Define the user experience for the Super Auto Pets pack builder: device priority, pack structure, key interactions, and visual direction — producing a written spec that downstream phases can build from.

## Context

Phase 1 established that all game data (670 pets, 195 spells, 104 perks) will be extracted from the decompiled game files via a Playwright-based pipeline. The data exists.

**Pivotal decision (this phase):** The pack builder is the primary product, not the wiki. The data wiki is API infrastructure that backs the pack builder. This reorders the charter significantly — the pack builder drives the UX, not a general-purpose data browser.

**Device priority:** Mobile-first (user confirmed)
**Aesthetic direction:** Playful & colorful (user confirmed)

This means UX must center the pack builder flow (adding pets, arranging food, publishing, sharing) with the data being secondary — surfaced within the builder context, not as a standalone browsing experience.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Product center | Pack builder as the star | User confirmed pack builder is primary; wiki/data is infrastructure |
| Device priority | Mobile-first | Primary users on phones; design scales up to desktop |
| Aesthetic | Playful & colorful | Matches the personality of Super Auto Pets; game itself is bright and fun |
| Data model | Pack builder owns pet/spell/food data | Pet/spell/food data consumed from API within builder context |
| v1 scope | Pets + food in builder UI; perks API in scope, perks UI deferred to v2 | Perks API needed for cross-referencing in pet detail sheet; UI builder excludes them |
| Food vs spells | Food and spells are synonymous in SAP; use "food" in UI | Internal API may use "spell" but user-facing strings say "food" |
| Lobby system | In scope for v1 | Enables discovery + collaboration without pre-coordination |
| Private lobby | URL share creates a private lobby (not listed in lobby browser) | Same session model as public lobby; just not discoverable |
| Lobby name = pack name | Lobby and pack share one name; renaming renames both | Lobby URL uses randomized slug so URL stays stable across renames |
| Lobby slug = pack ID | One ID serves as both lobby identifier and pack DB record | Simpler routing; no mapping needed |
| Pack lifecycle | Account-scoped persistent packs | Users own packs; packs persist in DB |
| Publish model | Lobbies are draft space; publishing freezes pack for community browsing | Enables clean upvoting/downvoting against a fixed artifact; creator can fork to iterate |
| Fork | Any user can fork any published pack into a new draft | Fork lives on published pack page; collaborators use this to get their own copy |
| Save to my account | Collaborators can save pack state from within lobby (upsert) | First press creates draft linked to lobby; subsequent presses update it |
| Collaborators on published packs | All collaborators listed on published pack | Lobby tracks participants; captured at publish time |
| Upvote / downvote | In scope for v1 | Community rating against immutable published packs; Phase 4 to define detail |
| Comments | Deferred to v2 | Significant scope and moderation complexity |
| Max collaborators | 8 per lobby | Reasonable WebSocket limit; covers all practical use cases |
| Picker pool | All rollable pets from all available packs | Maximum flexibility for custom pack building |
| Mascot pet | One pet selected as pack icon; shown in lobby browser | Matches SAP native export format (Minion field); no extra data needed |
| Import/Export | SAP native JSON format | Compatible with packs players have already built in-game; enumIds match extracted data |
| Pet detail | Tap opens detail sheet; "Add to pack" button inside | Better mobile UX; allows reviewing stats, ability, perks, and toys before committing |
| Perk/toy cross-referencing | Referenced perks and toys shown inline in detail sheet | Pipeline must extract perk descriptions; name-matching used for linking — dependency on future pipeline phase |
| Slot counts | 10 pets + 3 food per tier — human verified | Confirmed from in-game SAP custom pack builder and native export format |
| Format | Written UX spec with ASCII/page diagrams | Faster to produce than full wireframes; communicates decisions clearly |

## Deliverables

- [x] Written UX spec for the pack builder: add/remove pets and food, publish, share
- [x] Mobile-first pack builder layout described
- [x] Data access pattern: how the builder queries pet/spell/perk data (API shape)
- [x] Sharing and publish flow described
- [x] Open questions surfaced for Phase 4 (feature scope)

## Open Questions

- ~~Is there a minimum viable pack?~~ All 10 pets per tier are **required** for a complete pack. An incomplete pack (e.g. 7/10) can be saved but must be visually marked as **incomplete** with a reason shown in the UI.
- ~~Pack lifecycle~~ — **Account-scoped persistent packs.** User accounts own packs. Phase 4 to define: pack browsing, upvote/downvote detail.

## Phase 4 Directive

The following are deferred to Phase 4 (Feature Scope) for detailed design — do not implement in v1:

- Pack browsing / discovery feed
- Comments on packs (v2 — significant scope and moderation complexity)

---

## UX Spec — Pack Builder

### Unauthenticated Landing State

Users who arrive without an account see a landing page with a sign-up / log-in CTA. They cannot access the lobby browser or pack builder until authenticated. Auth method TBD (Phase 5 — DB decisions phase).

### Screen: Pack Builder (Mobile-First)

```
Desktop:
┌──────────────────────────────────────────────────┐
│ [🐾 Mascot] [Pack Name (editable)] [Share][Hist] │
├────────────────────────┬─────────────────────────┤
│                        │  LIVE HISTORY           │
│   YOUR PACK            │  ● Zoe added Cricket    │
│                        │    to Tier 1 (3/10)     │
│   TIER 1  [■][■][■].. │  ● Alex removed Beaver  │
│            10 pets 3/10│    from Tier 2           │
│            [F][F][F]2/3│  ● Zoe renamed pack     │
│   TIER 2  [■][■][■].. │                         │
│            10 pets 0/10│                         │
│            [F][F][F]0/3│                         │
│   ...                  │                         │
│                        │                         │
│   Zoe · Alex · Crane + │                         │
├────────────────────────┴─────────────────────────┤
│   [Tier 1][2][3][4][5][6]                        │
│   Pets: [Pet][Pet][Pet]...  Food: [Food][Food]   │
└──────────────────────────────────────────────────┘

Mobile (history closed / open):
┌─────────────────────────────┐   ┌─────────────────────────┐
│ [🐾][Pack Name] [Share][☰] │   │  LIVE HISTORY        [✕] │
├─────────────────────────────┤   ├─────────────────────────┤
│ YOUR PACK                   │   │ ● Zoe added Cricket      │
│ TIER 1  [■][■][■]...        │   │   to Tier 1 (3/10)      │
│         10 pets 3/10        │   │ ● Alex removed Beaver    │
│         [F][F][F] 2/3       │   │   from Tier 2            │
│ ...                         │   │ ● ...                    │
│ Zoe · Alex · Crane +        │   │                         │
├─────────────────────────────┤   │                         │
│ [Tier 1][2][3][4][5][6]     │   │                         │
│ Pets: ...  Food: ...        │   └─────────────────────────┘
└─────────────────────────────┘
```

**Interaction model — pets:**

1. Tap a tier tab (1–6) to filter the pet and food grids to that tier
2. Tap a pet card → opens the pet detail sheet (see below)
3. Inside detail sheet: tap "Add to Tier N" → fills next empty slot; sheet closes
4. Tap a filled slot in YOUR PACK → removes that pet, slot empties
5. Pet cards in picker show selected state (glow) when already in the pack
6. Progress indicator (e.g. "3/10") shows how many pets selected in each tier

**Interaction model — food:**

7. Food shown below pets in the same tier tab view
8. Tap a food card → opens food detail sheet (same pattern as pets)
9. Inside detail sheet: tap "Add to Tier N" → fills next empty food slot; sheet closes
10. Tap a filled food slot in YOUR PACK → deselects that food

**Interaction model — general:**

11. Pack name inline-editable; auto-saves on blur; also renames the lobby
12. Mascot pet selector: tap the mascot icon in the header → opens pet picker to choose a mascot
13. Share button → copies lobby URL to clipboard; toast confirms
14. Collaborator list shows display names (e.g. "Zoe · Alex · Crane"); "+" shown if more than fit

### Pet Detail Sheet

Opened by tapping any pet card in the picker. Displayed as a bottom sheet on mobile, a modal on desktop.

```
┌─────────────────────────────┐
│ [Pet Image]                 │
│ Cricket          ATK 1 HP 2 │
│ Tier 1  · Turtle Pack       │
├─────────────────────────────┤
│ ABILITY                     │
│ Trigger: When this faints   │
│                             │
│ Level 1: Summon a 1/1       │
│          Cricket.           │
│ Level 2: Summon a 2/2       │
│          Cricket.           │
│ Level 3: Summon a 3/3       │
│          Cricket.           │
├─────────────────────────────┤
│ RELATED PERKS               │
│ ┌────────┐                  │
│ │ Peanut │ Give ...         │
│ └────────┘                  │
├─────────────────────────────┤
│ RELATED TOYS                │
│ (none)                      │
├─────────────────────────────┤
│      [Add to Tier 1]        │
└─────────────────────────────┘
```

- **Related perks and toys** are cross-referenced by name from ability text and shown as inline cards with their own descriptions. This requires perk descriptions to be extracted by the pipeline — **dependency: future pipeline phase.**
- "Add to Tier N" button is disabled if the tier is already full (10/10); shows "Tier N is full" instead.
- If pet is already in the pack, button reads "Remove from pack."

### Empty State (Fresh Pack)

A new pack starts with all 6 tiers visible, each showing "0/10 pets" and "0/3 food" with empty slot outlines. The picker below shows Tier 1 selected by default. The pack name starts as "Untitled Pack" and is immediately editable. Mascot defaults to a random pet.

### Error States

| Error | Trigger | UI response |
|---|---|---|
| Tier full | User tries to add pet/food to a full tier | "Add" button in detail sheet disabled; shows "Tier N is full" |
| WebSocket disconnected | Connection drops | Banner: "Connection lost — reconnecting…"; actions disabled until reconnected |
| Server rejection | Server rejects an action (race condition) | Toast: "Couldn't add [Pet] — Tier N is full" |
| Lobby not found | Expired or invalid lobby URL | Full-page error: "This lobby has expired." with CTA to create a new one |
| Auth required | Unauthenticated user tries to access builder | Redirect to landing/login page |

### Lobby System

A lobby system sits between the user and the pack builder. Two entry points coexist:

1. **Public lobby** — open the app, see active lobbies, join one
2. **Private lobby** — share a URL directly; lobby not listed in the browser

**User accounts:**
- Users create an account with a username — that username is their display name throughout the app
- No separate display name field; username and display name are one and the same
- Auth method TBD (Phase 5 — DB decisions phase)

**Lobby home screen:**

```
┌─────────────────────────────────────┐
│         Super Auto Pack Builder     │
│                          [+ Create] │
│                                     │
│  ACTIVE LOBBIES                     │
│                                     │
│  ┌──────────────────────────────┐  │
│  │ [🐾] "Tuesday team" 2 people │  │
│  │       3m ago                 │  │
│  └──────────────────────────────┘  │
│  ┌──────────────────────────────┐  │
│  │ [🐾] "Crane"        1 person │  │
│  │       11m ago                │  │
│  └──────────────────────────────┘  │
│  ...                                │
│                                     │
│  [Create private lobby instead]    │
└─────────────────────────────────────┘
```

"Active lobbies" = lobbies with at least one connection in the last hour (within expiry window). Each lobby card shows the mascot pet image, pack name, collaborator count, and time since last activity.

**Create lobby flow:**
1. Tap "+ Create" (or "Create private lobby instead" for a private lobby)
2. Enter pack/lobby name (optional — defaults to a random animal name, e.g. "Crane")
3. Immediately enter pack builder with a fresh pack; lobby is live and joinable
4. Lobby URL is a randomized slug (e.g. `/lobby/crane-7x2k`) — stable across renames
5. Private lobbies use the same slug model but are not listed in the lobby browser

**Join lobby flow:**
1. Tap a lobby card → enter that pack builder session
2. See current pack state + live collaborators immediately

**Leave lobby:**
- Closing the tab disconnects the user from the session
- No explicit leave button; idle disconnection is handled server-side
- Collaborator list updates in real-time as users join and leave

**Save to my account:**
- Any participant (including non-creators) can tap "Save to my account" in the lobby
- First press: creates a draft pack in their account linked to this lobby
- Subsequent presses in the same lobby: updates that draft with the current state
- Saved drafts appear in the user's own pack library, not the lobby browser

**Lobby auto-expiry:**
- Lobbies expire after **1 hour of inactivity** (no connections)
- After 1 hour of zero connections, the lobby and all its state are deleted
- Lobbies do NOT persist after expiry — no graveyard, no manual cleanup
- Packs saved to user accounts (via "Save to my account") are unaffected by lobby expiry

**Max collaborators:** 8 per lobby. Joining a full lobby shows: "This lobby is full (8/8)."

### Publish Flow

Publishing freezes the pack and makes it publicly browsable. It is a deliberate action separate from saving.

1. Creator taps "Publish" (available from within the lobby or from their pack library)
2. Confirmation modal: pack name, mascot, collaborator list shown for review
3. Confirm → pack is frozen; assigned a public URL (e.g. `/packs/crane-7x2k`)
4. Published pack appears in the community browser (Phase 4 to design this)
5. Collaborators are listed on the published pack page
6. Creator cannot edit the published pack — to iterate, they use "Fork to new draft"

**Fork:**
- Available on any published pack page
- Creates a new draft in the forker's account with the same pets/food/mascot
- The fork is a new independent pack; changes do not affect the original

### Import / Export

Uses SAP's native JSON format — compatible with packs players have already built in-game.

**Export format:**
```json
{
  "Title": "PackName",
  "Minion": 653,
  "Minions": [48, 232, 204, ...],
  "Spells": [117, 225, 136, ...]
}
```

- `Minion`: mascot pet `enumId`
- `Minions`: 60 `enumId`s — 10 pets × 6 tiers, in tier order (Tier 1 first)
- `Spells`: 18 `enumId`s — 3 food × 6 tiers, in tier order

**Import:** User pastes or uploads a JSON file. App validates the `enumId`s against known pets/spells, shows a preview, then loads into a new draft lobby.

**Export:** Available from the lobby header and from published pack pages. Copies JSON to clipboard or triggers a file download.

### Real-Time Collaboration

- On page load with lobby slug in URL: joins the existing lobby session
- On page load with no lobby ID (root URL): lands on the lobby browser
- Collaborators shown as display names in the header (e.g. "Zoe · Alex · Crane"); "+" if overflow
- All actions (pet select, deselect, rename, food add) broadcast to all participants instantly
- Conflict resolution: first-come first-served — server processes actions in order; rejected actions show an error toast to the acting user only
- Rejected actions do NOT appear in the live history feed

### Live History Feed

A real-time activity feed showing what is happening in the pack as it happens.

**Desktop:** Fixed panel on the right side of the screen, always visible alongside the pack builder.

**Mobile:** Slide-out drawer triggered by a history icon in the header. Overlay on top of the builder.

**Feed entries:**
```
● Zoe added Cricket to Tier 1 (3/10)
● Alex removed Beaver from Tier 2
● Zoe renamed pack to "Tuesday team"
● Zoe added Melon (food) to Tier 4 (1/3)
```

- Each entry timestamped (relative: "2s ago", "just now")
- Each user's entries shown in their assigned color (same color as their name in the header)
- Feed is scrollable within its window (up to ~50 entries)
- Entries beyond 50 fade out and are dropped from the top
- Feed is per-session only; not persisted

### Sharing Flow

1. User taps "Share" button
2. Current lobby URL copied to clipboard
3. Toast: "Link copied! Anyone with this link can edit the pack in real-time."
4. Recipient opens link → joins same lobby, sees current pack state immediately

---

## Data Access (API Shape Needed)

```
POST /api/lobbies             → { id, name, slug, mascotId }
POST /api/packs               → { id, name, tiers, mascotId, collaborators }
GET  /api/packs/:id           → { id, name, mascotId, tiers: { 1: { pets: petId[], food: foodId[] }, ..., 6: {...} }, collaborators: [] }
PUT  /api/packs/:id           → update full pack state (initial load / save flows only)
GET  /api/pets?tier=N         → [{ id, name, attack, health, ability, trigger, packs, ... }]
GET  /api/foods?tier=N        → [{ id, name, effect, ... }]  (rollable:true only — excludes ability-generated tokens)
GET  /api/perks               → [{ id, name, description, ... }]
WS   /ws/pack/:id             → real-time sync channel (granular patch operations)
```

> **Note for Dev Phase 2 (API Layer):** Real-time collaborative editing uses granular WebSocket patch operations, not full-document PUTs on every change. `PUT /api/packs/:id` is kept for initial load and explicit save flows only. WebSocket message format (envelope, event types, initial snapshot) to be defined in Dev Phase 2.

### Key Architectural Signals

| Signal | Implication |
|---|---|
| Live collaborative | WebSockets first-class from day one; Dev Phase 6/7 moves earlier |
| All 6 tiers always active | Pack summary shows all 6 tiers simultaneously; tier tabs filter the picker panel only |
| 10 pets + 3 food per tier | Fixed slot model — human verified against in-game pack builder and native export format |
| Publish model | Pack state must be immutable after publish; DB needs draft/published distinction |
| Mobile-first | Component layout must work at 375px width; bottom sheets for detail views |

---

## What I Learned

- **Specifying real-time collaboration at the design stage changes what the spec looks like.** Naming the conflict resolution strategy (first-come first-served, server-authoritative), the session model, and the API shape before a line of code exists forces precision that would otherwise be deferred and become a source of bugs.
- **Starting with the primary user goal reframes everything.** This started as "a wiki for SAP data" but the actual product is the pack builder. Once that flipped, the wiki became pure infrastructure, the tier structure became the core interaction model, and the UX made a lot more sense.
- **Import/export compatibility with the source game is a free win.** Because the game's native export format uses the same `enumId`s as our extraction pipeline, we get import/export compatibility with no extra data work. Design decisions that align with the source format reduce implementation cost.

## Evals

| Eval | File | Result |
|---|---|---|
| UX Design completeness | `docs/evals/product-phase-3-ux-design.md` | not-run |

## Related

- Product Phase 1 — Data Source and Discovery (`docs/phases/product-phase-1-data-source-and-discovery.md`)
- Product Phase 2 — Data Extraction Pipeline (`docs/phases/product-phase-2-data-extraction-pipeline.md`)
- Product Phase 4 — Feature Scope (`docs/phases/product-phase-4-feature-scope.md`) (next up)
