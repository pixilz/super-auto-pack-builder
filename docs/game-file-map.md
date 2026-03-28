# Super Auto Pets — Game File Map

> For AI agents. Describes what data exists where in the game files and how to extract it.
> Last updated: 2026-03-27 (game version 0.46)

## Game Build Info

- **Engine:** Unity (IL2CPP backend, NOT Mono)
- **Platform:** StandaloneWindows64
- **Current version:** 0.46.7
- **Steam App ID:** 1714040
- **Internal codename:** Spacewood (`com.teamwood.spacewood.unity`)
- **Internal terminology:** Pets are called "Minions", Foods are called "Spells"

## Source Location

Game files are copied from the Steam install to `Downloaded Super Auto Pets/` in the repo root (gitignored). The pipeline input path is configurable.

```
Downloaded Super Auto Pets/
├── GameAssembly.dll              # IL2CPP compiled game logic (C#→C++)
├── Super Auto Pets.exe           # Unity player launcher
├── UnityPlayer.dll               # Unity runtime
├── Super Auto Pets_Data/
│   ├── il2cpp_data/
│   │   ├── Metadata/
│   │   │   └── global-metadata.dat    # IL2CPP type metadata (needed by Il2CppDumper)
│   │   └── Resources/                 # .NET resource files
│   ├── StreamingAssets/
│   │   ├── aa/
│   │   │   ├── catalog.json           # Unity Addressables catalog (asset index)
│   │   │   ├── settings.json          # Addressables config (build target, version)
│   │   │   └── StandaloneWindows64/   # Asset bundles
│   │   │       ├── defaultlocalgroup_assets_all_*.bundle
│   │   │       ├── duplicateassetisolation_assets_all_*.bundle
│   │   │       └── localization-*_assets_all.bundle (x24)
│   │   ├── google-services-desktop.json
│   │   └── UnityServicesProjectConfiguration.json
│   ├── sharedassets0.assets       # Shaders, materials, UI base
│   ├── sharedassets1.assets       # MAIN DATA: 9690 MonoBehaviours, 2494 Sprites, 768 AnimationClips, 623 AudioClips
│   ├── sharedassets2.assets       # Scene data, particles, colliders
│   ├── sharedassets3.assets       # Fonts, additional scene objects
│   ├── sharedassets4-7.assets     # PreloadData only (empty)
│   ├── resources.assets           # Unity built-in resources, IAP catalog
│   ├── globalgamemanagers*        # Unity engine settings
│   ├── level0-7                   # Scene files
│   ├── app.info                   # "Team Wood / Super Auto Pets"
│   ├── boot.config                # Build GUID, GC settings
│   └── ScriptingAssemblies.json   # List of all managed DLLs
└── __MACOSX/                      # macOS metadata (ignore)
```

## Where Each Data Type Lives

### Pet definitions (stats, tiers, pack membership)

- **Location:** The pet stat/tier/pack data is **NOT in asset files**. It is hardcoded in C# method bodies inside `GameAssembly.dll`.
- **Registry class:** `Spacewood.Core.Enums.MinionConstants` — holds a `Dictionary<MinionEnum, MinionTemplate>` populated by `Create*()` methods
- **Pack creation methods:** `CreatePack1Turtle()`, `CreatePack2Puppy()`, `CreatePack3Star()`, `CreatePack4Golden()`, `CreatePack5Unicorn()`, `CreatePack6Danger()`, `CreatePack7Color()`, `CreatePack8PlusMini1-4()`
- **Count:** 775 unique pet names confirmed via binary string search in `sharedassets1.assets`
- **AssetRipper Free limitation:** Decompiles class structure (fields, method signatures) but method bodies are empty stubs. The actual data values (SetStats, SetTier, AddPack calls) are locked in native code.
- **Next step:** Use **Cpp2IL** or **Ghidra** with Il2CppDumper output to reconstruct the method bodies and extract the actual stat values.

### Pet data model (decompiled class structure)

