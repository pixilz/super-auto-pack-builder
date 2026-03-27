---
eval-for: <phase-or-feature-slug>
date: <YYYY-MM-DD>
last-run: <YYYY-MM-DDThh:mm:ss or never>
---

# Eval — <Title>

## What This Eval Covers

Describe the scope: which decisions, outputs, or behaviors this eval is checking.

## Why This Eval Exists

What risk or assumption motivated creating this eval? What would go wrong if this weren't checked?

## How to Run

Step-by-step instructions for executing this eval. Include commands, manual steps, or both. Anyone should be able to reproduce this without asking for help.

If any checks require Docker or other commands the AI cannot run, the AI will generate a script, write it to `tmp/`, and ask the user to run it. Output is captured to `tmp/eval-<phase-slug>-<concern>-<timestamp>.txt` so the AI can read it and determine pass/fail. Scripts are generated fresh each time and are not stored permanently.

The `last-run` frontmatter field records the timestamp of the most recent run and corresponds to the output file for that run.

```bash
# example commands
```

## Checks

Each check is a specific, testable claim. Pass/fail is determined by reading the output file — not recorded in this document.

| # | Check | Expected |
|---|---|---|
| 1 | | |
| 2 | | |

## Pass Criteria

All checks must pass. Document any intentional exceptions here with justification. An undocumented exception is a failure.

## When to Re-run

An eval result is a snapshot in time, not a permanent pass. Re-run this eval if:

- Any of the tools, config files, or infrastructure it covers are modified
- A new phase touches the outputs of this phase
- Something breaks and you want to confirm where it broke

## Notes

Anything surprising, ambiguous, or worth flagging for the next time this eval runs.
