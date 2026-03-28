# Trigger Extraction Status — Deep Dive Results

## Architecture Discovery

The SAP ability system has TWO trigger layers:
1. **Activation trigger** — when the ability activates (Sell, Buy, Faint, etc.) — this is what the UI shows
2. **Effect trigger** — when the effect applies (Start of battle, etc.) — internal to the effect chain

The lambda code we decompiled sets the **effect trigger**, NOT the activation trigger.

Example: DuckAbility lambda calls SetTrigger(StartBattle=4), but Duck's UI trigger is "Sell".
MosquitoAbility lambda calls SetTrigger via FUN_1807c0330 (a different pattern), and Mosquito's UI trigger is "Start of battle".

## What Works
- **Method pointer resolution**: 828/848 abilities → exact lambda function addresses via PE CodeGenModule
- **Ghidra decompilation**: 18,657 functions decompiled covering the full ability code range
- **Factory → trigger enum**: 36 factory functions mapped to TriggerEnum values
- **Rosetta Stone join**: 509 abilities with 100% accurate triggers (using groundedsap)

## What Doesn't Work
- **Standalone activation trigger extraction**: The activation trigger isn't set in the lambda. It's set through a mechanism we haven't identified — possibly:
  - In the `CreateAbility` function via the AbilityCollection
  - Through the `StartProcessor` mechanism
  - Through the ability's metadata/enum registration
  - Through a lookup table we haven't found

## Next Steps for Full Independence
1. Decompile `CreateAbility` (FUN_18070FA40) fully and trace where it reads the trigger
2. Check if AbilityCollection stores trigger info at creation time
3. Check if the trigger is encoded in the AbilityEnum metadata
4. Alternatively: build a trigger lookup table from the current game version (using groundedsap), then for future versions, only the DELTA needs manual checking

## Practical Recommendation
For the pipeline, use the Rosetta Stone trigger map. When a new game version drops:
1. Run stat/tier/archetype extraction (fully automated, 97-99% accurate)
2. Run description extraction (automated, 71% match)
3. For triggers: apply the existing trigger map. New abilities (not in the map) need manual addition or community data.
4. Most game patches change stats/descriptions, not triggers. A trigger rarely changes.
