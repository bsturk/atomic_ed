# Terrain movement and combat rules

Open **Scenario Settings → Game Profile → Edit Terrain Rules** to customize
terrain behavior for the current scenario. Select a terrain, edit its values,
and click **Apply**. Pending changes stay with each terrain while you browse.
**Restore This Terrain** and **Restore All D-Day Defaults** reset the values.

## Movement costs

| Control | Meaning | Range |
| --- | --- | --- |
| Dry / Light mud | Movement points for a step through uniform terrain, by movement class | 0–10 MP in steps of 0.02 |
| Dirt road / Paved road / Railroad | Movement points per step in Strategic mode, by movement class | 0.002–10 MP in steps of 0.002 |

A terrain cost of **zero means blocked**. Water terrain and Fixed movement
remain blocked. A step between different terrain types averages their movement
contributions; the game's crossing and visibility modifiers then apply.

The controls cover twelve movement classes and fourteen playable terrain codes.
Weather selects the applicable ground state during play.

## Combat modifiers

| Control | Meaning |
| --- | --- |
| Defense | Terrain's defensive strength multiplier |
| Anti-armor defense | Terrain's anti-armor defensive multiplier |
| Bombardment received | Percentage of bombardment reaching the target before fortification protection |

Each accepts **0–400%**. A value of 100% keeps the incoming value unchanged at
that calculation stage. Lower bombardment percentages provide more protection.
The game's minimum-damage rules also apply, including when this value is zero.

Supply, fatigue, fortifications, crossings and other combat factors continue
to contribute to the final result. The AI uses the authored movement costs
and adjusts its terrain ratings for changed combat modifiers.

## Pairing rules with artwork

Import or select artwork on **Map** or **Terrain Reference**, then edit the
rules for its assigned terrain code. All six artwork variants of that code
share the same rules. Each code can have its own movement values, including
Clear and Bunker.

Cross-game artwork uses these D-Day terrain slots. The assigned slot also
retains its terrain name and special engine behavior. Use the preview and
terrain description to choose a suitable slot for custom artwork.

## Saving and playing

Apply creates one Undo/Redo step. Save and Save As retain the settings with
the editing document. **Export for DOS** includes them in the matching REZ.
Use the patched executable and copy the **SCN, REZ and AI** together.

Keep the matching REZ when resuming a saved game. Editing its terrain rules
affects subsequent play. See [installation](../game/waw/README.md) and
[game profiles](GAME_PROFILES.md).