The full C# class hierarchy has been decompiled by AssetRipper to `tmp/assetripper-output/Scripts/Assembly-CSharp/`:

**`Spacewood.Core.Enums.MinionTemplate`** (extends `ItemTemplate`):
- `MinionEnum Enum` — pet identifier (numeric enum)
- `int Attack`, `int Health` — base stats
- `int? AttackMax`, `int? HealthMax` — stat caps
- `int? Countdown` — countdown mechanic
- `MinionType Type` — minion classification
- `RelicType RelicType` — relic classification
- `List<TribeEnum> Tribes` — tribe affiliations
- `List<AbilityEnum> AbilityEnums` — ability references
- `List<MinionAbilityModel> Abilities` — ability definitions
- `List<MinionStackRule> StackRules` — stacking behavior
- `bool Cursed`, `bool HasOldSkin`, `bool AttackWithHealth`, `bool ForceActivateImmune`
- `int TierMax` — max tier
- `string Note` — special notes

**`Spacewood.Core.Models.Item.ItemTemplate`** (base class):
- `string Name`, `string NameNormalized`
- `int Tier`, `int Price`
- `string About` — description
- `bool Active`, `bool Rollable`, `bool Bad`, `bool Unique`, `bool Unreleased`, `bool Elusive`, `bool Premium`
- `HashSet<Pack> Packs` — which packs this item appears in
- `HashSet<Pack> PacksOwnership` — pack ownership requirements
- `List<Role> Roles`
- `HashSet<Archetype> ArchetypeProducer`, `ArchetypeConsumer`
- `int? ReleaseVersion`

**`Spacewood.Core.Enums.MinionEnum`** — numeric ID mapping (partial):
- `Ant = 0`, `AntToken = 1`, `Badger = 2`, `Beaver = 3`, `Bee = 4`, `Bison = 5`, `Blowfish = 7`, `Buffalo = 8`, `Butterfly = 9`, `Camel = 10`, `Cat = 11`, `Cricket = 17`, `Deer = 20`, etc.
- Test minions at IDs 9000+ and 12000+
- Full enum at: `tmp/assetripper-output/Scripts/Assembly-CSharp/Spacewood/Core/Enums/MinionEnum.cs`

**`Spacewood.Unity.MinionAsset`** (ScriptableObject — links enum to Unity assets):
- `MinionEnum Enum`
- `BestDictionary<string, MinionSkinAsset> Skins`
- `LocalizedString Name`
- `Sprite Sprite`, `Sprite Sprite2x`

**`Spacewood.Unity.AbilityAsset`** (ScriptableObject):
- `AbilityEnum Enum`
- `LocalizedLevelCollection Abilities` — per-level descriptions
- `LocalizedLevelCollection FinePrints`

**`Spacewood.Core.Models.MinionModel`** (runtime instance):
- `MinionEnum Enum`, `IntegerStat Health`, `IntegerStat Attack`
- `int Level`, `int Exp`, `int Mana`
- `Perk? Perk`, `List<MinionAbilityModel> Abilities`
- `TribeEnum? Tribe`, `int? SellValue`
- JSON-serialized with short property names (`"Hp"`, `"At"`, `"Enu"`, `"Lvl"`, etc.)

### Pack names (internal → display)

From `MinionConstants` method names and the codebase:

| Internal | Display Name | Method |
|---|---|---|
| Pack1 / Turtle | Turtle Pack (free) | `CreatePack1Turtle()` |
| Pack2 / Puppy | Puppy Pack (paid) | `CreatePack2Puppy()` |
| Pack3 / Star | Star Pack (paid) | `CreatePack3Star()` |
| Pack4 / Golden | Golden Pack (paid) | `CreatePack4Golden()` |
| Pack5 / Unicorn | Unicorn Pack (paid) | `CreatePack5Unicorn()` |
| Pack6 / Danger | Danger Pack (paid) | `CreatePack6Danger()` |
| Pack7 / Color | Color Pack (paid) | `CreatePack7Color()` |
| Pack8Plus / Mini1-4 | Mini Packs (paid) | `CreatePack8PlusMini1-4()` |

