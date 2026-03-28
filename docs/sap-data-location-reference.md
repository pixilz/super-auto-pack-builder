# SAP Data Location Reference

> Where every piece of Super Auto Pets game data lives, how to get it out, and how accurate our extraction is today.
>
> **Goal:** Reduce dependency on groundedsap.co.uk by documenting exactly where data originates in the game files.
>
> Last updated: 2026-03-28 (game version 0.46)

---

## Quick Reference Table

| Data | Location | Extraction Tool | Our Accuracy | groundedsap Needed? |
|------|----------|----------------|-------------|---------------------|
| Pet names (internal) | `MinionEnum.cs` via Cpp2IL | Cpp2IL → parser | 100% | No |
| Pet names (display) | Localization bundles | UnityPy | 99.1% | No |
| Attack / Health | `MinionConstants.CreatePack*()` method bodies | Cpp2IL → ISIL parser | 98.7% / 97.7% | No |
| Tier | `MinionConstants.StartGroup()` calls | Cpp2IL → ISIL parser | 99.4% | No |
| Ability descriptions | `localization-string-tables-english` bundle | UnityPy → binary parser | ~71% | Helps with template params |
| Ability triggers | Lambda code + IL2CPP type metadata | **Not yet automated** | 0% standalone / 100% with trigger-map | Yes, for now |
| Archetypes | `MinionTemplate.SetArchetype*()` calls | Cpp2IL → ISIL parser | 89.6% | No, but parser needs improvement |
| Pack membership | `CreatePack*()` method name | Cpp2IL → parser | 100% | No |
| Pet sprites | `sharedassets1.assets` (Texture2D) | UnityPy or AssetRipper | 100% | No |
| Audio clips | `sharedassets1.assets` (AudioClip) | UnityPy or AssetRipper | 100% | No |
| Patch changelog | `defaultlocalgroup` bundle → `Changes.json` | UnityPy | 100% | No |
| Food/spell data | `GameAssembly.dll` (SpellConstants) | Not yet built | 0% | Yes, for now |
| Game constants | `GameAssembly.dll` (various classes) | Not yet built | 0% | Community wiki |
| Categories/tags | Unknown — possibly community-curated | N/A | 0% | Probably not in game files |

---

## Detailed Breakdown

### 1. Pet Stats (Attack, Health, Tier)

**Where it lives:** Hardcoded in native x86-64 code inside `GameAssembly.dll`.

The C# class `Spacewood.Core.Enums.MinionConstants` has methods like `CreatePack1Turtle()`, `CreatePack2Puppy()`, etc. Each method creates pet objects and calls:
- `MinionConstants.Create(enumValue)` — registers a new pet
- `MinionTemplate.SetStats(self, attack, health)` — sets base stats
- `MinionConstants.StartGroup(tier)` — sets the tier for subsequent pets

**Why it's hard:** Unity IL2CPP compiles C# to C++ to native code. The original C# is gone. What remains is machine code with numeric arguments pushed into registers before function calls.

**How we extract it:** Cpp2IL reconstructs an intermediate representation (ISIL) from the native code. Our `extract.py` simulates register state to track which values flow into which function arguments:

```
ISIL example (from CreatePack1Turtle, line ~242-255):
  242 Call MinionConstants.Create     ← registers Duck (first Turtle Pack pet)
  243 Move rdx, "Duck"               ← pet name visible in output
  251 Move rdx, 2                    ← attack = 2
  253 Move r8, rdx                   ← health = 2
  255 Call MinionTemplate.SetStats, rcx, rdx, r8
```

**Current accuracy vs groundedsap:**
- Attack: 98.7% (7 mismatches out of 554)
- Health: 97.7% (12 mismatches out of 554)
- Tier: 99.4% (after fixing token tier bug)

**Known issues:**
- Some pets have stats set through indirect code paths our parser doesn't follow
- Token pets (summoned copies) sometimes get wrong tier assignments

---

### 2. Pet Names

**Internal names:** Come from `MinionEnum.cs`, extracted by Cpp2IL's diffable-cs output. Maps integers to names: `Ant = 0`, `Beaver = 3`, `Cricket = 17`, etc. This is 100% accurate.

**Display names:** Stored in Unity localization bundles as string tables.

- **SharedTableData** bundle: `localization-assets-shared_assets_all.bundle` — maps key names like `Minion.Beaver.Name` to key IDs
- **StringTable** bundle: `localization-string-tables-english_assets_all.bundle` — maps key IDs to actual text

Both are MonoBehaviour objects with a custom binary table format (no type tree in IL2CPP builds). Our parser reads:
```
[8-byte key ID] [4-byte string length] [UTF-8 string, 0-padded to 4-byte alignment] [4-byte padding]
```

**Current accuracy:** 99.1% — a few internal names don't have localization entries (test pets, removed pets).

---

### 3. Ability Descriptions

**Where it lives:** Same localization bundles as pet names.

Key pattern: `Ability.{AbilityName}.{Level}.About` and `Ability.{AbilityName}.{Level}.FinePrint`

