---
phase: setup-phase-4
status: complete
started: 2026-03-26
completed: 2026-03-27
---

# Phase 4 — Testing Infrastructure

## Goal

Get unit/integration and E2E test frameworks installed and verified running inside Docker before any packages are built.

## Context

Tests need a home before code does. Retrofitting a test framework onto existing code is painful — you end up wrestling with module resolution and config instead of writing tests. This phase gates all development phases.

Setup Phase 3 (Linting) must be complete first — linting and testing config go hand in hand and both need to be in place before services are built.

## Decisions Made

| Decision | Choice | Rationale |
|---|---|---|
| Unit/integration framework | Vitest 4.x | First-class ESM and TypeScript support, native pnpm workspace integration, no Node 24 bugs unlike Jest, zero transform config |
| E2E framework | Playwright | Current industry standard for new projects |
| Jest | Not chosen | ESM still requires `--experimental-vm-modules`, active Node 24 bug in config parsing, needs manual TypeScript transform config |
| Playwright Docker setup | Separate service with `Dockerfile.e2e` | Keeps main app image lean; browser binaries (~400-600MB each) live in dedicated `super-auto-e2e-tests` image built from `mcr.microsoft.com/playwright:v1.58.2-noble` |
| Playwright browser | Chromium only | Sufficient for this project; multi-browser support can be added later via `projects` in `playwright.config.ts` |
| E2E test file suffix | `.spec.ts` | Distinct from Vitest's `.test.ts`, no overlap between runners |

## Deliverables

- [x] Install and configure Vitest at the monorepo root
- [x] Write an example unit test and verify it runs inside Docker
- [x] Install and configure Playwright
- [x] Write an example E2E test and verify it runs inside Docker
- [x] Add `test` and `test:e2e` scripts to `package.json`

## Open Questions

- Should Playwright run in headless mode only, or do we want a headed mode for local debugging?

## What I Learned

- Vitest and Jest have identical APIs — if you know Jest, you know Vitest. The difference is ESM/TypeScript support out of the box.
- Playwright browser binaries are large (~400-600MB each); keeping them in a separate Docker service is the standard pattern.
- The official Playwright image is on MCR (`mcr.microsoft.com/playwright`), not Docker Hub. Pin the image version to match the installed `@playwright/test` version.
- `tail -f /dev/null` keeps a Docker container alive with no long-running process.
- Docker Compose tries to pull an image before building it. The "pull access denied" warning on first run is expected — it disappears after the image is built and cached locally.
- Running containers before `DOCKER_UID`/`DOCKER_GID` are set creates root-owned files on bind-mounted volumes. Fix with `sudo chown -R $USER:$USER node_modules`.

## Evals

| Eval | File | Result |
|---|---|---|
| Test Runner Verification | `docs/evals/setup-phase-4-test-runner-verification.md` | last-run: 2026-03-27T11:37:43 |

## Related

- [Setup Phase 3 — Linting](setup-phase-3-linting.md)