> **Note:** More packs exist than originally expected. The earlier data-schema-spec.md only scoped Turtle, Puppy, Star, Golden — this needs updating.

### Pet sprites (images)

- **Location:** `sharedassets1.assets` → Texture2D + Sprite objects
- **Count:** 2494 Sprites, 2485 Texture2D
- **Extraction:** UnityPy can extract these directly (no type tree needed for textures)
- **AssetRipper output:** `tmp/assetripper-output/Assets/Texture2D/{PetName}.png`
- **Also available at 2x resolution:** `{PetName}_2x.png` files exist for many pets

### Pet abilities

- **Location:** `sharedassets1.assets` → MonoBehaviour objects
- **Naming pattern in binary:** `{PetName}Ability` (e.g., `AntAbility`, `BeaverAbility`, `GiantOtterAbility2`)
- **Contains GUID references** to other assets (format: `GUID:dab4223...`)
- **Ability data model:** Defined by `AbilityEnum` and `MinionAbilityModel` classes
- **Same extraction problem as pets:** Method bodies are empty stubs in decompiled output

### Animation clips

- **Location:** `sharedassets1.assets` → AnimationClip objects
- **Count:** 768

### Audio clips

- **Location:** `sharedassets1.assets` → AudioClip objects (623) + Addressable bundles
- **Addressable bundles contain:** Menu music, ambiance (Birds, Night, River, Wind), Battle music
- **AssetRipper output:** `tmp/assetripper-output/Assets/AudioClip/{PetName}.ogg`

### Patch changes (what changed in latest update)

- **Location:** Addressable bundle `defaultlocalgroup_assets_all_*.bundle` → TextAsset `Assets/Spacewood/Data/Changes.json`
- **Format:** JSON with structure `{ "Pets": [...], "Food": [...], "Perk": [] }`
- **Pet entries:** `{ "Id": "709", "New": true }` or `{ "Id": "88", "Ability": true, "Attack": true }`
- **Note:** Uses internal numeric IDs (matches MinionEnum values), not slugs

### Mascot poses

- **Location:** Addressable bundle `defaultlocalgroup_assets_all_*.bundle` → MonoBehaviour
- **Path pattern:** `Assets/Spacewood/AutoGenerated/Mascots/{Animal}Poses.asset`
- **Count:** 31 mascots

### Localization strings

- **Location:** Addressable bundles `localization-string-tables-{lang}_assets_all.bundle`
- **Languages:** English, French, German, Italian, Spanish, Portuguese, Russian, Polish, Turkish, Japanese, Korean, Chinese (Simplified), Chinese (Traditional)
- **Contains:** Pet names, food names, ability descriptions, UI strings

### Background sprites

- **Location:** Addressable bundle `defaultlocalgroup_assets_all_*.bundle` → Texture2D + Sprite
- **Path pattern:** `Assets/Spacewood/Sprites/Backgrounds2/{Location}{Time}{Mode}.png`
- **Examples:** `ArcticNightBattle.png`, `BeachBuild.png`, `CaveBattle.png`

### Relic/item definitions

- **Location:** `sharedassets1.assets` → MonoBehaviour objects
- **Naming pattern:** `Relic{ItemName}` (e.g., `RelicBoomerang`, `RelicTreasureChest`)
- **Count:** ~120 relic items identified from binary string search

### Food/perk definitions

- **Location:** Hardcoded in `GameAssembly.dll` like pet data
- **Registry:** Likely in a `SpellConstants` class (food = "Spells" internally)
- **Same extraction challenge as pets**

### Game logic constants (gold, XP, shop tiers, battle formulas)

