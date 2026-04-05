---
topic: wasm-live-game-extraction
date: 2026-04-05
tags: [wasm, playwright, il2cpp, unity, reverse-engineering, browser-automation]
---

# Learning Note: Extracting Game Data from a Live Unity WebGL Build

> How we bypassed all static decompilation limitations by running the game in a headless browser and calling its functions directly through the WASM function table.

## The Problem

Static decompilation tools (Cpp2IL, Ghidra, Il2CppDumper) can recover most game data from Unity IL2CPP binaries, but some data is only assembled at runtime through callbacks, lazy initialization, or data-driven mechanisms that decompilers can't trace. In our case, 35 pets (the Unicorn pack mythological creatures) were invisible to every static analysis tool.

## The Insight

Unity WebGL builds compile IL2CPP to **WebAssembly** instead of native x86. The WASM runs in a browser with full JavaScript interop. If you can get a reference to the WASM Module, you can:
1. Call any game function through the **function table** (`Module.asm.__indirect_function_table`)
2. Read any game object from **linear memory** (`Module.HEAPU8`)

The game has already initialized everything — all pets, spells, perks are in memory. You just read them.

## How It Works

### Step 1: Get the Module reference

Unity WebGL games call `createUnityInstance()` which returns a promise. Patch the loader JS via Playwright route interception to capture the result:

```javascript
const _o = window.createUnityInstance;
window.createUnityInstance = function(...a) {
    return _o(...a).then(i => {
        window.__mod = i.Module;  // Now accessible from page.evaluate()
        return i;
    });
};
```

### Step 2: Find function table indices

Run **Il2CppDumper** on `game.wasm` + `global-metadata.dat` (extracted from `game.data`). The `script.json` output maps C# method names to WASM function table indices:

```json
{"Name": "Spacewood.Core.Enums.MinionConstants$$GetReleasedMinions", "Address": 11688}
```

### Step 3: Call game functions

```javascript
const table = mod.asm.__indirect_function_table;
const fn = table.get(11688);  // GetReleasedMinions
const listPtr = fn();          // Returns a C# List pointer in WASM memory
```

### Step 4: Read C# objects from linear memory

C# objects in IL2CPP WASM are laid out in linear memory with fixed field offsets. For 32-bit WASM:

```javascript
const mem = mod.HEAPU8;
function r32(addr) { return mem[addr]|(mem[addr+1]<<8)|(mem[addr+2]<<16)|(mem[addr+3]<<24); }

// List<T>: items array at +8, count at +12
const itemsArr = r32(listPtr + 8);
const count = r32(listPtr + 12);

// Each element: pointer at items + 16 + i*4
const petPtr = r32(itemsArr + 16 + i * 4);

// MinionTemplate fields: Name at +8, Tier at +16, Attack at +132, Health at +144
const name = readCSharpString(r32(petPtr + 8));
const attack = r32(petPtr + 132);
```

### Step 5: Read C# strings

IL2CPP C# strings in WASM: `[klass:4][monitor:4][length:4][UTF-16 chars...]`

```javascript
function readCSharpString(ptr) {
    const len = r32(ptr + 8);
    let s = '';
    for (let i = 0; i < len; i++)
        s += String.fromCharCode(mem[ptr+12+i*2] | (mem[ptr+12+i*2+1]<<8));
    return s;
}
```

## Key Discoveries

### Field offsets must be verified empirically

The struct layouts from `il2cpp.h` give you a starting point, but padding and alignment differ between platforms. We verify offsets on every run by checking known values (Ant: attack=2, health=2, tier=1) and auto-discover the correct offsets if they change.

### GetAbilities() returns a List, not a Dictionary

The Il2CppDumper `dump.cs` shows `Dictionary<AbilityEnum, AbilityCollection>` but at runtime `GetAbilities()` returns a `List<AbilityCollection>`. Reading it as a dictionary (16-byte entries with hash codes) only found 216/892 entries. Reading as a list (4-byte pointer array) found all 867.

### Trigger offset is deep in the Ability object

`Ability.Trigger` is a `TriggerBase` pointer at offset +356 in the Ability object (after dozens of bool/nullable/pointer fields). `TriggerBase.Enum` is at +8. This offset is auto-discovered by checking known ability→trigger mappings (CricketAbility→18, MosquitoAbility→4).

### HashSet reading requires slot iteration

C# `HashSet<T>` in IL2CPP stores values in a slot array at +12, with count at +16 and lastIndex at +20. Each slot is `[hashCode:4][next:4][value:4]` (12 bytes). Only slots where `hashCode >= 0` contain valid values.

### Localization bundles are captured during game load

The game fetches `.bundle` files from the itch.io CDN during initialization. Playwright route interception saves them to disk. UnityPy parses the binary table format: `[8-byte key][4-byte length][padded UTF-8 string][4-byte pad]`.

## Why This Beats Static Decompilation

| | Static (Cpp2IL/Ghidra) | Live WASM |
|---|---|---|
| Pets found | 637/670 (35 missing) | **670/670** |
| Requires game files | Yes (desktop build) | No (downloads from web) |
| Survives updates | Breaks (hardcoded addresses) | Auto-discovers everything |
| Runtime callbacks | Can't trace | Already executed |
| Speed | Minutes (Ghidra) | ~3 minutes total |

## Tools Used

- **Playwright** — browser automation, route interception, JS evaluation
- **Il2CppDumper** — metadata extraction (function indices, enum names)
- **UnityPy** — Unity asset bundle parsing (localization)
- **il2cpp.h** — struct layout reference (from Il2CppDumper output)
