---
topic: docker-basics
date: 2026-03-26
tags: [docker, containers, devops, dockerfile, docker-compose]
---

# Docker Basics

## What I Learned

Docker lets you package an application and everything it needs to run into a container — an isolated environment that works the same way on any machine. You stop worrying about "it works on my machine" because the machine *is* the container.

### The Dockerfile

A Dockerfile is a recipe for building a container image. Each instruction adds a layer:

```dockerfile
FROM node:lts-alpine    # start from an existing base image
WORKDIR /app            # set the working directory inside the container
```

Every Dockerfile starts with `FROM` — you always build on top of someone else's image. You could theoretically start from `FROM scratch` (nothing) but in practice nobody does that.

**Why Alpine?**
Base images come in different variants. Alpine Linux is a minimal distribution — about 5MB vs ~200MB for a full Debian image. Smaller means faster builds, faster pulls, and less attack surface. The tradeoff is it's missing some tools you might take for granted; you have to install them explicitly if you need them. For most projects it's fine.

**Why `lts` instead of a version number?**
`node:lts-alpine` is better than `node:20-alpine` because it automatically tracks whichever Node version is currently LTS. Pin to a number and you have to manually update the Dockerfile when that version reaches end-of-life. LTS tags do it for you.

### Images vs Containers

- **Image** — the built recipe, stored in Docker. Static, doesn't run.
- **Container** — a running instance of an image. You can have many containers from the same image.

`docker build` creates an image. `docker run` (or `docker compose up`) starts a container from it.

### docker-compose

Running a container manually looks like:

```
docker run -v .:/app -p 3000:3000 --env NODE_ENV=production my-image
```

That gets unwieldy fast — easy to forget a flag, hard to share with a teammate. `docker-compose.yml` encodes all of that into a file:

```yaml
services:
  app:
    build: .
    volumes:
      - .:/app
```

Now you just run `docker compose up` and everything is configured correctly every time.

### Volumes (Bind Mounts)

A bind mount maps a folder on your host machine to a folder inside the container:

```yaml
volumes:
  - .:/app   # current directory on host → /app inside container
```

This is how your code gets into the container in development. You edit a file on your machine, the container sees it immediately — no rebuild needed.

Docker also has "named volumes" — storage Docker manages internally, not directly accessible on your host. Used for things like database data that needs to persist between container restarts.

### Exit Code 0

A container with no long-running process exits immediately with code 0. That's a clean exit — not an error. It just means "I started, did nothing, finished successfully." Once you add a server process the container stays running.

## Why It Matters

Docker is standard in professional development. Any team running microservices, any CI/CD pipeline, any cloud deployment uses containers. Understanding how images are built, how volumes work, and how docker-compose ties it together is foundational DevOps knowledge.

For this project specifically: running everything inside Docker means the environment is consistent across machines (Windows, WSL, CI) and nothing pollutes the host.

## Key Takeaways

- Every Dockerfile starts with `FROM` — you always build on an existing base
- Alpine is small and fast; the tradeoff is fewer preinstalled tools
- Use `lts` tags instead of pinning version numbers to avoid manual maintenance
- docker-compose replaces long `docker run` commands with a readable config file
- Bind mounts let you edit code on your host and have the container see changes instantly
- Exit code 0 = clean exit, not an error

## Resources

- [Docker official docs](https://docs.docker.com)
- [Docker Hub — official images](https://hub.docker.com)
- [Node official image tags](https://hub.docker.com/_/node/tags)

## Questions Still Open

- When do you switch from bind mounts to copying files into the image (`COPY`)?
- How do multi-stage builds work, and when are they useful?
