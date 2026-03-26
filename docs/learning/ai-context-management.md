---
topic: ai-context-management
date: 2026-03-25
tags: [ai, context-management, claude, workflow, skills, architecture]
---

# AI Context Management — Building Systems Agents Can Navigate

## What I Learned

When working with AI agents on long-running projects, the biggest failure mode is **context loss**. A new conversation, a cleared session, or a fresh agent starts with nothing. If the project's state only exists in conversational history, the agent has to guess, ask, or reconstruct everything from scratch — and it will get things wrong.

The solution is to treat context as a system you design, not something that happens naturally. Every piece of information an agent needs should have a **durable, discoverable home**.

Here's what that looks like in practice, broken into layers:

---

### Layer 1: Principles and Conventions — CLAUDE.md

`CLAUDE.md` loads automatically at the start of every session. It should contain:
- What the project is and what it's trying to achieve
- How AI should behave (build in, not pile on; ask before expanding scope)
- Folder conventions and naming standards
- Where to look for more context

**What it should NOT contain:** workflow steps, procedures, or task-specific instructions. Those belong in skills. CLAUDE.md should stay lean — it loads every session, so bloating it degrades every conversation.

---

### Layer 2: Live Project State — CURRENT.md

A new agent reading only CLAUDE.md knows the conventions but not where the project is *right now*. `CURRENT.md` fills that gap:
- Which phase is active
- Which GitHub issues are open
- What decisions are blocking progress

CLAUDE.md tells every agent to read `CURRENT.md` first. Skills that start or complete phases update it automatically. This means any agent can orient itself in under a minute without asking the user.

---

### Layer 3: Permanent Decision Record — Phase Docs

Phase docs in `docs/phases/` are the long-term memory of the project. Each one records:
- What was decided and why
- What was built
- What was learned

When a new agent needs to understand a past decision, it reads the phase doc — not the user's memory. This prevents decisions from being relitigated and ensures consistency across agents and sessions.

---

### Layer 4: Task Discoverability — GitHub Issues and Milestones

GitHub issues are the canonical task list. They are:
- Queryable by an agent via the MCP at any time
- Tied to a milestone (phase) so the agent knows what phase they belong to
- Closeable as work completes, keeping the open list accurate

The combination of CURRENT.md (which lists open issue numbers) and GitHub (which holds the live state) means an agent can always answer "what is left to do in this phase?" without relying on the user to remember.

---

### Layer 5: Consistent Procedures — Skills

Skills encode *how* to do recurring tasks — not just what to do. Without skills:
- One agent creates a phase doc with the wrong format
- Another forgets to update CURRENT.md when closing an issue
- A third skips the eval before marking a phase complete

With skills, the procedure is written down and Claude triggers it automatically when the situation matches the description. The agent doesn't need to know the procedure from memory — it just needs to recognise when to reach for the skill.

Skills live in `.claude/skills/<name>/SKILL.md`. The `description` field is critical: Claude uses it to decide when to invoke the skill. A vague description means the skill gets missed or triggered at the wrong time.

---

### Layer 6: Output Verification — Evals

Context management ensures agents know *what* to do and *how* to do it. Evals answer a different question: **did the agent actually do it correctly?**

AI output can look correct without being correct. A phase doc can be filled in, issues can be created, linting can appear to be configured — and still have subtle errors that only surface three phases later when something breaks in an unexpected way.

Evals are structured, pass/fail checks written before a phase is marked complete. Each eval covers a specific concern and defines explicit criteria — not "does this look right?" but "does `npm run lint` exit 0 on a file with a known error?"

Without evals:
- Phases get marked complete based on vibes
- Mistakes compound silently across phases
- The cost of catching errors grows the later you find them

With evals:
- Every phase has a documented definition of done
- Regressions are caught at phase boundaries, not three phases later
- The eval doc becomes part of the permanent record — future agents can re-run it

Evals live in `docs/evals/<phase-slug>-<concern>.md`. The `/new-eval` skill creates them from a template. A phase is not complete until its evals pass.

---

### Layer 7: User Preferences and Feedback — Memory Files

Memory files (in `~/.claude/projects/.../memory/`) persist across conversations at the user level. They capture:
- How the user likes to work
- Corrections to past AI behaviour
- Project-specific constraints that aren't in the codebase

These are different from phase docs — they're about the *collaboration*, not the *project*. An agent that reads them can avoid repeating past mistakes and tailor its communication style to the user.

---

## The Core Principle

**Never rely on a single agent having full conversational history.**

Every piece of context needs a durable home:

| Context type | Where it lives |
|---|---|
| Conventions and principles | `CLAUDE.md` |
| Current project state | `CURRENT.md` |
| Past decisions | `docs/phases/` |
| Open tasks | GitHub issues |
| Procedures | `.claude/skills/` |
| Output verification | `docs/evals/` |
| User preferences | Memory files |

If information only exists in chat history, it will be lost.

---

## Why It Matters

This is directly applicable to any professional AI-assisted project. Teams that treat AI as a stateless tool that needs to be re-briefed every session waste enormous amounts of time. Teams that build context infrastructure — even lightweight versions of what's described here — get consistent, compounding output across sessions and across team members.

It's also a pattern that transfers to building AI products: any system where an AI agent needs to operate reliably over time needs the same layers — state management, task tracking, procedure encoding, and persistent memory.

## Key Takeaways

- CLAUDE.md is for conventions, not procedures — keep it lean
- CURRENT.md solves the "where are we?" problem for every new agent
- Phase docs prevent decisions from being relitigated
- GitHub issues make tasks discoverable without relying on human memory
- Skills enforce consistent procedures across agents and sessions
- Evals are the definition of done — a phase isn't complete until they pass
- Memory files capture the collaboration layer that the codebase can't

## Resources

- [Claude Code Skills docs](https://code.claude.com/docs/en/skills)
- [Claude Code Memory docs](https://code.claude.com/docs/en/memory)

## Questions Still Open

- At what project scale does this system start to break down? (Too many skills? Too many phase docs to load?)
- Is there a better pattern for the CURRENT.md → GitHub issues handoff, or should CURRENT.md just point to GitHub entirely?
