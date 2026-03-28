#!/usr/bin/env python3
"""
Parse the ISIL (Intermediate Static IL) section of Cpp2IL output to extract pet data.

The ISIL section comes after the raw x86 disassembly in each method and has resolved
method names like "Call MinionConstants.Create, rcx, rdx, r8, r9".
"""

import re
import json
from pathlib import Path

ISIL_FILE = Path("tmp/cpp2il-isil/IsilDump/Assembly-CSharp/Spacewood/Core/Enums/MinionConstants.txt")
ENUM_FILE = Path("tmp/cpp2il-cs/DiffableCs/Assembly-CSharp/Spacewood/Core/Enums/MinionEnum.cs")
ABILITY_FILE = Path("tmp/cpp2il-cs/DiffableCs/Assembly-CSharp/Spacewood/Core/Models/Abilities/AbilityEnum.cs")
ARCHETYPE_FILE = Path("tmp/cpp2il-cs/DiffableCs/Assembly-CSharp/Spacewood/Core/Enums/Archetype.cs")
ROLE_FILE = Path("tmp/cpp2il-cs/DiffableCs/Assembly-CSharp/Spacewood/Core/Enums/Role.cs")


def parse_cs_enum(filepath):
    """Parse a C# enum file to build value->name mapping."""
    enum_map = {}
    if filepath.exists():
        content = filepath.read_text()
        for match in re.finditer(r'(\w+)\s*=\s*(-?\d+)', content):
            name, value = match.group(1), int(match.group(2))
            enum_map[value] = name
    return enum_map


def extract_methods(content):
    """Split ISIL dump into individual methods."""
    methods = {}
    parts = re.split(r'\nMethod: ', content)
    for part in parts[1:]:
        sig = part.split('\n')[0].strip()
        methods[sig] = part
    return methods


def extract_isil_section(method_text):
    """
    Extract the ISIL section from a method's text.
    The ISIL section starts after the 'ISIL:' marker and contains numbered instructions like:
      001 Move rcx, 0x1234
      002 Call MinionConstants.Create, rcx, rdx, r8, r9
    """
    lines = method_text.split('\n')
    isil_lines = []
    in_isil = False
    for line in lines:
        stripped = line.strip()
        if stripped == 'ISIL:':
            in_isil = True
            continue
        if in_isil and re.match(r'\d+\s+\w', stripped):
            isil_lines.append(stripped)
    return isil_lines


def parse_isil_value(s):
    """Parse an ISIL operand value."""
    s = s.strip()
    if s.startswith('0x'):
        return int(s, 16)
    if s.startswith('[') and '+' in s:
        # [rbx+1] style - need to know base reg value
        return None
    try:
        return int(s)
    except ValueError:
        return None


def track_and_extract(isil_lines, enum_map, ability_map, archetype_map, role_map, pack_name):
    """
    Walk through ISIL instructions, track register values, and extract pet data.
    """
    regs = {}
    pets = []
    current_pet = None
    current_tier = None
    pending_tier = None
    pending_archetype_values = []

    for line in isil_lines:
        # Parse the instruction
        # Format: NUMBER OPCODE ARGS...
        m = re.match(r'(\d+)\s+(\w+)\s*(.*)', line)
        if not m:
            continue
        num, opcode, args = int(m.group(1)), m.group(2), m.group(3).strip()

        if opcode == 'Move':
            # Move dst, src
            parts = args.split(',', 1)
            if len(parts) == 2:
                dst, src = parts[0].strip(), parts[1].strip()
                val = parse_isil_value(src)
                # Track array element writes: Move [rax+32], VALUE
                # These are archetype enum values written to .NET arrays
                arr_write = re.match(r'\[(\w+)\+(\d+)\]', dst)
                if arr_write and val is not None:
                    offset = int(arr_write.group(2))
                    if offset >= 32 and val < 100:  # Array elements at offset 32+, small enum values
                        pending_archetype_values.append(val)
                elif val is not None:
                    regs[dst] = val
                elif src in regs:
                    regs[dst] = regs[src]
                elif src.startswith('typeof('):
                    regs[dst] = src  # Keep type references
                else:
                    regs.pop(dst, None)

        elif opcode == 'LoadAddress':
            # LoadAddress dst, [base+offset]
            parts = args.split(',', 1)
            if len(parts) == 2:
                dst, src = parts[0].strip(), parts[1].strip()
                # Parse [reg+N] pattern
                lea_m = re.match(r'\[(\w+)\+(\d+)\]', src)
                if lea_m:
                    base_reg, offset = lea_m.group(1), int(lea_m.group(2))
                    if base_reg in regs and isinstance(regs[base_reg], int):
                        regs[dst] = regs[base_reg] + offset
                    else:
                        regs.pop(dst, None)
                else:
                    regs.pop(dst, None)

        elif opcode == 'Call':
            # Call MethodName, arg1, arg2, ...
            call_parts = args.split(',')
            method_name = call_parts[0].strip()
            call_args = [p.strip() for p in call_parts[1:]] if len(call_parts) > 1 else []

            # Resolve argument values
            arg_vals = []
            for a in call_args:
                if a in regs:
                    arg_vals.append(regs[a])
                else:
                    arg_vals.append(None)

            # Process known methods
            if method_name == '0x1811A24E0':
                # Nullable<Int32> constructor - rdx has the tier value
                if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                    pending_tier = arg_vals[1]

            elif method_name == 'MinionConstants.StartGroup':
                # StartGroup uses the tier from the preceding Nullable constructor
                if pending_tier is not None:
                    current_tier = pending_tier
                    pending_tier = None

            elif method_name == 'MinionConstants.StartTokenGroup':
                # Token pets have tier 1 (they're summoned, not bought)
                current_tier = 1

            elif method_name == '"SzArrayNew"':
                # New array created — reset pending archetype values
                pending_archetype_values = []

            elif method_name == 'MinionConstants.Create':
                # Create(enum, tier_override, packs, ?) - rcx has enum
                enum_val = arg_vals[0] if arg_vals and isinstance(arg_vals[0], int) else None
                pet_name = enum_map.get(enum_val, f"Unknown_{enum_val}") if enum_val is not None else "Unknown"

                current_pet = {
                    'enum': enum_val,
                    'name': pet_name,
                    'pack': pack_name,
                    'tier': current_tier,
                    'abilities': [],
                    'archetypes': {'producer': [], 'consumer': [], 'custom': [], 'mvp': []},
                    'roles': [],
                }
                pets.append(current_pet)

            elif current_pet:
                if method_name == 'MinionTemplate.SetStats':
                    # SetStats(this, attack, health) - rdx=attack, r8=health
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
                    # Archetypes are passed as arrays. The array was built by
                    # SzArrayNew + Move [rax+32], VAL + Move [rax+36], VAL2 etc.
                    # We track these via pending_archetype_values
                    arch_type = method_name.split('SetArchetype')[1].lower()
                    if arch_type not in current_pet['archetypes']:
                        current_pet['archetypes'][arch_type] = []
                    for av in pending_archetype_values:
                        at_name = archetype_map.get(av, f"Archetype_{av}")
                        current_pet['archetypes'][arch_type].append(at_name)
                    pending_archetype_values = []

                elif method_name == 'MinionTemplate.SetRoles':
                    if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                        r_name = role_map.get(arg_vals[1], f"Role_{arg_vals[1]}")
                        current_pet['roles'].append(r_name)

                elif method_name == 'MinionTemplate.AddPack':
                    if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                        current_pet.setdefault('extra_packs', []).append(arg_vals[1])

                elif method_name == 'MinionTemplate.SetSoundEnum':
                    if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                        sound_name = enum_map.get(arg_vals[1], f"Sound_{arg_vals[1]}")
                        current_pet['sound_enum'] = sound_name

            # After a call, clobber volatile regs
            for vol in ['rcx', 'rdx', 'r8', 'r9', 'rax']:
                regs.pop(vol, None)
            regs['rax'] = 'CALL_RESULT'

    return pets


