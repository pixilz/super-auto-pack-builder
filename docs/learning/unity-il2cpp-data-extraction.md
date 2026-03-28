# Learning Note: Extracting Data from a Unity IL2CPP Game

> How we reverse-engineered Super Auto Pets to find where the game data lives and how to extract it.

## The Goal

Build a data pipeline that extracts pet stats, abilities, food definitions, and sprites from Super Auto Pets — a Unity game — without relying on community datasets.

## Step 1: Figure Out What Kind of Unity Build It Is

Unity games compile to one of two backends:

- **Mono** — ships `Assembly-CSharp.dll` in a `Managed/` folder. This is a normal .NET DLL you can open in ILSpy/dnSpy and read like source code.
- **IL2CPP** — compiles C# to C++, then to native code. Ships `GameAssembly.dll` (a native binary, not .NET) plus `il2cpp_data/Metadata/global-metadata.dat`.

**How to tell which one:** Look in the game's root directory. If you see `GameAssembly.dll` without a `Managed/Assembly-CSharp.dll`, it's IL2CPP.

SAP is IL2CPP. This means standard .NET decompilers (ILSpy, dnSpy) can't read the game logic directly.

## Step 2: Find Where the Data Lives

Unity games store data in several places. We checked each one:

### Asset Bundles (Addressables)

Located in `StreamingAssets/aa/StandaloneWindows64/`. These are Unity's modern asset packaging system. We used **UnityPy** (a Python library) to inspect them:

```python
import UnityPy
env = UnityPy.load("path/to/bundle.bundle")
for path, obj in env.container.items():
    print(obj.type.name, "|", path)
```

**What we found:** Background sprites, mascot pose data, audio clips, localization string tables, and a `Changes.json` (patch notes). No pet stat data.

The `catalog.json` in the `aa/` folder is the index of all addressable assets. It tells you what's in each bundle without opening them. It's a single minified JSON line — parse it with a script, don't try to read it.

### sharedassets Files

These are Unity's scene-embedded asset files. We inventoried them:

```python
env = UnityPy.load("sharedassets1.assets")
types = {}
for obj in env.objects:
    types[obj.type.name] = types.get(obj.type.name, 0) + 1
print(types)
```

**What we found:** `sharedassets1.assets` contains 9,690 MonoBehaviours, 2,494 Sprites, and 768 AnimationClips. This is where the pet data lives.

### The Problem: IL2CPP Strips Type Trees

In a Mono build, MonoBehaviour objects carry their full type tree — UnityPy can decode every field by name. In IL2CPP builds, Unity strips this metadata to save space. All you get is raw binary data with no field labels.

We confirmed this by reading MonoBehaviours — they only showed base fields (`m_GameObject`, `m_Enabled`, `m_Script`, `m_Name`) with empty names.

### Searching Raw Binary

We searched the raw bytes for recognizable strings like pet names:

```python
raw = obj.get_raw_data()
if b'Animals' in raw:
    # Found a pet definition
```

This confirmed 775 unique pets exist as binary MonoBehaviours. We could see names (`Beaver`, `Cricket`, etc.) and category markers (`Animals`), but couldn't decode the fields (stats, tiers, abilities) without type information.

### The m_Script Reference Trick

Even without type trees, you can identify WHAT each MonoBehaviour is by reading its `m_Script` reference:

```python
data = obj.read()
script = data.m_Script.read()
class_name = script.m_ClassName  # e.g., "SoundGroupVariationUpdater"
```

This tells you the C# class name. Unfortunately, most pet-related scripts didn't resolve this way because the references pointed to stripped IL2CPP types.

## Step 3: Check If the Data Comes From a Network API

Many modern games fetch configuration data from servers. We used `strings` on the IL2CPP metadata to find URL patterns:

```bash
strings global-metadata.dat | grep "teamwood\|api\."
```

This revealed: `https://api.teamwood.games/{0}.{1}/api/`

We then probed the API with curl. Version discovery:

```bash
# Old versions return HTTP 300 "needs update"
curl -sL "https://api.teamwood.games/0.43/api/version/current"
# → "Super Auto Pets needs to be updated"

# Current version returns data
curl -s "https://api.teamwood.games/0.46/api/version/current"
# → {"Major":0,"Minor":46,"Patch":7,"MinimumClientPatch":0}
```

We captured the full auth flow from the browser (itch.io web version + DevTools Network tab):

1. `GET /api/version/current` — no auth needed
2. `POST /api/user/register-guest` with `{"Version":46}` — returns a JWT
3. All subsequent requests use `Authorization: Bearer <jwt>`

**Key finding:** The API handles user accounts and game state, NOT pet/food definitions. No endpoint returns game data. The pet data is compiled into the binary.

## Step 4: The Right Tool — AssetRipper

Since the data is in binary MonoBehaviours and we're on IL2CPP, the correct tool is **AssetRipper**. It:

1. Reads `GameAssembly.dll` + `global-metadata.dat` to reconstruct type definitions
2. Uses those types to decode every MonoBehaviour field
3. Outputs a full Unity project with human-readable YAML or JSON

This replaces manual binary parsing entirely.

**Alternative approach:** Use **Il2CppDumper** to extract type definitions as `dump.cs`, then manually feed those into UnityPy. This gives more control but requires more work. AssetRipper automates both steps.

## Step 5: Sprite Extraction (Works Without Type Trees)

Sprites and textures don't need type tree reconstruction — their binary format is standardized. UnityPy handles them natively:

