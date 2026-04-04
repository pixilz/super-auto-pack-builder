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


def run_il2cppdumper(wasm_path, metadata_path, output_dir):
    """Run Il2CppDumper to produce script.json and dump.cs."""
    # Find Il2CppDumper
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    dumper_locations = [
        repo_root / "tmp" / "webgl" / "il2cppdumper-tool" / "Il2CppDumper.dll",
        repo_root / "tools" / "Il2CppDumper.dll",
    ]

    dumper = None
    for loc in dumper_locations:
        if loc.exists():
            dumper = str(loc)
            break

    if not dumper:
        log("WARNING: Il2CppDumper not found — using fallback function indices")
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


def build_dump_js(func_idx_pets, func_idx_spells, func_idx_perks):
    """Build a single JS evaluation that dumps all three data types at once."""
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
            name: rStr(r32(p + 8)),
            enumId: r32(p + 116),
            tier: r32(p + 16),
            attack: r32(p + 132),
            health: r32(p + 144),
            price: r32(p + 20),
            rollable: rByte(p + 29) === 1,
            active: rByte(p + 28) === 1,
            about: clean(rStr(r32(p + 24))),
            archetypeProducer: rHashSet(r32(p + 64)),
            archetypeConsumer: rHashSet(r32(p + 68)),
            archetypeCustom: rList(r32(p + 72)),
            roles: rList(r32(p + 104)),
            packs: rHashSet(r32(p + 108)),
            abilityEnums: rList(r32(p + 216)),
        }}));

        const spells = dumpList({func_idx_spells}, p => ({{
            name: rStr(r32(p + 8)),
            enumId: r32(p + 116),
            tier: r32(p + 16),
            price: r32(p + 20),
            rollable: rByte(p + 29) === 1,
            active: rByte(p + 28) === 1,
            about: clean(rStr(r32(p + 24))),
            archetypeProducer: rHashSet(r32(p + 64)),
            archetypeConsumer: rHashSet(r32(p + 68)),
            packs: rHashSet(r32(p + 108)),
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
        # Step 2: Dump all game data from WASM memory
        # ============================================================
        log("Dumping game data from WASM memory...")
        dump_js = build_dump_js(
            func_indices['GetReleasedMinions'],
            func_indices['GetReleasedSpells'],
            func_indices['GetReleasedPerks'],
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
