# SAP Decompilation & Reverse Engineering Guide

> A hands-on guide for humans who want to explore Super Auto Pets game data using our decompilation tools. No prior reverse engineering experience required.
>
> **Why this exists:** Our automated pipeline extracts ~97% of pet data, but some fields (especially ability triggers) still need human investigation. This guide teaches you to use the same tools our scripts use, so you can verify data, investigate gaps, or just satisfy your curiosity about how the game works.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Understanding the Game's Architecture](#2-understanding-the-games-architecture)
3. [Tool 1: Cpp2IL — Reading Pet Stats from Native Code](#3-tool-1-cpp2il--reading-pet-stats-from-native-code)
4. [Tool 2: UnityPy — Extracting Localization and Assets](#4-tool-2-unitypy--extracting-localization-and-assets)
5. [Tool 3: AssetRipper — Understanding Class Structure](#5-tool-3-assetripper--understanding-class-structure)
6. [Tool 4: Ghidra — Deep Binary Analysis](#6-tool-4-ghidra--deep-binary-analysis)
7. [Common Tasks (How Do I Find...?)](#7-common-tasks-how-do-i-find)
8. [Using Our Scripts as Helpers](#8-using-our-scripts-as-helpers)
9. [Glossary](#9-glossary)

---

## 1. Prerequisites

### Game Files

You need a copy of the SAP game files from a Steam (Windows) installation. Copy the entire game folder to `Downloaded Super Auto Pets/` in the repo root (this path is gitignored).

The key files you need:
- `GameAssembly.dll` — the compiled game logic (this is the big one, ~60MB)
- `Super Auto Pets_Data/il2cpp_data/Metadata/global-metadata.dat` — type metadata
- `Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64/*.bundle` — asset bundles

### Tools

All tools should be run inside the Docker container unless noted:

| Tool | Where to Get It | Used For |
|------|----------------|----------|
| **Cpp2IL** | [GitHub releases](https://github.com/SamboyCoding/Cpp2IL/releases) — download to `tmp/cpp2il/` | Reading method bodies (pet stats) |
| **UnityPy** | `pip install UnityPy` (in container) | Asset bundles, localization |
| **AssetRipper** | [GitHub releases](https://github.com/AssetRipper/AssetRipper/releases) — download to `tmp/assetripper/` | Class structure, sprites |
| **Ghidra** | Already at `tmp/ghidra/ghidra_12.0.4_PUBLIC/` — requires JDK 21 | Deep binary analysis |
| **Python 3** | Already in container | Running scripts |

---

## 2. Understanding the Game's Architecture

Before touching any tools, you need to understand what kind of game this is.

### SAP is a Unity IL2CPP Build

Unity games can compile in two ways:
- **Mono** — ships a `Assembly-CSharp.dll` that any .NET decompiler (ILSpy, dnSpy) can open and read like source code. Easy mode.
- **IL2CPP** — compiles C# to C++ to native machine code. Ships `GameAssembly.dll` which is just x86-64 binary. No standard decompiler works.

**SAP uses IL2CPP.** This is why we need specialized tools.

### Where Data Lives (The Short Version)

The game's internal naming is different from what players see:
- **Pets** are called "Minions" in code
- **Foods** are called "Spells" in code
- **Packs** use internal names: Pack1 = Turtle, Pack2 = Puppy, etc.

```
Pet stats (attack, health, tier)     → locked in native code (GameAssembly.dll)
Pet/ability names and descriptions   → in localization string bundles
Pet sprites and audio                → in sharedassets1.assets
Ability triggers                     → locked in native code (the hard problem)
Patch changelog                      → in an addressable bundle as Changes.json
```

### The IL2CPP Challenge

In a Mono Unity game, finding "Beaver has 3 attack and 2 health" would be as simple as opening a DLL in a decompiler and reading:

```csharp
// What you'd see in a Mono game:
beaver.SetStats(attack: 3, health: 2);
```

In IL2CPP, that same line becomes something like:

```asm
; What you see in the native binary:
mov ecx, 3        ; attack value
mov edx, 2        ; health value
call 0x180A3F210  ; MinionTemplate.SetStats (but you don't know that yet)
```

The tools below help reconstruct the original C# intent from this machine code.

---

## 3. Tool 1: Cpp2IL — Reading Pet Stats from Native Code

Cpp2IL is your primary tool for extracting game data. It takes the IL2CPP binary and reconstructs human-readable intermediate code.

### Running Cpp2IL

```bash
# From the repo root, inside Docker:
docker compose run app tmp/cpp2il/Cpp2IL \
  --game-path "Downloaded Super Auto Pets" \
  --output-as isil \
  --output-to tmp/pipeline/cpp2il-isil

# Also generate C# stubs (useful for enum definitions):
docker compose run app tmp/cpp2il/Cpp2IL \
  --game-path "Downloaded Super Auto Pets" \
  --output-as diffable-cs \
  --output-to tmp/pipeline/cpp2il-cs
```

This takes 60-120 seconds and produces two output directories.

### What You Get

**ISIL output** (`tmp/pipeline/cpp2il-isil/IsilDump/Assembly-CSharp/`):
Text files with reconstructed method bodies. This is where all the pet data lives.

**C# stubs** (`tmp/pipeline/cpp2il-cs/DiffableCs/Assembly-CSharp/`):
Decompiled class definitions with enum values, field types, and method signatures (but empty method bodies — only Cpp2IL's ISIL output has the actual logic).

### Finding Pet Data

The master file is:
```
tmp/pipeline/cpp2il-isil/IsilDump/Assembly-CSharp/Spacewood/Core/Enums/MinionConstants.txt
```

Open this file and search for `CreatePack1Turtle` to find the Turtle Pack pets. Here's what you'll see (simplified from actual output — line numbers match the real file):

```
Method: System.Void CreatePack1Turtle()

ISIL (simplified from actual output — line numbers match real file):
  222 LoadAddress rdx, [rbx+1]       ← tier value = 1
  223 Call 0x1811A24E0, rcx, rdx     ← Nullable<int> constructor
  235 Call MinionConstants.StartGroup ← sets tier for following pets

  242 Call MinionConstants.Create     ← registers a new pet (Duck)
  243 Move rdx, "Duck"               ← name string visible in ISIL

  251 Move rdx, 2                    ← attack = 2
  253 Move r8, rdx                   ← health = 2
  255 Call MinionTemplate.SetStats, rcx, rdx, r8

  264 Move [rax+32], 16             ← archetype enum 16 in array
  270 Call MinionTemplate.SetArchetypeProducer

  274 LoadAddress rdx, [rbx+41]     ← AbilityEnum value 41 = DuckAbility
  276 Call MinionTemplate.AddAbility, rcx, rdx
```

### Reading ISIL: A Practical Primer

ISIL (Intermediate Static IL) looks intimidating but follows simple patterns:

**Registers** are named storage slots: `rcx`, `rdx`, `r8`, `r9`, `rax`. Think of them as variables.

**Move** puts a value into a register:
```
Move rcx, 0x3     → rcx now holds the value 3
Move rdx, rcx     → rdx now holds whatever rcx holds
```

**LoadAddress** computes an address offset (pointer arithmetic):
```
LoadAddress rdx, [rbx+3]  → rdx = rbx + 3. If rbx is 0, rdx = 3.
```
This is commonly how stat values and enum IDs are loaded.

**Call** invokes a function, passing arguments from registers:
```
Call MinionTemplate.SetStats, rcx, rdx, r8
                              ↑     ↑    ↑
                              self   atk  hp
```

The x86-64 calling convention uses registers in order: `rcx` (1st arg), `rdx` (2nd), `r8` (3rd), `r9` (4th).

**The pattern for every pet is:**
1. `Call MinionConstants.Create` — registers the pet (enum value passed in a register)
2. `Move rdx, <attack>` + `Move r8, <health>` → `Call SetStats` — sets stats
3. `Move rdx, <ability_enum>` or `LoadAddress rdx, [rbx+N]` → `Call AddAbility` — assigns ability
4. (Optional) Array construction + `Call SetArchetypeProducer/Consumer` — assigns archetypes

### Looking Up Enum Values

To translate the numeric values to names, check the C# stubs:

```
tmp/pipeline/cpp2il-cs/DiffableCs/Assembly-CSharp/Spacewood/Core/Enums/MinionEnum.cs
```

This file has entries like:
```csharp
Ant = 0,
AntToken = 1,
Badger = 2,
Beaver = 3,
Bee = 4,
```

Similarly for abilities:
```
.../Spacewood/Core/Models/Abilities/AbilityEnum.cs
```

And archetypes:
```
.../Spacewood/Core/Enums/Archetype.cs
```

### Tips for Browsing ISIL

- **Search for a specific pet:** Find its enum value in `MinionEnum.cs`, then search for the corresponding `Move` or `LoadAddress` before a `Create` call in `MinionConstants.txt`
- **Find all pets in a pack:** Search for the `CreatePack*` method name
- **Tier changes:** Look for `StartGroup` calls — every pet created after a `StartGroup` inherits that tier until the next one
- **Multiple abilities:** Some pets have multiple `AddAbility` calls (one per ability slot)
- **Name strings:** Many pets have a `Move rdx, "PetName"` right after their `Create` call — this helps confirm which pet you're looking at

---

## 4. Tool 2: UnityPy — Extracting Localization and Assets

UnityPy is a Python library for reading Unity asset files. You'll use it for localization strings, sprites, and anything stored in `.assets` or `.bundle` files.

### Quick Start — Interactive Exploration

```bash
# Inside Docker:
docker compose run app python3
```

```python
import UnityPy

# Load an asset bundle
env = UnityPy.load("Downloaded Super Auto Pets/Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64/localization-string-tables-english_assets_all.bundle")

# See what's inside
for obj in env.objects:
    print(f"Type: {obj.type.name}, Size: {len(obj.get_raw_data())} bytes")
```

### Extracting Sprites

```python
import UnityPy

env = UnityPy.load("Downloaded Super Auto Pets/Super Auto Pets_Data/sharedassets1.assets")

for obj in env.objects:
    if obj.type.name == "Texture2D":
        data = obj.read()
        if data.m_Name:  # Skip unnamed textures
            data.image.save(f"tmp/sprites/{data.m_Name}.png")
            print(f"Saved {data.m_Name}.png")
```

### Exploring What's in sharedassets1

This is the biggest asset file. Here's what's inside (verified counts):

| Type | Count |
|------|-------|
| MonoBehaviour | 9,690 |
| Sprite | 2,494 |
| Texture2D | 2,485 |
| AnimationClip | 768 |
| AudioClip | 623 |

### Exploring Localization Strings

The localization system uses two bundles that work together:

1. **SharedTableData** (key registry): Maps human-readable key names to numeric key IDs — `localization-assets-shared_assets_all.bundle` (195,096 bytes, 4,476 keys)
2. **StringTable** (text data): Maps key IDs to actual text strings — `localization-string-tables-english_assets_all.bundle` (293,560 bytes, 5,304 entries)

Both are MonoBehaviour objects with a custom binary table format (no type tree in IL2CPP builds). Our parser reads:
```
[8-byte key ID] [4-byte string length] [UTF-8 string, 0-padded to 4-byte alignment] [4-byte padding]
```

You can verify the keys are there by searching the raw bytes:

```python
import UnityPy

env = UnityPy.load("Downloaded Super Auto Pets/Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64/localization-assets-shared_assets_all.bundle")

for obj in env.objects:
    if obj.type.name == "MonoBehaviour":
        raw = obj.get_raw_data()
        if len(raw) > 100000:
            text = raw.decode('utf-8', errors='replace')
            # Search for specific keys:
            print(f"Minion.Beaver.Name: {'Minion.Beaver.Name' in text}")
            print(f"Ability.BeaverAbility: {'Ability.BeaverAbility' in text}")
```

The full parser is in `extract.py` — the `parse_binary_table()` and `extract_localization()` functions. Use those as reference.

### The IL2CPP Type Tree Problem

When you try to read MonoBehaviour objects, you'll notice most fields are empty or missing. This is because IL2CPP builds strip type trees to save space. UnityPy can only decode fields for objects with standardized binary formats (Texture2D, AudioClip, TextAsset).

For MonoBehaviours (which hold game-specific data), you'll see only base fields:
```python
data = obj.read()
print(data.m_Name)        # Works
print(data.m_Script)      # Works (gives you the class reference)
# But game-specific fields (attack, health, etc.) are NOT accessible
```

This is why we need Cpp2IL for stats and Ghidra for deep analysis — the data is in compiled code, not in asset fields.

### Useful Things to Explore with UnityPy

| Asset File | What You'll Find |
|------------|-----------------|
| `sharedassets1.assets` | 9,690 MonoBehaviours, 2,494 Sprites, 768 AnimationClips, 623 AudioClips |
| `localization-string-tables-english_assets_all.bundle` | All English text (pet names, ability descriptions, UI strings) |
| `defaultlocalgroup_assets_all_*.bundle` | Changes.json, backgrounds, mascot poses |

---

## 5. Tool 3: AssetRipper — Understanding Class Structure

AssetRipper does a full extraction of a Unity project. It gives you the complete C# class hierarchy — every field, every interface, every enum. The catch: method bodies are empty stubs (because IL2CPP).

### Running AssetRipper

```bash
# Make it executable (first time only)
chmod +x tmp/assetripper/AssetRipper.GUI.Free

# Start the headless server
tmp/assetripper/AssetRipper.GUI.Free --headless --port 8765

# In another terminal, load the game data:
curl -X POST "http://localhost:8765/LoadFolder" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "path=$(pwd)/Downloaded Super Auto Pets/Super Auto Pets_Data"

# Export everything:
curl -X POST "http://localhost:8765/Export/PrimaryContent" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "path=$(pwd)/tmp/assetripper-output"
```

The export takes a few minutes and produces ~20,000 files.

### What AssetRipper Gives You

The real value is the decompiled C# source in `tmp/assetripper-output/Scripts/Assembly-CSharp/Spacewood/`:

**Understanding pet data structure** — read `Core/Enums/MinionTemplate.cs`:
```csharp
public class MinionTemplate : ItemTemplate
{
    public MinionEnum Enum;
    public int Attack;
    public int Health;
    public int? AttackMax;
    public int? HealthMax;
    public List<AbilityEnum> AbilityEnums;
    public List<TribeEnum> Tribes;
    // ... many more fields

    // All methods return null — empty stubs:
    public MinionTemplate SetStats(int attack, int health) { return null; }
    public MinionTemplate AddAbility(AbilityEnum ability) { return null; }
    public MinionTemplate SetArchetypeProducer(params Archetype[] archetypes) { return null; }
}
```

This tells you WHAT fields and methods exist, even though it can't tell you what VALUES they hold. The empty stubs are the key limitation of AssetRipper on IL2CPP builds.

### Key Files to Browse

| File | What You Learn |
|------|---------------|
| `Spacewood/Core/Enums/MinionConstants.cs` | All `CreatePack*()` method signatures — tells you which packs exist |
| `Spacewood/Core/Enums/MinionTemplate.cs` | Every field a pet can have (295 lines of fields and methods) |
| `Spacewood/Core/Models/Item/ItemTemplate.cs` | Base fields (Name, Tier, Price, Packs, Archetypes, Active, Rollable) |
| `Spacewood/Core/Enums/MinionEnum.cs` | Full pet ID → name mapping |
| `Spacewood/Core/Models/Abilities/AbilityEnum.cs` | Full ability ID → name mapping |
| `Spacewood/Unity/MinionAsset.cs` | How pets link to sprites and sounds |
| `Spacewood/Unity/AbilityAsset.cs` | How abilities link to descriptions |

### When to Use AssetRipper vs Cpp2IL

- **AssetRipper:** "What fields does a pet have?" / "What classes exist?" / "How are abilities structured?"
- **Cpp2IL:** "What are Beaver's actual stats?" / "Which pets are in the Star pack?"

AssetRipper gives you the blueprint. Cpp2IL gives you the data that fills the blueprint.

---

## 6. Tool 4: Ghidra — Deep Binary Analysis

Ghidra is the NSA's open-source reverse engineering tool. It's powerful but has a steep learning curve. You'll use it when the other tools aren't enough — specifically for understanding complex native code patterns like trigger assignment.

### When You Need Ghidra

- Investigating ability trigger assignment (the mechanism that determines "this ability fires on Sell")
- Understanding complex control flow in lambda functions
- Resolving IL2CPP metadata tokens to class names
- Tracing code paths that Cpp2IL can't reconstruct

### Setting Up a Ghidra Project

**Ghidra 12.0.4 requires JDK 21.** Install it first:
```bash
sudo apt-get install -y openjdk-21-jdk-headless
export JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64
```

1. **Launch Ghidra:**
   ```bash
   JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
   tmp/ghidra/ghidra_12.0.4_PUBLIC/ghidraRun
   ```

2. **Create a new project:** File → New Project → Non-Shared → pick a folder and name

3. **Import GameAssembly.dll:** File → Import File → select `Downloaded Super Auto Pets/GameAssembly.dll`
   - Format: PE (auto-detected)
   - Language: x86:LE:64:default (auto-detected)
   - Click OK

4. **Auto-analyze:** When prompted, accept the default analysis options. **This takes 30-60 minutes for SAP's ~60MB binary.** Go make coffee — seriously. Don't check on it every 2 minutes.

5. **Apply Il2CppDumper metadata (optional but very helpful):**
   - Run Il2CppDumper first to generate `script.json`
   - In Ghidra: File → Parse C Source → load the `dump.cs` from Il2CppDumper
   - Or use the [Il2CppDumper Ghidra plugin](https://github.com/praydog/Il2CppDumper-Ghidra) to auto-label functions

### Headless Mode (Batch Analysis)

For unattended analysis, use headless mode:
```bash
JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64 \
tmp/ghidra/ghidra_12.0.4_PUBLIC/support/analyzeHeadless \
  tmp/ghidra_project SAP_Analysis \
  -import "Downloaded Super Auto Pets/GameAssembly.dll" \
  -processor "x86:LE:64:default" \
  -analysisTimeoutPerFile 7200 \
  > tmp/ghidra_headless.log 2>&1
```

This is how we batch-decompiled 18,657 functions for the trigger research. The output goes into a Ghidra project that you can then open in the GUI.

### Navigating Ghidra for SAP Data

Once analysis completes:

**Finding a specific function by name:**
1. Window → Symbol Table
2. Filter by name (e.g., "CreatePack1Turtle")
3. Double-click to go to the function

**Reading decompiled code:**
The Decompiler window (right panel) shows reconstructed C-like pseudocode:

```c
void MinionConstants$$CreatePack1Turtle(void) {
    // Nullable<int> tier = new Nullable<int>(1);
    local_38 = FUN_1811A24E0(1);
    // MinionConstants.StartGroup(tier)
    FUN_18070F840(local_38);

    // MinionConstants.Create(MinionEnum.Duck)
    local_30 = FUN_18070F920(26);

    // pet.SetStats(2, 2)
    FUN_18070FAC0(local_30, 2, 2);

    // pet.AddAbility(AbilityEnum.DuckAbility)
    FUN_18070FB40(local_30, 41);
}
```

Without Il2CppDumper labels, function names will be `FUN_XXXXXXXXX`. With labels, they'll have readable names.

**Finding trigger factories:**
Search the decompiled output for functions that call `SetTrigger` or create `TriggerBase` subclass instances. Our research identified 36 such factory functions in the ability code range.

### Init Flags — Cross-Referencing with Cpp2IL

A powerful technique: each lambda function has a unique initialization flag with pattern `DAT_183aXXXXX == '\0'`. This exact same address appears in both Ghidra decompiled output and Cpp2IL ISIL output.

To cross-reference:
1. Find the lambda in Ghidra — note its `DAT_183a` address
2. Search for that same address in the Cpp2IL ISIL dump
3. Now you know which lambda in Ghidra corresponds to which ability in our extracted data

We verified this across all 785 ability lambdas with 100% match rate.

### Ghidra Tips for Beginners

- **Don't panic** — the decompiled output looks messy because it's reconstructed from machine code, not original source
- **Rename things** — right-click any `FUN_` or `DAT_` label and rename it when you figure out what it is. Ghidra saves these labels.
- **Follow the calls** — double-click any function name to jump to its implementation
- **Go back** — Alt+Left Arrow to return to where you were
- **Xrefs** — right-click a function → "References to" shows everywhere that function is called. Essential for understanding patterns.
- **The Listing view** (left panel) shows raw assembly — you can match this against Cpp2IL's ISIL output
- **Save often** — Ghidra auto-saves, but Ctrl+S doesn't hurt
- **Be patient** — initial analysis takes 30-60 minutes. Let it run.

---

## 7. Common Tasks (How Do I Find...?)

### "What are the stats for a specific pet?"

1. Look up the pet's enum value in `MinionEnum.cs` (e.g., Beaver = 3)
2. Open `MinionConstants.txt` (the ISIL dump)
3. Search for the `CreatePack*` method that contains this pack
4. Find the `Create` call followed by a `Move rdx, "Beaver"` name string
5. The next `SetStats` call has attack in `rdx` and health in `r8`

**Or, faster:** Run our pipeline script and check the output:
```bash
docker compose run app python3 scripts/data-pipeline/extract.py \
  --game-dir "Downloaded Super Auto Pets" --output tmp/pets.json
# Then search tmp/pets.json for the pet name
```

### "What ability does a pet have?"

1. Find the pet in ISIL (same as above)
2. Look for `Call MinionTemplate.AddAbility` — the `rdx` argument is the AbilityEnum value
3. Look up that value in `AbilityEnum.cs`
4. Then find the ability description in localization (key: `Ability.{Name}.{Level}.About`)

### "What does an ability actually do?" (beyond the description)

This is where Ghidra comes in:
1. Find the AbilityEnum value
2. In Ghidra, find the lambda function that registers this ability
3. Read the decompiled pseudocode to understand the actual effect logic

### "What trigger fires this ability?"

This is the hard one. Current options:
1. **Check trigger-map.json** — if the ability is in there (509 entries), you have the answer
2. **Check groundedsap.co.uk** — for the current version, they have all triggers
3. **Ghidra research** — find the lambda, trace which `TriggerBase` subclass is instantiated. See `docs/research/trigger-extraction-status.md` for what we've learned so far.

### "What changed in the latest patch?"

```python
import UnityPy, json
env = UnityPy.load("Downloaded Super Auto Pets/Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64/defaultlocalgroup_assets_all_<hash>.bundle")
for path, obj in env.container.items():
    if 'Changes' in path:
        data = obj.read()
        changes = json.loads(data.m_Script)  # or data.text depending on version
        print(json.dumps(changes, indent=2))
```

Note: `Changes.json` uses numeric pet IDs, not names. Cross-reference with `MinionEnum.cs`.

### "What packs exist and what's in them?"

Search `MinionConstants.txt` for all methods matching `Create\w+()`. Each method name tells you the pack:

```bash
grep "Method: System.Void Create" tmp/pipeline/cpp2il-isil/IsilDump/Assembly-CSharp/Spacewood/Core/Enums/MinionConstants.txt
```

We found 37 Create methods including all standard packs plus Custom, Draft, Relic, Rework, and test methods.

### "Is there a pet sprite for X?"

```python
import UnityPy
env = UnityPy.load("Downloaded Super Auto Pets/Super Auto Pets_Data/sharedassets1.assets")
names = [obj.read().m_Name for obj in env.objects if obj.type.name == "Texture2D"]
# Search for your pet:
matches = [n for n in names if 'Beaver' in n]
print(matches)  # ['Beaver', 'Beaver_2x']
```

---

## 8. Using Our Scripts as Helpers

You don't have to do everything manually. Our pipeline scripts handle the heavy lifting.

### Full Pipeline Run

```bash
docker compose run app python3 scripts/data-pipeline/extract.py \
  --game-dir "Downloaded Super Auto Pets" \
  --output tmp/pets.json \
  --trigger-map scripts/data-pipeline/trigger-map.json
```

This runs Cpp2IL, parses ISIL, extracts localization, applies triggers, and outputs a complete `pets.json`.

**Expected output:** 672 pets, 554 with stats, 617 with abilities, 501 with triggers.

### Standalone ISIL Parser (for development/debugging)

If you've already run Cpp2IL and just want to re-parse the output:

```bash
docker compose run app python3 scripts/data-pipeline/parse-isil-standalone.py
```

This reads from `tmp/cpp2il-isil/` and `tmp/cpp2il-cs/`, outputs to `tmp/extracted-pets-full.json`, and prints detailed per-pack statistics.

### Version Checker

```bash
docker compose run app python3 scripts/data-pipeline/check-version.py
# Exit code 0 = new version available
# Exit code 1 = no update
```

### Modifying the Parser

If you're investigating a data gap (e.g., improving archetype extraction), the key function to modify is `extract_pets_from_isil()` in `extract.py`. The parser works by:

1. Splitting `MinionConstants.txt` by method boundaries
2. For each `CreatePack*` method, extracting the ISIL section
3. Simulating register state line by line
4. Recognizing known `Call` patterns and extracting arguments

To add support for a new call pattern, add another `elif` branch in the call handler:
```python
elif method_name == 'MinionTemplate.SomeNewMethod':
    # Extract whatever this method sets
    if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
        current_pet['new_field'] = arg_vals[1]
```

---

## 9. Glossary

| Term | Meaning |
|------|---------|
| **IL2CPP** | Unity's "Intermediate Language to C++" compiler. Converts C# to native code for performance. Makes decompilation harder. |
| **ISIL** | Intermediate Static IL — Cpp2IL's reconstructed representation of method bodies. Human-readable but not real C#. |
| **Metadata token** | A numeric reference (e.g., `0x6000XXXX`) that IL2CPP uses to refer to types, methods, and fields at runtime. Must be resolved through the metadata tables. |
| **global-metadata.dat** | The IL2CPP metadata file containing all type definitions, method signatures, string literals, etc. Required by every decompilation tool. |
| **MonoBehaviour** | Unity's base class for game scripts attached to GameObjects. In SAP, each pet/ability/item is a MonoBehaviour. |
| **Type tree** | Metadata that describes MonoBehaviour fields by name and type. Present in Mono builds, stripped in IL2CPP builds. This is why UnityPy can't read pet fields directly. |
| **Addressables** | Unity's modern asset packaging system. Bundles are in `StreamingAssets/aa/`. The `catalog.json` indexes them. |
| **Enum** | A named set of integer constants. `MinionEnum.Beaver = 3` means Beaver's internal ID is 3. |
| **Lambda** | An anonymous function. In SAP, each ability's behavior is defined in a lambda that gets compiled to a separate native function. |
| **Init flag** | A static boolean (`DAT_183aXXXXX`) that each lambda checks to see if it's been initialized. Unique per lambda — useful as a fingerprint. |
| **Factory function** | A function that constructs a specific type of trigger object. We found 36 of these, mapping to 14 different trigger types. |
| **Rosetta Stone** | Our name for the technique of using groundedsap's known-good data to map between our extracted enums and human-readable trigger names. |
| **GSAP** | Shorthand for groundedsap.co.uk — the community data source we validate against. |
| **Calling convention** | The rule for how function arguments are passed. x86-64 Windows uses: rcx (1st), rdx (2nd), r8 (3rd), r9 (4th). |
| **Volatile registers** | Registers that a function call is allowed to destroy: rcx, rdx, r8, r9. After a `Call`, these may contain garbage. |
