# Super Auto Pets Full Website — Project Charter

## Purpose

This project exists primarily as a **learning vehicle**. Getting the product shipped matters, but if the process doesn't grow your skills and your ability to work with AI effectively, the project has failed. Every phase should produce documented knowledge, not just working code.

---

## Core Learning Goals

| # | Goal |
|---|------|
| 1 | Grow TypeScript proficiency through real use |
| 2 | Evaluate and learn Drizzle ORM (decision to be made in Product Phase) |
| 3 | Learn DevOps from scratch — trial by fire, AI-assisted |
| 4 | Develop better AI context management strategies for professional use |

---

## Product Summary

A data-focused wiki/tooling site for Super Auto Pets, built by decompiling the game files. The site will expose structured game data via a proper API, provide a clean frontend, support real-time features (websockets, pack builder), and include a full DevOps pipeline. Everything is self-hosted and fully owned.

---

## Decided Architecture

These decisions are locked in and do not need a phase discussion.

| Decision | Choice | Reason |
|---|---|---|
| Repo structure | Monorepo | Keeps AI context unified across the stack; simpler cross-package tooling |

---

## Phase Overview

Phases are meant to be worked through in order. Each phase should produce a **Phase Results document** stored in `docs/phases/` so we can reference decisions later without re-litigating them.

---

### Phase 0 — Continuous: Learning Documentation

> Runs alongside every other phase. Never ends.

- Document everything learned as it is learned.
- These notes are resume material. Write them as if explaining to a future interviewer.
- Store in `docs/learning/`.

> **Prerequisite before Phase 1:** Review Team Wood's Terms of Service to understand what is and isn't permitted around game file decompilation and public hosting of derived data. Do not begin Product Phase 1 until this is done.

---

### Product Phases — Discovery & Design

These phases produce decisions, not code.

**Phase 1 — Data Source & Discovery**
- All data will be pulled directly from decompiled game files.
- What decompiler do we use? What format does the output come in?
- What game data do we want to expose to end users?
- What is actually available from the decompiled output?
- Note: these two questions are iterative — what we want informs what we look for, and what we find informs what's possible. Treat this as one conversation, not two sequential steps.
- Deliverables: data pipeline strategy doc + data schema spec doc.

**Phase 2 — UX Design**
- What does the user experience look like?
- Mobile-first? Desktop? Both?
- Deliverable: wireframes or written UX spec.

**Phase 3 — Feature Scope**
- What features does the site have at launch vs. later?
- Enumerate and prioritize all features here, not just the pack builder.
- Deliverable: feature list with priority tiers.

**Phase 4 — Collaborative Pack Builder**
- Real-time, multi-user pack editing (webhook-lobby style).
- Goal: usable on mobile, shared with others (e.g., building a pack with a partner).
- Deliverable: feature spec for pack builder.

**Phase 5 — Database Infrastructure**
- What DB do we use? (Drizzle ORM is a candidate — evaluate during this phase)
- Deliverable: DB decision doc.

**Phase 6 — Hosting & Pricing**
- Where do we host? Likely Railway or Render for v1 — learning focus, not cost optimization.
- What does the pricing model look like at various scales?
- Deliverable: hosting decision doc.

**Phase 7 — CI/CD Tooling**
- What pipeline tooling do we use?
- Deliverable: CI/CD decision doc.

**Phase 8 — Reverse Proxy**
- What reverse proxy do we use?
- Deliverable: reverse proxy decision doc.

**Phase 9 — Versioning & Changelog**
- On new game version: detect, decompile, auto-generate changelog from diff of game data.
- Changelog must be derived entirely from our decompiled results — not from external patch notes.
- Deliverable: changelog strategy doc.

---

### Pre-Dev Setup

> Everything in this section happens before any other phase begins — including Product Phases. Work through these in order.

**Setup 1 — Documentation Standards & AI Skills**
- Define templates for: phase docs, learning notes, evals.
- Define naming conventions (see Phase Results Storage in Task & Project Management below).
- Create `CLAUDE.md` at the repo root encoding project conventions, AI behavior expectations, and context guidelines. Add package-level `CLAUDE.md` files as packages are created.
- Define eval standards: what an eval covers, how it's structured, where it lives, and when it runs. Evals are how AI validates its own output — without a standard they become inconsistent and useless.
- Write AI skills (Claude Code slash commands) for:
  - Creating a new phase doc from template
  - Adding a learning note
  - Marking a phase complete
  - Creating a new eval from template
- Deliverable: templates committed to `docs/templates/`, skills committed to `.claude/skills/`, root `CLAUDE.md` committed.

