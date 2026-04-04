#!/usr/bin/env python3
"""
Extract ALL game data from the SAP WebGL build via Playwright.

Launches the game in a headless browser, calls IL2CPP functions directly
through the WASM function table, and reads C# object data from WASM memory.

This is the authoritative extraction method — it reads live game state after
full initialization, capturing all pets/spells/perks including those set
through runtime callbacks that static decompilation can't trace.

Usage:
    python3 extract_web.py --output-dir tmp/webgl-extract
    python3 extract_web.py --output-dir tmp/webgl-extract --timeout 120

Dependencies: playwright (pip install playwright && playwright install chromium)
"""

import argparse
import asyncio
import json
import os
import sys
from playwright.async_api import async_playwright


GAME_URL = "https://html-classic.itch.zone/html/16823967/Production%20WebGL/index.html?v=1773655781"

# WASM function table indices from Il2CppDumper script.json
# These are looked up dynamically at runtime to avoid hardcoding.
FUNCTION_NAMES = {
    'GetReleasedMinions': 'Spacewood.Core.Enums.MinionConstants$$GetReleasedMinions',
    'GetReleasedSpells': 'Spacewood.Core.Enums.SpellConstants$$GetReleasedSpells',
    'GetReleasedPerks': 'Spacewood.Core.Enums.PerkConstants$$GetReleasedPerks',
}

# IL2CPP object field offsets for 32-bit WASM build.
# Derived from Il2CppDumper il2cpp.h struct definitions.
# ItemTemplate_o: klass(4) + monitor(4) + fields
ITEM_TEMPLATE = {
    'Name': 8,           # string ptr
    'NameNormalized': 12, # string ptr
    'Tier': 16,          # int32
    'Price': 20,         # int32
    'About': 24,         # string ptr
    'Active': 28,        # byte
    'Rollable': 29,      # byte
    'Bad': 30,           # byte
    'Unique': 31,        # byte
    'Unreleased': 32,    # byte
}

# MinionTemplate extends ItemTemplate, Enum starts after all ItemTemplate fields
MINION_TEMPLATE = {
    **ITEM_TEMPLATE,
    'Enum': 116,         # int32 (MinionEnum)
    'Attack': 132,       # int32
    'Health': 144,       # int32
}

# Spell extends ItemTemplate with same base offsets
SPELL_TEMPLATE = {
    **ITEM_TEMPLATE,
    'Enum': 116,         # int32 (SpellEnum) — same offset as MinionTemplate
}

# PerkTemplate is standalone (NOT extending ItemTemplate)
PERK_TEMPLATE = {
    'Enum': 8,           # int32 (Perk enum) — after klass(4)+monitor(4)
    'Name': 12,          # string ptr
    'NameNormalized': 16, # string ptr
    'EffectName': 20,    # string ptr
    'Positive': 36,      # byte (approximate, after Abilities ptr + Localization + Spell nullable)
}


def log(msg):
    print(f"[WEB-EXTRACT] {msg}", file=sys.stderr)