- **Location:** `GameAssembly.dll` (IL2CPP compiled C++)
- **Extraction:** Need Cpp2IL or Ghidra to reconstruct method bodies
- **Metadata required:** `il2cpp_data/Metadata/global-metadata.dat`
- **Known constants from community wiki:**
  - Gold per turn: 10
  - XP for level 2: 2, level 3: 3 (5 total)
  - Shop tier unlock: tier X on turn 2X−1
  - Max stats: 50 (100 with specific game effects)

## Network API

### Base URL

```
https://api.teamwood.games/{major}.{minor}/api/
```

Currently: `https://api.teamwood.games/0.46/api/`

### Auth flow

1. **Version check** (no auth):
   ```
   GET /api/version/current → {"Major":0,"Minor":46,"Patch":7,"MinimumClientPatch":0}
   ```

2. **Register guest** (no auth):
   ```
   POST /api/user/register-guest
   Content-Type: application/json; utf-8
   Body: {"Version":46}
   → { UserId, Email, Password, Login: { Token, RefreshToken, DeviceId, ... } }
   ```

3. **Login** (subsequent runs):
   ```
   POST /api/user/login
   Content-Type: application/json; utf-8
   Body: {"Email":"...@teamwoodgames.com","Password":"...","Version":46}
   → { Login: { Token, RefreshToken, ... } }
   ```

4. **Authenticated requests** use:
   ```
   Authorization: Bearer <jwt>
   device-id: <uuid>
   language: en
   refresh-token: <token>
   ```

### Known endpoints

| Endpoint | Auth | Returns |
|---|---|---|
| `GET /api/version/current` | No | Version info |
| `POST /api/user/register-guest` | No | Guest credentials + JWT |
| `POST /api/user/login` | No | JWT + refresh token |
| `GET /api/user/current` | Yes | Current user profile |

### What the API does NOT serve

Pet/food game data is **not** served by the network API. The API handles user accounts, matchmaking, and game state. All pet/food/ability definitions are compiled into the game binary.

### Version discovery

- Probing with old versions (e.g., 0.43) returns HTTP 300 with body "Super Auto Pets needs to be updated"
- Current version returns data normally
- Future versions return HTTP 404
- Auto-discovery: probe upward from last known version until a non-300 response

## AssetRipper Output

AssetRipper 1.3.12 Free (Linux x64) was run on the game data. Output at `tmp/assetripper-output/` (20,167 files):

### Key output paths

| Path | Contents |
|---|---|
| `Scripts/Assembly-CSharp/Spacewood/` | Full decompiled C# source (class structure only — method bodies are empty stubs) |
| `Assets/Texture2D/` | Pet sprites as PNG files |
| `Assets/AudioClip/` | Pet sounds as OGG files |
| `Assets/Sprite/` | Sprite metadata as JSON |
| `Assets/Spacewood/Data/` | Changes.json (from Addressable bundle) |
| `Assets/Spacewood/Sprites/` | Backgrounds, previews, stickers |
| `Assemblies/` | Compiled assembly stubs |

### Important decompiled source files

| File | What it contains |
|---|---|
| `Spacewood/Core/Enums/MinionConstants.cs` | Master pet registry — `Dictionary<MinionEnum, MinionTemplate>`, per-pack Create methods |
| `Spacewood/Core/Enums/MinionTemplate.cs` | Pet definition class — Attack, Health, Tier, Packs, Abilities, Tribes |
| `Spacewood/Core/Enums/MinionEnum.cs` | Pet ID → numeric enum mapping (Ant=0, Beaver=3, etc.) |
| `Spacewood/Core/Models/Item/ItemTemplate.cs` | Base item class — Name, Tier, Price, Packs, Roles, Archetypes |
| `Spacewood/Core/Models/MinionModel.cs` | Runtime pet instance — JSON-serializable with short property names |
| `Spacewood/Unity/MinionAsset.cs` | ScriptableObject linking MinionEnum to sprites/sounds/skins |
| `Spacewood/Unity/AbilityAsset.cs` | ScriptableObject for abilities — enum + localized level descriptions |

### What AssetRipper Free CANNOT do

