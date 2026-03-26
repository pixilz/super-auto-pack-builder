Start a phase by creating a GitHub issue for each task and assigning them to the correct milestone.

Arguments: $ARGUMENTS
Format: `<category>-phase-<n>-<slug>`
Examples: `setup-phase-3-linting`, `product-phase-1-data-source-discovery`

Steps:
1. Construct the file path: `docs/phases/<arguments>.md`
2. Read the file. If it does not exist, tell the user and stop.
3. Check the current `status` in the frontmatter:
   - If `complete`, tell the user the phase is already done and stop.
   - If `not-started`, update `status` to `in-progress` and set `started` to today's date.
   - If `in-progress`, note that the phase is already started and continue.
4. Look up the milestone number for this phase from memory (reference_milestones.md). If not found, ask the user for the milestone number before continuing.
5. Read the phase doc's **Deliverables** section. Based on the deliverables, propose a list of discrete GitHub issues — one issue per concrete task. Each proposed issue should have:
   - A short, action-oriented title (e.g. "Decide on package manager and Node version")
   - A one-sentence description
   Display the full proposed list and ask the user to confirm, remove, or add items before proceeding.
6. Once the user confirms the list, create each issue via the GitHub MCP (`owner: pixilz`, `repo: super-auto-pack-builder`) assigned to the milestone number from step 4.
7. Report the created issue numbers and titles.
8. Remind the user to add the issues to the project board ("Super Auto Pack Builder") since the board cannot be updated automatically.
