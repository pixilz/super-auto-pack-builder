---
topic: github-projects-v2-graphql
date: 2026-03-25
tags: [github, graphql, rest-api, mcp, tooling]
---

# GitHub Projects V2 and the GraphQL-Only Wall

## What I Learned

GitHub has two generations of project boards:

**Projects Classic (v1)** was built on GitHub's REST API. Third-party tools, the `gh` CLI, and integrations could manage it directly — creating columns, moving cards, updating items — all via standard HTTP calls.

**Projects (v2)** — the current version — was rebuilt from the ground up and is **GraphQL-only**. There are no REST endpoints for board-level operations. To add an item to a project, move a card, or create a column, you must use GitHub's GraphQL API with a project node ID.

This matters because most GitHub integrations — including the MCP server used in this project — are built on the REST API. They can fully manage issues, PRs, branches, and files, but they hit a hard wall when you ask them to touch the Projects board.

In practice this means:
- Creating an issue via the MCP works fine
- Assigning that issue to a milestone via the MCP works fine
- Moving that issue's card on the Projects board requires GraphQL — which the MCP doesn't support

## Why It Matters

This is a real-world constraint that comes up any time you're building automation or AI tooling around GitHub. Understanding *why* something doesn't work (API architecture, not a missing feature) is more useful than just knowing it doesn't work.

For this project: the workaround is that the AI creates and closes issues (which reflect milestone progress), and the human manually moves cards on the board. This keeps the automation where it works and the human in the loop where it doesn't.

## Key Takeaways

- GitHub Projects v2 is GraphQL-only — no REST endpoints for board operations
- Most GitHub tooling (including MCP servers) targets REST, so board automation requires extra work
- Milestones are REST-accessible and show % complete, but they're not the same as board columns
- Issues assigned to milestones are the bridge between REST tooling and the Projects board

## Resources

- [GitHub GraphQL API docs — Projects](https://docs.github.com/en/graphql/reference/objects#projectv2)
- [GitHub REST API docs](https://docs.github.com/en/rest)

## Questions Still Open

- Is there a community MCP server that wraps the GitHub GraphQL API for Projects v2?
- Would it be worth building one as a stretch goal in Dev Phase 8 (MCP Server)?
