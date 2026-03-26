---
phase: dev-phase-0
status: in-progress
started: 2026-03-25
completed:
---

# Dev Phase 0 — Docker

## Goal

Create a Dockerfile that containerises the project so all tooling runs inside the container and nothing is installed directly on the host machine.

## Context

Claude runs inside yolobox — a Docker container running inside WSL. The user also has a Windows host. Rather than installing project tooling in three places, everything runs inside a project-specific Docker image. This means Dev Phase 0 is a prerequisite for Setup Phase 3 (Linting) — linting tools get installed inside the container, not locally.

This also sets the pattern for all future tooling: if it's part of the project, it lives in the Dockerfile.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Phase order | Dev Phase 0 before Setup Phase 3 | Claude runs in Docker (yolobox/WSL); installing tooling locally first would mean doing it twice |

## Deliverables

- [ ] Define container structure and working directory (#11)
- [ ] Decide how host filesystem is exposed to the container (#12)
- [ ] Verify container builds and runs (#13)

Note: runtime (Node/Bun/etc.) and package manager are decided in Setup Phase 3 and folded back into the Dockerfile as part of that phase.

## Open Questions

- What base image? (Node LTS Alpine is a common lightweight starting point)
- How does the container interact with the host filesystem for game files?

## What I Learned

_To be filled in._

## Evals

| Eval | File | Result |
|---|---|---|
| — | — | — |

## Related

- [Setup Phase 3 — Linting](setup-phase-3-linting.md)