- **Reconstruct method bodies** — all methods return `null`, `false`, `0`, or `default`. The actual game logic and data initialization code is in native `GameAssembly.dll` and requires Cpp2IL or Ghidra.
- **Decode IL2CPP MonoBehaviours into readable fields** — the PrimaryContent export does not reconstruct type trees for MonoBehaviours from IL2CPP builds. The MonoBehaviour binary data in sharedassets is not decoded.

## Extraction Tools

| Tool | Purpose | Input | Output | Status |
|---|---|---|---|---|
| **AssetRipper 1.3.12 Free** | Full Unity project extraction | `Super Auto Pets_Data/` | C# stubs, sprites, audio | Done — output at `tmp/assetripper-output/` |
| **UnityPy** | Read Unity assets (limited without type trees) | `.assets` / `.bundle` files | Sprites, TextAssets, AudioClips | Used for initial exploration |
| **Cpp2IL** | Reconstruct IL2CPP method bodies to C# | `GameAssembly.dll` + `global-metadata.dat` | C# source with actual logic and data values | **Next step — needed to extract pet stats** |
| **Il2CppDumper** | Extract type definitions from IL2CPP binary | `GameAssembly.dll` + `global-metadata.dat` | `dump.cs`, stub DLLs | Alternative to Cpp2IL |
| **Ghidra** | Binary analysis of native code | `GameAssembly.dll` | Reconstructed C/pseudocode | Alternative to Cpp2IL (more manual) |
| **ILSpy CLI** | Decompile .NET DLLs to C# source | Stub DLLs from Il2CppDumper | C# source code | Only for Mono builds or Il2CppDumper stubs |

## Key Gotchas

1. **IL2CPP strips type trees** — UnityPy cannot decode MonoBehaviour fields without external type info. Always use AssetRipper for MonoBehaviour extraction.
2. **AssetRipper Free gives stubs, not implementations** — method bodies are empty. The actual data values (pet stats, tiers, pack assignments) are in native code and require Cpp2IL or Ghidra.
3. **Pet data is NOT in asset files or the network API** — it is hardcoded in `GameAssembly.dll` C# method bodies compiled to native code. The `MinionConstants.CreatePack*()` methods contain all the `SetStats()`, `SetTier()`, `AddPack()` calls but their bodies are empty in the decompiled output.
4. **Pet IDs are numeric internally** — `MinionEnum` maps names to ints (Ant=0, Beaver=3). `Changes.json` uses these numeric IDs.
5. **Internal terminology differs from display names** — Pets = "Minions", Foods = "Spells", Packs use internal names (Pack1=Turtle, Pack2=Puppy, etc.)
6. **More packs exist than originally scoped** — Unicorn (Pack5), Danger (Pack6), Color (Pack7), and Mini packs (Pack8+) were discovered in addition to Turtle/Puppy/Star/Golden.
7. **Addressable catalog is single-line minified JSON** — 128K tokens, must be parsed programmatically, not read directly.
8. **Network API requires version in URL** — old versions return HTTP 300 "needs update"; future versions return 404.
9. **Guest registration creates a real (anonymous) account** — credentials persist. Pipeline should register once and store credentials.
10. **AssetRipper runs as a headless web server** — API at `http://localhost:{port}`. Load via `POST /LoadFolder`, export via `POST /Export/PrimaryContent`. Binary at `tmp/assetripper/AssetRipper.GUI.Free` (needs `chmod +x`).

## Next Steps

1. **Run Cpp2IL** on `GameAssembly.dll` + `global-metadata.dat` to reconstruct the `MinionConstants.CreatePack*()` method bodies and extract all pet stats/tiers/packs.
2. **Build a parser** that reads the Cpp2IL output and produces structured JSON (pets.json, foods.json).
3. **Update data-schema-spec.md** to reflect the actual data model (MinionTemplate fields, additional packs discovered).
4. **Update data-pipeline-strategy.md** to reflect that data extraction is from `GameAssembly.dll` via Cpp2IL, not from the network API.
