# FireRed Reconstruction Workbench

A playable ROM-to-3D integration prototype. Art and game coverage remain incomplete.

## Run

Double-click `Launch Workbench.command`, or run from the agarstra repository:

```sh
npm start --prefix outputs/pokemon-remake/app
```

The app loads the locally verified ROM at `work/pokemon/rom/firered-user.gba`. On this machine, app dependencies are shared with the SMB3 demo via a node_modules symlink. A separate checkout needs its own app/package.json dependencies installed.

Arrows move/select, X or Space confirms, Z cancels, Enter is Start, Shift is Select, P pauses. The Source / controls button exposes the original framebuffer and checkpoint selector: Pallet Town, first battle, and after the first turn. Loading a checkpoint resets the original simulation. Switching windows pauses normal play; press P to resume. Inspect cottage shows the actual exported asset.

## Current coverage

- Original mGBA simulation controls rules, collisions, movement, dialog, combat and timing. Presentation reads memory; it does not invent damage or run a second game simulation.
- Pallet Town has two cottage instances, the laboratory exterior, 29 trees, source-aligned PBR terrain, fences and signs. Source doorway anchors align with all three buildings.
- Player house 1F/2F and Oak’s laboratory have source-aligned 3D interiors. Characters remain temporary markers.
- Dialog follows the actual source text printer. Unsupported text/choice layouts preserve cropped source UI pixels.
- First battle displays original creature sprite cutouts, HP, levels, native command and move menus, PP and source sprite motion. Party/bag menus still use the original framebuffer. Separate attack effects and battle background effects are not reconstructed.
- Other maps show an explicit coverage message and the last town view. Full-game replacement is not implemented.

The 425 map records and 3,154 source PNGs in the extraction inventory are source coverage, not completed 3D assets.

## Asset workflow

Use extracted sprites directly to constrain Blender geometry, proportions and feature placement. Add materials, topology and a rig, export GLB, then inspect the actual renderer and motion. An intermediate generated concept image is optional and must not override source identity. Pixels do not contain hidden surfaces, depth, joints or topology: these are authored or inferred, not recovered from the ROM.

The existing Charmander candidate was imported from an independently authored FBX. It is not extracted geometry or a sprite-to-mesh result. Credit and CC BY-NC 4.0 license details are in verification/charmander-existing/export.json. Its skin was inspected, but the clip appears to be a rig demonstration with neck distortion. It is not approved or used as the battle runtime character.

## Quality status

No photoreal assets or scenes are approved. Cottage roof detail and baked reflections need repair. Laboratory vent, roof and glazing need repair. Trees have narrow crowns; terrain reads too dry and sparse. Interiors use candidate geometry/materials. Trainer models and accepted creature motion are unfinished. No fidelity percentage is claimed.

## Verification

```sh
npm run smoke --prefix outputs/pokemon-remake/app
```

The integrated Electron test checks original simulation, restoration, coordinates, doorway entry, source dialog, battle scene/menu selection, native damage, pause and reset. It saves results and six renderer captures to verification/workbench/. Exact attack replay restores the saved frame without an extra redraw step, which would advance RNG. Normal checkpoint viewing redraws one frame.

Independent dialog, battle and interior evidence is in verification/dialog/, verification/battle/ and verification/interiors/. Rendering samples are short and local, not full-game or input-latency guarantees. See STATE.md and design/production.json for unresolved work.
