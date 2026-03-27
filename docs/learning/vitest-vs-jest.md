---
topic: vitest-vs-jest
date: 2026-03-27
tags: [testing, vitest, jest, esm, typescript, node]
---

# Vitest vs Jest for ESM and Node 24

## What I Learned

Vitest and Jest have nearly identical APIs — `describe`, `it`, `expect`, `beforeEach` all work the same way. If you know Jest, you know Vitest. The difference is under the hood.

### Why Jest struggles with modern stacks

Jest was built for CommonJS. ESM support exists but is still behind an experimental Node flag (`--experimental-vm-modules`). On top of that, there is an active bug in Node 24 that breaks Jest config file parsing entirely. Running TypeScript with Jest also requires manual transform configuration via Babel or `ts-jest`.

### Why Vitest works out of the box

Vitest was built for the ESM + TypeScript world from the start. No transform config needed, no experimental flags, no Node 24 bugs. It uses its own esbuild-based transpiler internally, so TypeScript just works.

### `vitest run` vs `vitest`

- `vitest run` — runs once and exits. Use this in CI and for `pnpm test`.
- `vitest` — watch mode, re-runs tests on file changes. Use this during development.

### Config

Vitest config lives in `vitest.config.ts`, using `defineConfig` from `vitest/config`. Same pattern as Vite projects. Key options:

- `include` — glob patterns for test files (e.g. `**/*.test.ts`)
- `exclude` — patterns to ignore (always exclude `node_modules`)

## Why It Matters

Vitest is the standard choice for new TypeScript projects. It's widely used, well documented, and a marketable skill. More importantly, it solves a real problem — Jest on Node 24 with ESM is genuinely broken without workarounds, and Vitest just works.

## Key Takeaways

- Vitest API is identical to Jest — zero relearning if you know Jest
- Jest ESM support requires `--experimental-vm-modules` and has a Node 24 bug
- Vitest handles TypeScript natively with no transform config
- `vitest run` for CI, `vitest` for watch mode during development
- Config lives in `vitest.config.ts` using `defineConfig`

## Resources

- [Vitest docs](https://vitest.dev)
- [Vitest config reference](https://vitest.dev/config/)

## Questions Still Open

- How does Vitest handle test coverage reporting?
- How does workspace-level Vitest config interact with per-package configs in a monorepo?
