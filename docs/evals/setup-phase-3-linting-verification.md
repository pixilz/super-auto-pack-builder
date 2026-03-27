---
eval-for: setup-phase-3
date: 2026-03-27
last-run: 2026-03-27T05:50:59
---

# Eval — Linting Verification

## What This Eval Covers

Verifies all linters are installed, configured, and run cleanly inside Docker against the current codebase.

## Why This Eval Exists

Linting standards must be confirmed working before code is written. A linter that's installed but misconfigured or silently skipping files provides no value.

## How to Run

The AI will generate a script and ask you to run it. Output will be saved to `tmp/`.

## Checks

| # | Check | Expected |
|---|---|---|
| 1 | `pnpm lint:js` exits with 0 | No ESLint errors |
| 2 | `pnpm lint:css` exits with 0 | No Stylelint errors |
| 3 | `pnpm lint:ts` exits with 0 | No TypeScript type errors |
| 4 | `pnpm lint:md` exits with 0 | No Markdownlint errors |
| 5 | `hadolint Dockerfile` exits with 0 | No Dockerfile lint errors |
| 6 | `pnpm lint:full` exits with 0 | All linters pass in sequence |

## Pass Criteria

All checks must pass.

## Notes

Backfilled eval — phase was completed on 2026-03-26 without a formal eval.
