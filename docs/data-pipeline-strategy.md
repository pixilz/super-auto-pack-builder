# Data Pipeline Strategy

> Phase 1 deliverable. Describes how game files are obtained, data is extracted, and outputs are produced.

## Overview

Super Auto Pets game data comes from two sources:

1. **Network API** — pet/food/ability/turn data fetched by the game client at startup from Team Wood Games' servers
2. **Local Unity asset bundles** — sprites, sounds, and localization strings bundled with the Steam installation

A third source, the compiled game binary, is needed for game mechanics constants not exposed by the API.

---

## Extraction Paths

### Path 1 — Network API (pets, foods, abilities, turns)

**Source:** `https://api.teamwood.games/{major}.{minor}/api/`

The game fetches structured JSON from this endpoint on startup. The version component (`{major}.{minor}`) matches the installed game version (currently `0.45`).

**Confirmed endpoints (from IL2CPP metadata and community research):**

| Endpoint | Content |
|---|---|
| `/api/data/animals` (or similar) | Pet definitions |
| `/api/data/perks` (or similar) | Food/perk definitions |
| `/api/data/hats` (or similar) | Cosmetic hat definitions |

> **Open item:** The exact path and request headers are not yet confirmed. Direct HTTP requests to the API return 404. The game client likely sends specific headers (User-Agent, session token, or auth token) that gate access. This must be resolved in Dev Phase 1 by running the game with mitmproxy or Fiddler to capture one real request.

**Version discovery mechanism:**
- Versions below current return HTTP 300 with "Super Auto Pets needs to be updated"
- Current version returns game data
- Versions above current return HTTP 404

The pipeline can auto-discover the current version by probing sequentially from the last known version upward until a non-300 response is received.

**Format:** JSON. Internal pet IDs are numeric strings (e.g. `"709"`, `"88"`). The pipeline will map these to human-readable slugs (e.g. `"pet-ant"`) on output.

---

### Path 2 — Unity Addressable bundles (sprites and localization)

**Source:** `Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64/*.bundle`

**Tool:** [UnityPy](https://github.com/K0lb3/UnityPy) (Python library)

**Contents confirmed via UnityPy inspection:**

| Bundle | Content |
|---|---|
| `defaultlocalgroup_assets_all_*.bundle` | Pet mascot poses (MonoBehaviour), background sprites (Texture2D), sounds (AudioClip), `Changes.json` (TextAsset) |
| `localization-string-tables-english_assets_all.bundle` | English localization strings |
| `localization-asset-tables-*_assets_all.bundle` | Localization asset tables (other languages) |
| `duplicateassetisolation_assets_all_*.bundle` | De-duplicated shared assets |

**What to extract:**
- `Texture2D` assets → PNG files (pet images, UI sprites)
- `TextAsset` (`Changes.json`) → patch change log
- English localization string tables → pet/food display names and descriptions

**Format output:** PNG files for sprites, JSON for text data.

> **Note:** Pet sprite images may not be in the `defaultlocalgroup` bundle — if they live in the Addressables catalog as remote assets (loaded from the CDN at runtime), they will need to be fetched via the catalog's remote URL rather than extracted from local bundles. This requires verification in Dev Phase 1.

---

### Path 3 — IL2CPP decompilation (game mechanics constants)

**Source:** `GameAssembly.dll` + `Super Auto Pets_Data/il2cpp_data/Metadata/global-metadata.dat`

**Backend:** IL2CPP (confirmed — `GameAssembly.dll` present, no `Assembly-CSharp.dll`)

**Tool chain:**
1. **[Il2CppDumper](https://github.com/Perfare/Il2CppDumper)** — takes `GameAssembly.dll` + `global-metadata.dat`, produces stub DLLs and a `dump.cs` file with all class/method signatures
2. **[ILSpy CLI (`ilspycmd`)](https://github.com/icsharpcode/ILSpy)** — decompiles the stub DLLs to readable C# source

**What to extract:**
- Gold per turn (currently 10, hardcoded)
- XP required per level (2 for level 2, 3 for level 3 = 5 total)
- Shop tier unlock turns (tier X unlocks on turn 2X−1)
- Battle damage formula and turn order rules

**Format output:** Extracted as constants into a JSON file.

> **Note:** Much of this data is stable and documented on the community wiki. IL2CPP extraction is the authoritative source but is the most complex pipeline step. It can be deferred to a later Dev Phase iteration if needed.

---

## Input Requirements

- Steam installation of Super Auto Pets (Windows)
- Game files mounted or copied to the pipeline's working directory
- Path expected by the pipeline: configurable, defaulting to a `game-files/` directory at repo root (gitignored)

---

## Pipeline Flow

```
Steam game files
       │
       ├── StreamingAssets/aa/*.bundle ──► UnityPy ──► sprites/, Changes.json
       │
       ├── GameAssembly.dll + global-metadata.dat ──► Il2CppDumper + ILSpy ──► mechanics.json
       │
       └── Version probe ──► api.teamwood.games/{v}/api/ ──► pets.json, foods.json
```

All outputs land in a `data/extracted/` directory. The API layer reads from there.

---

## Update Trigger

On game update (detected by version probe returning a new version):
1. Re-run network API extraction
2. Re-extract `Changes.json` from bundles (track which entities changed)
3. Re-run IL2CPP extraction only if `GameAssembly.dll` changed (file hash check)
4. Re-extract sprites only if bundle hash changed

For v1, this can be triggered manually. Automation is Dev Phase 5 (CronJobs).

---

## Open Items for Dev Phase 1

| Item | Details |
|---|---|
| API request format | Run game with mitmproxy/Fiddler to capture exact headers and path |
| Pet sprite location | Confirm whether sprites are in local bundles or fetched remotely |
| IL2CPP tooling in Docker | Verify Il2CppDumper + ilspycmd run on Linux in the container |
| Numeric ID → slug mapping | Build the ID map from a live API response |
