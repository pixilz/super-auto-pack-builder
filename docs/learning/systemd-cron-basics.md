---
topic: systemd-cron-basics
date: 2026-03-27
tags: []
---

# systemd and Cron Basics

## What I Learned

There are two separate things to understand here:

**The cron config (`crontab -l`)** — this shows the scheduled job definitions: what commands run, on what schedule. It's a static file. Viewing it tells you what *should* happen, not what *is* happening.

**The cron daemon (`systemctl status cron`)** — this is the background process that actually reads the config and fires the jobs. `systemctl` is the interface to systemd, the Linux init system that manages services. `status cron` shows whether the daemon is running, if it crashed, and recent log output.

**`systemctl daemon-reload`** — when a unit file (the config file systemd uses to describe a service) changes on disk, systemd doesn't automatically pick it up. This command tells systemd to re-read all unit files. It does *not* restart any services — it only syncs the in-memory config. You run it when systemd warns "unit file changed on disk."

**Logs (`grep CRON /var/log/syslog`)** — this shows the actual execution history: when jobs fired, whether they succeeded or failed.

## Why It Matters

In this project, cron and systemd are relevant for any scheduled automation (e.g. scheduled remote agents, background jobs). Understanding the difference between "what is scheduled" and "is the scheduler running" is a basic ops skill that comes up whenever you're debugging why a job didn't fire.

In professional work, systemd is the standard service manager on most Linux servers. Knowing how to inspect service state and reload config without restarting services is essential for safe production operations.

## Key Takeaways

- `crontab -l` = the schedule config; `systemctl status cron` = the daemon state. These are different things.
- `daemon-reload` syncs config from disk — it does not restart services.
- Always `daemon-reload` before trusting `systemctl status` output if you see a "unit file changed" warning.

## Resources

- `man crontab`, `man systemctl`

## Questions Still Open

- What triggers the unit file to change? (package updates? manual edits? hooks?)
- How does `journalctl -u cron` compare to grepping syslog directly?
