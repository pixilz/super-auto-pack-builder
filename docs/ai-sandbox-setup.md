# AI Agent Docker Sandbox — Research & Setup Guide

## Background

This document covers research into open source Docker sandboxes for running AI coding agents (Claude Code, Gemini CLI, etc.) in "yolo mode" (`--dangerously-skip-permissions`) more safely on Windows/WSL2.

---

## Using a Company's Internal Tool

If your employer has an internal sandbox tool, even if they call it "open source", do not use it on your personal machine unless it has been publicly released under an open source license. Key risks:

- Copying internal tooling to a personal machine may violate your employment agreement
- Internal tooling often embeds config, registry URLs, internal hostnames, or credentials
- If you build something personal with it and your contract has an IP assignment clause, that personal project could become complicated

**Use a public alternative instead.** They cover the same ground.

---

## Tools Evaluated

### 1. yolobox — Recommended
**Repo:** https://github.com/finbarr/yolobox

A community-built Docker sandbox specifically for running AI agents in yolo mode. 532 stars, actively maintained.

**What it includes out of the box:**
- Node.js 22, Python 3, Bun, Go
- pnpm, yarn, npm, uv (Python)
- Claude Code, Gemini CLI, OpenAI Codex, GitHub Copilot, OpenCode — all pre-configured for full-auto mode
- Git, GitHub CLI, Docker CLI, ripgrep, fzf, jq, and other utilities
- UID/GID remapping to handle host permission mismatches

**Gaps:**
- No Volta
- No persistent AI memories out of the box
- Windows/WSL2 not explicitly documented (works via WSL terminal in practice)
- Pulls a pre-built image from `ghcr.io` by default with no signature verification

---

### 2. deva.sh
**Repo:** https://github.com/thevibeworks/claude-code-yolo

Multi-agent focused. Auto-links auth homes for Claude/Codex/Gemini into a shared config dir. Thinner documentation, less community traction than yolobox.

---

### 3. Docker Sandboxes (Official)
**Docs:** https://docs.docker.com/ai/sandboxes/

Docker Inc.'s own sandbox product. MicroVM-based (stronger isolation than plain containers). Supports Claude Code, Gemini, Codex, Copilot, and others.

**Why it loses for this use case:**
- Windows support is listed as experimental
- Pre-installed tooling not documented
- Less control/customization than yolobox

---

## Security Analysis of yolobox

### install.sh (runs on your host machine) — Low risk
- Downloads a pre-built binary from GitHub releases or builds from source with Go
- No curl|bash patterns
- No phone-home or host modifications beyond placing a binary in `~/.local/bin`

### Dockerfile (runs inside the container) — Two things to note

1. `curl -fsSL https://claude.ai/install.sh | bash` — how Anthropic distributes the Claude CLI. Expected, but unverified execution.
2. `curl -fsSL https://deb.nodesource.com/setup_22.x | bash` — standard Node.js install method, widely used but also unverified.

Both are common in the Docker ecosystem. Neither is a red flag given the context, but neither has cryptographic verification.

### Pre-built image concern
By default yolobox pulls `ghcr.io/finbarr/yolobox:latest` — a pre-built image maintained by one person, with no image signing or provenance attestation. You cannot verify this image was built from the Dockerfile you reviewed.

**Mitigation: build the image locally from the Dockerfile you've audited.** See setup steps below.

### No telemetry or phone-home detected.

---

## Requirements vs. Tool Coverage

| Requirement | yolobox (stock) | yolobox (custom) |
|---|---|---|
| Windows/WSL2 + permissions | Works via WSL terminal | Same |
| Mount CWD | Automatic | Same |
| node, python, bun, pnpm, yarn | Yes | Same |
| Volta | No | Added via Dockerfile extension |
| Claude, Gemini, Codex CLIs | Yes | Same |
| Persistent AI memories | No | Added via volume mounts |
| Agent-agnostic shared memory | No | Partial — shared markdown file |

---

## Setup Guide

### Prerequisites

- Docker Desktop installed with WSL2 backend enabled
- All commands run from a **WSL terminal** (not PowerShell or CMD)

