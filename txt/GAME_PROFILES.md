# Game profiles

A game profile sets a scenario's victory ratios and winter behavior. Choose it
in **New Scenario** or **Scenario Settings → Game Profile → Edit Game Profile**.
Importing an earlier-game scenario selects its source profile automatically.

## Settings

| Setting | Effect |
| --- | --- |
| Major victory ratio | Winning score must be at least this percentage of the losing score. Default: 200%. |
| Minor victory ratio | Winning score must be greater than this percentage of the losing score. Default: 125%. |
| Winter model | D-Day, Stalingrad, V4V or V4V Velikiye Luki ground-condition behavior. |
| Snow and rain coefficients | Accumulation from precipitation. |
| Melt and drying coefficients | How quickly snow and wetness decline. |
| Ice settings | Growth divisor, crossing threshold and crossing adjustment. |

Use **Restore Defaults** to return to the selected profile's values. Profile
edits support Undo/Redo, Save and Save As. Initial snow, ice and wetness are
set separately under **Scenario Settings → Weather** and stay in place when
you change profiles.

Ground quantities use thousandths. Stalingrad and V4V winter calculations are
adapted to this precision, so accumulation and threshold behavior can differ
slightly from the original games. Operation Crusader uses the D-Day winter
model. All profiles start with the 200%/125% victory ratios above.

V4V imports calculate initial ground conditions from the source weather before
the scenario starts. Stalingrad imports retain their saved initial conditions.

## Terrain and other rules

**Edit Terrain Rules** controls movement costs and terrain combat modifiers;
see [terrain rules](TERRAIN_RULES.md). Those values start with D-Day defaults
and retain your overrides when you change the game profile.

D-Day's combat, pathfinding, supply and scenario-specific behavior govern play.
Profiles supply the selected victory and winter settings within that engine.
Review **File → Conversion Notes** for the source scenario's adaptations,
then playtest its balance with your chosen rules. See the
[WaW](WAW_CONVERSION.md) and [V4V](V4V_CONVERSION.md) conversion guides.

## Saving and playing

Save and Save As keep the profile with the scenario's editing assets. Imported
documents also retain their source records. Keep the `assets` folder with the
SCN when moving an editing document.

**Export for DOS** includes the runtime rules in the scenario's `.REZ` file.
Install the matching **SCN, REZ and AI** together and play with
`INVADE-PATCHED.EXE`, installed as `INVADE.EXE`.

Keep the exported REZ with any saved game: Resume reads its rules. Changing that
file changes the rules used by the resumed game. Opening a DOS export in the
editor also reads its rules from the matching REZ.
