Mark a phase document as complete by updating its frontmatter.

Arguments: $ARGUMENTS
Format: `<category>-phase-<n>-<slug>`
Examples: `product-phase-6-hosting-decision`, `setup-phase-1-docs-standards-ai-skills`

Steps:
1. Construct the file path: `docs/phases/<arguments>.md`
2. Read the file. If it does not exist, tell the user and stop.
3. Check the current `status` in the frontmatter:
   - If already `complete`, tell the user and stop.
   - If `not-started`, warn the user that the phase was never marked in-progress and ask them to confirm before proceeding.
4. Check if `started` is blank. If it is, ask the user for the start date (YYYY-MM-DD) before proceeding.
5. Update the frontmatter:
   - Set `status` to `complete`
   - Set `completed` to today's date in YYYY-MM-DD format
6. Confirm the update and display the updated frontmatter block.
7. Update `CURRENT.md`:
   - Move this phase from the Active Phase section into the Recently Completed table
   - Clear the Active Phase and Blocking Decisions sections (leave them blank until the next phase starts)
8. Run `git diff HEAD` to see what has changed. Draft a commit message based on the actual diff. Format:
   - Subject line: `docs: mark <phase-id> complete` (e.g. `docs: mark setup-phase-1 complete`)
   - Body: 2–4 bullet points summarising the meaningful changes visible in the diff.
   Display the commit message for the user to copy.
