---
name: new-phase-doc
description: Create a new phase document from the template. Use when starting work on a phase that doesn't have a phase doc yet.
---

Create a new phase document from the template at `docs/templates/phase-doc.md`.

Arguments: $ARGUMENTS
Format: `<category> <n> <slug>`
Examples: `product 6 hosting-decision`, `dev 2 api-layer`, `setup 2 task-management`

Steps:
1. Parse $ARGUMENTS to extract: category (e.g. `product`, `dev`, `setup`, `lt`), phase number n, and slug.
2. Construct the file path: `docs/phases/<category>-phase-<n>-<slug>.md`
3. Check if a file already exists at that path. If it does, tell the user and stop.
4. Read `docs/templates/phase-doc.md`.
5. Create the new file at the constructed path. Replace template placeholders:
   - `<category-phase-n>` → `<category>-phase-<n>`
   - `<N>` → the phase number
   - `<Title>` → a title derived from the slug (un-hyphenate and title-case it)
   - Set `status` to `not-started`, leave `started` and `completed` blank.
6. Confirm the file was created and show the full path.
