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
import re
import sys
from playwright.async_api import async_playwright


GAME_URL = "https://html-classic.itch.zone/html/16823967/Production%20WebGL/index.html?v=1773655781"

# IL2CPP function names → resolved dynamically from script.json
FUNCTION_NAMES = {
    'GetReleasedMinions': 'Spacewood.Core.Enums.MinionConstants$$GetReleasedMinions',
    'GetReleasedSpells': 'Spacewood.Core.Enums.SpellConstants$$GetReleasedSpells',
    'GetReleasedPerks': 'Spacewood.Core.Enums.PerkConstants$$GetReleasedPerks',
}


def log(msg):
    print(f"[WEB-EXTRACT] {msg}", file=sys.stderr)


def load_enum_lookups(enum_dir=None):
    """Load enum name lookups from Cpp2IL C# stubs."""
    if enum_dir and os.path.exists(enum_dir):
        lookups = {}
        enum_files = {
            'Archetype': 'Core/Enums/Archetype.cs',
            'Pack': 'Core/Enums/Pack.cs',
            'AbilityEnum': 'Core/Models/Abilities/AbilityEnum.cs',
            'Role': 'Core/Enums/Role.cs',
            'TriggerEnum': 'Core/Enums/TriggerEnum.cs',
        }
        for key, path in enum_files.items():
            full = os.path.join(enum_dir, path)
            if os.path.exists(full):
                with open(full) as f:
                    lookups[key] = {int(m.group(2)): m.group(1)
                                    for m in re.finditer(r'(\w+)\s*=\s*(-?\d+)', f.read())}
        return lookups
    return {}


