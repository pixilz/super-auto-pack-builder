---
eval-for: dev-phase-0
date: 2026-03-27
last-run: 2026-03-27T05:50:59
---

# Eval — Docker Verification

## What This Eval Covers

Verifies the Docker setup is correct — the image builds, the container runs commands, and the bind mount works.

## Why This Eval Exists

All project tooling runs inside Docker. If the container doesn't build or the volume mount is broken, nothing else works. This eval confirms the foundation is solid.

## How to Run

The AI will generate a script and ask you to run it. Output will be saved to `tmp/`.

## Checks

| # | Check | Expected |
|---|---|---|
| 1 | `docker compose build app` exits with 0 | Build succeeds with no errors |
| 2 | `node --version` inside container returns a version | `v22.x.x` or higher |
| 3 | `pnpm --version` inside container returns a version | `9.15.9` |
| 4 | `node_modules` is visible inside the container | `ls node_modules` lists packages — should include vitest, @playwright, eslint |

## Pass Criteria

All checks must pass.

## Notes

Backfilled eval — phase was completed on 2026-03-26 without a formal eval.
