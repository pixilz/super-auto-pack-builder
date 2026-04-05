#!/usr/bin/env python3
"""
Extract ALL game data from the SAP WebGL build — fully self-contained.

No pre-existing game files needed. Downloads the game from itch.io,
extracts IL2CPP metadata, resolves function indices and enum names,
then dumps live game data from WASM memory.

Usage:
    python3 extract_web.py --output-dir data/extracted
    python3 extract_web.py --output-dir data/extracted --timeout 120

Dependencies:
    pip install playwright
    playwright install chromium
    dotnet 6+ (for Il2CppDumper)
"""

import argparse
import asyncio
import json
import os
import re
import struct
import subprocess
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

# Try importing playwright — fail with helpful message if missing
try:
    from playwright.async_api import async_playwright
except ImportError:
    print("ERROR: playwright not installed. Run: pip install playwright && playwright install chromium", file=sys.stderr)
    sys.exit(1)


GAME_URL = "https://html-classic.itch.zone/html/16823967/Production%20WebGL/index.html"

# IL2CPP function names we need to call
FUNCTION_NAMES = {
    'GetReleasedMinions': 'Spacewood.Core.Enums.MinionConstants$$GetReleasedMinions',
    'GetReleasedSpells': 'Spacewood.Core.Enums.SpellConstants$$GetReleasedSpells',
    'GetReleasedPerks': 'Spacewood.Core.Enums.PerkConstants$$GetReleasedPerks',
}

# Enum names we need to resolve
ENUM_NAMES = ['Archetype', 'Pack', 'Role', 'AbilityEnum', 'MinionEnum', 'SpellEnum', 'Perk']

# JS helpers injected into browser for reading WASM memory
JS_HELPERS = """
function r32(a) { return a>=0&&a+4<=mem.length ? mem[a]|(mem[a+1]<<8)|(mem[a+2]<<16)|(mem[a+3]<<24) : -1; }
function rByte(a) { return mem[a]; }
function rStr(ptr) {
    if (ptr < 1000 || ptr >= mem.length - 20) return null;
    const len = r32(ptr + 8);
    if (len <= 0 || len > 500) return null;
    let s = '';
    for (let i = 0; i < len; i++) s += String.fromCharCode(mem[ptr+12+i*2]|(mem[ptr+12+i*2+1]<<8));
    return s;
}
function rList(listPtr) {
    if (listPtr < 1000) return null;
    const items = r32(listPtr + 8);
    const size = r32(listPtr + 12);
    if (size <= 0 || size > 100 || items < 1000) return null;
    const vals = [];
    for (let i = 0; i < size; i++) vals.push(r32(items + 16 + i * 4));
    return vals;
}
function rHashSet(setPtr) {
    if (setPtr < 1000) return null;
    const count = r32(setPtr + 16);
    const slots = r32(setPtr + 12);
    if (count <= 0 || count > 50 || slots < 1000) return null;
    const lastIdx = r32(setPtr + 20);
    const vals = [];
    for (let i = 0; i < lastIdx && vals.length < count; i++) {
        const hashCode = r32(slots + 16 + i * 12);
        const value = r32(slots + 16 + i * 12 + 8);
        if (hashCode >= 0) vals.push(value);
    }
    return vals;
}
function clean(s) { return s ? s.replace(/\\{\\w*Icon\\}\\s*/g, '').trim() : null; }
"""


def log(msg):
    print(f"[WEB-EXTRACT] {msg}", file=sys.stderr)


def extract_metadata_from_data(data_bytes):
    """Find and extract global-metadata.dat from Unity game.data."""
    magic = bytes([0xAF, 0x1B, 0xB1, 0xFA])
    start = data_bytes.find(magic)
    if start == -1:
        return None

    # Estimate size from metadata header section offsets
    max_end = 0
    for i in range(8, 264, 8):
        offset = struct.unpack_from('<I', data_bytes, start + i)[0]
        count = struct.unpack_from('<I', data_bytes, start + i + 4)[0]
        if offset > 0 and count > 0 and offset + count > max_end:
            max_end = offset + count

    return data_bytes[start:start + max_end]


IL2CPP_DUMPER_URL = "https://github.com/Perfare/Il2CppDumper/releases/download/v6.7.46/Il2CppDumper-net6-v6.7.46.zip"
IL2CPP_DUMPER_CACHE = Path(__file__).parent.parent.parent / "tmp" / "il2cppdumper-tool"


