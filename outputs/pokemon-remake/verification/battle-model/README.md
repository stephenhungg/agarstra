# Battle model loader preparation

The loader is implemented and verified for its integration contract. This does not accept Charmander v1 as a battle asset. Its original rig-demonstration clip is never played. The current image is an explicitly labeled static inspection of the creator-derived candidate.

## API

```js
import {createBattleModel} from './battle-model.js';
const model = await createBattleModel(renderer, {url, sha256});
scene.add(model.group);
// Original emulation frame/time is authoritative; call only when source state updates.
model.setTime(sourceFrame / sourceFramesPerSecond);
// Dispose after removing/replacing the owned instance.
model.dispose();
```

The loader verifies SHA256 before parsing, requires GLB v2 with embedded buffers/textures, and retains the complete scene hierarchy. It does not strip the existing Armature rotation/scale, convert units, normalize proportions, or reparent skin meshes. Position/rotate/uniformly scale the returned outer `group`; `report.height`, `report.bounds` and `report.groundOffset` describe the initial pose in preserved scene units. If scaling, apply ground offset in the same scaled coordinate system. Initial bounds are not an animated motion envelope.

Only an animation with the exact name `idle` is selected. Duplicate or invalid idle clips reject the asset. A model without it remains static, reports `staticOnly: true`, and `setTime()` returns false. An available idle is evaluated at supplied absolute seconds modulo its duration, so repeated timestamps pause, backwards timestamps restore earlier poses, and resets need no independent clock. Invalid or negative time rejects. The module has no timer, animation-frame loop, input, emulator write or battle state logic.

`report` includes the verified URL/hash, file size, preserved initial bounds/height, all clip names/durations/track counts, selected clip, skinned meshes, bones, mesh/node counts, latest supplied seconds and disposal status. Its candidate status is deliberately separate from visual acceptance. A matching hash is not an art-quality approval. The caller must retain the last good source sprite/model if loading rejects and must decide visibility, battle action compatibility and accepted candidate version.

`dispose()` stops/uncaches the owned mixer and releases geometries, materials, textures and skeleton resources once. Each invocation creates its own asset instance. It is idempotent; calls to `setTime` after disposal reject.

## Completed checks

`browser-results.json` is from real Electron/WebGL, not a mocked loader. `v1-static-webgl.png` was captured and visually inspected.

- SHA256 mismatch rejected before parsing.
- Actual 15,178,784-byte Charmander v1 loaded with all 60 bones, one skin, 7,767 exported vertices and 64 scene nodes.
- Preserved static height: 0.5954580843 scene units. Source armature transforms remain intact.
- Original `Armature|Take 001|BaseLayer` (6.7 seconds, 180 tracks) remained unselected. Calling `setTime(10)` left every node transform unchanged.
- A clearly separate triangle fixture with an explicit `idle` verified forward evaluation, repeated-time pause, backward seeking, exact loop phase, preserved parent translation, invalid-time rejection and idempotent disposal.
- WebGL inspection frame: two draw calls including the stage, 13,762 triangles. This is not an FPS benchmark or proof of battle-scene acceptance.
- JavaScript syntax check passed.

The triangle fixture exists only to test deterministic mixer mechanics. It is not a character asset, and no existing rig-demo clip was renamed to create it. An actual v2 idle still needs its own pose/deformation review and actual battle placement inspection.

## Reproduce

From the repository root:

```sh
python3 outputs/pokemon-remake/verification/battle-model/build-fixture.py
node --check outputs/pokemon-remake/app/battle-model.js
outputs/smb3-demo/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron outputs/pokemon-remake/verification/battle-model/browser.cjs
```

The v1 hash used for static inspection is `95ea02802032e55fcaaa06d8f6b53df89b5bf130b1bb22787ab5d399c9e7a3f0`. Existing creator attribution and CC BY-NC 4.0 terms remain recorded in `verification/charmander-existing/`. This module does not change those terms or make the asset accepted for battle.
