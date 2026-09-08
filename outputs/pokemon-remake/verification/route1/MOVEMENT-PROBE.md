# Doorway Readiness and Player Walk Signal

The final **post-starter-ready** checkpoint is exactly **60 native no-input frames** after `post-starter-pallet.state`. It is packaged in `runtime-core/checkpoints` and declared as the catalog default. The original Pallet Town checkpoint and raw post-starter doorway checkpoint remain untouched.

- Frame: **39079**
- Map: **PalletTown 3:0**
- Player: **(16, 14)**, facing down, visible
- `runningState = 0`, `tileTransitionState = 0`
- SHA-256: **fa39d4852fd8f1e4b8d770c9d46398379fd84ed19a429e6be978ab9705c6a0c6**
- Native Right 12 frames reaches X=16.25; 16 frames reaches X=16.5; 32 frames reaches X=17.5. Y remains 14.

The old snapshot was taken during the automatic laboratory exit. With no input, +20 frames still has the player at Y=13.3125. +40 reaches the pavement but is still in transition state 2. The detailed exploratory probe found the earliest fully idle, responsive point at +51; the packaged checkpoint uses the explicitly requested stable +60 margin. `movement-probe.json` and `ready-frame-probe.json` preserve these intermediate measurements; their candidate hashes are not the packaged checkpoint.

## Correct walk signal

The original observer's `moving` field reads bit 1, `ObjectEvent.singleMovementActive`. This remains false throughout the tested player walk. Source `include/global.fieldmap.h` defines player `runningState` at offset +2 (0 stopped, 1 turning, 2 moving) and `tileTransitionState` at +3 (0 stopped, 1 between tiles, 2 tile-center continuation / jump).

From the original Pallet checkpoint, native Right first turns for eight frames. At +12, X=6.25; at +16, X=6.5. Both have **runningState=2**, **tileTransitionState=1**, but `moving=false`. Bit 6 `heldMovementActive` remains true at idle and during a turn too, so that bit alone is insufficient. For ordinary player locomotion, use `runningState === 2 && tileTransitionState !== 0`; actual source displacement can supplement scripted movement. When paused, do not treat repeated reads of the same frame as new zero-speed samples.

## Reproduce

Run the scripts from repository root:

```sh
node outputs/pokemon-remake/verification/route1/movement-probe.mjs
node outputs/pokemon-remake/verification/route1/ready-frame-probe.mjs
node outputs/pokemon-remake/verification/route1/create-ready-checkpoint.mjs
node outputs/pokemon-remake/app/prepare.mjs --check-checkpoints
```

The first two scripts record exploratory results. Only `create-ready-checkpoint.mjs` writes the final ready state, provenance, observed state and catalog entry. All six checkpoint integrity checks pass. No app main/observer/avatar code was edited by this probe worker.