# JS helper functions injected into the browser — shared across all dumps
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
function cleanDesc(s) {
    if (!s) return null;
    return s.replace(/\\{\\w*Icon\\}\\s*/g, '').trim();
}
"""


def build_pet_js(func_idx):
    return f"""() => {{
        const mod = window.__mod;
        const mem = mod.HEAPU8;
        const table = mod.asm.__indirect_function_table;
        {JS_HELPERS}
        const fn = table.get({func_idx});
        const listPtr = fn();
        const arr = r32(listPtr + 8);
        const count = r32(listPtr + 12);
        const pets = [];
        for (let i = 0; i < count; i++) {{
            const p = r32(arr + 16 + i * 4);
            if (!p) continue;
            const archProd = rHashSet(r32(p + 64));
            const archCons = rHashSet(r32(p + 68));
            const archCust = rList(r32(p + 72));
            const roles = rList(r32(p + 104));
            const packs = rHashSet(r32(p + 108));
            const abilityEnums = rList(r32(p + 216));
            pets.push({{
                name: rStr(r32(p + 8)),
                enumId: r32(p + 116),
                tier: r32(p + 16),
                attack: r32(p + 132),
                health: r32(p + 144),
                price: r32(p + 20),
                rollable: rByte(p + 29) === 1,
                active: rByte(p + 28) === 1,
                about: cleanDesc(rStr(r32(p + 24))),
                archetypeProducer: archProd,
                archetypeConsumer: archCons,
                archetypeCustom: archCust,
                roles: roles,
                packs: packs,
                abilityEnums: abilityEnums,
            }});
        }}
        return pets;
    }}"""


def build_spell_js(func_idx):
    return f"""() => {{
        const mod = window.__mod;
        const mem = mod.HEAPU8;
        const table = mod.asm.__indirect_function_table;
        {JS_HELPERS}
        const fn = table.get({func_idx});
        const listPtr = fn();
        const arr = r32(listPtr + 8);
        const count = r32(listPtr + 12);
        const spells = [];
        for (let i = 0; i < count; i++) {{
            const p = r32(arr + 16 + i * 4);
            if (!p) continue;
            const archProd = rHashSet(r32(p + 64));
            const archCons = rHashSet(r32(p + 68));
            const packs = rHashSet(r32(p + 108));
            spells.push({{
                name: rStr(r32(p + 8)),
                enumId: r32(p + 116),
                tier: r32(p + 16),
                price: r32(p + 20),
                rollable: rByte(p + 29) === 1,
                active: rByte(p + 28) === 1,
                about: cleanDesc(rStr(r32(p + 24))),
                archetypeProducer: archProd,
                archetypeConsumer: archCons,
                packs: packs,
            }});
        }}
        return spells;
    }}"""


def build_perk_js(func_idx):
    return f"""() => {{
        const mod = window.__mod;
        const mem = mod.HEAPU8;
        const table = mod.asm.__indirect_function_table;
        {JS_HELPERS}
        const fn = table.get({func_idx});
        const listPtr = fn();
        const arr = r32(listPtr + 8);
        const count = r32(listPtr + 12);
        const perks = [];
        for (let i = 0; i < count; i++) {{
            const p = r32(arr + 16 + i * 4);
            if (!p) continue;
            // PerkTemplate: klass(4)+monitor(4)+fields
            // Fields: Enum(4), Name(4), NameNorm(4), EffectName(4), Abilities(4),
            //         Localization(1+pad), Spell(Nullable=8), Durability(Nullable=8),
            //         Positive(1), MidBattle(1), Universal(1), Unreleased(1), ...
            const abilEnums = rList(r32(p + 24));  // Abilities list ptr
            perks.push({{
                name: rStr(r32(p + 12)),
                enumId: r32(p + 8),
                effectName: rStr(r32(p + 20)),
                abilityEnums: abilEnums,
            }});
        }}
        return perks;
    }}"""


def resolve_enums(data, lookups, field_mappings):
    """Replace enum integer values with human-readable names."""
    for item in data:
        for field, enum_name in field_mappings.items():
            if field not in item or item[field] is None:
                continue
            lookup = lookups.get(enum_name, {})
            if isinstance(item[field], list):
                item[field] = [lookup.get(v, v) for v in item[field]]
            elif isinstance(item[field], int):
                item[field] = lookup.get(item[field], item[field])


async def extract_all(output_dir, script_json_path=None, enum_dir=None, timeout=90):
    """Launch game, wait for init, dump all data."""

    # Resolve function indices
    func_indices = {}
    if script_json_path and os.path.exists(script_json_path):
        with open(script_json_path) as f:
            script = json.load(f)
        for key, full_name in FUNCTION_NAMES.items():
            for entry in script['ScriptMethod']:
                if entry.get('Name') == full_name:
                    func_indices[key] = entry['Address']
                    break
        log(f"Function indices from script.json: {func_indices}")
    else:
        func_indices = {
            'GetReleasedMinions': 11688,
            'GetReleasedSpells': 30368,
            'GetReleasedPerks': 30225,
        }
        log("Using fallback function indices")

    lookups = load_enum_lookups(enum_dir)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

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

        canvas = await page.wait_for_selector('canvas', timeout=10000)
        if canvas:
            await canvas.click()

        log(f"Waiting {timeout}s for game initialization...")
        await page.wait_for_timeout(timeout * 1000)

        check = await page.evaluate("() => ({ ok: !!(window.__mod && window.__mod.asm.__indirect_function_table) })")
        if not check.get('ok'):
            log("ERROR: WASM module not loaded. Increase --timeout.")
            await browser.close()
            return

        # Dump pets
        log("Dumping pets...")
        pets = await page.evaluate(build_pet_js(func_indices['GetReleasedMinions']))
        log(f"  Pets: {len(pets)}")

        # Dump spells
        log("Dumping spells...")
        spells = await page.evaluate(build_spell_js(func_indices['GetReleasedSpells']))
        log(f"  Spells: {len(spells)}")

        # Dump perks
        log("Dumping perks...")
        perks = await page.evaluate(build_perk_js(func_indices['GetReleasedPerks']))
        log(f"  Perks: {len(perks)}")

        await browser.close()

    # Resolve enum IDs to names
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

    # Save
    os.makedirs(output_dir, exist_ok=True)

    for name, data in [('pets', pets), ('spells', spells), ('perks', perks)]:
        path = os.path.join(output_dir, f'{name}.json')
        with open(path, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    # Summary
    log(f"Done! Saved to {output_dir}/")
    log(f"  Pets: {len(pets)} ({sum(1 for p in pets if p['rollable'])} rollable)")
    log(f"  Spells: {len(spells)} ({sum(1 for s in spells if s['rollable'])} rollable)")
    log(f"  Perks: {len(perks)}")


def main():
    parser = argparse.ArgumentParser(description="Extract SAP game data from WebGL build")
    parser.add_argument("--output-dir", default="tmp/webgl-extract", help="Output directory")
    parser.add_argument("--script-json", default=None, help="Il2CppDumper script.json for function index resolution")
    parser.add_argument("--enum-dir", default=None, help="Cpp2IL DiffableCs/Assembly-CSharp/Spacewood dir for enum name resolution")
    parser.add_argument("--timeout", type=int, default=90, help="Seconds to wait for game init")
    args = parser.parse_args()

    asyncio.run(extract_all(args.output_dir, args.script_json, args.enum_dir, args.timeout))


if __name__ == "__main__":
    main()