def ensure_il2cppdumper():
    """Download Il2CppDumper if not present. Returns path to DLL or None."""
    dll_path = IL2CPP_DUMPER_CACHE / "Il2CppDumper.dll"
    if dll_path.exists():
        return str(dll_path)

    # Check other known locations
    for loc in [
        Path(__file__).parent.parent.parent / "tmp" / "webgl" / "il2cppdumper-tool" / "Il2CppDumper.dll",
        Path(__file__).parent.parent.parent / "tools" / "Il2CppDumper.dll",
    ]:
        if loc.exists():
            return str(loc)

    # Check dotnet is available
    try:
        subprocess.run(["dotnet", "--version"], capture_output=True, timeout=5)
    except (FileNotFoundError, subprocess.TimeoutExpired):
        log("WARNING: dotnet not found — cannot run Il2CppDumper")
        return None

    # Download
    log(f"Downloading Il2CppDumper...")
    os.makedirs(IL2CPP_DUMPER_CACHE, exist_ok=True)
    zip_path = IL2CPP_DUMPER_CACHE / "Il2CppDumper.zip"

    try:
        urllib.request.urlretrieve(IL2CPP_DUMPER_URL, zip_path)
        with zipfile.ZipFile(zip_path) as zf:
            zf.extractall(IL2CPP_DUMPER_CACHE)
        zip_path.unlink(missing_ok=True)
        log(f"  Installed to {IL2CPP_DUMPER_CACHE}")
    except Exception as e:
        log(f"WARNING: Failed to download Il2CppDumper: {e}")
        return None

    return str(dll_path) if dll_path.exists() else None


def run_il2cppdumper(wasm_path, metadata_path, output_dir):
    """Run Il2CppDumper to produce script.json and dump.cs."""
    dumper = ensure_il2cppdumper()
    if not dumper:
        log("WARNING: Il2CppDumper not available — using fallback function indices")
        return None, None

    os.makedirs(output_dir, exist_ok=True)
    result = subprocess.run(
        ["dotnet", "--roll-forward", "LatestMajor", dumper, wasm_path, metadata_path, output_dir],
        capture_output=True, text=True, timeout=120,
        input="\n",  # handle "press any key" prompt
    )

    script_json = os.path.join(output_dir, "script.json")
    dump_cs = os.path.join(output_dir, "dump.cs")
    return (script_json if os.path.exists(script_json) else None,
            dump_cs if os.path.exists(dump_cs) else None)


def parse_function_indices(script_json_path):
    """Extract WASM function table indices from Il2CppDumper script.json."""
    with open(script_json_path) as f:
        script = json.load(f)
    indices = {}
    for key, full_name in FUNCTION_NAMES.items():
        for entry in script['ScriptMethod']:
            if entry.get('Name') == full_name:
                indices[key] = entry['Address']
                break
    return indices


def parse_enum_lookups(dump_cs_path):
    """Extract enum name mappings from Il2CppDumper dump.cs."""
    with open(dump_cs_path) as f:
        content = f.read()
    lookups = {}
    for enum_name in ENUM_NAMES:
        pattern = rf'public enum {enum_name}\b.*?\{{(.*?)\}}'
        m = re.search(pattern, content, re.DOTALL)
        if m:
            entries = re.findall(rf'public const {enum_name} (\w+) = (-?\d+);', m.group(1))
            lookups[enum_name] = {int(v): n for n, v in entries}
    return lookups


def resolve_enums(data, lookups, field_mappings):
    """Replace enum integer values with human-readable names."""
    for item in data:
        for field, enum_name in field_mappings.items():
            if field not in item or item[field] is None:
                continue
            lookup = lookups.get(enum_name, {})
            if isinstance(item[field], list):
                item[field] = [lookup.get(v, v) for v in item[field]]


