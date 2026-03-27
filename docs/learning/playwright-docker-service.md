---
topic: playwright-docker-service
date: 2026-03-27
tags: [playwright, docker, e2e, testing, docker-compose]
---

# Playwright as a Separate Docker Service

## What I Learned

Playwright requires browser binaries (Chromium, Firefox, WebKit) to run. These binaries are large — roughly 400–600MB each. Baking them into your main app image makes it unnecessarily heavy. The standard solution is a dedicated Docker service using the official Playwright image.

### The official Playwright image

Microsoft publishes an official image at `mcr.microsoft.com/playwright` — note this is MCR (Microsoft Container Registry), not Docker Hub. Tags follow the pattern `v<version>-<distro>`. The `-noble` suffix refers to Ubuntu 24.04 (Ubuntu names releases alphabetically; noble is the current LTS codename). The Playwright docs recommend `-noble` for new projects.

Always pin the image version to match your installed `@playwright/test` package version. Mismatches between the package and the browser binaries can cause subtle API failures.

### Keeping the container alive

Docker containers exit when their main process exits. A service with no long-running process needs a keepalive trick:

```yaml
command: tail -f /dev/null
```

`tail -f /dev/null` is a process that does nothing but never exits — it watches a file that never gets new content. The container stays alive, and you can run commands inside it via `docker compose run` independently.

### Adding pnpm to the Playwright image

The official Playwright image ships with Node but not pnpm. To run `pnpm test:e2e` inside it, you need a custom `Dockerfile.e2e` that extends the Playwright image and installs pnpm via corepack:

```dockerfile
FROM mcr.microsoft.com/playwright:v1.58.2-noble

ENV COREPACK_HOME=/usr/local/share/corepack
RUN corepack enable && corepack prepare pnpm@9.15.9 --activate

WORKDIR /app
```

Reference it in `docker-compose.yml` using the `build` key instead of `image`:

```yaml
playwright:
  image: super-auto-e2e-tests
  build:
    context: .
    dockerfile: Dockerfile.e2e
```

### Docker Compose pull vs build behaviour

When a service has both `image:` and `build:`, Docker Compose tries to pull the image from a registry first. If the image doesn't exist remotely it fails, then falls back to building locally. After the first local build the image is cached — subsequent runs find it locally and skip the pull attempt entirely.

This means the "pull access denied" warning on first run is expected and harmless. It disappears after the image is built once.

## Why It Matters

E2E tests are heavyweight by nature — they need real browsers. Keeping browser binaries in a separate service means the main app image stays lean, which matters for CI download times and production image size. This pattern (separate service per concern) is standard in Docker Compose setups for professional projects.

## Key Takeaways

- Playwright images live on MCR, not Docker Hub — `mcr.microsoft.com/playwright`
- Pin the image version to match your `@playwright/test` package version
- `-noble` = Ubuntu 24.04, recommended by Playwright docs
- Use `tail -f /dev/null` to keep a service container alive with no long-running process
- Use a custom `Dockerfile.e2e` to add pnpm to the Playwright image
- "Pull access denied" on first run is expected — disappears after first local build

## Resources

- [Playwright Docker docs](https://playwright.dev/docs/docker)
- [MCR Playwright image](https://mcr.microsoft.com/en-us/artifact/mar/playwright)

## Questions Still Open

- How do you connect the Playwright container to the app container over Docker's internal network for real E2E tests?
- When should you use `webServer` in `playwright.config.ts` vs a separate running app service?