def clean_pet(pet):
    """Remove empty optional fields."""
    if not pet.get('abilities'):
        del pet['abilities']
    if not any(pet.get('archetypes', {}).values()):
        pet.pop('archetypes', None)
    else:
        # Remove empty archetype sublists
        pet['archetypes'] = {k: v for k, v in pet['archetypes'].items() if v}
    if not pet.get('roles'):
        del pet['roles']
    if not pet.get('extra_packs'):
        pet.pop('extra_packs', None)
    return pet


def main():
    enum_map = parse_cs_enum(ENUM_FILE)
    ability_map = parse_cs_enum(ABILITY_FILE)
    archetype_map = parse_cs_enum(ARCHETYPE_FILE)
    role_map = parse_cs_enum(ROLE_FILE)

    print(f"Loaded enums: {len(enum_map)} minions, {len(ability_map)} abilities, "
          f"{len(archetype_map)} archetypes, {len(role_map)} roles")

    content = ISIL_FILE.read_text()
    methods = extract_methods(content)

    # Find all CreatePack methods
    pack_methods = {}
    for sig, text in methods.items():
        m = re.match(r'System\.Void (Create\w+)\(\)', sig)
        if m and ('Pack' in m.group(1) or 'Token' in m.group(1) or 'Misc' in m.group(1)
                  or 'Bully' in m.group(1) or 'Custom' in m.group(1) or 'Draft' in m.group(1)
                  or 'Relic' in m.group(1) or 'Rework' in m.group(1)):
            pack_methods[m.group(1)] = text

    print(f"\nFound {len(pack_methods)} creation methods")

    all_pets = []
    for name, text in sorted(pack_methods.items()):
        isil = extract_isil_section(text)
        if not isil:
            print(f"  {name}: No ISIL section found")
            continue

        pets = track_and_extract(isil, enum_map, ability_map, archetype_map, role_map, name)
        for p in pets:
            clean_pet(p)

        print(f"  {name}: {len(pets)} pets, {len(isil)} ISIL instructions")
        for p in pets[:3]:
            stats = f"{p.get('attack', '?')}/{p.get('health', '?')}"
            tier = f"T{p.get('tier', '?')}"
            abilities = ', '.join(p.get('abilities', [])[:2])
            print(f"    {p['name']} ({tier}): {stats} [{abilities}]")
        if len(pets) > 3:
            print(f"    ... and {len(pets) - 3} more")

        all_pets.extend(pets)

    # Save full output
    output = Path("tmp/extracted-pets-full.json")
    output.write_text(json.dumps(all_pets, indent=2, default=str))

    # Summary
    with_stats = sum(1 for p in all_pets if 'attack' in p and 'health' in p)
    with_tier = sum(1 for p in all_pets if p.get('tier') is not None)
    with_abilities = sum(1 for p in all_pets if p.get('abilities'))
    print(f"\nTotal: {len(all_pets)} pets extracted → {output}")
    print(f"  With stats: {with_stats}")
    print(f"  With tier: {with_tier}")
    print(f"  With abilities: {with_abilities}")


if __name__ == '__main__':
    main()
