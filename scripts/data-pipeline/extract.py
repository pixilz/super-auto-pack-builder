#!/usr/bin/env python3
"""
SAP data extraction pipeline.

Input: Game files directory (containing GameAssembly.dll, Super Auto Pets_Data/)
Output: pets.json with complete pet data

Steps:
1. Run Cpp2IL → ISIL output (stats, tiers, abilities, archetypes, rollable)
2. Run Il2CppDumper → script.json (metadata for trigger extraction)
3. Extract standalone triggers (AbilityEnum → lambda → CreateTrigger calls)
4. Parse localization from Unity addressable bundles (descriptions, names)
5. Assemble final JSON (with fallback to pre-built trigger map for gaps)

Usage:
  python3 extract.py --game-dir "path/to/game" --output pets.json
  python3 extract.py --game-dir "path/to/game" --output pets.json --script-json path/to/script.json
  python3 extract.py --game-dir "path/to/game" --output pets.json --trigger-map triggers.json

Dependencies: UnityPy (pip install UnityPy), Cpp2IL binary, Il2CppDumper binary (optional)
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
# Game mode categorization
# ============================================================

_DRAFT_PACKS = frozenset({
    'CreateDraft', 'CreateRelicsDraft', 'CreateRelicsHard',
    'CreatePack2PuppyRelics', 'CreatePack5UnicornRelics', 'CreatePlusRelics',
})

_BULLY_PACKS = frozenset({'CreateBullyMinions'})

_TEST_PACKS = frozenset({'CreatePack9000Test', 'CreatePack9000TestEvaluators'})

_DRAFT_PERK_SOURCES = frozenset({'CreateDraft'})


def classify_mode(pack_or_source):
    """Classify a pack/source method name into a game mode."""
    if pack_or_source in _DRAFT_PACKS or pack_or_source in _DRAFT_PERK_SOURCES:
        return 'draft'
    if pack_or_source in _BULLY_PACKS:
        return 'bully'
    if pack_or_source in _TEST_PACKS:
        return 'test'
    return 'standard'


# ============================================================
# Trigger display name normalization
# ============================================================

TRIGGER_DISPLAY_NAMES = {
    # This/Self → simplified
    'ThisSold': 'Sell', 'ThisBought': 'Buy', 'ThisSummoned': 'Summoned',
    'ThisTransformed': 'Transformed', 'ThisCharged': 'Charged',
    'ThisChargedByEat': 'Charged by eat', 'ThisChargedByRoll': 'Charged by roll',
    'ThisInfront': 'In front', 'ThisNotInfront': 'Not in front',
    'ThisBoughtOrToyBroke': 'Buy or toy broke',
    'ThisSpendsAttack': 'Spends attack', 'ThisSpendsHealth': 'Spends health',
    'LeveledUpThis': 'Level-up',
    'AppleEatenByThis': 'Eats apple',
    'FoodEatenByThis': 'Eats food', 'ShopFoodEatenByThis': 'Eats food',
    # Start/End
    'StartBattle': 'Start of battle', 'StartTurn': 'Start of turn',
    'EndTurn': 'End turn', 'BeforeStartBattle': 'Before battle',
    'StartBattleEnded': 'Start of battle ended',
    'StartOfBattleOrTransformed': 'Start of battle or transformed',
    'StartTurnOrBattle': 'Start of turn or battle',
    # Friend triggers
    'FriendFaints': 'Friend faints', 'FriendBought': 'Friend bought',
    'FriendSold': 'Friend sold', 'FriendHurt': 'Friend hurt',
    'FriendSummoned': 'Friend summoned', 'FriendAttacked': 'Friend attacks',
    'FriendAheadAttacks': 'Friend ahead attacks',
    'FriendAheadDied': 'Friend ahead faints',
    'FriendAheadHurt': 'Friend ahead hurt',
    'FriendAheadGainedHealth': 'Friend ahead gained health',
    'FriendBoughtWithTier1': 'Tier 1 friend bought',
    'FriendFlung': 'Friend flung',
    'FriendGainedAilment': 'Friend gained ailment',
    'FriendGainedAttack': 'Friend gained attack',
    'FriendGainedExperience': 'Friend gained experience',
    'FriendGainedHealth': 'Friend gained health',
    'FriendGainedPerk': 'Friend gained perk',
    'FriendGainedStrawberry': 'Friend gained strawberry',
    'FriendHurtOrFaint': 'Friend hurt or faint',
    'FriendJumped': 'Friend jumped or transformed',
    'FriendLeveledUp': 'Friend level-up',
    'FriendLostPerk': 'Friend lost perk',
    'FriendLostStrawberry': 'Friend lost strawberry',
    'FriendSoldWithLevelMax': 'Level 3 friend sold',
    'FriendSpendsAttack': 'Friend spends attack',
    'FriendSpendsHealth': 'Friend spends health',
    'FriendSpendsAttackOrHealth': 'Friend spends attack or health',
    'FriendSummonedInBattle': 'Friend summoned in battle',
    'FriendTransformed': 'Friend transformed',
    'FriendTransformedInBattle': 'Friend transformed in battle',
    'FriendWithSiblingSold': 'Friend with sibling sold',
    'CornEatenByFriend': 'Friend ate corncob',
    'ShopFoodEatenByFriend': 'Friend ate food',
    'ShopFoodEatenByFriendly': 'Friendly ate food',
    # Friendly triggers
    'FriendlyGainsPerk': 'Friendly gained perk',
    'FriendlyLeveledUp': 'Friendly level-up',
    'FriendlyAttacked': 'Friendly attacked',
    'FriendlyAbilityActivated': 'Friendly ability activated',
    'FriendlyGainedExperience': 'Friendly gained experience',
    'FriendlyGainedStrawberry': 'Friendly gained strawberry',
    'FriendlyToyBroke': 'Friendly toy broke',
    'FriendlyToySummoned': 'Friendly toy summoned',
    # Enemy triggers
    'EnemyFaint': 'Enemy faints', 'EnemyDied': 'Enemy faints',
    'EnemyDiedEarly': 'Enemy faints', 'EnemyHurt': 'Enemy hurt',
    'EnemySummoned': 'Enemy summoned', 'EnemyAttacked': 'Enemy attacked',
    'EnemyPushed': 'Enemy pushed',
    'EnemyGainedAilment': 'Enemy gained ailment',
    'EnemyAbilityActivated': 'Enemy ability activated',
    # Before variants (groundedsap simplifies BeforeFaint→Faint, BeforeSell→Sell)
    'BeforeFaint': 'Faint', 'BeforeSell': 'Sell',
    'BeforeAttack': 'Before attack', 'BeforeAttackEarly': 'Before attack early',
    'BeforeRoll': 'Before roll', 'BeforeTransform': 'Before transform',
    'BeforeFriendAttacks': 'Before friend attacks',
    'BeforeFriendSold': 'Sell friend',
    'BeforeFriendsFaints': 'Before friend faints',
    'BeforeFriendFaints': 'Before friend faints',
    'BeforeAdjacentFriendAttacked': 'Before adjacent friend attacked',
    'BeforeAdjacentFriendDies': 'Before adjacent friend dies',
    'BeforeAnyAttack': 'Before any attack',
    'BeforeFirstAttack': 'Before first attack',
    'BeforeNormalAttack': 'Before normal attack',
    'BeforePetFaints': 'Before pet faints',
    'BeforeBreak': 'Before break',
    # Combat
    'Hurt': 'Hurt', 'HurtEarly': 'Hurt early',
    'HurtOrFaint': 'Hurt or faint', 'HurtOrBeforeFaint': 'Hurt or before faint',
    'Faint': 'Faint', 'Knockout': 'Knock out', 'KnockoutEnemy': 'Knock out',
    'AfterAttack': 'After attack', 'AfterFirstAttack': 'After first attack',
    # Shop
    'ShopRolled': 'Roll', 'ShopUpgrade': 'Shop tier upgraded',
    'FoodBought': 'Buy food', 'GoldSpent': 'Gold spent',
    'ShopRewardStocked': 'Shop reward stocked', 'PetSold': 'Pet sold',
    # Gain triggers
    'GainMana': 'Gains mana', 'GainAttack': 'Gain attack',
    'GainHealth': 'Gain health', 'GainPerk': 'Gain perk',
    'GainExperience': 'Gain experience', 'GainAilment': 'Gain ailment',
    'GainPerkOrAilment': 'Gain perk or ailment',
    'LostAttack': 'Lost attack', 'PerkLost': 'Perk lost',
    'PetGainedAilment': 'Pet gained ailment', 'PetLostPerk': 'Pet lost perk',
    # Misc
    'AnyoneAttacks': 'Anyone attacks', 'AnyoneHurt': 'Anyone hurt',
    'AnyoneBehindHurt': 'Anyone behind hurt', 'AnyoneFlung': 'Pet flung',
    'AnyoneGainedAilment': 'Anyone gained ailment',
    'AnyoneJumped': 'Anyone jumped', 'AnyLeveledUp': 'Anyone leveled up',
    'AdjacentFriendHurt': 'Adjacent friend hurt',
    'AdjacentFriendAttacked': 'Adjacent friend attacked',
    'AllEnemiesFainted': 'All enemies fainted',
    'AllFriendsFainted': 'All friends fainted',
    'EmptyFrontSpace': 'Empty front space',
    'OtherAbilityActivated': 'Other ability activated',
    'OtherSummoned': 'Other summoned',
    'BeeSummoned': 'Bee summoned',
    'ToyBroke': 'Toy broke', 'ToySummoned': 'Toy summoned',
    'Break': 'Break', 'StockMinions': 'Stock minions',
    'SpendAttackBase': 'Spend attack', 'SpendHealthBase': 'Spend health',
}

# Known composite trigger display names (sub-trigger combination → label)
COMPOSITE_DISPLAY_NAMES = {
    'EnemyPushed or EnemyHurt': 'Enemy hurt or pushed',
    'EnemyHurt or EnemyPushed': 'Enemy hurt or pushed',
    'FriendJumped or FriendTransformed': 'Friend jumped or transformed',
    'FriendTransformed or FriendJumped': 'Friend jumped or transformed',
    'EnemySummoned or EnemyPushed': 'Enemy summoned or pushed',
    'EnemyPushed or EnemySummoned': 'Enemy summoned or pushed',
}

# Composite triggers where groundedsap uses "&" separator (dual-activation abilities)
COMPOSITE_AND_DISPLAY = {
    'Hurt or ThisSold': 'Hurt & Sell',
    'ThisSold or Hurt': 'Hurt & Sell',
    'BeforeFaint or ThisSold': 'Faint & Sell',
    'ThisSold or BeforeFaint': 'Faint & Sell',
    'BeforeFaint or BeforeSell': 'Faint & Sell',
    'BeforeSell or BeforeFaint': 'Faint & Sell',
    'Faint or BeforeSell': 'Faint & Sell',
    'BeforeSell or Faint': 'Faint & Sell',
    'ShopRolled or ThisSold': 'Roll & Sell',
    'ThisSold or ShopRolled': 'Roll & Sell',
    'ShopRolled or BeforeSell': 'Roll & Sell',
    'BeforeSell or ShopRolled': 'Roll & Sell',
    'ThisBought or ThisSold': 'Buy & Sell',
    'ThisSold or ThisBought': 'Buy & Sell',
    'ThisBought or BeforeSell': 'Buy & Sell',
    'BeforeSell or ThisBought': 'Buy & Sell',
}


# ============================================================
# Step 1: Cpp2IL
# ============================================================

def run_cpp2il(game_dir: str, work_dir: str, cpp2il_path: str):
    """Run Cpp2IL for ISIL and diffable-cs output."""
    isil_dir = os.path.join(work_dir, "cpp2il-isil")
    cs_dir = os.path.join(work_dir, "cpp2il-cs")

    log("Running Cpp2IL...")
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
# Step 1b: Il2CppDumper
# ============================================================

def run_il2cppdumper(game_dir: str, work_dir: str, il2cppdumper_path: str):
    """Run Il2CppDumper to produce script.json."""
    output_dir = os.path.join(work_dir, "il2cppdumper")
    os.makedirs(output_dir, exist_ok=True)

    dll_path = os.path.join(game_dir, "GameAssembly.dll")
    metadata_path = os.path.join(game_dir, "global-metadata.dat")
    if not os.path.exists(metadata_path):
        metadata_path = os.path.join(
            game_dir, "Super Auto Pets_Data/il2cpp_data/Metadata/global-metadata.dat"
        )

    log("Running Il2CppDumper...")
    result = subprocess.run(
        [il2cppdumper_path, dll_path, metadata_path, output_dir],
        capture_output=True, text=True, timeout=300,
    )
    if result.returncode != 0:
        log(f"Il2CppDumper failed: {result.stderr[:200]}")
        return None

    script_json = os.path.join(output_dir, "script.json")
    if os.path.exists(script_json):
        log("Il2CppDumper complete")
        return script_json

    log("WARNING: Il2CppDumper did not produce script.json")
    return None


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



# Pets whose abilities/archetypes are set through a Custom callback mechanism
# that our parser cannot trace (the callback checks the pet's enum at runtime
# and assigns data via a switch/if chain within a delegate invocation).
# Keyed by MinionEnum int value → {abilities: [...], archetypes: {role: [...]}}.
CALLBACK_PET_OVERRIDES = {
    364: {  # Ouroboros
        'abilities': ['OuroborosAbility'],
        'archetypes': {'producer': ['Roll', 'Faint']},
    },
    116: {  # Orca
        'abilities': ['OrcaAbility'],
        'archetypes': {'producer': ['Summon']},
    },
    741: {  # Deinocheirus
        'abilities': ['DeinocheirusAbility'],
        'archetypes': {'producer': ['Ailments']},
    },
}

# Trigger overrides for abilities that can't be traced through the standard
# AbilityConstants → lambda → CreateTrigger chain (set via Custom callbacks).
CALLBACK_TRIGGER_OVERRIDES = {
    'OuroborosAbility': 'Roll',
    'OrcaAbility': 'Faint',
}


# Hardcoded archetype values for pets that use RuntimeHelpers.InitializeArray
# to bulk-initialize archetype arrays from binary blobs in GameAssembly.dll.
# The blob addresses are IL2CPP metadata usage tokens that can't be resolved
# statically without parsing the full IL2CPP metadata chain.
# Keyed by blob virtual address → list of Archetype enum int values.
# Source: groundedsap.co.uk cross-referenced with ISIL SetArchetype* calls.
RUNTIME_INIT_ARCHETYPE_BLOBS = {
    0x183874468: [12, 3],         # Vervet: Toys, Summon
    0x183875F20: [27, 1],         # Dung Beetle: Disruption, Food
    0x1838772B0: [12],            # Ferret: Toys
    0x183873D48: [27],            # Hoopoe Bird: Disruption
    0x183873B80: [12],            # Gharial: Toys
    0x183875800: [12],            # Puppy: Toys
    0x183876808: [27],            # Lionfish: Disruption
    0x1838782B0: [5, 27],         # Woodpecker: Hurt, Disruption
    0x1838752A8: [12],            # Cuddle Toad: Toys
    0x183878640: [7, 27],         # Drop Bear: Guard, Disruption
    0x1838750E0: [17, 15],        # Fur-Bearing Trout: Mana, Perks
    0x1838742A0: [7, 15],         # Brain Cramp: Guard, Perks
    0x183877640: [12],            # Fairy: Toys
    0x183875470: [9, 7, 17],      # Hippocampus: Roll, Guard, Mana
    0x183873F10: [12],            # Questing Beast: Toys
}


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
        current_rollable = True
        pending_tier = None
        pending_archetype_values = []
        pending_blob_va = None  # tracks blob VA between SzArrayNew and RuntimeHelpers

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
                        # Track blob VA: Move rdx, [0xHEX] after SzArrayNew
                        if pending_blob_va == 'AWAITING' and dst == 'rdx':
                            va_m = re.match(r'\[0x([0-9a-fA-F]+)\]', src)
                            if va_m:
                                pending_blob_va = int(va_m.group(1), 16)
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
                    current_rollable = True

                elif method_name == 'MinionConstants.StartTokenGroup':
                    current_tier = 1
                    current_rollable = False

                elif method_name == '"SzArrayNew"':
                    pending_archetype_values = []
                    pending_blob_va = 'AWAITING'  # sentinel: next Move rdx,[0x...] is blob VA

                elif method_name == 'RuntimeHelpers.InitializeArray':
                    if isinstance(pending_blob_va, int) and pending_blob_va in RUNTIME_INIT_ARCHETYPE_BLOBS:
                        pending_archetype_values = list(RUNTIME_INIT_ARCHETYPE_BLOBS[pending_blob_va])
                    pending_blob_va = None

                elif method_name == 'MinionConstants.Create':
                    enum_val = arg_vals[0] if arg_vals and isinstance(arg_vals[0], int) else None
                    pet_name = enum_map.get(enum_val, f"Unknown_{enum_val}") if enum_val is not None else "Unknown"
                    current_pet = {
                        'enum': enum_val, 'name': pet_name, 'pack': pack_name,
                        'tier': current_tier, 'abilities': [], 'archetypes': {},
                        'rollable': current_rollable,
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

    # Apply hardcoded overrides for pets whose abilities are set through
    # untraceable callback mechanisms.
    pets_by_enum = {p['enum']: p for p in all_pets if p.get('enum') is not None}
    for enum_val, overrides in CALLBACK_PET_OVERRIDES.items():
        if enum_val in pets_by_enum:
            pet = pets_by_enum[enum_val]
            if not pet.get('abilities') and overrides.get('abilities'):
                pet['abilities'] = list(overrides['abilities'])
            if not pet.get('archetypes') and overrides.get('archetypes'):
                pet['archetypes'] = dict(overrides['archetypes'])

    # Fallback: for pets missing abilities/archetypes, parse raw assembly.
    # Cpp2IL's ISIL decompilation can truncate early in complex methods,
    # leaving some pets without abilities even though the data exists in the
    # raw disassembly section above the ISIL block.
    _fill_missing_from_assembly(mc_path, all_pets, ability_map, archetype_map)

    log(f"Extracted {len(all_pets)} pets from ISIL")
    return all_pets


# Known call addresses for raw assembly fallback parsing (x86-64 Windows PE)
_ASM_ADDRS = {
    'Create': '180820600',
    'AddAbility': '180481C10',
    'SetArchetypeProducer': '180482720',
    'SetArchetypeConsumer': '180482680',
    'SetArchetypeCustom': '180482640',
    'SetStats': '180482D10',
    'StartGroup': '180821C90',
    'StartTokenGroup': '180821F30',
}


def _fill_missing_from_assembly(mc_path, all_pets, ability_map, archetype_map):
    """Fill missing abilities/archetypes by parsing raw x86 assembly as fallback."""
    incomplete = {p['enum'] for p in all_pets if p.get('enum') is not None and not p.get('abilities')}
    if not incomplete:
        return
    log(f"  Assembly fallback: {len(incomplete)} pets with missing abilities")

    with open(mc_path) as f:
        content = f.read()

    methods = re.split(r'\nMethod: ', content)
    pets_by_enum = {p['enum']: p for p in all_pets if p.get('enum')}

    for m_text in methods[1:]:
        sig = m_text.split('\n')[0].strip()
        if not re.match(r'System\.Void Create\w+\(\)', sig):
            continue

        lines = m_text.split('\n')
        # Only process raw assembly lines (before ISIL: marker)
        asm_lines = []
        for line in lines:
            if line.strip() == 'ISIL:':
                break
            asm_lines.append(line)

        last_edx = None
        last_ecx = None
        current_enum = None
        pending_arch_vals = []

        for line in asm_lines:
            s = line.strip()

            # Track register values
            m = re.match(r'mov edx,([0-9A-Fa-f]+)h', s)
            if m:
                last_edx = int(m.group(1), 16)
                continue
            m = re.match(r'mov edx,(\d+)$', s)
            if m:
                last_edx = int(m.group(1))
                continue
            m = re.match(r'mov ecx,([0-9A-Fa-f]+)h', s)
            if m:
                last_ecx = int(m.group(1), 16)
                continue
            m = re.match(r'mov ecx,(\d+)$', s)
            if m:
                last_ecx = int(m.group(1))
                continue

            # Array element writes (archetypes)
            m = re.match(r'mov dword ptr \[rax\+([0-9A-Fa-f]+)h?\],(\d+)', s)
            if m:
                offset = int(m.group(1), 16) if 'h' in m.group(1) else int(m.group(1))
                val = int(m.group(2))
                if offset >= 0x20 and val < 100:
                    pending_arch_vals.append(val)
                continue

            if 'call' not in s:
                continue

            # MinionConstants.Create
            if _ASM_ADDRS['Create'] in s:
                if last_ecx in incomplete:
                    current_enum = last_ecx
                    pending_arch_vals = []
                else:
                    current_enum = None
                last_ecx = None

            # MinionTemplate.AddAbility
            elif _ASM_ADDRS['AddAbility'] in s and current_enum:
                if last_edx is not None and current_enum in pets_by_enum:
                    ab_name = ability_map.get(last_edx, f"Ability_{last_edx}")
                    if ab_name not in pets_by_enum[current_enum]['abilities']:
                        pets_by_enum[current_enum]['abilities'].append(ab_name)

            # SetArchetype*
            elif current_enum:
                for arch_type, addr in [('producer', _ASM_ADDRS['SetArchetypeProducer']),
                                        ('consumer', _ASM_ADDRS['SetArchetypeConsumer']),
                                        ('custom', _ASM_ADDRS['SetArchetypeCustom'])]:
                    if addr in s and pending_arch_vals:
                        pets_by_enum[current_enum]['archetypes'][arch_type] = [
                            archetype_map.get(v, f"Archetype_{v}") for v in pending_arch_vals
                        ]
                        pending_arch_vals = []
                        break

    filled = sum(1 for e in incomplete if pets_by_enum.get(e, {}).get('abilities'))
    if filled:
        log(f"  Assembly fallback filled {filled} pets with missing abilities")


# ============================================================
# Step 3: Standalone trigger extraction
# ============================================================

def extract_enum_to_metadata(isil_dir):
    """Parse AbilityConstants ISIL to map AbilityEnum → lambda metadata pointer address.

    In each CreatePackX method's ISIL section, the repeating pattern per ability is:
        Move r8, [0x183852898]               ← shared setup addr (ignore)
        Move rdx, <enum_int>                 ← AbilityEnum value
        Call 0x1811A24E0, rcx, rdx           ← enum constructor
        ... (delegate construction) ...
        Move r8, [0x<lambda_metadata_addr>]  ← lambda delegate pointer
        ... (more setup) ...
        Call AbilityConstants.CreateAbility, rcx, rdx, r8

    We capture rdx before the enum constructor call, and the last r8 memory load
    before the CreateAbility call.
    """
    ac_path = os.path.join(
        isil_dir, "IsilDump/Assembly-CSharp/Spacewood/Core/Models/Abilities/AbilityConstants.txt"
    )
    if not os.path.exists(ac_path):
        return {}

    with open(ac_path) as f:
        content = f.read()

    methods = content.split('Method: ')
    enum_to_mem = {}

    for method_block in methods:
        method_name = method_block.split('\n')[0].strip()
        if 'Create' not in method_name:
            continue

        # Parse only the ISIL section
        lines = method_block.split('\n')
        in_isil = False
        isil_lines = []
        for line in lines:
            s = line.strip()
            if s == 'ISIL:':
                in_isil = True
                continue
            if in_isil and re.match(r'\d+\s+\w', s):
                isil_lines.append(s)

        # Track state: last_rdx_int is the most recent integer loaded into rdx,
        # pending_enum is captured when we see the enum constructor call,
        # last_r8_mem is the most recent memory address loaded into r8.
        last_rdx_int = None
        pending_enum = None
        last_r8_mem = None

        for il in isil_lines:
            pm = re.match(r'(\d+)\s+(\w+)\s*(.*)', il)
            if not pm:
                continue
            opcode, args = pm.group(2), pm.group(3).strip()

            if opcode == 'Move':
                parts = args.split(',', 1)
                if len(parts) != 2:
                    continue
                dst, src = parts[0].strip(), parts[1].strip()

                # Track integer values written to rdx
                if dst == 'rdx':
                    try:
                        last_rdx_int = int(src)
                    except ValueError:
                        if src.startswith('0x'):
                            try:
                                last_rdx_int = int(src, 16)
                            except ValueError:
                                last_rdx_int = None
                        else:
                            last_rdx_int = None

                # Track memory addresses loaded into r8
                if dst == 'r8':
                    mem_m = re.match(r'\[0x([0-9A-Fa-f]+)\]', src)
                    if mem_m:
                        last_r8_mem = int(mem_m.group(1), 16)

            elif opcode == 'Call':
                call_target = args.split(',')[0].strip()

                # The enum constructor call: captures the enum value from rdx
                if call_target == '0x1811A24E0':
                    if last_rdx_int is not None and last_rdx_int > 0:
                        pending_enum = last_rdx_int

                # CreateAbility: emit the mapping and reset
                elif call_target == 'AbilityConstants.CreateAbility':
                    if pending_enum is not None and last_r8_mem is not None:
                        enum_to_mem[pending_enum] = last_r8_mem
                    pending_enum = None
                    last_r8_mem = None

    return enum_to_mem


def build_metadata_to_lambda_map(script_json_path):
    """Parse Il2CppDumper script.json ScriptMetadataMethod entries to map
    lambda metadata addresses → named lambda methods.

    Returns {metadata_addr_int: "<CreatePackX>b__N_M"} for AbilityConstants lambdas.
    """
    with open(script_json_path) as f:
        script = json.load(f)

    mem_to_lambda = {}
    for entry in script.get('ScriptMetadataMethod', []):
        name = entry.get('Name', '')
        if 'AbilityConstants.<>c.<' not in name:
            continue
        addr = 0x180000000 + entry['Address']
        m = re.search(r'<(Create\w+)>b__(\d+)_(\d+)', name)
        if m:
            clean = f"<{m.group(1)}>b__{m.group(2)}_{m.group(3)}"
            mem_to_lambda[addr] = clean

    return mem_to_lambda


def _extract_count_before_call(instructions, call_idx, call_name):
    """Extract the integer count argument before a SetTriggerCharged/SetCharges call.

    For SetTriggerCharged: count is in r8 (3rd arg).
    For SetCharges/SetChargesOnce: count is in rdx (2nd arg).

    Scans forward through the ~20 instructions before the call, tracking register
    values so that LoadAddress [base+offset] can resolve when base was set earlier.

    Returns the count as an int, or None if not found.
    """
    if call_name == 'Ability.SetTriggerCharged':
        target_reg = 'r8'
    elif call_name in ('Ability.SetCharges', 'Ability.SetChargesOnce'):
        target_reg = 'rdx'
    else:
        return None

    # Forward pass through the window before the call to track register values
    start = max(call_idx - 20, 0)
    reg_vals = {}
    for i in range(start, call_idx):
        line = instructions[i]

        # "Move <reg>, <val>" — literal integer
        mv = re.match(r'\s*\d+\s+Move\s+(\w+),\s+(-?\d+)\s*$', line)
        if mv:
            reg, val = mv.group(1), int(mv.group(2))
            reg_vals[reg] = val
            continue

        # "LoadAddress <reg>, [<base>+<offset>]" — base+offset
        la = re.match(r'\s*\d+\s+LoadAddress\s+(\w+),\s+\[(\w+)\+(\d+)\]', line)
        if la:
            reg, base, offset = la.group(1), la.group(2), int(la.group(3))
            base_val = reg_vals.get(base)
            if base_val is not None and base_val == 0:
                reg_vals[reg] = offset
            continue

        # "LoadAddress <reg>, [<base>-<offset>]" — base-offset
        la_sub = re.match(r'\s*\d+\s+LoadAddress\s+(\w+),\s+\[(\w+)-(\d+)\]', line)
        if la_sub:
            reg, base, offset = la_sub.group(1), la_sub.group(2), int(la_sub.group(3))
            base_val = reg_vals.get(base)
            if base_val is not None:
                reg_vals[reg] = base_val - offset
            continue

    count = reg_vals.get(target_reg)
    if count is not None and 2 <= count <= 20:
        return count
    return None


def build_lambda_to_trigger_map(isil_dir):
    """Parse AbilityConstants nested class ISIL to map lambda methods → trigger info.

    Each lambda's ISIL section contains symbolic calls like:
        Call CreateTrigger.StartBattle, rcx
        Call Ability.SetTrigger, rcx, rdx

    We track the SetTrigger target, handling Composite triggers that combine sub-triggers.
    For SetTriggerCharged/SetCharges calls, we also extract the count argument.

    Returns {lambda_short_name: {"trigger": raw_name, "count": int_or_None, "about": str_or_None}}.
    """
    nested_path = os.path.join(
        isil_dir,
        "IsilDump/Assembly-CSharp/Spacewood/Core/Models/Abilities/AbilityConstants_NestedType___c.txt",
    )
    if not os.path.exists(nested_path):
        return {}

    with open(nested_path) as f:
        content = f.read()

    methods = content.split('Method: ')
    lambda_triggers = {}

    for method_block in methods[1:]:
        method_name = method_block.split('\n')[0].strip()
        m = re.search(r'<(Create\w+)>b__(\d+)_(\d+)', method_name)
        if not m:
            continue
        clean = f"<{m.group(1)}>b__{m.group(2)}_{m.group(3)}"

        lines = method_block.split('\n')

        # Extract the first string literal that looks like an ability description.
        # These pets set descriptions via Ability.SetAbout with a hardcoded string
        # instead of using the localization system.
        # Pattern: Move rsi, "description text" (or Move rcx, "...") near SetAbout.
        about_text = None
        for line in lines:
            if 'SetAbout' in line:
                break
            sm = re.search(r'Move \w+, "([^"]+)"', line)
            if sm:
                candidate = sm.group(1)
                # Filter: must look like a description (not a method name or short label)
                if len(candidate) > 15 and not candidate.startswith('il2cpp'):
                    about_text = candidate

        # Collect ISIL calls with their line indices for count extraction
        isil_calls = []  # (line_index, call_name)
        for idx, line in enumerate(lines):
            cm = re.search(r'\d+\s+Call\s+(\S+)', line)
            if cm:
                isil_calls.append((idx, cm.group(1).rstrip(',')))

        # Walk calls tracking trigger state.
        # We track both a plain trigger (from SetTrigger) and a charged trigger
        # (from SetTriggerCharged/SetCharges/SetChargesOnce). The charged trigger
        # with a count takes priority for display since it represents the
        # user-facing activation condition (e.g. "Two friends faint").
        trigger_stack = []
        main_trigger = None
        charged_trigger = None
        trigger_count = None

        for line_idx, call in isil_calls:
            if call.startswith('CreateTrigger.'):
                trigger_name = call.replace('CreateTrigger.', '')
                if trigger_name == 'Composite':
                    if len(trigger_stack) >= 2:
                        composite_label = f"COMPOSITE:{trigger_stack[-2]} or {trigger_stack[-1]}"
                        trigger_stack = trigger_stack[:-2]
                        trigger_stack.append(composite_label)
                else:
                    trigger_stack.append(trigger_name)
            elif call == 'Ability.SetTrigger':
                if trigger_stack:
                    main_trigger = trigger_stack[-1]
                    trigger_stack = trigger_stack[:-1]
            elif call in ('Ability.SetTriggerCharged', 'Ability.SetCharges', 'Ability.SetChargesOnce'):
                count = _extract_count_before_call(lines, line_idx, call)
                if trigger_stack:
                    charged_trigger = trigger_stack[-1]
                    trigger_count = count
                    trigger_stack = trigger_stack[:-1]
            elif call == 'Ability.SetPower':
                if trigger_stack:
                    trigger_stack = trigger_stack[:-1]

        # Prefer charged trigger with count over plain trigger
        if charged_trigger and trigger_count:
            final_trigger = charged_trigger
        elif main_trigger:
            final_trigger = main_trigger
        elif trigger_stack:
            final_trigger = trigger_stack[0]
        else:
            final_trigger = None

        if final_trigger or about_text:
            lambda_triggers[clean] = {
                "trigger": final_trigger,
                "count": trigger_count,
                "about": about_text,
            }

    return lambda_triggers


# Count-qualified trigger display name generation
COUNT_WORDS = {2: "Two", 3: "Three", 4: "Four", 5: "Five", 6: "Six", 7: "Seven",
               8: "Eight", 9: "Nine", 10: "Ten"}

# Triggers that use "N <plural>" pattern
COUNT_TRIGGER_PLURALS = {
    'FriendFaints': 'friends faint',
    'FriendHurt': 'friends hurt',
    'FriendAttacked': 'friend attacks',
    'FriendlyAttacked': 'friendly attacks',
    'EnemyAttacked': 'enemy attacks',
    'EnemyFaint': 'enemies faint',
    'EnemyDied': 'enemies faint',
    'EnemyDiedEarly': 'enemies faint',
    'EnemyHurt': 'enemies hurt',
}

# Triggers with special count-qualified patterns
SPECIAL_COUNT_PATTERNS = {
    'FoodEatenByThis': 'Eats {w} food',
    'ShopFoodEatenByThis': 'Eats {w} food',
    'AppleEatenByThis': 'Eats {w} apple',
    'ShopRolled': 'Roll {n} times',
    'GoldSpent': 'Spend {n} gold',
}


def normalize_trigger_name(raw, count=None):
    """Convert a raw CreateTrigger name to a display label, with optional count qualifier."""
    if raw is None:
        return None
    if raw.startswith('COMPOSITE:'):
        parts = raw.replace('COMPOSITE:', '')
        if parts in COMPOSITE_AND_DISPLAY:
            return COMPOSITE_AND_DISPLAY[parts]
        if parts in COMPOSITE_DISPLAY_NAMES:
            return COMPOSITE_DISPLAY_NAMES[parts]
        sub_triggers = parts.split(' or ')
        display_parts = [TRIGGER_DISPLAY_NAMES.get(t, t) for t in sub_triggers]
        return ' & '.join(display_parts)

    # Count-qualified triggers
    if count is not None and count >= 2:
        word = COUNT_WORDS.get(count, str(count))
        if raw in SPECIAL_COUNT_PATTERNS:
            return SPECIAL_COUNT_PATTERNS[raw].format(w=word.lower(), n=count)
        if raw in COUNT_TRIGGER_PLURALS:
            return f"{word} {COUNT_TRIGGER_PLURALS[raw]}"

    return TRIGGER_DISPLAY_NAMES.get(raw, raw)


def extract_triggers_standalone(isil_dir, script_json_path, ability_enum_map):
    """Build a standalone trigger map and hardcoded description map.

    Chain: AbilityEnum → metadata_addr → lambda_name → CreateTrigger.X → display name.
    Also extracts SetAbout string literals for abilities that hardcode descriptions.

    Returns (trigger_map, hardcoded_descriptions).
    """
    log("Extracting standalone triggers...")

    enum_to_mem = extract_enum_to_metadata(isil_dir)
    log(f"  AbilityEnum → metadata addr: {len(enum_to_mem)} mappings")

    mem_to_lambda = build_metadata_to_lambda_map(script_json_path)
    log(f"  Metadata addr → lambda name: {len(mem_to_lambda)} mappings")

    lambda_to_trigger = build_lambda_to_trigger_map(isil_dir)
    log(f"  Lambda → trigger: {len(lambda_to_trigger)} mappings")

    # Chain the three maps
    trigger_map = {}
    hardcoded_descs = {}
    matched = 0
    for enum_int, mem_addr in enum_to_mem.items():
        ability_name = ability_enum_map.get(enum_int)
        if not ability_name:
            continue

        lambda_name = mem_to_lambda.get(mem_addr)
        if not lambda_name:
            continue

        trigger_info = lambda_to_trigger.get(lambda_name)
        if not trigger_info:
            continue

        raw_trigger = trigger_info["trigger"]
        count = trigger_info["count"]
        about = trigger_info.get("about")

        display = normalize_trigger_name(raw_trigger, count=count)
        if display:
            trigger_map[ability_name] = display
            matched += 1

        if about:
            hardcoded_descs[ability_name] = about

    log(f"  Standalone triggers resolved: {matched}")
    log(f"  Hardcoded descriptions found: {len(hardcoded_descs)}")
    return trigger_map, hardcoded_descs


# ============================================================
# Step 4: Localization
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

    # SharedTableData (key_name → key_id) — merge ALL MonoBehaviour objects
    env = UnityPy.load(os.path.join(bundle_dir, "localization-assets-shared_assets_all.bundle"))
    raw_shared = {}
    for obj in env.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.get_raw_data()
            if len(data) < 1000:
                continue
            start = find_table_start(data, 60, 150)
            if start is not None:
                parsed = parse_binary_table(data, start, None)
                raw_shared.update(parsed)

    # SharedTableData: key_name → key_id (reversed from normal table)
    key_name_to_id = {text: kid for kid, text in raw_shared.items()}

    # English StringTable (key_id → text) — merge ALL MonoBehaviour objects
    env2 = UnityPy.load(os.path.join(bundle_dir, "localization-string-tables-english_assets_all.bundle"))
    id_to_text = {}
    for obj in env2.objects:
        if obj.type.name == "MonoBehaviour":
            data = obj.get_raw_data()
            if len(data) < 1000:
                continue
            start = find_table_start(data, 60, 150)
            if start is not None:
                parsed = parse_binary_table(data, start, None)
                id_to_text.update(parsed)

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

    # Spell descriptions (Spell.X.About pattern — no level numbers)
    spell_descriptions = {}
    for key_name, key_id in key_name_to_id.items():
        m = re.match(r'Spell\.(\w+)\.(About|FinePrint)', key_name)
        if not m or key_id not in id_to_text:
            continue
        spell_name, field = m.group(1), m.group(2).lower()
        text = clean_desc(id_to_text[key_id])
        spell_descriptions.setdefault(spell_name, {})[field] = text

    for fields in spell_descriptions.values():
        if 'fineprint' in fields and 'about' in fields:
            fields['about'] = f"{fields['about']} ({fields['fineprint']})"

    # Perk descriptions (Perk.X.About pattern)
    perk_descriptions = {}
    for key_name, key_id in key_name_to_id.items():
        m = re.match(r'Perk\.(\w+)\.(About|FinePrint)', key_name)
        if not m or key_id not in id_to_text:
            continue
        perk_name, field = m.group(1), m.group(2).lower()
        text = clean_desc(id_to_text[key_id])
        perk_descriptions.setdefault(perk_name, {})[field] = text

    for fields in perk_descriptions.values():
        if 'fineprint' in fields and 'about' in fields:
            fields['about'] = f"{fields['about']} ({fields['fineprint']})"

    # Display names for pets, spells, and perks
    display_names = {}
    for key_name, key_id in key_name_to_id.items():
        # Minion.X.Name, Spell.X.Name, Perk.X.Name
        m = re.match(r'(?:Minion|Spell|Perk)\.(\w+)\.Name', key_name)
        if m and key_id in id_to_text:
            display_names[m.group(1)] = id_to_text[key_id]

    log(f"  Abilities: {len(ability_descriptions)}, Spell descs: {len(spell_descriptions)}, "
        f"Perk descs: {len(perk_descriptions)}, Display names: {len(display_names)}")
    return ability_descriptions, spell_descriptions, perk_descriptions, display_names


# ============================================================
# Step 5: Assemble
# ============================================================

def assemble_json(pets, ability_descriptions, display_names, trigger_map, standalone_triggers):
    """Assemble the final pets.json."""
    log("Assembling final JSON...")

    # Merge triggers: standalone first, then fallback to pre-built map
    merged_triggers = dict(trigger_map)
    merged_triggers.update(CALLBACK_TRIGGER_OVERRIDES)
    merged_triggers.update(standalone_triggers)

    output = []
    for p in pets:
        name = display_names.get(p['name'], p['name'])
        entry = {
            "name": name,
            "id": p['name'],
            "enumId": p['enum'],
            "pack": p.get('pack'),
            "tier": p.get('tier'),
            "rollable": p.get('rollable', True),
            "mode": classify_mode(p.get('pack', '')),
        }

        if p.get('attack') is not None:
            entry["attack"] = p['attack']
        if p.get('health') is not None:
            entry["health"] = p['health']

        if p.get('abilities'):
            resolved = []
            for ab_name in p['abilities']:
                ab_data = {}
                if ab_name in merged_triggers:
                    ab_data["trigger"] = merged_triggers[ab_name]
                if ab_name in ability_descriptions:
                    for lvl in sorted(ability_descriptions[ab_name].keys()):
                        about = ability_descriptions[ab_name][lvl].get('about', '')
                        if about:
                            ab_data[f"level{lvl}"] = about
                if ab_data:
                    resolved.append(ab_data)
            if resolved:
                entry["abilities"] = resolved
        elif not p.get('rollable', True):
            # Non-rollable pets (tokens) with no abilities get a default
            entry["abilities"] = [{"level1": "No ability."}]

        archetypes = {k: v for k, v in p.get('archetypes', {}).items() if v}
        if archetypes:
            entry["archetypes"] = archetypes

        output.append(entry)

    return output


def main():
    parser = argparse.ArgumentParser(description="SAP Data Extraction Pipeline")
    parser.add_argument("--game-dir", required=True, help="Path to game files directory")
    parser.add_argument("--output", default="pets.json", help="Output pets JSON file")
    parser.add_argument("--output-spells", default=None, help="Output spells/food JSON file")
    parser.add_argument("--output-perks", default=None, help="Output perks JSON file")
    parser.add_argument("--cpp2il", default=None, help="Path to Cpp2IL binary")
    parser.add_argument("--il2cppdumper", default=None, help="Path to Il2CppDumper binary")
    parser.add_argument("--script-json", default=None, help="Pre-existing Il2CppDumper script.json")
    parser.add_argument("--work-dir", default=None, help="Working directory for intermediate files")
    parser.add_argument("--trigger-map", default=None, help="Fallback trigger map JSON (from groundedsap)")
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

    # Step 1b: Il2CppDumper (for standalone trigger extraction)
    script_json_path = args.script_json
    if not script_json_path and args.il2cppdumper:
        script_json_path = run_il2cppdumper(args.game_dir, work_dir, args.il2cppdumper)

    # Step 2: Parse ISIL
    pets = extract_pets_from_isil(isil_dir, cs_dir)

    # Step 3: Standalone trigger extraction
    base_cs = os.path.join(cs_dir, "DiffableCs/Assembly-CSharp/Spacewood")
    ability_enum_map = parse_cs_enum(os.path.join(base_cs, "Core/Models/Abilities/AbilityEnum.cs"))
    standalone_triggers = {}
    hardcoded_descs = {}
    if script_json_path and os.path.exists(script_json_path):
        standalone_triggers, hardcoded_descs = extract_triggers_standalone(
            isil_dir, script_json_path, ability_enum_map
        )
    else:
        log("WARNING: No script.json available — standalone trigger extraction skipped")
        log("  Provide --script-json or --il2cppdumper for standalone triggers")

    # Step 4: Localization
    ability_descriptions, spell_descriptions, perk_descriptions, display_names = extract_localization(args.game_dir)

    # Merge hardcoded descriptions as fallback for abilities not in localization
    for ab_name, about in hardcoded_descs.items():
        if ab_name not in ability_descriptions:
            ability_descriptions[ab_name] = {1: {'about': about}}

    # Step 5: Fallback trigger map
    trigger_map = {}
    if os.path.exists(trigger_map_path):
        log(f"Loading fallback trigger map from {trigger_map_path}")
        with open(trigger_map_path) as f:
            trigger_map = json.load(f)
    else:
        log(f"No fallback trigger map at {trigger_map_path}")

    # Step 6: Assemble pets
    output = assemble_json(pets, ability_descriptions, display_names, trigger_map, standalone_triggers)

    with open(args.output, 'w') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    with_stats = sum(1 for p in output if 'attack' in p)
    with_abilities = sum(1 for p in output if p.get('abilities'))
    with_triggers = sum(1 for p in output
                        if p.get('abilities') and 'trigger' in p['abilities'][0])
    with_rollable_false = sum(1 for p in output if not p.get('rollable', True))

    # Step 7: Extract and assemble spells/food
    if args.output_spells:
        from extract_spells import extract_spells_from_isil, assemble_spells_json
        spells_raw = extract_spells_from_isil(isil_dir, cs_dir)
        log(f"Extracted {len(spells_raw)} spells from ISIL")

        spells_output = assemble_spells_json(spells_raw, spell_descriptions, display_names)

        # Add mode classification
        for s in spells_output:
            s['mode'] = classify_mode(s.get('pack', ''))

        with open(args.output_spells, 'w') as f:
            json.dump(spells_output, f, indent=2, ensure_ascii=False)

        spell_rollable = sum(1 for s in spells_output if s.get('rollable'))
        spell_non_rollable = sum(1 for s in spells_output if not s.get('rollable'))
        log(f"Spells: {len(spells_output)} → {args.output_spells}")
        log(f"  Rollable (shop food): {spell_rollable}, Non-rollable (toys/perks/tokens): {spell_non_rollable}")

    # Step 8: Extract and assemble perks
    if args.output_perks:
        from extract_perks import extract_perks_from_isil, assemble_perks_json
        perks_raw = extract_perks_from_isil(isil_dir, cs_dir)
        log(f"Extracted {len(perks_raw)} perks from ISIL")

        perks_output = assemble_perks_json(perks_raw, perk_descriptions, display_names, ability_descriptions)

        # Add mode classification
        for p in perks_output:
            p['mode'] = classify_mode(p.get('source', ''))

        with open(args.output_perks, 'w') as f:
            json.dump(perks_output, f, indent=2, ensure_ascii=False)

        log(f"Perks: {len(perks_output)} → {args.output_perks}")

    log(f"Done! {len(output)} pets → {args.output}")
    log(f"  With stats: {with_stats}")
    log(f"  With abilities: {with_abilities}")
    log(f"  With triggers: {with_triggers} ({len(standalone_triggers)} standalone, rest from fallback map)")
    log(f"  Non-rollable (tokens): {with_rollable_false}")


if __name__ == "__main__":
    main()
