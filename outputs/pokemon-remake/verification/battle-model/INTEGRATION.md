# Charmander v2 battle integration

`app/battle.js` now lazily loads the SHA-verified v2 candidate for the first opponent with species ID 4. Other battlers retain live source sprite cutouts. The original cutout remains visible while loading and after a load failure, whose reason is exposed as `battle.report.modelError`.

The model keeps its original armature hierarchy and skin bindings. An outer placement group gives it a 3.5-unit height, grounds it at Y -0.04 on the opponent platform at X 4 / Z -3, and faces the player platform at X -4 / Z 3. Presentation offsets come directly from each source sprite's current x2/y2 fields, without capturing a possibly animated initial position. Source visibility and absence of opaque pixels hide the model. Source affine deformation, palette flashes, and separate attack effects remain incomplete for the 3D candidate and are explicitly listed in the runtime report.

Only the reviewed `idle` plays, driven exclusively by `state.frame / 59.7275`. The model introduces no gameplay clock or attack animation. The HUD identifies the mixed 3D candidate/source-sprite presentation, and the runtime report retains creator attribution and CC BY-NC 4.0.

## Verification

- Existing `verification/battle/check-battle.mjs`: **13 checks passed**, including 1,564 original attack replay frames, source pixel fidelity, source state immutability, original menus, and final HP `[11,14]`.
- `integration-runner.cjs`: **12 actual WebGL checks passed**, including exact v2 hash/clip, species restriction, fixed platform anchor, source-clock idle, pause, reset, source x2/y2 mapping, source hide/show, and an actual forced HTTP 503 load failure preserving the cutout.
- `integrated-v2-battle.png` was visually inspected: the candidate occupies the opponent platform, faces the player, leaves the source Bulbasaur visible, and does not overlap the battle controls or health cards.
- The isolated scene rendered 6 draw calls and 14,594 triangles. These are scene counts, not a whole-app performance claim.

The integration harness reads the user's local ROM through the existing verification preload. Its movement/hide fixture alters a copied sprite-memory read only, never core memory. `integration-results.json` contains the detailed checks. Final packaged-app launch and controls remain the main task owner's verification responsibility.

Model SHA256: `ad78d6f71b421d5f3ce534806b2f816d160647be282276152dca03a25c6ce7e6`.

This is a playable candidate integration, not photoreal/source-identity acceptance. The solid glowing tail tip, coarse base-color scale pattern, and stylized facial design remain documented in `verification/charmander-v2/REVIEW.md`.