---

### Step 1 — Clone yolobox

```bash
git clone https://github.com/finbarr/yolobox ~/yolobox
cd ~/yolobox
```

---

### Step 2 — Build the base image from source

This ensures you're running what you've audited, not a remote image you haven't seen.

```bash
docker build -t ghcr.io/finbarr/yolobox:latest .
```

The `-t` flag names the image. Nothing is pushed to the internet — it stays on your machine. Docker will use this local image instead of pulling from ghcr.io.

---

### Step 3 — Extend with Volta

Create `~/yolobox/Dockerfile.local`:

```dockerfile
FROM ghcr.io/finbarr/yolobox:latest

# Install Volta system-wide
ENV VOLTA_HOME=/usr/local/volta
ENV PATH=$VOLTA_HOME/bin:$PATH

RUN curl https://get.volta.sh | bash -s -- --skip-setup \
    && chmod -R a+rx $VOLTA_HOME
```

Build it on top of the base:

```bash
docker build -f Dockerfile.local -t ghcr.io/finbarr/yolobox:latest .
```

---

### Step 4 — Set up persistent memory directories on your host

```bash
# Claude and Gemini store auth, settings, and memories here
mkdir -p ~/.claude ~/.gemini

# Shared context readable by any agent
mkdir -p ~/.ai-context
cat > ~/.ai-context/SHARED.md << 'EOF'
# Shared AI Context

Put notes here that you want any agent to know about.
Projects, preferences, recurring instructions, etc.
EOF
```

---

### Step 5 — Install the yolobox binary

```bash
curl -fsSL https://raw.githubusercontent.com/finbarr/yolobox/master/install.sh | bash
```

Add to PATH if prompted:

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

---

### Step 6 — Create launch aliases

Add to `~/.bashrc` or `~/.zshrc`:

```bash
# Shared memory mounts used by all agents
_YOLO_MOUNTS="--mount $HOME/.claude:/home/yolo/.claude \
              --mount $HOME/.gemini:/home/yolo/.gemini \
              --mount $HOME/.ai-context:/home/yolo/.ai-context"

alias yolo-claude="yolobox claude $_YOLO_MOUNTS"
alias yolo-gemini="yolobox gemini $_YOLO_MOUNTS"
alias yolo-codex="yolobox codex $_YOLO_MOUNTS"
```

Reload:

```bash
source ~/.bashrc
```

---

### Step 7 — Wire up shared memory to each agent

**Claude** — add to `~/.claude/CLAUDE.md`:
```markdown
See /home/yolo/.ai-context/SHARED.md for shared context and preferences.
```

**Gemini** — add to `~/.gemini/GEMINI.md`:
```markdown
See /home/yolo/.ai-context/SHARED.md for shared context and preferences.
```

Each agent reads its own config file, which points to the shared file. You maintain one file and all agents benefit.

---

### Step 8 — Usage

```bash
cd ~/my-project
yolo-claude    # Claude Code in yolo mode, full persistent memory
yolo-gemini    # Gemini CLI, same setup
yolo-codex     # Codex, same setup
```

Files written by the agent inside the container are immediately accessible on your host at the same path. Auth tokens and memories in `~/.claude` and `~/.gemini` persist across sessions.

---

## Rebuilding After yolobox Updates

When yolobox releases a new version, rebuild both layers:

```bash
cd ~/yolobox
git pull
docker build -t ghcr.io/finbarr/yolobox:latest .
docker build -f Dockerfile.local -t ghcr.io/finbarr/yolobox:latest .
```

Do **not** run `yolobox upgrade` — that would pull the unverified remote image and overwrite your local build.

---

## Notes on Agent-Agnostic Memory

There is no universal memory format across AI agents. Each has its own:

- Claude Code: `~/.claude/` and `CLAUDE.md` files
- Gemini CLI: `~/.gemini/`

The `~/.ai-context/SHARED.md` approach is the best available workaround — a human-maintained file that each agent's config references. It requires manual upkeep but gives you one source of truth for context you want all agents to have.
