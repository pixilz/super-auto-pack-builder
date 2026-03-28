# R4: Ability Description Validation

## Results
- Compared: 503 abilities (L1 text)
- Match: 382 (75.9%)
- Mismatch: 121
- Missing: 14 (no localization entry found)

## Mismatch Categories
1. **Icon placeholders not stripped** — `{HealthIcon}`, `{DamageIcon}`, `{ScaredIcon}`, `{PerkIcon}` remain in our text. Easy fix: expand the strip list.
2. **Template params `{0}` unresolved** — e.g., "per {0} friend" should be "per Faint friend". The param value comes from `AboutArgs` in the Ability config code. Needs Ghidra or groundedsap mapping.
3. **"Works N times per turn" missing** — This comes from `TriggerLimit`/`Repeat` fields, not the About text. Set in native code.
4. **Condition prefixes missing** — e.g., "If turn number is even" or "If you have a toy". These are from `CustomNote` or conditional logic in the ability setup.

## Fixes for Pipeline
- Strip ALL `{XxxIcon}` patterns (regex `\{[A-Za-z]+Icon\}`)
- `{0}` params: build a lookup from groundedsap (ability→param value), or extract from Ability.AboutArgs in native code
- "Works N times": extract from Ability.TriggerLimit/Repeat (in native code) or supplement from groundedsap
- Condition prefixes: extract from Ability.CustomNote or supplement from groundedsap
