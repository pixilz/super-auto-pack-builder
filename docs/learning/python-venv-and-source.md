---
topic: python-venv-and-source
date: 2026-04-06
tags: []
---

# Python venv and source

## What I Learned

A Python virtual environment (`venv`) is just a folder containing a copy (or symlink) of the Python binary, its own `pip`, and its own `site-packages/` directory for installed libraries. There is no VM, no container, and no OS-level isolation — it is purely a directory structure.

`source venv/bin/activate` updates your shell's `PATH` to prepend the venv's `bin/` directory. Because the venv's Python and pip appear first in `PATH`, they take precedence over the system versions for the remainder of that terminal session. Running `echo $PATH` before and after activating shows exactly one new directory prepended.

`source` is a shell built-in that runs a script in the current shell session rather than spawning a subprocess. This matters because environment variable changes (like `PATH`) only persist if they happen in the current shell. A subprocess would inherit the current environment, make changes, then exit — leaving the parent shell unaffected.

On WSL/Ubuntu (Python 3.11+), the system Python is marked as "externally managed" and rejects direct `pip install` calls. Using a venv sidesteps this entirely because the venv's pip has no such restriction.

`playwright install --with-deps chromium` is needed on WSL specifically because it downloads not just the Chromium binary but the Linux system libraries (fonts, graphics, etc.) that Chromium depends on and that are typically absent on a minimal WSL install.

**Gotcha: venv binaries can be shadowed by project tooling.** Even with a venv active, a project may have a shell wrapper or Docker Compose script earlier in `PATH` that intercepts commands like `playwright`. In this project, `playwright` routes to a Docker Compose service — so `playwright install` actually runs inside a container and fails. The fix is to invoke the venv binary directly: `./venv/bin/playwright install --with-deps chromium`. The same applies to running scripts: `./venv/bin/python extract_web.py` guarantees you're using the venv's Python regardless of what else is in `PATH`. Use `which playwright` to diagnose which binary your shell is actually finding.

## Why It Matters

Venvs are the standard Python dependency isolation pattern. Understanding that they are just a `PATH` trick — not real isolation — explains their limits: `sudo pip install` bypasses the venv because `sudo` resets `PATH` for security reasons.

In this project, the data extraction pipeline (`extract_web.py`) runs on the host machine (not in Docker) and requires Playwright. A venv is the correct way to install it without conflicting with system Python on WSL.

## Key Takeaways

- A venv is a folder + a `PATH` change. No VM, no container.
- `source` runs a script in the current shell so environment changes stick.
- `sudo` resets `PATH`, so `sudo pip` always hits the system Python even inside a venv.
- On WSL, use `playwright install --with-deps chromium` to get browser system dependencies.
- If a venv binary is shadowed by project tooling, call it directly: `./venv/bin/playwright` instead of `playwright`.

## Resources

## Questions Still Open