Example keys:
- `Ability.BeaverAbility.1.About` → "Give a random friendly +1 attack"
- `Ability.BeaverAbility.1.FinePrint` → additional detail text

**Current accuracy:** ~71% match vs groundedsap. Gaps:
1. **Icon placeholders** — our text contains `{HealthIcon}`, `{DamageIcon}` etc. that groundedsap strips
2. **Template parameters** — `{0}` in text like "per {0} friend" needs the value from native code (`Ability.AboutArgs`)
3. **"Works N times" suffixes** — come from `TriggerLimit`/`Repeat` fields in native code, not the localization text
4. **Condition prefixes** — "If turn number is even" comes from native code `CustomNote` fields

**What it would take to reach 100%:**
- Icon stripping: regex `\{[A-Za-z]+Icon\}` — easy fix
- Template params: need to decompile `AboutArgs` from native code, or build a lookup table
- Works N times: need to decompile `TriggerLimit`/`Repeat` from native code
- Condition prefixes: need to decompile `CustomNote` from native code

---

### 4. Ability Triggers (the big gap)

**This is the main reason we still need groundedsap.**

**Background:** SAP abilities have two trigger layers:
1. **Activation trigger** — when the ability fires (Sell, Buy, Faint, etc.) — this is what players see in the UI
2. **Effect trigger** — when the effect executes (Start of battle, etc.) — internal to the effect chain

**Where activation triggers live:** They are NOT stored as a simple enum or field. The activation trigger is determined by **which `TriggerBase` subclass** is instantiated for each ability. The TYPE ITSELF encodes the trigger — a `SellTrigger` class fires on sell, a `FaintTrigger` class fires on faint.

**Why this is hard to extract:** In IL2CPP native code, class instantiation uses **metadata tokens** — opaque numeric references like `0x6000XXXX` that must be resolved through the IL2CPP runtime's `CodeGenModule.methodPointers` array. We haven't built the full token-to-class-name resolution chain.

**What Ghidra shows:** Lambda functions for each ability call factory functions that construct trigger objects. We identified 36 factory functions mapping to 14 `TriggerEnum` values. But these are effect triggers, not activation triggers.

**What works today:** The "Rosetta Stone" approach — cross-referencing groundedsap's known triggers with our extracted ability enum values. This produces `trigger-map.json` with 509 ability→trigger mappings at 100% accuracy.

