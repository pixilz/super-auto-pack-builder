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
| | | |

## Deliverables

- [ ] Data pipeline strategy doc — how game files are obtained, decompiled, and processed
- [ ] Data schema spec doc — what data we expose and in what shape

## Open Questions

- What decompiler do we use?
- What format does the decompiled output come in?
- What game data do we want to expose to end users?
- What is actually available from the decompiled output?

## What I Learned

_To be filled in._

## Evals

| Eval | File | Result |
|---|---|---|
| | | |

## Related

- [Dev Phase 1 — Game File Pipeline](dev-phase-1-game-file-pipeline.md)