async def extract_all(output_dir, script_json_path=None, timeout=90):
    """Launch game, wait for init, dump all data."""

    # Resolve function indices from script.json if available
    func_indices = {}
    if script_json_path and os.path.exists(script_json_path):
        with open(script_json_path) as f:
            script = json.load(f)
        for key, full_name in FUNCTION_NAMES.items():
            for entry in script['ScriptMethod']:
                if entry.get('Name') == full_name:
                    func_indices[key] = entry['Address']
                    break
        log(f"Resolved function indices from script.json: {func_indices}")
    else:
        # Fallback: hardcoded indices from current build
        func_indices = {
            'GetReleasedMinions': 11688,
            'GetReleasedSpells': 30368,
            'GetReleasedPerks': 30225,
        }
        log("Using fallback function indices (no script.json provided)")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Patch the Unity loader to capture the Module reference
        async def patch_loader(route):
            response = await route.fetch()
            body = await response.text()
            body += ("\nconst _o=window.createUnityInstance;"
                     "window.createUnityInstance=function(...a){"
                     "return _o(...a).then(i=>{"
                     "window.__inst=i;window.__mod=i.Module;return i})};")
            await route.fulfill(response=response, body=body, headers={**response.headers})

        await page.route('**/*.loader.js', patch_loader)

        log("Loading game...")
        await page.goto(GAME_URL, wait_until='networkidle', timeout=120000)
        await page.wait_for_timeout(45000)

        # Click canvas to trigger user gesture (starts AudioContext, scene load)
        canvas = await page.wait_for_selector('canvas', timeout=10000)
        if canvas:
            await canvas.click()

        log(f"Waiting {timeout}s for game initialization...")
        await page.wait_for_timeout(timeout * 1000)

        # Verify module is loaded
        check = await page.evaluate("() => ({ hasModule: !!window.__mod, hasTable: !!(window.__mod && window.__mod.asm.__indirect_function_table) })")
        if not check.get('hasTable'):
            log("ERROR: WASM module not loaded. Try increasing --timeout.")
            await browser.close()
            return

        # ============================================================
        # DUMP PETS
        # ============================================================
        log("Dumping pets...")
        pets = await page.evaluate(f"""() => {{
            const mod = window.__mod;
            const mem = mod.HEAPU8;
            const table = mod.asm.__indirect_function_table;
            function r32(a) {{ return mem[a]|(mem[a+1]<<8)|(mem[a+2]<<16)|(mem[a+3]<<24); }}
            function rStr(ptr) {{
                if (ptr < 1000 || ptr >= mem.length - 20) return null;
                const len = r32(ptr + 8);
                if (len <= 0 || len > 200) return null;
                let s = '';
                for (let i = 0; i < len; i++) s += String.fromCharCode(mem[ptr+12+i*2]|(mem[ptr+12+i*2+1]<<8));
                return s;
            }}
            const fn = table.get({func_indices['GetReleasedMinions']});
            const listPtr = fn();
            const arr = r32(listPtr + 8);
            const count = r32(listPtr + 12);
            const pets = [];
            for (let i = 0; i < count; i++) {{
                const p = r32(arr + 16 + i * 4);
                if (!p) continue;
                pets.push({{
                    name: rStr(r32(p + {MINION_TEMPLATE['Name']})),
                    enumId: r32(p + {MINION_TEMPLATE['Enum']}),
                    tier: r32(p + {MINION_TEMPLATE['Tier']}),
                    attack: r32(p + {MINION_TEMPLATE['Attack']}),
                    health: r32(p + {MINION_TEMPLATE['Health']}),
                    price: r32(p + {MINION_TEMPLATE['Price']}),
                    rollable: mem[p + {MINION_TEMPLATE['Rollable']}] === 1,
                    active: mem[p + {MINION_TEMPLATE['Active']}] === 1,
                    about: rStr(r32(p + {MINION_TEMPLATE['About']})),
                }});
            }}
            return pets;
        }}""")

        log(f"  Pets: {len(pets)}")

        # ============================================================
        # DUMP SPELLS
        # ============================================================
        log("Dumping spells...")
        spells = await page.evaluate(f"""() => {{
            const mod = window.__mod;
            const mem = mod.HEAPU8;
            const table = mod.asm.__indirect_function_table;
            function r32(a) {{ return mem[a]|(mem[a+1]<<8)|(mem[a+2]<<16)|(mem[a+3]<<24); }}
            function rStr(ptr) {{
                if (ptr < 1000 || ptr >= mem.length - 20) return null;
                const len = r32(ptr + 8);
                if (len <= 0 || len > 200) return null;
                let s = '';
                for (let i = 0; i < len; i++) s += String.fromCharCode(mem[ptr+12+i*2]|(mem[ptr+12+i*2+1]<<8));
                return s;
            }}
            const fn = table.get({func_indices['GetReleasedSpells']});
            const listPtr = fn();
            const arr = r32(listPtr + 8);
            const count = r32(listPtr + 12);
            const spells = [];
            for (let i = 0; i < count; i++) {{
                const p = r32(arr + 16 + i * 4);
                if (!p) continue;
                spells.push({{
                    name: rStr(r32(p + {SPELL_TEMPLATE['Name']})),
                    enumId: r32(p + {SPELL_TEMPLATE['Enum']}),
                    tier: r32(p + {SPELL_TEMPLATE['Tier']}),
                    price: r32(p + {SPELL_TEMPLATE['Price']}),
                    rollable: mem[p + {SPELL_TEMPLATE['Rollable']}] === 1,
                    active: mem[p + {SPELL_TEMPLATE['Active']}] === 1,
                    about: rStr(r32(p + {SPELL_TEMPLATE['About']})),
                }});
            }}
            return spells;
        }}""")

        log(f"  Spells: {len(spells)}")

        # ============================================================
        # DUMP PERKS
        # ============================================================
        log("Dumping perks...")
        perks = await page.evaluate(f"""() => {{
            const mod = window.__mod;
            const mem = mod.HEAPU8;
            const table = mod.asm.__indirect_function_table;
            function r32(a) {{ return mem[a]|(mem[a+1]<<8)|(mem[a+2]<<16)|(mem[a+3]<<24); }}
            function rStr(ptr) {{
                if (ptr < 1000 || ptr >= mem.length - 20) return null;
                const len = r32(ptr + 8);
                if (len <= 0 || len > 200) return null;
                let s = '';
                for (let i = 0; i < len; i++) s += String.fromCharCode(mem[ptr+12+i*2]|(mem[ptr+12+i*2+1]<<8));
                return s;
            }}
            const fn = table.get({func_indices['GetReleasedPerks']});
            const listPtr = fn();
            const arr = r32(listPtr + 8);
            const count = r32(listPtr + 12);
            const perks = [];
            for (let i = 0; i < count; i++) {{
                const p = r32(arr + 16 + i * 4);
                if (!p) continue;
                perks.push({{
                    name: rStr(r32(p + {PERK_TEMPLATE['Name']})),
                    enumId: r32(p + {PERK_TEMPLATE['Enum']}),
                }});
            }}
            return perks;
        }}""")

        log(f"  Perks: {len(perks)}")

        await browser.close()

    # Save outputs
    os.makedirs(output_dir, exist_ok=True)

    with open(os.path.join(output_dir, 'pets.json'), 'w') as f:
        json.dump(pets, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir, 'spells.json'), 'w') as f:
        json.dump(spells, f, indent=2, ensure_ascii=False)

    with open(os.path.join(output_dir, 'perks.json'), 'w') as f:
        json.dump(perks, f, indent=2, ensure_ascii=False)

    log(f"Done! Saved to {output_dir}/")
    log(f"  Pets: {len(pets)}")
    log(f"  Spells: {len(spells)}")
    log(f"  Perks: {len(perks)}")


def main():
    parser = argparse.ArgumentParser(description="Extract SAP game data from WebGL build")
    parser.add_argument("--output-dir", default="tmp/webgl-extract", help="Output directory")
    parser.add_argument("--script-json", default=None, help="Il2CppDumper script.json for function index resolution")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds to wait for game init (default: 90)")
    args = parser.parse_args()

    asyncio.run(extract_all(args.output_dir, args.script_json, args.timeout))


if __name__ == "__main__":
    main()
