# Pokémon FireRed remake — playable prototype, photoreal work incomplete

## Current delivery

App rebuilt, tested and reopened after the 30-degree return-on-release camera revision. Launch Workbench.command or `npm start --prefix outputs/pokemon-remake/app` from the repository. Default Explore town checkpoint is post-starter-ready: native frame 39079 outside Oak’s lab at (16,14), starter obtained and doorway animation completed. Existing progress file is preserved.

The latest user revision supersedes the fully locked camera: default north-up orthographic angle is now 30°. Pointer drag temporarily orbits, scroll temporarily zooms, and release eases back to the default angle/zoom. Outdoor tracking uses original player position and map bounds, interiors use fixed room framing, battles retain a separate fixed camera. Asset inspection keeps a separate free camera. Default tracking stays tied to the source; only pointer-release return uses render-time easing. There is no gameplay overview toggle.

Visible controls: Explore town, Battle, Pause, Sound, Save progress, Resume save, Original view. Arrows move/select; X confirms, Z cancels, Enter opens the native menu, P pauses. Unsupported scenes/menus use labeled live original graphics so gameplay continues. Persistent quicksave: work/pokemon/player-progress.json; smoke uses a separate verification-save.json.

## Verified scope

Latest smoke passed 33 integration checks and 11 actual Electron mouse/keyboard/button checks. Covered: source simulation and deterministic restore, coordinates and doors, printer dialog, battle menus/HP/damage, pause/reset, rigged player idle/walk, native Pallet-to-Route1 replay, screen direction alignment, fixed camera across transitions, actual drag/scroll response and automatic return, immediate starting movement, and persistent save/resume. Results/captures: verification/workbench/. Exact build/source hashes and visual review: delivery.json there.

Short local town sample: 228 simulated frames in 3.81 seconds, median render interval 15.3 ms, p95 20.7 ms at 2880×1562. This is not full-game performance or input-latency coverage. Eighteen independent save checks from the previous delivery remain valid; checkpoint preparation now verifies six state hashes/sizes/magic.

## Source and presentation

User ROM BPRE English rev0 SHA1 41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc. Matching pret source rebuilt byte-for-byte;54,248 symbols. Inventory3154PNG/425maps/3169matchingINCBIN ranges is source coverage, not completed3D assets. Original mGBA WASM owns all gameplay.

Rendered scenes: Pallet Town, Route1, player house1F/2F, Oak’s lab, first battle. Source-aligned door anchors, native dialog printer, source creature cutouts and battle menus. Full game3D coverage is not implemented.

Active environment: cottagev2, laboratoryv2, original treev1, revised lawn/terrain and daylight HDR. Treev2 is a separately reviewed candidate; broad crown improved but dark/angular leaves prevent visual promotion. Source-aligned Route1 uses candidate grass/ledges and native transition checkpoint with exact input replay.

Player: trainer-direct-v2.glb SHA fd14343ce1c070bdd3bd51c6c01b8c871bf26f81f7206c57466bb33270c1fe74. Direct extracted trainer sprite→image_to_3d job completed, no generated concept image. Preserved24-bone rig/idle; authored1-second walk, nominal.64model-unit stride before scaling. Source movement selects walk using tileTransitionState and displacement, not ObjectEvent.singleMovementActive. Pause/rewind stable. Stylized, with raised battle-pose arms still needing correction.

Opponent Charmander: charmander-existing-v2.glb, SHA ad78d6f71b421d5f3ce534806b2f816d160647be282276152dca03a25c6ce7e6. Existing creator model under CC BY-NC4.0; credits preserved. Verified local idle replaces unsuitable rig demonstration, original skin preserved. Coarse texture/solid flame tip and missing attack-specific motion remain. Other creatures use source sprites.

## Separate character task and next work

User requested a new task responsible for player/NPC sprites. Codex app creation requested as “Pokémon player and NPC rendering”, isolated worktree, client-new-thread:76098502-bbbe-44ee-a07c-593c2be45a9f. Detailed prompt points to current canonical files and asks for source-faithful NPC rendering, player pose improvement, isolated module/patch and screenshots; no camera ownership. Creation returned queued; do not invent a ready thread ID or duplicate it.

No photoreal asset/scene acceptance and no95% claim. Remaining: NPC marker replacement, player pose, battle effects, materials/geometry refinement, map-edge composition, and broader3D map coverage. Prior Squirtle/Bulbasaur image-generation rejections remain recorded; do not reroute those rejected requests. Preserve unrelated root Next.js work.