def build_offset_discovery_js(func_idx_pets):
    """Build JS that discovers field offsets by checking known pet values.

    Reads the first 250 bytes of several pet objects and finds offsets where
    known values (Ant: attack=2, health=2, enum=0, tier=1) consistently appear.
    """
    return f"""() => {{
        const mod = window.__mod;
        const mem = mod.HEAPU8;
        const table = mod.asm.__indirect_function_table;
        {JS_HELPERS}

        const fn = table.get({func_idx_pets});
        const listPtr = fn();
        const arr = r32(listPtr + 8);
        const count = r32(listPtr + 12);
        if (count < 10) return {{error: 'too few pets', count}};

        // Read first 50 pets, find ones with known stats
        const known = {{}};
        for (let i = 0; i < Math.min(count, 200); i++) {{
            const p = r32(arr + 16 + i * 4);
            if (!p) continue;
            // Try reading name at offset +8 (should be stable)
            const name = rStr(r32(p + 8));
            if (['Ant','Beaver','Cricket','Fish','Horse','Pig','Dog','Otter'].includes(name)) {{
                const dump = [];
                for (let off = 0; off < 250; off += 4) dump.push(r32(p + off));
                known[name] = dump;
            }}
        }}

        // Expected values (stable across versions)
        const expect = {{
            'Ant': {{attack: 2, health: 2, tier: 1, enum: 0}},
            'Beaver': {{attack: 3, health: 2, tier: 1, enum: 3}},
            'Cricket': {{attack: 1, health: 3, tier: 1, enum: 17}},
            'Pig': {{attack: 4, health: 1, tier: 1, enum: 59}},
        }};

        // Find offsets where values consistently match
        const offsets = {{}};
        const candidates = {{'attack': {{}}, 'health': {{}}, 'tier': {{}}, 'enum': {{}}}};

        for (const [name, exp] of Object.entries(expect)) {{
            if (!known[name]) continue;
            const dump = known[name];
            for (let idx = 0; idx < dump.length; idx++) {{
                const off = idx * 4;
                for (const [field, val] of Object.entries(exp)) {{
                    if (dump[idx] === val) {{
                        if (!candidates[field][off]) candidates[field][off] = 0;
                        candidates[field][off]++;
                    }}
                }}
            }}
        }}

        // Pick offsets with the most matches (and > 1 match to avoid false positives)
        for (const [field, offs] of Object.entries(candidates)) {{
            let bestOff = -1, bestCount = 0;
            for (const [off, cnt] of Object.entries(offs)) {{
                // For enum, require exact match count since values are unique
                if (cnt > bestCount) {{ bestOff = parseInt(off); bestCount = cnt; }}
            }}
            if (bestCount >= 2 || (field === 'enum' && bestCount >= 1)) {{
                offsets[field] = bestOff;
            }}
        }}

        // Also verify Name offset (+8) and Price offset (+20)
        const nameCheck = known['Ant'] ? rStr(r32(r32(arr + 16) + 8)) : null;
        offsets['nameVerified'] = nameCheck === known['Ant'] ? true : nameCheck;

        return {{offsets, petCount: count, knownPets: Object.keys(known)}};
    }}"""


# Default field offsets for 32-bit WASM IL2CPP (from il2cpp.h analysis)
DEFAULT_OFFSETS = {
    'Name': 8, 'NameNormalized': 12, 'Tier': 16, 'Price': 20, 'About': 24,
    'Active': 28, 'Rollable': 29,
    'ArchetypeProducer': 64, 'ArchetypeConsumer': 68, 'ArchetypeCustom': 72,
    'Roles': 104, 'Packs': 108,
    'Enum': 116, 'Attack': 132, 'Health': 144,
    'AbilityEnums': 216,
}


