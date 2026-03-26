---
name: close-issue
description: Close a GitHub issue and update CURRENT.md. Use this when work described in a GitHub issue has been completed — the implementation is done, committed, and verified.
---

Close a GitHub issue and update CURRENT.md to reflect the completed work.

Arguments: $ARGUMENTS
Format: `<issue-number>`
Example: `3`

Steps:
1. Close issue $ARGUMENTS via the GitHub MCP (`owner: pixilz`, `repo: super-auto-pack-builder`, `state: closed`, `state_reason: completed`).
2. Remove issue #$ARGUMENTS from the open issues list in `CURRENT.md`.
3. Confirm the issue is closed and CURRENT.md is updated.
4. Remind the user to move the card on the project board ("Super Auto Pack Builder").
