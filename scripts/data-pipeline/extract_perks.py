"""
Perk extraction from PerkConstants ISIL.

Extracts: enum, name, abilities, associated spell, durability, flags.
"""

# Descriptions for perks whose ability descriptions are dynamically constructed
# at runtime rather than stored as static strings.
# Sourced from in-game UI.
HARDCODED_PERK_DESCRIPTIONS = {
    'Pomegranate': 'Give two back-most friends +1 attack and +1 health.',
    'Manchineel': 'Deal 2 damage to two random enemies.',
    'FrenchFries': 'Attack twice, dealing half damage each.',
    'BrusselsSprout': 'Give one friend behind +2 attack and +2 health.',
}

import os
import re


def _parse_cs_enum(filepath):
    enum_map = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            for m in re.finditer(r'(\w+)\s*=\s*(-?\d+)', f.read()):
                enum_map[int(m.group(2))] = m.group(1)
    return enum_map


def extract_perks_from_isil(isil_dir, cs_dir):
    """Parse PerkConstants ISIL to extract perk data."""
    base_cs = os.path.join(cs_dir, "DiffableCs/Assembly-CSharp/Spacewood")
    perk_enum_map = _parse_cs_enum(os.path.join(base_cs, "Core/Enums/Perk.cs"))
    ability_map = _parse_cs_enum(os.path.join(base_cs, "Core/Models/Abilities/AbilityEnum.cs"))
    spell_map = _parse_cs_enum(os.path.join(base_cs, "Core/Enums/SpellEnum.cs"))

    pc_path = os.path.join(isil_dir, "IsilDump/Assembly-CSharp/Spacewood/Core/Enums/PerkConstants.txt")
    if not os.path.exists(pc_path):
        return []

    with open(pc_path) as f:
        content = f.read()

    methods = re.split(r'\nMethod: ', content)
    all_perks = []

    for m_text in methods[1:]:
        sig = m_text.split('\n')[0].strip()
        method_match = re.match(r'System\.Void (Create\w+)\(\)', sig)
        if not method_match:
            continue
        source_method = method_match.group(1)

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
        # PerkConstants.CreatePerk(Perk enum, string name, Action<PerkTemplate> action)
        # The enum is in rcx, name in rdx, action in r8
        # Pattern: LoadAddress rcx, [r9+<enum>] or Move rcx, <enum>
        #          Move rdx, "name"
        #          Move r8, <delegate>
        #          Call PerkConstants.CreatePerk

        pending_name = None

        for il in isil_lines:
            pm = re.match(r'(\d+)\s+(\w+)\s*(.*)', il)
            if not pm:
                continue
            opcode, args = pm.group(2), pm.group(3).strip()

            if opcode == 'Move':
                parts = args.split(',', 1)
                if len(parts) == 2:
                    dst, src = parts[0].strip(), parts[1].strip()
                    val = None
                    if src.startswith('"') and src.endswith('"'):
                        val = src[1:-1]
                    else:
                        try:
                            val = int(src)
                        except ValueError:
                            if src.startswith('0x'):
                                try:
                                    val = int(src, 16)
                                except ValueError:
                                    pass
                            elif src in regs:
                                val = regs[src]
                    if val is not None:
                        regs[dst] = val
                    else:
                        regs.pop(dst, None)

            elif opcode == 'LoadAddress':
                parts = args.split(',', 1)
                if len(parts) == 2:
                    dst, src = parts[0].strip(), parts[1].strip()
                    lea_m = re.match(r'\[(\w+)\+(\d+)\]', src)
                    if lea_m and lea_m.group(1) in regs:
                        base = regs[lea_m.group(1)]
                        if isinstance(base, int):
                            regs[dst] = base + int(lea_m.group(2))
                        else:
                            regs.pop(dst, None)
                    else:
                        regs.pop(dst, None)

            elif opcode == 'Call':
                call_parts = args.split(',')
                method_name = call_parts[0].strip()
                call_args = [p.strip() for p in call_parts[1:]]
                arg_vals = [regs.get(a) for a in call_args]

                if method_name == 'PerkConstants.CreatePerk':
                    enum_val = arg_vals[0] if arg_vals and isinstance(arg_vals[0], int) else None
                    name = arg_vals[1] if len(arg_vals) > 1 and isinstance(arg_vals[1], str) else None
                    perk_name = perk_enum_map.get(enum_val, f"Unknown_{enum_val}") if enum_val is not None else "Unknown"

                    perk = {
                        'enum': enum_val,
                        'name': perk_name,
                        'displayName': name,
                        'source': source_method,
                    }
                    all_perks.append(perk)

                for vol in ['rcx', 'rdx', 'r8', 'r9', 'rax']:
                    regs.pop(vol, None)
                regs['rax'] = 'CALL_RESULT'

    return all_perks


def assemble_perks_json(perks, perk_descriptions, display_names, ability_descriptions=None):
    """Assemble perk data into output format.

    perk_descriptions: {perk_internal_name: {"about": "text"}} from Perk.X.About keys
    ability_descriptions: {ability_name: {level: {"about": "text"}}} — fallback for perk
        descriptions via the PerkAbility naming convention (e.g., CoconutAbility for Coconut)
    """
    output = []
    for p in perks:
        name = p.get('displayName') or display_names.get(p['name'], p['name'])
        entry = {
            "name": name,
            "id": p['name'],
            "enumId": p['enum'],
            "source": p.get('source'),
        }

        # Try Perk.X.About localization key first
        desc = perk_descriptions.get(p['name'], {})
        if desc.get('about'):
            entry["description"] = desc['about']
        elif ability_descriptions:
            # Fallback: use the matching ability description (PerkName → PerkNameAbility)
            ab_name = f"{p['name']}Ability"
            ab_desc = ability_descriptions.get(ab_name, {})
            if isinstance(ab_desc, dict):
                # Get level 1 about text
                level1 = ab_desc.get(1, {})
                if isinstance(level1, dict) and level1.get('about'):
                    entry["description"] = level1['about']

        # Final fallback: hardcoded descriptions for runtime-constructed text
        if 'description' not in entry and p['name'] in HARDCODED_PERK_DESCRIPTIONS:
            entry["description"] = HARDCODED_PERK_DESCRIPTIONS[p['name']]

        output.append(entry)

    return output