**Setup 2 — Task Management**
- Create GitHub Project board with Kanban columns.
- Create Milestones for each phase.
- Configure GitHub MCP server in Claude settings with a personal access token scoped to this repo.
- Verify AI can open, update, and close issues through the MCP before proceeding.

**Setup 3 — Linting**
- Decide on package manager (npm / pnpm / yarn) and Node version — lock both in before any other tooling is installed.
- Set up linting for everything in the monorepo, enforced consistently across all packages.

**Setup 4 — Testing Infrastructure**
- Unit and integration test framework in place before services are built.
- E2E framework (Playwright or equivalent) configured.
- Tests do not need to exist yet — the infrastructure and conventions do.

---

### Development Phases — Building

**Dev Phase 0 — Docker**
- Dockerfile to containerize the entire project.
- All tooling (decompiler, etc.) runs inside the container so nothing pollutes the host machine.

**Dev Phase 1 — Game File Pipeline**
- Scripts to: download game files → decompile → extract target data → store.
- Runs inside Docker.

**Dev Phase 2 — API Layer (Backend)**
- NodeJS API to serve pet/game data.
- Setup Postman for manual testing.
- Swagger (or equivalent) for API visualization.
- Explore Postman API visualization as an alternative/addition.

**Dev Phase 3 — Error Logging & Alerting**
- Full observability stack: human-readable AND AI-readable logs.
- Real-time phone alerts for critical errors (this is the production-grade target).
- Deliverable: logging system that works the way a real prod system would.

**Dev Phase 4 — Frontend**
- Consumes the API, displays data to users.
- This is where the user specializes — keep AI interaction tight and focused here; use this phase to practice AI collaboration patterns.
- **Step 1 — Design System**: Build a fully accessible design system with CSS variables. Goal: fast to build, reusable, WCAG-compliant.
- **Step 2 — Feature Implementation**: Build all scoped features using the design system.

**Dev Phase 5 — CronJobs (Auto-Update)**
- Implements the strategy defined in Product Phase 9 (Versioning & Changelog) — read that doc before starting.
- Weekly (or on-demand) cron to re-fetch and decompile the game.
- Version check first — skip decompile if version hasn't changed.

**Dev Phase 6 — Redis**
- Solves: API response caching, websocket pub/sub for the pack builder across server instances, async job queuing for decompile pipeline.
- Deliverable: Redis integrated and actively solving at least one of the above problems.

**Dev Phase 7 — WebSockets**
- Monitor active users.
- Push notifications when a new patch drops.

**Dev Phase 8 — MCP Server**
- Expose an MCP server so an AI can communicate with the site.
- High resume value — document this phase thoroughly.

---

### Long-Term / Stretch Phases

**LT Phase 1 — VPS Migration**
- Move off Railway/Render onto a VPS for deeper infrastructure learning.

**LT Phase 2 — Terraform**
- Learn and implement Terraform for infrastructure as code.

---

## Task & Project Management

| Concern | Tool |
|---|---|
| Granular tasks & kanban board | GitHub Projects |
| Phase progress & decisions | `docs/phases/` documents |
| Learning notes | `docs/learning/` |
| AI task interaction | GitHub MCP server |

### GitHub Projects Workflow

- Each phase gets a **Milestone** in GitHub.
- Tasks within a phase are **Issues** assigned to that Milestone.
- PRs reference their issue (`closes #42`) so the board updates automatically when work merges.
- The board reflects current state; `docs/phases/` is the permanent record.

### Phase Results Storage

Phase docs live in `docs/phases/` and use a category prefix to avoid naming collisions:

```
docs/phases/product-phase-<n>-<slug>.md
docs/phases/dev-phase-<n>-<slug>.md
docs/phases/tooling-phase-<n>-<slug>.md
```

Examples:
- `docs/phases/product-phase-6-hosting-decision.md`
- `docs/phases/dev-phase-2-api-layer.md`

Each phase doc carries a status header:

```markdown
---
phase: product-6
status: in-progress
started: 2026-03-24
completed:
---
```

Statuses: `not-started` | `in-progress` | `complete`

The phase doc is both the deliverable and the status tracker. GitHub Milestones show task-level completion; the phase doc shows whether the phase itself is done and what was decided.

---

## AI Design Principles

The goal is for AI to **build in** — extending and integrating with what already exists — not to **pile on** new layers. This requires:

- Comprehensive evals and tests so regressions are caught immediately.
- Consistent code standards and linting so AI output is predictable.
- Well-maintained `CLAUDE.md` files at the repo and package level.
- Custom commands and skills that encode project-specific patterns.
- Context management discipline: prune aggressively, keep context relevant to the current phase.

---

## A Note

This is intentionally ambitious and verbose. That is the point. The goal is not to ship fast — it is to learn deeply and build something worth putting on a resume.
