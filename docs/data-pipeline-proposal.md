# Data Pipeline Proposal

## Overview

A backend service that keeps our SAP pet database up to date by combining web scraping (primary) with binary extraction (fallback/validation).

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌───────────────┐
│  Cron (daily)│────▶│ Version Check│────▶│ Data Pipeline │
└─────────────┘     └──────────────┘     └───────┬───────┘
                                                  │
                                    ┌─────────────┼─────────────┐
                                    ▼             ▼             ▼
                              ┌──────────┐ ┌───────────┐ ┌──────────┐
                              │ Scrape   │ │ Binary    │ │ Diff &   │
                              │ Grounded │ │ Extract   │ │ Validate │
                              └────┬─────┘ └─────┬─────┘ └────┬─────┘
                                   │             │             │
                                   ▼             ▼             ▼
                              ┌──────────────────────────────────────┐
                              │            pets.json                  │
                              └──────────────────────────────────────┘
```

## Step 1: Version Check (runs daily via cron)

**Script:** `scripts/data-pipeline/check-version.py`

Probes `https://api.teamwood.games/0.{N}/api/version/current` to detect new game versions. If no new version, exit early. If new version detected, trigger the pipeline.

- Exit code 0 = new version found
- Exit code 1 = no change
- Stores last known version in `last-known-version.json`

## Step 2: Scrape Groundedsap (primary source)

**New script needed:** `scripts/data-pipeline/scrape-groundedsap.py`

Fetches `https://www.groundedsap.co.uk/Pets.aspx` and parses the DevExpress GridView HTML.

**What we get (581 pets, 100% accuracy):**

| Field | Column | Notes |
|-------|--------|-------|
| Name | [1] | Display name |
| Archetype | [2] | Image filename → archetype name |
| Attack | [3] | Integer |
| Health | [4] | Integer |
| Tier | [5] | Integer |
| Level 1 ability | [6] | "Trigger: Description" format |
| Level 2 ability | [7] | Same format |
| Level 3 ability | [8] | Same format |
| Categories | [16] | "F2P", "Star", "Unicorn", etc. |
| Custom tags | [18] | "Buy/Sell, Shop Scaling", etc. |
| Internal ID | [20] | MinionEnum integer value |

**Trigger extraction:** Split on first `:` in the ability text — everything before is the trigger, everything after is the description. Already confirmed working.

**Update frequency:** Groundedsap typically updates within days of a game patch. We should scrape on detection of a new game version, then retry daily until the pet count changes (indicating groundedsap has updated).

**Failure mode:** If groundedsap is down or returns unexpected HTML, fall back to binary extraction.

## Step 3: Binary Extraction (fallback + validation)

**Existing script:** `scripts/data-pipeline/extract.py`

Runs Cpp2IL + UnityPy localization extraction on game files. Requires the game binary to be downloaded (manual step — Steam doesn't have a public API for this).

**What we get (97.1% accuracy excluding triggers):**

| Field | Accuracy | Source |
|-------|----------|--------|
| Name | 99.1% | Localization bundles |
| Attack | 98.7% | Cpp2IL ISIL |
| Health | 97.7% | Cpp2IL ISIL |
| Tier | 99.4% | Cpp2IL ISIL |
| Archetype | 89.6% | Cpp2IL ISIL |
| Trigger | 0% | Not extractable from binary alone |
| Description | ~71% | Localization bundles |

**When to use:**
- Groundedsap is down
- Validation: diff binary extraction against scrape to catch errors in either source
- New pets that groundedsap hasn't added yet (binary has them immediately)

## Step 4: Diff & Validate

Compare scrape vs binary extraction. Flag discrepancies for review:
- Stat differences → likely a game balance patch (trust scrape, update binary trigger map)
- New pets in binary but not in scrape → groundedsap hasn't updated yet, use binary data
- New pets in scrape but not in binary → we don't have the new game files yet

## Output: pets.json

```json
{
  "version": "0.47",
  "updated": "2026-03-28T12:00:00Z",
  "source": "groundedsap",
  "pets": [
    {
      "name": "Duck",
      "id": 26,
      "tier": 1,
      "attack": 2,
      "health": 2,
      "archetype": "Buff",
      "abilities": [
        {
          "trigger": "Sell",
          "level1": "Give shop pets +1 health.",
          "level2": "Give shop pets +2 health.",
          "level3": "Give shop pets +3 health."
        }
      ]
    }
  ]
}
```

## Cron Setup

```bash
# Daily at 6am UTC — check for new version and update data
0 6 * * * cd /app && python3 scripts/data-pipeline/run.py >> logs/pipeline.log 2>&1
```

## Scripts Needed

| Script | Status | Purpose |
|--------|--------|---------|
| `check-version.py` | Done | Detect new game versions |
| `extract.py` | Done | Binary extraction pipeline |
| `scrape-groundedsap.py` | **TODO** | Scrape primary data source |
| `run.py` | **TODO** | Orchestrator: version check → scrape → extract → diff → output |
| `trigger-map.json` | Done | Fallback trigger data (509 abilities) |

## Dependencies

**For scraping (lightweight):**
- Python 3.12+
- No pip packages needed (stdlib `urllib` + `html.parser`)

**For binary extraction (heavyweight, optional):**
- Cpp2IL binary (~17MB)
- UnityPy (`pip install UnityPy`)
- Game files (manual download from Steam)

**Not needed in production:**
- Ghidra (only for research)
- AssetRipper (only for initial exploration)
- Java (only for Ghidra)

## Open Questions

1. **Game file download:** Three options, none yet proven end-to-end:
   - **Option A: itch.io via headless browser.** The web version is hosted at `html-classic.itch.zone/html/16823967/Production/`. The CDN requires itch.io's auth flow (signed redirect), so simple HTTP requests get 403. A Playwright script could navigate to the game page, click "Run game", and capture the WASM binary + data files from network requests. Cpp2IL supports WASM via `--wasm-framework-file`. We already have Playwright in the project. Not yet tested.
   - **Option B: SteamCMD with a bot account.** Standard approach for Steam games. Requires maintaining a Steam account.
   - **Option C: Manual download.** Version check script sends an alert, human downloads and drops files in a directory. Pipeline picks them up.
2. **Groundedsap update lag:** How long after a patch does groundedsap update? If >24 hours, we might want to serve binary-extracted data for new pets during the gap.
3. **Food/spell data:** Groundedsap also has a Foods page. Same scraping approach applies.
4. **Rate limiting:** One scrape per day is well within reasonable limits. No API key needed.
