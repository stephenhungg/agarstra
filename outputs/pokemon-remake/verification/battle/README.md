# Native battle presentation verification

`app/battle.js` exposes `await createBattle(renderer)` with `group`, `camera`, `update(core, state)`, `resize(width, height)`, `setVisible(boolean)`, `dispose()`, `report`, and snapshot getters. The renderer parent hosts its CSS overlay. Root owns scene switching and original game input; this module only reads the core.

## Verified behavior

- Thirteen CPU/source checks pass against the verified local FireRed ROM and real `first-battle.state` / `first-attack.state` checkpoints.
- Both transparent creature cutouts come from live OBJ VRAM, OBJ palettes, native sprite tile selection and affine matrices. All compared opaque pixels match the original framebuffer: 1,143 player pixels and 760 opponent pixels. Pixels below the original battle UI boundary were excluded from the comparison.
- Native action cursor, move choice, PP, names, level and HP are decoded from the running core. Initial HP is 20/20 and 18/18; the original 1,564-frame input replay reaches 11/20 and 14/18.
- The presentation reads leave serialized core state unchanged. The replay with presentation reads is byte-identical to the same per-frame replay without presentation reads. The supplied checkpoint differs in 34 emulator header/IO bytes below offset 0x1000; this is recorded separately, not claimed as full checkpoint equality.
- Attack replay observes nine source transform states, ten sprite pixel hashes and native TACKLE/SCRATCH signals. There are no independent action timers or damage rules.
- Actual Electron/WebGL screenshots pass for first battle, after attack and move selection. See `webgl-checks.json`, `source-checks.json` and paired `*-3d.png` / `*-source.png` evidence.
- Source party/bag screens and unknown controller menus have native pixel fallbacks. These fallbacks have not received exhaustive battle-mode coverage in this pass.

## Reproduce

From repository root:

```sh
node --experimental-loader ./outputs/pokemon-remake/verification/battle/css-loader.mjs ./outputs/pokemon-remake/verification/battle/check-battle.mjs
```

From this verification directory, run the local Vite harness and then Electron in a second terminal:

```sh
node ../../app/node_modules/vite/bin/vite.js . --host 127.0.0.1 --port 4187 --strictPort
node ../../app/node_modules/electron/cli.js ./webgl-runner.cjs
```

The harness reads the existing local verified ROM through its own preload and does not package or redistribute it.

## Remaining requirements

Status: functional interim candidate; visual changes required. Creatures remain source pixel billboards, not rigged photoreal 3D models. The neutral battle stage is draft terrain. Separate attack-effect sprites, battle background effects, and every controller variant are not rebuilt. Native battler motion, visibility, palette and affine state are followed; that is not a complete reconstruction of all battle animation layers. The external Charmander model is intentionally not integrated pending its owner's rig/material review.
