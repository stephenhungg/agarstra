# Source-aligned 3D interiors

Status: candidate 3D geometry, not photoreal approved. Three source-driven interiors are implemented: the player's house upstairs/downstairs and Professor Oak's laboratory. Floors, furniture, stairs and walls are actual geometry; there is no framebuffer plane or second movement controller.

## Integration contract

`app/interiors.js` exports asynchronous `createInteriors(renderer)` returning:

- `group`, `camera`: add the group to the main scene and render with this camera for supported maps.
- `supports(mapName)`: accepts the three exact source map names in `source/interiors.json`.
- `update(core, state)`: observes `readFireRedState` output; changes visible room and actor positions. Does not advance or write the core.
- `resize(width, height)`, `setVisible(boolean)`.
- `report`: candidate status, dimensions, source hashes, feature counts, source warps, active map and actor positions.

Source coordinates use +Y up, x=source worldX, z=source worldY, with integer tile centers. Trainer and NPC actors are temporary direction markers. Starter balls and Pokédex objects use their live source graphics IDs. Script-hidden objects remain hidden; original viewport culling does not remove objects in the wider 3D camera.

## Source correspondence

The ROM is FireRed US 1.0, SHA1 `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`; source commit is `c75f352304d529f6ba92d4f74b9cf8b5c3810788`. `source/interiors.json` preserves the exact map dimensions, metatile IDs, collisions, map-data hashes and warp events from the matching source build.

Forty furniture groups record their full source metatile footprints. Furniture names and heights are interpretations of the assembled source tiles; they are not claimed to be official source labels. The player's PC has an explicit source metatile constant. `render-source.py` reconstructs the original map previews from source tiles, palettes and metatile definitions. The source and grid PNGs beside this document are the placement references.

| Room | Source-aligned contents | Critical transition tiles |
|---|---|---|
| PlayersHouse1F, 13×10 | Kitchen at x1–4, north TV/window, dining rug/table/chairs, side plants, rising east stairs | Stairs (10,2) → 2F warp 0; exits (5,8), (4,8), (3,9) → Pallet Town warp 0 |
| PlayersHouse2F, 12×9 | Northwest PC desk, bookshelf, bed, central rug/TV/console, east stair opening | Stairs (10,2) → 1F warp 2 |
| ProfessorOaksLab, 13×14 | North computer bench, shelves, notices, healer, starter table, partition shelves with central aisle, entrance plants | Exits (6,12), (7,12), (5,12) → Pallet Town warp 2 |

The north wall is full height and the side walls are cut away for gameplay visibility. Floor material treatments and vertical furniture profiles are presentation interpretations. Source collision remains authoritative, including stairs and blocked furniture tiles. The wider source sprite footprint is not interpreted as a new physical collider.

## Verification results

`source-results.json`: all three map arrays, dimensions, collision fields and warp events match the source export exactly; all 40 furniture groups preserve their declared source cells. The reciprocal stair coordinates match (10,2). All three transition replay transcripts are exact suffixes of the recorded original input histories.

`browser-results.json`: four scene loads (2F → 1F → lab → 2F) passed in real Electron/WebGL; active room routing and every visible actor position match the source observer. Draw calls and triangles are 66/23,680 upstairs, 95/29,100 downstairs, and 145/41,684 in the lab. These are draw statistics, not an FPS benchmark.

A real Down input at the downstairs checkpoint changes the source position from (10,2) to (10,2.0625) on the ninth frame; the displayed actor matches the fractional coordinate exactly. The initial eight frames were source turn/startup behavior, so the test waits for the first actual source movement instead of assuming movement starts immediately.

Three real input replays were run one frame at a time while updating this scene:

| Replay | Source map transition frame | Endpoint source frame | Result |
|---|---:|---:|---|
| Bedroom → house downstairs | 10521 | 10629 | Correct 2F/1F routing |
| House downstairs → Pallet Town | 11784 | 11979 | Interior clears on unsupported outdoor map |
| Pallet Town → Oak's lab | 15486 | 15693 | Lab becomes active on source map change |

All serialized bytes from offset 0x800 onward match their original target checkpoints exactly, covering palette, OAM, VRAM, IWRAM and EWRAM. Entire serialized savestates are **not** byte-identical after restoring a checkpoint: 8–18 differing bytes remain in the preceding hardware/IO portion. The report preserves exact difference offsets and `exactState: false`; it does not claim complete CPU/hardware equivalence. No RAM patch was used.

The three `*-3d.png` images were captured from the actual renderer and visually inspected. Camera framing was expanded after the first capture clipped room edges; PC desk depth was corrected so the computer rests on its support. Main-app integration and combined lighting are tested separately by the parent workbench harness.

## Reproduce

From the project root:

```sh
python3 outputs/pokemon-remake/verification/interiors/build-manifest.py
python3 outputs/pokemon-remake/verification/interiors/verify-source.py
node --check outputs/pokemon-remake/app/interiors.js
outputs/smb3-demo/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron outputs/pokemon-remake/verification/interiors/browser.cjs
```

The local test uses the user ROM and existing states under `work/pokemon/bridge-probe/`; it creates no replacement simulation. Native GBA interaction and dialogs are handled by the main runtime and dialog overlay. The source array and furniture feature checks validate placement provenance, not photoreal quality or complete geometric coverage of every decorative source pixel.