def build_dump_js(func_idx_pets, func_idx_spells, func_idx_perks, offsets=None):
    """Build a single JS evaluation that dumps all three data types at once."""
    o = offsets or DEFAULT_OFFSETS
    return f"""() => {{
        const mod = window.__mod;
        const mem = mod.HEAPU8;
        const table = mod.asm.__indirect_function_table;
        {JS_HELPERS}

        function dumpList(funcIdx, readItem) {{
            const fn = table.get(funcIdx);
            const listPtr = fn();
            const arr = r32(listPtr + 8);
            const count = r32(listPtr + 12);
            const items = [];
            for (let i = 0; i < count; i++) {{
                const p = r32(arr + 16 + i * 4);
                if (p) items.push(readItem(p));
            }}
            return items;
        }}

        const pets = dumpList({func_idx_pets}, p => ({{
            name: rStr(r32(p + {o['Name']})),
            enumId: r32(p + {o['Enum']}),
            tier: r32(p + {o['Tier']}),
            attack: r32(p + {o['Attack']}),
            health: r32(p + {o['Health']}),
            price: r32(p + {o['Price']}),
            rollable: rByte(p + {o['Rollable']}) === 1,
            active: rByte(p + {o['Active']}) === 1,
            about: clean(rStr(r32(p + {o['About']}))),
            archetypeProducer: rHashSet(r32(p + {o['ArchetypeProducer']})),
            archetypeConsumer: rHashSet(r32(p + {o['ArchetypeConsumer']})),
            archetypeCustom: rList(r32(p + {o['ArchetypeCustom']})),
            roles: rList(r32(p + {o['Roles']})),
            packs: rHashSet(r32(p + {o['Packs']})),
            abilityEnums: rList(r32(p + {o['AbilityEnums']})),
        }}));

        const spells = dumpList({func_idx_spells}, p => ({{
            name: rStr(r32(p + {o['Name']})),
            enumId: r32(p + {o['Enum']}),
            tier: r32(p + {o['Tier']}),
            price: r32(p + {o['Price']}),
            rollable: rByte(p + {o['Rollable']}) === 1,
            active: rByte(p + {o['Active']}) === 1,
            about: clean(rStr(r32(p + {o['About']}))),
            archetypeProducer: rHashSet(r32(p + {o['ArchetypeProducer']})),
            archetypeConsumer: rHashSet(r32(p + {o['ArchetypeConsumer']})),
            packs: rHashSet(r32(p + {o['Packs']})),
        }}));

        const perks = dumpList({func_idx_perks}, p => ({{
            name: rStr(r32(p + 12)),
            enumId: r32(p + 8),
            effectName: rStr(r32(p + 20)),
            abilityEnums: rList(r32(p + 24)),
        }}));

        return {{pets, spells, perks}};
    }}"""


