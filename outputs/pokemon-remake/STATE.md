# Pokémon FireRed remake — playable prototype, photoreal work incomplete

## Current delivery

App rebuilt, tested and reopened after the 30-degree return-on-release camera revision. Launch Workbench.command or `npm start --prefix outputs/pokemon-remake/app` from the repository. Default Explore town checkpoint is post-starter-ready: native frame 39079 outside Oak’s lab at (16,14), starter obtained and doorway animation completed. Existing progress file is preserved.

The latest user revision supersedes the fully locked camera: default north-up orthographic angle is now 30°. Pointer drag temporarily orbits, scroll temporarily zooms, and release eases back to the default angle/zoom. Outdoor tracking uses original player position and map bounds, interiors use fixed room framing, battles retain a separate fixed camera. Asset inspection keeps a separate free camera. Default tracking stays tied to the source; only pointer-release return uses render-time easing. There is no gameplay overview toggle.

Visible controls: Explore town, Battle, Pause, Sound, Save progress, Resume save, Original view. Arrows move/select; X confirms, Z cancels, Enter opens the native menu, P pauses. Unsupported scenes/menus use labeled live original graphics so gameplay continues. Persistent quicksave: work/pokemon/player-progress.json; smoke uses a separate verification-save.json.

## Verified scope

A 20-second silent recording of the actual 3D Bulbasaur versus Charmander fight is available at `verification/starter-battle-runtime/fight-preview.mp4`. It includes source-driven Tackle and Scratch, with the original menus and HP changes. Launch directly into the first battle with `npm start --prefix outputs/pokemon-remake/app -- --battle`.

Latest smoke passed 34 integration checks and 11 actual Electron mouse/keyboard/button checks. Covered: source simulation and deterministic restore, coordinates and doors, printer dialog, battle menus/HP/damage, pause/reset, rigged player idle/walk, native Pallet-to-Route1 replay, screen direction alignment, fixed camera across transitions, actual drag/scroll response and automatic return, immediate starting movement, and persistent save/resume. Results/captures: verification/workbench/. Battle source/event/clip checks are under verification/battle/ and verification/battle-model/. The isolated battle renderer passes source replay, paused asset loading and move-menu checks under verification/starter-battle-runtime/. Squirtle passed 12 additional WebGL fixture checks for its actual asset, facing, scale, Tackle, Tail Whip and pause. The fixture substitutes observed species and Tail Whip signals without changing cartridge bytes; it is not a native Squirtle playthrough. delivery.json describes the earlier camera delivery.

Short local town sample: 228 simulated frames in 3.81 seconds, median render interval 15.3 ms, p95 20.7 ms at 2880×1562. This is not full-game performance or input-latency coverage. Eighteen independent save checks from the previous delivery remain valid; checkpoint preparation now verifies six state hashes/sizes/magic.

## Source and presentation

User ROM BPRE English rev0 SHA1 41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc. Matching pret source rebuilt byte-for-byte;54,248 symbols. Inventory3154PNG/425maps/3169matchingINCBIN ranges is source coverage, not completed3D assets. Original mGBA WASM owns all gameplay.

Rendered scenes: Pallet Town, Route1, player house1F/2F, Oak’s lab, first battle. Source-aligned door anchors, native dialog printer, source creature cutouts and battle menus. Full game3D coverage is not implemented.

Active environment: cottagev2, laboratoryv2, original treev1, revised lawn/terrain and daylight HDR. Treev2 is a separately reviewed candidate; broad crown improved but dark/angular leaves prevent visual promotion. Source-aligned Route1 uses candidate grass/ledges and native transition checkpoint with exact input replay.

Player: trainer-direct-v3.glb SHA971ec6a4d9a6348a9ceb30509029bad021b66031a8fb8a4ac496b9e4a0a2a294. Direct extracted trainer sprite→image_to_3d job completed, no generated concept image. Preserved24-bone rig/idle; authored1-second walk, nominal.64model-unit stride before scaling. Source movement selects walk using tileTransitionState and displacement, not ObjectEvent.singleMovementActive. Pause/rewind stable. V3 lowers the arms and adds walk counter-swing; crouched stance and stylized facial/material detail remain.

Starter battles use the new textured 3D Oak lab and registry-selected Bulbasaur v1, Charmander v3 and Squirtle v1. Both sides load their species model with SHA256 verification and preserve the original sprite on asset failure. Native move-script edges trigger Tackle/Scratch/Growl/Tail Whip presentation; original controller edges trigger hit/faint. All combat, timing and damage remain in the cartridge simulation. The original Charmander creator credits and CC BY-NC 4.0 terms are preserved. Bulbasaur and Squirtle were authored directly in Blender from source sprites after image-reference requests were rejected. These models are stylized candidates, not photoreal-approved assets.

## Separate character task and next work

Character task01a08368-3b4d-7501-a203-04a07c64704b (“Pokémon player and NPC rendering”) completed isolated commitddcf666b. Its source character renderer and relaxed trainer v3 are now copied/integrated into canonical app. Native VRAM/palette sprites replace missing human rings; original source frame/facing/script hiding retained. Existing3D lab props preserved. Normal app reopened in session53265 after45 integration/input checks passed. Actual town/interior/lab captures in verification/workbench. NPCs remain2D, not photorealmodels.

Active local art workers: source-aligned water inlet replacing flat rectangle; Route1 natural grass/ledges/flowers; cottagev3 roof repair. Their files are candidates and must be reviewed in runtime before selection.

No photoreal asset/scene acceptance and no95% claim. Remaining: NPC photoreal geometry, player stance/material refinement, battle effects, materials/geometry refinement, map-edge composition, and broader3D map coverage. Prior Squirtle/Bulbasaur image-generation rejections remain recorded; do not reroute those rejected requests. Preserve unrelated root Next.js work.
