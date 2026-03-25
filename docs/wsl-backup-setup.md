# WSL to Windows Backup Setup (rsync + cron)

Automatically sync files from your WSL home directory to the Windows filesystem on a schedule.

---

## Prerequisites

Install rsync in WSL (if not already installed):

```bash
sudo apt update && sudo apt install rsync -y
```

---

## Step 1: Create the backup destination on Windows

In WSL, create the Windows folder where backups will be stored:

```bash
mkdir -p /mnt/c/Users/Zoe/wsl-backup
```

---

## Step 2: Test the rsync command manually

Before automating, run it once to confirm it works:

```bash
rsync -av --delete ~/ /mnt/c/Users/Zoe/wsl-backup/
```

**Flags explained:**
- `-a` — archive mode (preserves permissions, timestamps, symlinks)
- `-v` — verbose (shows files being copied)
- `--delete` — removes files from the backup that no longer exist in source

Check that `C:\Users\Zoe\wsl-backup` on Windows contains your files.

> **Note:** Remove `--delete` if you want the backup to keep old files even after you delete them in WSL.

---

## Step 3: Set up the cron job

Open your crontab:

```bash
crontab -e
```

If prompted to choose an editor, select `nano` (option 1).

Add this line at the bottom:

```
*/15 * * * * rsync -a --delete ~/ /mnt/c/Users/Zoe/wsl-backup/ >> /tmp/wsl-backup.log 2>&1
```

This runs every 15 minutes and logs output to `/tmp/wsl-backup.log`.

Save and exit: `Ctrl+O`, `Enter`, `Ctrl+X`.

---

## Step 4: Ensure cron is running

WSL does not start cron automatically. You need to start it each time you launch WSL:

```bash
sudo service cron start
```

### Optional: Auto-start cron on WSL launch

Add the following to your `~/.bashrc` so cron starts automatically when you open WSL:

```bash
echo 'sudo service cron start > /dev/null 2>&1' >> ~/.bashrc
```

To avoid being prompted for a password, add a sudoers entry:

```bash
sudo visudo
```

Add this line at the bottom (replace `yourusername` with your WSL username):

```
yourusername ALL=(ALL) NOPASSWD: /usr/sbin/service cron start
```

---

## Step 5: Verify the cron job is working

After 15 minutes, check the log:

```bash
cat /tmp/wsl-backup.log
```

You should see a list of synced files. If empty or erroring, re-check the rsync command and paths.

---

## Useful commands

| Task | Command |
|---|---|
| View crontab | `crontab -l` |
| Edit crontab | `crontab -e` |
| Remove crontab | `crontab -r` |
| Check cron status | `sudo service cron status` |
| Start cron | `sudo service cron start` |
| Run backup manually | `rsync -av --delete ~/ /mnt/c/Users/Zoe/wsl-backup/` |
| View backup log | `cat /tmp/wsl-backup.log` |

---

## Cron schedule reference

| Schedule | Cron expression |
|---|---|
| Every 15 minutes | `*/15 * * * *` |
| Every hour | `0 * * * *` |
| Every day at midnight | `0 0 * * *` |
| Every day at 9am | `0 9 * * *` |

---

## Excluding files/folders

To exclude certain directories (e.g., `node_modules`, `.git`), use `--exclude`:

```bash
rsync -a --delete --exclude='node_modules' --exclude='.git' ~/ /mnt/c/Users/Zoe/wsl-backup/
```

Multiple excludes can be chained. Update your crontab entry to match.
