# Character rendering handoff

Implemented: `app/characters.js` and `app/character-source.mjs` provide a scene-level, read-only source-sprite fallback for active FireRed ObjectEvents. No new image generation, simulation, ROM distribution, or source RAM writes. Existing source attribution in `source/README.md` remains authoritative.

## Integration

Copy the two module files into the integration checkout. Apply `integration.patch` there after review (`git apply --check` passed against the canonical checkout on 2026-09-08). The patch modifies only character hooks in `town.js`, `route1.js`, `interiors.js`, and `main.js`; it does not modify this task's copies of those files or touch camera code. Since the integration checkout is being edited concurrently, regenerate with:

```sh
python3 outputs/pokemon-remake/handoff/characters/build-integration-patch.py /path/to/integration/repo
```

The script only reads the reference and emits a patch beside itself; unique-anchor assertions stop on conflicting changes. No automatic application occurs. Preserve and recheck concurrent main-task changes.

```js
import {createCharacters} from './characters.js';
const characters = createCharacters();
scene.add(characters.group);
characters.update(core, state, {
  visible: !native && !inBattle && viewMode === 'town',
  playerModelVisible: Boolean(avatar?.group.visible),
  groundHeight: object => inInterior
    ? (object.graphicsId === 92 ? .82 : object.graphicsId === 94 ? .78 : 0)
    : -.005,
});
```

Call on every displayed source state, including transitions; call `dispose()` on renderer teardown. `report.actors` exposes source identity, graphics ID, facing, animation/command, addresses, pixel hash, visibility and world position. The default scale is 16 source pixels per world unit. The caller supplies terrain/table heights; these are presentation choices, not source elevation-derived terrain.

The patch suppresses old map markers, while retaining their source position bookkeeping for existing camera/testing hooks. It restricts the Red model to graphics ID 0 (`OBJ_EVENT_GFX_RED_NORMAL`). Female protagonist, bike, surf and other forms automatically retain their own source sprite when no verified matching model is active. Model-load failure also retains the source player. Update any additional app assertions that inspect old marker visibility to consult `characters.report.actors` instead.

## Provenance and behavior

- Exact ROM: BPRE English rev0, SHA1 `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`.
- Matching pret commit: `c75f352304d529f6ba92d4f74b9cf8b5c3810788`.
- `include/sprite.h`: 0x44-byte Sprite, OAM dimensions/tile/palette/flips and animation fields.
- `src/sprite.c`: `RequestSpriteFrameImageCopy`, `SetSpriteOamFlipBits`; source DMA owns the live OBJ tile image.
- `src/event_object_movement.c`: `UpdateObjEventSpriteVisibility` combines script hiding and viewport culling. The fallback honors ObjectEvent script hiding and intentionally ignores viewport culling.
- Live source VRAM at `0x06010000` and OBJ palette at `0x05000200` are decoded after the source frame. No invented frame timing or palette assignment. `imagesAddress` links the live Sprite to its source frame-image table.
- Identity keys include map group/number, event slot, local ID and graphics ID. Retired resources are disposed on disappearance, map changes, hidden state and model replacement; paused updates retain the same pixels and pose.

## Verification and limits

The optional relaxed-arm player candidate is `models/trainer-direct-v3.glb`, SHA256 `971ec6a4d9a6348a9ceb30509029bad021b66031a8fb8a4ac496b9e4a0a2a294`. To select it, copy its GLB and editable `.blend`, then update the trainer entry in the integration checkout's `design/runtime-candidates.json` to `file: "trainer-direct-v3.glb"`, this hash, and `height: 1.4`. Existing `prepare.mjs` copies the GLB and manifest on build. Retain candidate status and existing attribution/provenance; no new provider generation occurred. The current avatar API requires no changes to load it.

`verification/trainer-relaxed` includes the local arm edit, reimport/deformation checks and actual WebGL front/side/motion captures. Only arm rotation samples changed. Idle duration remains 4.0333333015441895 seconds, walk duration 1 second, and the 24-bone rig remains intact. Reimport checks found zero leg/foot vertex displacement against v2 at five idle and 31 walk samples, and an exact walk loop. Arms now hang lower with modest walk counter-swing. The existing crouched idle stance, held Poké Ball, open hand, face and texture defects remain; this is a better overworld candidate, not polished or photoreal acceptance. The source-sprite fallback is available independently of this model.

`node --test outputs/pokemon-remake/app/character-source.test.mjs`: four tests pass for palette/transparency, flips, 1D/2D tile stride, native culling, and invalid/unsupported data.

See `verification/characters/browser-results.json` and its README for actual-ROM gameplay evidence and runnable isolated capture harness. Screenshots show extracted source actors beside the actual source framebuffer. These verify the standalone renderer and source movement/dialog/transition behavior, not integration with the main task's changing camera, terrain occlusion or furniture heights. Run the primary app's integration smoke checks after applying the patch.

Remaining limits: 2D billboards; no NPC 3D assets or photoreal acceptance; affine/8bpp actor forms are reported unsupported; source mosaic/OBJ blend equations and separate ground-effect sprites are not reconstructed. Only actors active in the original simulation are drawn. No unsupported actors are invented to fill a wider view.
