---
name: new-eval
description: Create a new eval document from the template. Use when a phase is nearing completion and needs an eval before it can be marked done.
---

Create a new eval document from the template at `docs/templates/eval.md`.

Arguments: $ARGUMENTS
Format: `<phase-slug> <concern>`
Examples: `product-phase-6 cost-model`, `dev-phase-2 api-contract`

Steps:
1. Parse $ARGUMENTS to extract the phase slug (first word) and concern (remaining words joined with hyphens if multiple words).
2. Construct the file path: `docs/evals/<phase-slug>-<concern>.md`
3. Check if a file already exists at that path. If it does, tell the user and stop.
4. Read `docs/templates/eval.md`.
5. Create the new file at the constructed path. Fill in:
   - `eval-for` → the phase slug
   - `date` → today's date in YYYY-MM-DD format
   - `status` → `not-run`
   - The title heading → a human-readable title derived from the concern (un-hyphenate and title-case)
6. Confirm the file was created and show the full path.
7. Remind the user to link this eval in the relevant phase doc's Evals table.
