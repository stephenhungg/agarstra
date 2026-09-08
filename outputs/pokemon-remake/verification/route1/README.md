# Route 1 Playable Coverage Candidate

`app/route1.js` builds the complete **24 × 40** source map, with **69 tree placements, 178 tall-grass cells, 61 south-jump ledge cells, 25 flower patches and 18 fence cells**. Existing tree GLB and lawn/dirt maps are reused. Exact map words, collision layers, behavior IDs, source hash and connections live in `source/route1-layout.json`; no game rules or source states are patched.

## Integration

`await createRoute1(renderer)` returns `group`, `camera`, `update(state)`, `resize(width,height)`, `report`, `playerPosition`, `actorPositions` and `setPlayerModelVisible(boolean)`. Passing `true` to the visibility hook hides the interim player marker for the root's trainer model. The module imports its source JSON for Vite bundling and resolves existing `models/tree.glb` / `terrain/*.jpg` assets against the document base. Root owns scene routing, controls and model replacement. Update receives the original observer state, with no independent collision or movement.

The source elevation values 0/3 are collision layers rather than measured physical height. The walkable floor remains at y=0; local .28-tile relief is drawn only at original MB_JUMP_SOUTH cells. This avoids inventing inaccessible plateaus. Camera aim is clamped inside Route1. Connected-map objects outside this map's bounds are suppressed.

## Verified checkpoints

All checkpoints were obtained through original inputs from `first-attack.state`, including battle completion, lab dialogue, lab exit and the sign-lady tutorial at the town's north exit. `native-inputs.json` records the exact complete sequence. `check-source.mjs` replays it and reaches byte-identical Route1 state.

| Checkpoint | Map | Player | Frame | SHA-256 |
|---|---|---|---:|---|
| `post-starter-pallet.state` | PalletTown 3:0 | (16, 13), lab doorway | 39019 | `4bf4f58c1676700a62f862b4c3c35b1182013169521fe1ada498f2b86297469a` |
| `route1-entry.state` | Route1 3:19 | (13, 39) | 40715 | `6641dd09a0d51a4f49c868351930c2af58a25dbe64a2eddd0af04c5d0b6e7ccf` |

The canonical startup/Pallet checkpoint is untouched. Root may expose these as separate demo checkpoints. Source connections are PalletTown south offset 0 and ViridianCity north offset -12.

## Evidence and reproduction

Eight source checks passed. Standalone actual Electron/WebGL checks passed with 84 draw calls / approximately 4.28 million submitted triangles at the entry view, both tree primitives loaded, all source-ledges recorded, matching player coordinates and replacement visibility hook. These triangle counts are not a performance guarantee. `gameplay.png` and `overview.png` were opened and inspected after correcting dark grass, neighboring-map ghost markers and edge-camera framing. `native-entry.png` is the actual source framebuffer.

From repository root:

```sh
python3 outputs/pokemon-remake/verification/route1/extract-layout.py
node outputs/pokemon-remake/verification/route1/native-replay.mjs
node outputs/pokemon-remake/verification/route1/check-source.mjs
```

From this directory, run these in separate terminals:

```sh
node ../../app/node_modules/vite/bin/vite.js . --host 127.0.0.1 --port 4188 --strictPort
node ../../app/node_modules/electron/cli.js ./webgl-runner.cjs
```

## Visual limits

This extends functional coverage; it is not photoreal acceptance. Ledges are simple regular blocks, tall grass uses rigid blade candidates, trees retain their existing crown defects, paths have quarter-tile edge stepping, and signs/trainers/NPCs use interim geometry. Connected maps are not included in the isolated route scene. Root must inspect actual integrated transitions, trainer placement and frame rate. `review.json` binds current source/code/render evidence hashes.
