---
eval-for: setup-phase-4
date: 2026-03-27
last-run: 2026-03-27T05:50:59
---

# Eval — Test Runner Verification

## What This Eval Covers

Verifies that both test runners (Vitest and Playwright) are correctly installed, configured, and executable inside their respective Docker containers.

## Why This Eval Exists

Test infrastructure that can't run inside Docker is useless — CI will run in Docker. This eval confirms the runners work end-to-end in the actual execution environment before any real tests are written against real code.

## How to Run

The AI will generate a script and ask you to run it. Output will be saved to `tmp/`.

## Checks

| # | Check | Expected |
|---|---|---|
| 1 | `pnpm test` runs inside the app container | Exits with 0, 1 test passes |
| 2 | `pnpm test:e2e` runs inside the playwright container | Playwright launches, finds the test file, attempts to connect |
| 3 | E2E failure is `ERR_CONNECTION_REFUSED`, not a framework error | Error is `net::ERR_CONNECTION_REFUSED at http://localhost:3000/` |
| 4 | Both `test` and `test:e2e` scripts exist in `package.json` | Scripts present and correct |

## Pass Criteria

All checks must pass. Check 2 and 3 explicitly allow a test *failure* — what matters is that Playwright runs and fails for the right reason (no app), not a framework or config error.

## Notes

The E2E example test will fail until an app is running on localhost:3000. This is expected and not a blocker for closing this phase.