```python
for obj in env.objects:
    if obj.type.name == "Texture2D":
        data = obj.read()
        data.image.save(f"sprites/{data.m_Name}.png")
```

This works regardless of IL2CPP vs Mono.

## Summary of Tools

| Tool | What it does | When to use |
|---|---|---|
| **UnityPy** | Python library for reading Unity assets | Sprites, audio, text assets — anything with a known binary format |
| **AssetRipper** | Full project extraction with type reconstruction | MonoBehaviours in IL2CPP builds (pet data, abilities, configs) |
| **Il2CppDumper** | Extracts type defs from IL2CPP metadata | When you need C# class signatures but not the full project |
| **ILSpy/dnSpy** | .NET decompiler | Only works on Mono builds, or on stubs from Il2CppDumper |
| **strings + grep** | Search for readable strings in binary files | Quick recon — finding URLs, version strings, class names |
| **Browser DevTools** | Capture network requests | Understanding what the game fetches from servers |

## Step 6: AssetRipper — Getting the Class Structure

We ran AssetRipper 1.3.12 Free (Linux x64) against the entire `Super Auto Pets_Data/` folder. It runs as a headless web server:

```bash
chmod +x AssetRipper.GUI.Free
./AssetRipper.GUI.Free --headless --port 8765
# Load game data
curl -X POST "http://localhost:8765/LoadFolder" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "path=/path/to/Super Auto Pets_Data"
# Export
curl -X POST "http://localhost:8765/Export/PrimaryContent" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "path=/path/to/output"
```

It has a Swagger/OpenAPI spec at `/openapi.json` — use that to discover all available endpoints.

**What AssetRipper gave us (20,167 files):**
- Full decompiled C# class structure in `Scripts/Assembly-CSharp/`
- Pet sprites as PNG files in `Assets/Texture2D/`
- Audio clips as OGG files in `Assets/AudioClip/`
- The complete class hierarchy: `MinionConstants` → `MinionTemplate` → `ItemTemplate`

**What we learned from the decompiled code:**
- Pets are called "Minions" internally, foods are "Spells"
- `MinionConstants` is the master registry with `CreatePack1Turtle()`, `CreatePack2Puppy()`, etc.
- `MinionTemplate` has all the fields: Attack, Health, Tier, Packs, Abilities, Tribes
- `MinionEnum` maps pet names to numeric IDs (Ant=0, Beaver=3, Cricket=17)

**The critical limitation:** AssetRipper Free decompiles class structure (fields, method signatures) but **all method bodies are empty stubs** returning `null`/`0`/`false`. The actual data — every `SetStats(3, 2)`, `SetTier(1)`, `AddPack(Pack.Turtle)` call — is locked in the native `GameAssembly.dll` binary.

This means AssetRipper alone cannot extract pet stats. We need **Cpp2IL** or **Ghidra** to reconstruct the method implementations from native code.

## Step 7: The Network API Red Herring

We initially assumed the game fetched pet data from the network (community research suggested this). After capturing network traffic with browser DevTools on the itch.io web version, we found:

- The API (`api.teamwood.games`) handles user accounts, matchmaking, and game state
- The auth flow is: `register-guest` → JWT → authenticated requests
- **No endpoint serves pet/food game data** — it's all compiled into the client

This was an important discovery: the data extraction path is entirely local (decompile the binary), not network-based.

## What Would I Do Differently

1. **Check the build type first.** The Mono vs IL2CPP distinction determines your entire toolchain. Check for `GameAssembly.dll` vs `Assembly-CSharp.dll` before doing anything else.
2. **Start with AssetRipper.** We spent time manually inspecting binary MonoBehaviours with UnityPy before realizing type trees were stripped. AssetRipper should be the first tool for any IL2CPP game.
3. **Don't hand-parse binary when tools exist.** We wrote Python to decode raw MonoBehaviour bytes before realizing AssetRipper does this automatically. Use the right tool.
4. **Use browser DevTools immediately** for network recon rather than guessing API paths with curl. Opening the web version and watching the Network tab gave us the exact auth flow in seconds.
5. **Don't assume "decompile" means one thing.** For this game, the data extraction involves three completely different techniques: asset extraction (UnityPy/AssetRipper), native code decompilation (Cpp2IL/Ghidra), and network API capture (browser DevTools + curl). No single tool does everything.
6. **AssetRipper Free has real limits.** It gives class structure but not method implementations. For data that lives in code (not assets), you need Cpp2IL or a binary analysis tool like Ghidra.

## Key Takeaways for the Resume

- Unity IL2CPP builds require specialized tooling (AssetRipper, Il2CppDumper, Cpp2IL) — standard .NET decompilers don't work
- Game data can live in multiple places: asset bundles, sharedassets files, compiled native code, or network APIs
- For SAP specifically: pet/food data is hardcoded in native code, sprites are in sharedassets, and the network API only handles user/matchmaking
- The Unity Addressables system (`StreamingAssets/aa/`) has a catalog that maps assets to bundles
- `strings` on `global-metadata.dat` is a fast way to find URLs, version strings, and class names in IL2CPP builds
- The web/itch.io version of a game is the easiest target for network analysis — just use browser DevTools
- AssetRipper Free gives you the full class hierarchy (invaluable for understanding the data model) but not the data values — those need Cpp2IL or Ghidra
- The tool chain for full IL2CPP data extraction is: AssetRipper (class structure + assets) → Cpp2IL (method bodies + data values) → custom parser (structured JSON output)