async def extract_all(output_dir, timeout=90, il2cpp_dumper_path=None):
    """Full self-contained extraction pipeline."""

    work_dir = tempfile.mkdtemp(prefix='sap-extract-')
    log(f"Working directory: {work_dir}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Save game.data and game.wasm to disk as they download
        # (can't use response.body() — large files get evicted from inspector cache)
        game_files = {}
        wasm_path = os.path.join(work_dir, 'game.wasm')
        data_path = os.path.join(work_dir, 'game.data')

        async def save_build_file(route):
            url = route.request.url
            response = await route.fetch()
            body = await response.body()

            if '.wasm' in url and 'Production' in url:
                with open(wasm_path, 'wb') as f:
                    f.write(body)
                game_files['wasm'] = wasm_path
                log(f"  Saved WASM ({len(body):,} bytes)")
            elif '.data' in url and 'Production' in url:
                with open(data_path, 'wb') as f:
                    f.write(body)
                game_files['data'] = data_path
                log(f"  Saved game data ({len(body):,} bytes)")

            await route.fulfill(response=response)

        await page.route('**/*.wasm*', save_build_file)
        await page.route('**/*.data*', save_build_file)

        # Patch Unity loader to capture Module reference
        async def patch_loader(route):
            response = await route.fetch()
            body = await response.text()
            body += ("\nconst _o=window.createUnityInstance;"
                     "window.createUnityInstance=function(...a){"
                     "return _o(...a).then(i=>{"
                     "window.__inst=i;window.__mod=i.Module;return i})};")
            await route.fulfill(response=response, body=body, headers={**response.headers})

        await page.route('**/*.loader.js', patch_loader)

        log("Loading game from itch.io...")
        await page.goto(GAME_URL, wait_until='networkidle', timeout=120000)
        await page.wait_for_timeout(45000)

        # Click canvas to trigger user gesture
        canvas = await page.wait_for_selector('canvas', timeout=10000)
        if canvas:
            await canvas.click()

        log(f"Waiting {timeout}s for game initialization...")
        await page.wait_for_timeout(timeout * 1000)

        # Verify module loaded
        check = await page.evaluate("() => ({ ok: !!(window.__mod && window.__mod.asm.__indirect_function_table) })")
        if not check.get('ok'):
            log("ERROR: WASM module not loaded. Try increasing --timeout.")
            await browser.close()
            return

        # ============================================================
        # Step 1: Extract metadata and run Il2CppDumper
        # ============================================================
        func_indices = None
        lookups = {}

        if 'data' in game_files and 'wasm' in game_files:
            log("Extracting IL2CPP metadata from game data...")
            with open(game_files['data'], 'rb') as f:
                data_bytes = f.read()
            metadata = extract_metadata_from_data(data_bytes)
            del data_bytes  # free memory

            if metadata:
                meta_path = os.path.join(work_dir, 'global-metadata.dat')
                dump_dir = os.path.join(work_dir, 'dump')

                with open(meta_path, 'wb') as f:
                    f.write(metadata)

                log(f"  Metadata: {len(metadata):,} bytes (version {struct.unpack_from('<I', metadata, 4)[0]})")

                log("Running Il2CppDumper...")
                script_json, dump_cs = run_il2cppdumper(game_files['wasm'], meta_path, dump_dir)

                if script_json:
                    func_indices = parse_function_indices(script_json)
                    log(f"  Function indices: {func_indices}")

                if dump_cs:
                    lookups = parse_enum_lookups(dump_cs)
                    log(f"  Enum lookups: {', '.join(f'{k}({len(v)})' for k, v in lookups.items())}")

        # Fallback function indices
        if not func_indices:
            log("WARNING: Using fallback function indices (may break on game update)")
            func_indices = {
                'GetReleasedMinions': 11688,
                'GetReleasedSpells': 30368,
                'GetReleasedPerks': 30225,
            }

        # ============================================================
        # Step 2: Verify/discover field offsets
        # ============================================================
        log("Verifying field offsets...")
        discovery = await page.evaluate(build_offset_discovery_js(func_indices['GetReleasedMinions']))

        offsets = dict(DEFAULT_OFFSETS)
        if 'error' not in discovery:
            discovered = discovery.get('offsets', {})
            # Update offsets if discovery found different values
            offset_map = {'attack': 'Attack', 'health': 'Health', 'tier': 'Tier', 'enum': 'Enum'}
            changed = False
            for disc_key, offset_key in offset_map.items():
                if disc_key in discovered and discovered[disc_key] != offsets[offset_key]:
                    log(f"  OFFSET CHANGED: {offset_key} was {offsets[offset_key]}, now {discovered[disc_key]}")
                    offsets[offset_key] = discovered[disc_key]
                    changed = True
            if not changed:
                log(f"  All offsets verified OK ({discovery['petCount']} pets, checked: {discovery['knownPets']})")
        else:
            log(f"  WARNING: Offset discovery failed: {discovery}")

        # ============================================================
        # Step 3: Dump all game data from WASM memory
        # ============================================================
        log("Dumping game data from WASM memory...")
        dump_js = build_dump_js(
            func_indices['GetReleasedMinions'],
            func_indices['GetReleasedSpells'],
            func_indices['GetReleasedPerks'],
            offsets,
        )
        result = await page.evaluate(dump_js)

        pets = result['pets']
        spells = result['spells']
        perks = result['perks']

        log(f"  Pets: {len(pets)}, Spells: {len(spells)}, Perks: {len(perks)}")

        await browser.close()

    # ============================================================
    # Step 3: Resolve enum names
    # ============================================================
    if lookups:
        log("Resolving enum names...")
        resolve_enums(pets, lookups, {
            'archetypeProducer': 'Archetype',
            'archetypeConsumer': 'Archetype',
            'archetypeCustom': 'Archetype',
            'roles': 'Role',
            'packs': 'Pack',
            'abilityEnums': 'AbilityEnum',
        })
        resolve_enums(spells, lookups, {
            'archetypeProducer': 'Archetype',
            'archetypeConsumer': 'Archetype',
            'packs': 'Pack',
        })
        resolve_enums(perks, lookups, {
            'abilityEnums': 'AbilityEnum',
        })

    # ============================================================
    # Step 4: Save output
    # ============================================================
    os.makedirs(output_dir, exist_ok=True)

    for name, data in [('pets', pets), ('spells', spells), ('perks', perks)]:
        path = os.path.join(output_dir, f'{name}.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    log(f"Done! Saved to {output_dir}/")
    log(f"  Pets: {len(pets)} ({sum(1 for p in pets if p['rollable'])} rollable)")
    log(f"  Spells: {len(spells)} ({sum(1 for s in spells if s['rollable'])} rollable)")
    log(f"  Perks: {len(perks)}")

    # Cleanup work dir
    import shutil
    shutil.rmtree(work_dir, ignore_errors=True)


def main():
    parser = argparse.ArgumentParser(description="Extract SAP game data from WebGL build (fully self-contained)")
    parser.add_argument("--output-dir", default="tmp/webgl-extract", help="Output directory")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds to wait for game init (default: 90)")
    args = parser.parse_args()

    asyncio.run(extract_all(args.output_dir, args.timeout))


if __name__ == "__main__":
    main()
