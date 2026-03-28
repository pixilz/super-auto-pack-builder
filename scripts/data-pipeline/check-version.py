#!/usr/bin/env python3
"""
Check for new Super Auto Pets game version by probing the API.

Usage: python3 check-version.py [--last-known 46]

Returns exit code 0 if a new version is found, 1 if no change, 2 on error.
Prints the current version number on stdout.
"""

import argparse
import json
import os
import sys
import urllib.request
import urllib.error

API_BASE = "https://api.teamwood.games"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(SCRIPT_DIR, "last-known-version.json")


def probe_version(minor: int) -> dict | None:
    """Probe a specific minor version. Returns version info or None."""
    url = f"{API_BASE}/0.{minor}/api/version/current"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SAP-Pipeline/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read())
    except urllib.error.HTTPError:
        return None
    except Exception:
        return None


def find_current_version(start_minor: int = 40) -> tuple[int, dict] | None:
    """Find the current game version by probing upward."""
    last_valid = None
    minor = start_minor
    while minor < start_minor + 20:
        result = probe_version(minor)
        if result:
            last_valid = (minor, result)
            minor += 1
        else:
            break
    return last_valid


def load_last_known() -> int | None:
    try:
        with open(VERSION_FILE) as f:
            return json.load(f).get("minor")
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def save_last_known(minor: int, version_info: dict):
    with open(VERSION_FILE, "w") as f:
        json.dump({"minor": minor, "version_info": version_info}, f, indent=2)


def main():
    parser = argparse.ArgumentParser(description="Check for new SAP version")
    parser.add_argument("--last-known", type=int, default=None)
    args = parser.parse_args()

    last_known = args.last_known or load_last_known() or 44

    print(f"Checking for updates (last known: 0.{last_known})...", file=sys.stderr)

    result = find_current_version(last_known)
    if result is None:
        print("ERROR: Could not reach API", file=sys.stderr)
        sys.exit(2)

    current_minor, version_info = result
    patch = version_info.get("Patch", "?")
    print(f"Current version: 0.{current_minor}.{patch}", file=sys.stderr)

    if current_minor > last_known:
        print(f"NEW VERSION: 0.{current_minor}", file=sys.stderr)
        save_last_known(current_minor, version_info)
        print(current_minor)
        sys.exit(0)
    else:
        print(f"No update (still 0.{current_minor})", file=sys.stderr)
        save_last_known(current_minor, version_info)
        print(current_minor)
        sys.exit(1)


if __name__ == "__main__":
    main()
