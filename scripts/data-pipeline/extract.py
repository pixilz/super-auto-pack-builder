#!/usr/bin/env python3
"""
SAP data extraction pipeline.

Input: Game files directory (containing GameAssembly.dll, Super Auto Pets_Data/)
Output: pets.json with complete pet data

Steps:
1. Run Cpp2IL → ISIL output (stats, tiers, abilities, archetypes)
2. Parse localization from Unity addressable bundles (descriptions, names)
3. Apply trigger map (pre-built from groundedsap Rosetta Stone)
4. Assemble final JSON

Usage:
  python3 extract.py --game-dir "path/to/game" --output pets.json
  python3 extract.py --game-dir "path/to/game" --output pets.json --trigger-map triggers.json

Dependencies: UnityPy (pip install UnityPy), Cpp2IL binary
"""

import argparse
import json
import math
import os
import re
import struct
import subprocess
import sys
from pathlib import Path


def log(msg):
    print(f"[PIPELINE] {msg}", file=sys.stderr)


# ============================================================
# Step 1: Cpp2IL
# ============================================================

def run_cpp2il(game_dir: str, work_dir: str, cpp2il_path: str):
    """Run Cpp2IL for ISIL and diffable-cs output."""
    isil_dir = os.path.join(work_dir, "cpp2il-isil")
    cs_dir = os.path.join(work_dir, "cpp2il-cs")

    log(f"Running Cpp2IL...")
    for output_format, output_dir in [("isil", isil_dir), ("diffable-cs", cs_dir)]:
        result = subprocess.run(
            [cpp2il_path, "--game-path", game_dir, "--output-as", output_format, "--output-to", output_dir],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            log(f"Cpp2IL ({output_format}) failed: {result.stderr[:200]}")
            sys.exit(1)

    log("Cpp2IL complete")
    return isil_dir, cs_dir


# ============================================================
# Step 2: Parse ISIL for pet data
# ============================================================

def parse_cs_enum(filepath):
    enum_map = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            for m in re.finditer(r'(\w+)\s*=\s*(-?\d+)', f.read()):
                enum_map[int(m.group(2))] = m.group(1)
    return enum_map


def parse_isil_value(s):
    s = s.strip()
    if s.startswith('0x'):
        return int(s[2:], 16)
    if s.startswith('['):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def extract_pets_from_isil(isil_dir, cs_dir):
    """Parse Cpp2IL ISIL output to extract pet data."""
    log("Parsing ISIL for pet stats...")

    base_cs = os.path.join(cs_dir, "DiffableCs/Assembly-CSharp/Spacewood")
    enum_map = parse_cs_enum(os.path.join(base_cs, "Core/Enums/MinionEnum.cs"))
    ability_map = parse_cs_enum(os.path.join(base_cs, "Core/Models/Abilities/AbilityEnum.cs"))
    archetype_map = parse_cs_enum(os.path.join(base_cs, "Core/Enums/Archetype.cs"))

    mc_path = os.path.join(isil_dir, "IsilDump/Assembly-CSharp/Spacewood/Core/Enums/MinionConstants.txt")
    with open(mc_path) as f:
        content = f.read()

    methods = re.split(r'\nMethod: ', content)
    all_pets = []

    for m_text in methods[1:]:
        sig = m_text.split('\n')[0].strip()
        method_match = re.match(r'System\.Void (Create\w+)\(\)', sig)
        if not method_match:
            continue
        pack_name = method_match.group(1)
        if not any(kw in pack_name for kw in
                   ['Pack', 'Token', 'Misc', 'Bully', 'Custom', 'Draft', 'Relic', 'Rework', 'Plus']):
            continue

        # Extract ISIL section (after "ISIL:" marker)
        lines = m_text.split('\n')
        in_isil = False
        isil_lines = []
        for line in lines:
            s = line.strip()
            if s == 'ISIL:':
                in_isil = True
                continue
            if in_isil and re.match(r'\d+\s+\w', s):
                isil_lines.append(s)

        if not isil_lines:
            continue

        regs = {}
        pets = []
        current_pet = None
        current_tier = None
        pending_tier = None
        pending_archetype_values = []

        for il in isil_lines:
            pm = re.match(r'(\d+)\s+(\w+)\s*(.*)', il)
            if not pm:
                continue
            opcode, args = pm.group(2), pm.group(3).strip()

            if opcode == 'Move':
                parts = args.split(',', 1)
                if len(parts) == 2:
                    dst, src = parts[0].strip(), parts[1].strip()
                    arr_write = re.match(r'\[(\w+)\+(\d+)\]', dst)
                    if arr_write:
                        val = parse_isil_value(src)
                        if val is not None:
                            offset = int(arr_write.group(2))
                            if offset >= 32 and val < 100:
                                pending_archetype_values.append(val)
                    else:
                        val = parse_isil_value(src)
                        if val is not None:
                            regs[dst] = val
                        elif src in regs:
                            regs[dst] = regs[src]
                        else:
                            regs.pop(dst, None)

            elif opcode == 'LoadAddress':
                parts = args.split(',', 1)
                if len(parts) == 2:
                    dst, src = parts[0].strip(), parts[1].strip()
                    lea_m = re.match(r'\[(\w+)\+(\d+)\]', src)
                    if lea_m and lea_m.group(1) in regs and isinstance(regs[lea_m.group(1)], int):
                        regs[dst] = regs[lea_m.group(1)] + int(lea_m.group(2))
                    else:
                        regs.pop(dst, None)

            elif opcode == 'Call':
                call_parts = args.split(',')
                method_name = call_parts[0].strip()
                call_args = [p.strip() for p in call_parts[1:]]
                arg_vals = [regs.get(a) for a in call_args]

                if method_name == '0x1811A24E0':
                    if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                        pending_tier = arg_vals[1]

                elif method_name == 'MinionConstants.StartGroup':
                    if pending_tier is not None:
                        current_tier = pending_tier
                        pending_tier = None

                elif method_name == 'MinionConstants.StartTokenGroup':
                    current_tier = 1

                elif method_name == '"SzArrayNew"':
                    pending_archetype_values = []

                elif method_name == 'MinionConstants.Create':
                    enum_val = arg_vals[0] if arg_vals and isinstance(arg_vals[0], int) else None
                    pet_name = enum_map.get(enum_val, f"Unknown_{enum_val}") if enum_val is not None else "Unknown"
                    current_pet = {
                        'enum': enum_val, 'name': pet_name, 'pack': pack_name,
                        'tier': current_tier, 'abilities': [], 'archetypes': {},
                    }
                    pets.append(current_pet)

                elif current_pet:
                    if method_name == 'MinionTemplate.SetStats':
                        if len(arg_vals) >= 3:
                            if isinstance(arg_vals[1], int):
                                current_pet['attack'] = arg_vals[1]
                            if isinstance(arg_vals[2], int):
                                current_pet['health'] = arg_vals[2]

                    elif method_name == 'MinionTemplate.AddAbility':
                        if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                            ab_name = ability_map.get(arg_vals[1], f"Ability_{arg_vals[1]}")
                            current_pet['abilities'].append(ab_name)

                    elif method_name.startswith('MinionTemplate.SetArchetype'):
                        arch_type = method_name.split('SetArchetype')[1].lower()
                        if pending_archetype_values:
                            current_pet['archetypes'][arch_type] = [
                                archetype_map.get(v, f"Archetype_{v}") for v in pending_archetype_values
                            ]
                            pending_archetype_values = []

                for vol in ['rcx', 'rdx', 'r8', 'r9', 'rax']:
                    regs.pop(vol, None)
                regs['rax'] = 'CALL_RESULT'

        all_pets.extend(pets)

    log(f"Extracted {len(all_pets)} pets from ISIL")
    return all_pets


# ============================================================
# Step 3: Localization
# ============================================================

def parse_binary_table(raw, start_offset, entry_parser):
    """Parse a binary table with [8-byte key][4-byte len][padded string][4-byte pad] entries."""
    entries = {}
    pos = start_offset
    while pos + 16 < len(raw):
        key = struct.unpack_from('<q', raw, pos)[0]
        str_len = struct.unpack_from('<I', raw, pos + 8)[0]
        if str_len > 5000 or str_len <= 0:
            break
        str_padded = max(math.ceil(str_len / 4) * 4, 4)
        text_start = pos + 12
        if text_start + str_len > len(raw):
            break
        text = raw[text_start:text_start + str_len].decode('utf-8', errors='replace')
        entries[key] = text
        pos = text_start + str_padded + 4
    return entries


def find_table_start(raw, scan_start, scan_end):
    """Find the first valid entry in a binary table."""
    pos = scan_start
    while pos < scan_end:
        str_len = struct.unpack_from('<I', raw, pos + 8)[0]
        if 0 < str_len < 200:
            try:
                raw[pos + 12:pos + 12 + str_len].decode('utf-8')
                return pos
            except Exception:
                pass
        pos += 4
    return None


def extract_localization(game_dir):
    """Extract ability descriptions, pet names, and trigger names."""
    log("Extracting localization data...")
    import UnityPy

    bundle_dir = os.path.join(game_dir, "Super Auto Pets_Data/StreamingAssets/aa/StandaloneWindows64")

    # SharedTableData (key_name → key_id)
    env = UnityPy.load(os.path.join(bundle_dir, "localization-assets-shared_assets_all.bundle"))
    shared_raw = None
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour" and len(obj.get_raw_data()) > 100000:
            shared_raw = obj.get_raw_data()
            break

    # SharedTableData: key_name → key_id (reversed from normal table)
    raw_shared = parse_binary_table(shared_raw, 120, None) if shared_raw else {}
    key_name_to_id = {text: kid for kid, text in raw_shared.items()}

    # English StringTable (key_id → text)
    env2 = UnityPy.load(os.path.join(bundle_dir, "localization-string-tables-english_assets_all.bundle"))
    loc_raw = None
    for obj in env2.objects:
        if obj.type.name == "MonoBehaviour" and len(obj.get_raw_data()) > 100000:
            loc_raw = obj.get_raw_data()
            break

    start = find_table_start(loc_raw, 60, 150) if loc_raw else None
    id_to_text = parse_binary_table(loc_raw, start, None) if start else {}

    log(f"  SharedTableData: {len(key_name_to_id)} keys, StringTable: {len(id_to_text)} entries")

    def clean_desc(s):
        return re.sub(r'\s+', ' ', re.sub(r'\{(\w*Icon)\}\s*', '', s)).strip()

    # Ability descriptions
    ability_descriptions = {}
    for key_name, key_id in key_name_to_id.items():
        m = re.match(r'Ability\.(\w+)\.(\d+)\.(About|FinePrint)', key_name)
        if not m or key_id not in id_to_text:
            continue
        ab_name, level, field = m.group(1), int(m.group(2)), m.group(3).lower()
        text = clean_desc(id_to_text[key_id])
        ability_descriptions.setdefault(ab_name, {}).setdefault(level, {})[field] = text

    for levels in ability_descriptions.values():
        for fields in levels.values():
            if 'fineprint' in fields and 'about' in fields:
                fields['about'] = f"{fields['about']} ({fields['fineprint']})"

    # Pet display names
    pet_display_names = {}
    for key_name, key_id in key_name_to_id.items():
        m = re.match(r'Minion\.(\w+)\.Name', key_name)
        if m and key_id in id_to_text:
            pet_display_names[m.group(1)] = id_to_text[key_id]

    log(f"  Abilities: {len(ability_descriptions)}, Display names: {len(pet_display_names)}")
    return ability_descriptions, pet_display_names


# ============================================================
# Step 4: Assemble
# ============================================================

def assemble_json(pets, ability_descriptions, pet_display_names, trigger_map):
    """Assemble the final pets.json."""
    log("Assembling final JSON...")

    output = []
    for p in pets:
        name = pet_display_names.get(p['name'], p['name'])
        entry = {
            "name": name,
            "id": p['name'],
            "enumId": p['enum'],
            "pack": p.get('pack'),
            "tier": p.get('tier'),
        }

        if p.get('attack') is not None:
            entry["attack"] = p['attack']
        if p.get('health') is not None:
            entry["health"] = p['health']

        if p.get('abilities'):
            resolved = []
            for ab_name in p['abilities']:
                ab_data = {}
                if ab_name in trigger_map:
                    ab_data["trigger"] = trigger_map[ab_name]
                if ab_name in ability_descriptions:
                    for lvl in sorted(ability_descriptions[ab_name].keys()):
                        about = ability_descriptions[ab_name][lvl].get('about', '')
                        if about:
                            ab_data[f"level{lvl}"] = about
                if ab_data:
                    resolved.append(ab_data)
            if resolved:
                entry["abilities"] = resolved

        archetypes = {k: v for k, v in p.get('archetypes', {}).items() if v}
        if archetypes:
            entry["archetypes"] = archetypes

        output.append(entry)

    return output


def main():
    parser = argparse.ArgumentParser(description="SAP Data Extraction Pipeline")
    parser.add_argument("--game-dir", required=True, help="Path to game files directory")
    parser.add_argument("--output", default="pets.json", help="Output JSON file")
    parser.add_argument("--cpp2il", default=None, help="Path to Cpp2IL binary")
    parser.add_argument("--work-dir", default=None, help="Working directory for intermediate files")
    parser.add_argument("--trigger-map", default=None, help="Pre-built trigger map JSON")
    args = parser.parse_args()

    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root = os.path.dirname(os.path.dirname(script_dir))

    work_dir = args.work_dir or os.path.join(repo_root, "tmp/pipeline")
    cpp2il = args.cpp2il or os.path.join(repo_root, "tmp/cpp2il/Cpp2IL")
    trigger_map_path = args.trigger_map or os.path.join(script_dir, "trigger-map.json")

    os.makedirs(work_dir, exist_ok=True)

    if not os.path.exists(cpp2il):
        log(f"ERROR: Cpp2IL not found at {cpp2il}")
        log("Download from https://github.com/SamboyCoding/Cpp2IL/releases")
        sys.exit(1)

    # Step 1: Cpp2IL
    isil_dir, cs_dir = run_cpp2il(args.game_dir, work_dir, cpp2il)

    # Step 2: Parse ISIL
    pets = extract_pets_from_isil(isil_dir, cs_dir)

    # Step 3: Localization
    ability_descriptions, pet_display_names = extract_localization(args.game_dir)

    # Step 4: Trigger map
    trigger_map = {}
    if os.path.exists(trigger_map_path):
        log(f"Loading trigger map from {trigger_map_path}")
        with open(trigger_map_path) as f:
            trigger_map = json.load(f)
    else:
        log(f"WARNING: No trigger map at {trigger_map_path} — triggers will be missing")

    # Step 5: Assemble
    output = assemble_json(pets, ability_descriptions, pet_display_names, trigger_map)

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with_stats = sum(1 for p in output if 'attack' in p)
    with_abilities = sum(1 for p in output if p.get('abilities'))
    with_triggers = sum(1 for p in output
                        if p.get('abilities') and 'trigger' in p['abilities'][0])

    log(f"Done! {len(output)} pets → {args.output}")
    log(f"  With stats: {with_stats}")
    log(f"  With abilities: {with_abilities}")
    log(f"  With triggers: {with_triggers}")


if __name__ == "__main__":
    main()
