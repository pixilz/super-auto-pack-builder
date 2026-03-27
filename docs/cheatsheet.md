# Cheatsheet

## Docker

| Command | What it does |
|---------|-------------|
| `docker compose build` | Build (or rebuild) the image from the Dockerfile |
| `docker compose up` | Start the container |
| `docker compose up --build` | Rebuild and start in one command |
| `docker compose down` | Stop and remove the container and network |
| `docker compose run app sh` | Open a shell inside the container |
| `docker compose run app <cmd>` | Run a single command inside the container |
| `docker compose run --remove-orphans app sh` | Same, but clean up leftover containers first |

## Linting

| Command | What it does |
|---------|-------------|
| `docker compose run hadolint hadolint Dockerfile` | Lint the Dockerfile (run on host, not inside container) |

## Cron / systemd

| Command | What it does |
|---------|-------------|
| `crontab -l` | Show the cron config (scheduled job definitions) |
| `systemctl status cron` | Show whether the cron daemon is running |
| `sudo systemctl daemon-reload` | Re-read unit files from disk (run this if systemd warns about stale config) |
| `grep CRON /var/log/syslog \| tail -20` | See recent cron activity in the system log |

## pnpm

| Command | What it does |
|---------|-------------|
| `pnpm install` | Install all dependencies |
| `pnpm add <pkg>` | Add a dependency |
| `pnpm add -D <pkg>` | Add a dev dependency |
| `pnpm remove <pkg>` | Remove a dependency |
| `pnpm run <script>` | Run a script from package.json |
| `pnpm --version` | Check pnpm version |
