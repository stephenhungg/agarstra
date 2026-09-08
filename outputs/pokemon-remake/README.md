# FireRed Reconstruction Workbench

A playable ROM-to-3D integration prototype. Art and game coverage remain incomplete.

## Run

Double-click `Launch Workbench.command`, or run from the agarstra repository:

```sh
npm start --prefix outputs/pokemon-remake/app
```

The app loads the locally verified ROM at `work/pokemon/rom/firered-user.gba`. On this machine, app dependencies are shared with the SMB3 demo via a node_modules symlink. A separate checkout needs its own app/package.json dependencies installed.

Arrows move/select, X or Space confirms, Z cancels, Enter is Start, Shift is Select, P pauses. The top bar exposes Explore town, Battle, Pause, Sound, Save progress and Resume save. Source inspector exposes the original framebuffer and additional checkpoint selection. Loading a checkpoint resets the original simulation. Switching windows pauses normal play and returning resumes an automatic pause. A manual pause has a visible click-to-play overlay. Save progress writes a persistent local quicksave; Resume save restores it, including after restarting the app. The game starts outside the laboratory after obtaining the starter, with controls ready immediately. Explore town resets to that checkpoint. The default camera is north-up at 30°, with orthographic projection. Drag to look around or scroll to zoom temporarily; release to ease back to the default angle and zoom. It follows source movement within outdoor map bounds and frames interiors as rooms. Inspect cottage is a separate asset inspection view.

## Current coverage

- Original mGBA simulation controls rules, collisions, movement, dialog, combat and timing. Presentation reads memory; it does not invent damage or run a second game simulation.
- Pallet Town has two cottage instances, the laboratory exterior, 29 trees, source-aligned PBR terrain, fences and signs. Source doorway anchors align with all three buildings.
- Route 1 has source-aligned paths, grass and ledges; native movement, encounters and transitions remain controlled by the ROM.
- Player house 1F/2F and Oak’s laboratory have source-aligned 3D interiors. The player uses a skinned trainer candidate with idle and walking; NPCs remain temporary markers pending the separate character rendering task.
- Dialog follows the actual source text printer. Unsupported text/choice layouts preserve cropped source UI pixels.
- First battle displays a rigged Charmander candidate with authored source-clock idle, other original creature cutouts, HP, levels, native command and move menus, PP and source sprite motion. Party/bag menus still use the original framebuffer. Separate attack effects and battle background effects are not reconstructed.
- Other maps and unsupported full-screen menus use clearly labeled live original graphics so the game remains playable. Original view can also be selected manually. Full-game 3D replacement is not implemented.

The 425 map records and 3,154 source PNGs in the extraction inventory are source coverage, not completed 3D assets.

## Asset workflow

Use extracted sprites directly to constrain Blender geometry, proportions and feature placement. Add materials, topology and a rig, export GLB, then inspect the actual renderer and motion. An intermediate generated concept image is optional and must not override source identity. Pixels do not contain hidden surfaces, depth, joints or topology: these are authored or inferred, not recovered from the ROM.

The existing Charmander candidate was imported from an independently authored FBX. It is not extracted geometry or a sprite-to-mesh result. Credit and CC BY-NC 4.0 license details are in verification/charmander-existing/export.json. The original rig-demo clip was replaced in v2 with an authored idle and symmetric stance. All 91 clip frames were checked for fixed feet/root and loop closure. V2 is used for the opponent Charmander; it is still a visual candidate with coarse color detail and a solid glowing tail tip.

## Quality status

No photoreal assets or scenes are approved. Cottage roof detail and baked reflections need repair. The laboratory vent cap is repaired; roof and glazing still need repair. Trees have narrow crowns; the revised lawn is denser, while water and vegetation need further work. Interiors use candidate geometry/materials. The trainer has a working walk but retains raised arms from its source battle pose. NPC replacements and accepted creature motion are unfinished. No fidelity percentage is claimed.

## Verification

```sh
npm run smoke --prefix outputs/pokemon-remake/app
```

The integrated Electron test checks original simulation, restoration, coordinates, doorway entry, source dialog, battle scene/menu selection, native damage, pause and reset. It saves results and renderer captures to verification/workbench/. Exact attack replay restores the saved frame without an extra redraw step, which would advance RNG. Normal checkpoint viewing redraws one frame. The default ready-to-explore checkpoint includes 60 original no-input frames after the lab exit, avoiding a controls-locked doorway transition.

Independent dialog, battle and interior evidence is in verification/dialog/, verification/battle/ and verification/interiors/. Rendering samples are short and local, not full-game or input-latency guarantees. See STATE.md and design/production.json for unresolved work.

The smoke suite also checks player rig motion, the native town-to-Route 1 transition, cardinal screen directions, camera pause stability, and real mouse drag and temporary zoom with return to the home angle. Latest results are stored in verification/workbench/results.json. Eighteen separate persistent-save checks passed, including corruption rejection and restoration in a freshly initialized emulator. Evidence: verification/workbench/results.json and verification/playability/progress-store-results.json.
