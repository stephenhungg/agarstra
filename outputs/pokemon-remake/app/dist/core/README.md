# FireRed source runtime core

This is a tested original-ROM execution bridge. It does not generate 3D assets or substitute simulated gameplay.

## Verified cartridge

The user's local FireRed US revision 0 ROM has SHA1 `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc` and SHA256 `3d0c79f1627022e18765766f6cb5ea067f6b5bf7dca115552189ad65a5c3a8ac`. A matching pret/pokefirered build supplies exact symbol addresses. The ROM itself remains outside this runtime directory.

## Interfaces

```js
import { createGbaCore, GbaAudio } from './browser-core.mjs';
import { Keys } from './gba-adapter.mjs';
import { readFireRedState } from './firered-state.mjs';
const gba = await createGbaCore(romBytes);
gba.loadState(checkpointBytes);
const {audio} = gba.step(1, Keys.Right); // exactly one original source frame
const rgba = gba.pixels();             // 240 × 160 RGBA bytes
const scene = readFireRedState(gba);    // read-only source observation
```

`step(frames, keyMask)` drains original stereo PCM per frame and snapshots memory after the final frame. The source frame rate is 59.7275 Hz; it must not be assumed to be exactly 60. Repeated display frames should not advance the source. The host schedules the loop, input, rendering, and audio. `GbaAudio` plays interleaved signed-16 PCM at its declared source sample rate through Web Audio's resampler. Pause clears queued sources. Audio audibility is not claimed by headless tests; those validate nonzero PCM and expected sample counts.

Other interfaces: `setKeys`, `read8/16/32`, `readBytes`, `saveState`, `loadState`, `saveSram`, `loadSram`, `destroy`. Key masks: A1, B2, Select4, Start8, Right16, Left32, Up64, Down128, R256, L512.

State restoration resets held input and clears pending core audio. Framebuffer output updates on the next `step`, not immediately upon restore. Store and check the ROM identity alongside persistent checkpoints. SRAM should be restored before gameplay/reset; export is 131072 bytes for this ROM. Avoid multiple cores inside one WASM module; create a separate module for each instance.

## Memory and semantic observation

The published shim exposes no arbitrary bus-read function. This adapter uses mGBA's documented 397312-byte version `0x0100000b` snapshot to obtain EWRAM, IWRAM, IO, palette, VRAM, and OAM. It also exposes direct read-only cartridge bytes from `0x08000000`. Unsupported address ranges fail explicitly; this is not a general emulated bus API and does not implement address mirroring or side-effecting IO reads. Snapshot reserved bytes are cleared before serialization. This fixed actual stale-reserved-field warnings encountered during testing.

`readFireRedState` returns `{frame, phase, map, player, objectEvents, battle, source}`. Player/objects include `worldX/worldY` in map tiles, `tileX/tileY`, facing, sprite animation frame, visibility, elevation, graphics ID and source addresses. The 7-tile engine border is removed. Source `gFieldCamera` phase corrects early integer destination updates into actual 1/16-tile movement; no guessed smoothing or independent physics. Unknown maps retain numeric IDs and null dimensions. `hidden` is the ObjectEvent scripted invisibility flag; `spriteInvisible` and `offScreen` retain viewport culling separately. Use `!hidden` for a wider 3D camera. Actor output is restricted to the confirmed overworld callback to avoid presenting stale actors during menus/transitions/battles.

Battle output includes source active flag, battle flags/outcome, battler species/HP/maxHP/level/moves. The first rival battle is exercised in `checkpoints/battle-verification.json`: Bulbasaur (species 1, level 5, 20 HP) faces Charmander (species 4, level 5, 18 HP). Original Fight → Tackle and tutorial acknowledgments produce the next command menu at 11 and 14 HP. During battle animation/tutorial pauses the displayed HP bar can lead committed `gBattleMons.hp`; these are committed source values, not reconstructed UI pixels. Creature party encryption is not decoded by this adapter.

## Evidence and reproduction

- `probe-results.json`: 12 direct-core checks passed, real ROM video/audio, deterministic restored frame, memory observation, SRAM. 600 frames including per-frame snapshots took 1083 ms on this machine in that run. This is headless throughput, not a claim about 3D renderer performance.
- `checkpoints/pallet-town.state`: reached through controller input only, no RAM patch. Player A, rival GREEN, no starter yet, outdoors at (6,8).
- `checkpoints/pallet-town.state.replay.json`: 124 `{frames, keys}` segments from power-on, 11979 frames. This is a deterministic input record, not instructions to inject game state.
- `checkpoints/verification.json`: replay produced every byte of the saved mGBA state exactly; observer did not mutate emulation; movement produced fractional coordinates.
- `checkpoints/first-battle.state`: frame 30451, first rival battle command menu. Its complete input replay begins at power-on. `first-attack.state` records the next command menu after the first source-controlled turn.
- `browser-smoke.json/png`: Electron with nodeIntegration=false loaded the browser loader, checkpoint, source pixels and semantic observer successfully.
- `probe.html`: local `.gba` picker, original source view, keyboard and pause control. Serve this directory over localhost; no external hosted ROM required.

Probe scripts are in `work/pokemon/bridge-probe`: `probe.mjs`, `verify-checkpoint.mjs`, `browser-smoke.cjs`. Node 26 was used. The UMD loader is copied to `.cjs` for Node; browsers load it as a classic script.

## Dependencies and provenance

- `@wasm-gaming/mgba-wasm@0.1.1`: 319.4 KB npm archive; ~1.063 MB unpacked package. Runtime uses only 809645-byte WASM and ~68.7 KB UMD loader. No build toolchain, GPU or SharedArrayBuffer is required to execute it. Browser/Electron/Node WebAssembly support is required.
- Wrapper source: https://github.com/wasm-gaming/mGBA-wasm (thin shim and SDK).
- Pinned core source: https://github.com/mgba-emu/mgba/tree/c034660f007c543233f1cadeb0ca13c71afd8f41
- Snapshot contract: https://github.com/mgba-emu/mgba/blob/c034660f007c543233f1cadeb0ca13c71afd8f41/include/mgba/internal/gba/serialize.h
- Game source: https://github.com/pret/pokefirered/tree/c75f352304d529f6ba92d4f74b9cf8b5c3810788
- Object/player structs: `include/global.fieldmap.h`; battle structs: `include/pokemon.h`; camera correction: `src/field_camera.c:CameraUpdate` and `src/event_object_movement.c:GetMapCoordsFromSpritePos`.

mGBA and wrapper are MPL-2.0; license is preserved in `vendor/LICENSE`. For distribution preserve source availability and notices for covered files. No paid dependency or remote runtime inference is involved.