**Path to independence:**
1. Decompile the `CreateAbility` function (`FUN_18070FA40` in Ghidra) to trace where activation triggers are assigned
2. Build the full metadata token → class name resolution (requires parsing IL2CPP's `CodeGenModule` structure)
3. Match `TriggerBase` subclass names to trigger labels

This is the hardest remaining extraction problem. See `docs/research/trigger-extraction-status.md` for full details.

---

### 5. Archetypes

**Where it lives:** `MinionTemplate.SetArchetypeProducer()`, `SetArchetypeConsumer()`, `SetArchetypeCustom()`, `SetArchetypeMvp()` calls in `MinionConstants.CreatePack*()` methods.

**How it works in native code:** Archetypes are passed as arrays. The code:
1. Calls `SzArrayNew` to allocate an array
2. Writes enum values to array slots: `Move [rax+32], 5` (offset 32 = first element)
3. Passes the array to `SetArchetypeProducer(pet, array)`

**Current accuracy:** 89.6% — our parser catches the simple cases but misses some array construction patterns, particularly when:
- Multiple archetypes are set in sequence
- The array construction spans many instructions with intervening calls
- Archetype values are loaded from indirect memory references

**Path to improvement:** Better ISIL parser logic for tracking array state across instruction sequences.

---

### 6. Pack Membership

**Where it lives:** Implicit in the method name. Pets created in `CreatePack1Turtle()` are in the Turtle pack.

| Method | Pack |
|--------|------|
| `CreatePack1Turtle()` | Turtle (free) |
| `CreatePack2Puppy()` | Puppy |
| `CreatePack3Star()` | Star |
| `CreatePack4Golden()` | Golden |
| `CreatePack5Unicorn()` | Unicorn |
| `CreatePack6Danger()` | Danger |
| `CreatePack7Color()` | Color |
| `CreatePack8PlusMini1-4()` | Mini Packs |

Additional methods: `CreateTokens()`, `CreateMisc()`, `CreateBully()`, `CreateCustom()`, `CreateDraft()`, `CreateRelic()`, `CreateRework()`

**Accuracy:** 100% — the method name is unambiguous.

---

### 7. Pet Sprites

**Where it lives:** `sharedassets1.assets` as `Texture2D` and `Sprite` objects.

- 2,494 Sprites, 2,485 Texture2D objects
- Named by pet name: `Beaver.png`, `Beaver_2x.png` (high-res variant)
- Standard Unity binary format — no type tree needed

**Extraction:** UnityPy handles this directly:
```python
import UnityPy
env = UnityPy.load("sharedassets1.assets")
for obj in env.objects:
    if obj.type.name == "Texture2D":
        data = obj.read()
        data.image.save(f"sprites/{data.m_Name}.png")
```

AssetRipper also extracts these to `Assets/Texture2D/`.

**Accuracy:** 100%

---

### 8. Audio Clips

**Where it lives:** `sharedassets1.assets` (623 AudioClip objects) + Addressable bundles for music/ambiance.

**Extraction:** Same approach as sprites — UnityPy reads AudioClip objects natively.

---

### 9. Patch Changelog (Changes.json)

**Where it lives:** `defaultlocalgroup_assets_all_*.bundle` → TextAsset at path `Assets/Spacewood/Data/Changes.json`

**Format:**
```json
{
  "Pets": [
    {"Id": "709", "New": true},
    {"Id": "88", "Ability": true, "Attack": true}
  ],
  "Food": [...],
  "Perk": []
}
```

**Note:** Uses internal numeric IDs (MinionEnum values), not display names.

---

### 10. Food/Spell Data

**Where it lives:** `GameAssembly.dll` in a `SpellConstants` class (mirrors `MinionConstants` for pets).

**Status:** Not yet extracted. The same Cpp2IL + ISIL parsing approach should work — the code structure is believed to be parallel to `MinionConstants`.

---

### 11. Game Mechanics Constants

**Where it lives:** Various classes in `GameAssembly.dll`:
- Gold per turn, XP thresholds, shop tier timing, max stats, battle damage formula

**Status:** Not yet extracted. Known values from community wiki:
- Gold per turn: 10
- XP for level 2: 2, level 3: 3 (5 total)
- Shop tier X unlocks on turn 2X-1
- Max stats: 50 (100 with specific effects)

**Extraction path:** Cpp2IL or Ghidra on the relevant game logic classes.

---

## Game File Layout

```
Downloaded Super Auto Pets/
├── GameAssembly.dll              ← ALL pet/food stats, abilities, game logic
│                                    (IL2CPP compiled native x86-64)
│
├── Super Auto Pets_Data/
│   ├── il2cpp_data/
│   │   └── Metadata/
│   │       └── global-metadata.dat  ← IL2CPP type metadata (needed by ALL tools)
│   │
│   ├── StreamingAssets/aa/StandaloneWindows64/
│   │   ├── localization-assets-shared_assets_all.bundle
│   │   │   └── SharedTableData      ← localization key registry
│   │   ├── localization-string-tables-english_assets_all.bundle
│   │   │   └── StringTable           ← English text for all game strings
│   │   └── defaultlocalgroup_assets_all_*.bundle
│   │       ├── Changes.json          ← patch changelog
│   │       ├── Background sprites
│   │       └── Mascot pose data
│   │
│   ├── sharedassets1.assets          ← pet sprites, audio, MonoBehaviours
│   └── sharedassets0-7.assets        ← shaders, materials, scene data
│
└── Super Auto Pets.exe               ← Unity player launcher (not useful)
```

---

## What groundedsap Still Provides That We Can't

1. **Activation triggers** — the single biggest gap. Our trigger-map.json is derived from groundedsap. Without it, triggers are 0%.
2. **Template parameter values** — `{0}` in ability descriptions resolves to specific text (e.g., "Faint" in "per {0} friend")
3. **"Works N times" data** — `TriggerLimit`/`Repeat` values from native code
4. **Categories** — like "F2P", "Star Pack exclusive". May be community-curated, not game data.
5. **Custom gameplay tags** — "Buy/Sell", "Projectile", "Sniping" — almost certainly community-curated

**For a new game patch**, the practical impact:
- Stats, tiers, names, pack membership: fully automated, no groundedsap needed
- Ability descriptions: ~71% automated, rest needs native code work or groundedsap
- Triggers: existing pets keep their triggers (rarely change). NEW pets need manual trigger assignment or groundedsap lookup until we crack standalone extraction.

---

## Tools Summary

| Tool | What It Does | We Use It For |
|------|-------------|---------------|
| **Cpp2IL** | Reconstructs IL2CPP method bodies as ISIL/C# | Pet stats, tiers, archetypes, ability enums |
| **UnityPy** | Reads Unity asset bundles (Python) | Localization strings, sprites, audio |
| **AssetRipper** | Full Unity project extraction | Class structure (MinionTemplate fields), sprites |
| **Ghidra** | Binary analysis / native code decompilation | Trigger research, deep code analysis |
| **Il2CppDumper** | Extracts type definitions from IL2CPP metadata | Alternative to Cpp2IL for class signatures |

---

## Related Files

| File | Purpose |
|------|---------|
| `scripts/data-pipeline/extract.py` | End-to-end extraction pipeline |
| `scripts/data-pipeline/parse-isil-standalone.py` | Standalone ISIL parser for development |
| `scripts/data-pipeline/trigger-map.json` | Pre-built ability→trigger lookup (509 entries) |
| `scripts/data-pipeline/check-version.py` | Game version change detector |
| `docs/game-file-map.md` | AI-focused file layout reference |
| `docs/research/trigger-extraction-status.md` | Deep dive on trigger extraction architecture |
| `docs/research/r5-coverage-gaps.md` | Full coverage gap analysis vs groundedsap |
