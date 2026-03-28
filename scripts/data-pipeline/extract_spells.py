"""
Spell/Food extraction from SpellConstants ISIL.

Extracts: enum, name, pack, tier, rollable, price, archetypes, abilities.
Uses the same ISIL parsing approach as pet extraction.
"""

# Descriptions for spells whose about text is dynamically constructed at runtime
# rather than stored as a static string or localization key.
# Sourced from in-game UI.
HARDCODED_SPELL_DESCRIPTIONS = {
    'Guarana': 'Give +2 gold this turn.',
    'GingerbreadHouse': 'Stock one random pet from last battle at 1 gold.',
    'Juice': 'Give shop pets +1 attack and +1 health permanently.',
    'Parsnip': 'Give one random friend +1 attack and +1 health.',
    'Pomegranate': 'Give one pet Pomegranate.',
    'Manchineel': 'Give one pet Manchineel.',
    'Papaya': 'Give one pet Papaya.',
    'SweetLiquorice': 'Give one pet Liquorice.',
    'IceCream': 'Give one pet Ice Cream.',
}

import os
import re


def log(msg):
    print(f"[SPELLS] {msg}", __import__('sys').stderr)


def _parse_cs_enum(filepath):
    enum_map = {}
    if os.path.exists(filepath):
        with open(filepath) as f:
            for m in re.finditer(r'(\w+)\s*=\s*(-?\d+)', f.read()):
                enum_map[int(m.group(2))] = m.group(1)
    return enum_map


def _parse_isil_value(s):
    s = s.strip()
    if s.startswith('0x'):
        return int(s[2:], 16)
    if s.startswith('['):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def extract_spells_from_isil(isil_dir, cs_dir):
    """Parse SpellConstants ISIL to extract food/spell data."""
    base_cs = os.path.join(cs_dir, "DiffableCs/Assembly-CSharp/Spacewood")
    enum_map = _parse_cs_enum(os.path.join(base_cs, "Core/Enums/SpellEnum.cs"))
    ability_map = _parse_cs_enum(os.path.join(base_cs, "Core/Models/Abilities/AbilityEnum.cs"))
    archetype_map = _parse_cs_enum(os.path.join(base_cs, "Core/Enums/Archetype.cs"))

    sc_path = os.path.join(isil_dir, "IsilDump/Assembly-CSharp/Spacewood/Core/Enums/SpellConstants.txt")
    if not os.path.exists(sc_path):
        return []

    with open(sc_path) as f:
        content = f.read()

    methods = re.split(r'\nMethod: ', content)
    all_spells = []

    for m_text in methods[1:]:
        sig = m_text.split('\n')[0].strip()
        method_match = re.match(r'System\.Void (Create\w+)\(\)', sig)
        if not method_match:
            continue
        pack_name = method_match.group(1)
        if not any(kw in pack_name for kw in
                   ['Pack', 'Token', 'Ailment', 'Custom', 'Draft', 'Relic', 'Rework', 'Plus', 'Free']):
            continue

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
        spells = []
        current_spell = None
        current_tier = None
        current_rollable = True
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
                        val = _parse_isil_value(src)
                        if val is not None:
                            offset = int(arr_write.group(2))
                            if offset >= 32 and val < 100:
                                pending_archetype_values.append(val)
                    else:
                        val = _parse_isil_value(src)
                        if val is not None:
                            regs[dst] = val
                        elif src.startswith('"') and src.endswith('"'):
                            regs[dst] = src[1:-1]
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

                elif method_name == 'SpellConstants.StartGroup':
                    if pending_tier is not None:
                        current_tier = pending_tier
                        pending_tier = None
                    current_rollable = True

                elif method_name == 'SpellConstants.StartTokenGroup':
                    current_tier = None
                    current_rollable = False

                elif method_name == '"SzArrayNew"':
                    pending_archetype_values = []

                elif method_name in ('SpellConstants.CreateSpell',
                                     'SpellConstants.CreatePerkSpell',
                                     'SpellConstants.CreateRelicSpell',
                                     'SpellConstants.CreateCannedAilmentSpell'):
                    enum_val = arg_vals[0] if arg_vals and isinstance(arg_vals[0], int) else None
                    spell_name = enum_map.get(enum_val, f"Unknown_{enum_val}") if enum_val is not None else "Unknown"

                    spell_type = 'food'
                    if 'PerkSpell' in method_name:
                        spell_type = 'perk_spell'
                    elif 'RelicSpell' in method_name:
                        spell_type = 'relic_spell'
                    elif 'CannedAilment' in method_name:
                        spell_type = 'canned_ailment'

                    current_spell = {
                        'enum': enum_val, 'name': spell_name, 'pack': pack_name,
                        'tier': current_tier, 'rollable': current_rollable,
                        'type': spell_type, 'archetypes': {},
                    }
                    spells.append(current_spell)

                elif current_spell:
                    if method_name == 'Spell.SetPrice':
                        if len(arg_vals) >= 2 and isinstance(arg_vals[1], int):
                            current_spell['price'] = arg_vals[1]

                    elif method_name == 'Spell.Unrollable':
                        current_spell['rollable'] = False

                    elif method_name.startswith('Spell.SetArchetype'):
                        arch_type = method_name.split('SetArchetype')[1].lower()
                        if pending_archetype_values:
                            current_spell['archetypes'][arch_type] = [
                                archetype_map.get(v, f"Archetype_{v}") for v in pending_archetype_values
                            ]
                            pending_archetype_values = []

                for vol in ['rcx', 'rdx', 'r8', 'r9', 'rax']:
                    regs.pop(vol, None)
                regs['rax'] = 'CALL_RESULT'

        all_spells.extend(spells)

    return all_spells


def assemble_spells_json(spells, spell_descriptions, display_names):
    """Assemble spell data into output format.

    spell_descriptions: {spell_internal_name: {"about": "text", "fineprint": "text"}}
    """
    output = []
    for s in spells:
        name = display_names.get(s['name'], s['name'])
        entry = {
            "name": name,
            "id": s['name'],
            "enumId": s['enum'],
            "pack": s.get('pack'),
            "tier": s.get('tier'),
            "rollable": s.get('rollable', True),
            "type": s.get('type', 'food'),
        }

        if s.get('price') is not None:
            entry["price"] = s['price']

        # Description from Spell.X.About localization key, with hardcoded fallback
        desc = spell_descriptions.get(s['name'], {})
        if desc.get('about'):
            entry["description"] = desc['about']
        elif s['name'] in HARDCODED_SPELL_DESCRIPTIONS:
            entry["description"] = HARDCODED_SPELL_DESCRIPTIONS[s['name']]

        archetypes = {k: v for k, v in s.get('archetypes', {}).items() if v}
        if archetypes:
            entry["archetypes"] = archetypes

        output.append(entry)

    return output
