# Direct sprite trainer experiment

The single direct-sprite generation finished and produced a usable rigged **candidate**. A locally authored in-place walk is now verified in Blender and actual WebGL. Source identity is recognizable; the result remains stylized and is not photoreal approved. Runtime player placement and control integration are separate checks owned by the main app.

## Artifacts

- `models/trainer-direct-v1.glb`: corrected provider idle, SHA256 `e0928e00efe5acb3d6b0b2fca055185a02da66a31bc6041208d1125f7273e356`.
- `models/trainer-direct-v2.glb`: unchanged v1 mesh/skin/idle plus a locally authored `walk`, SHA256 `fd14343ce1c070bdd3bd51c6c01b8c871bf26f81f7206c57466bb33270c1fe74`.
- `models/trainer-direct-v2.blend`: editable walk authoring rig; its leg display lengths are corrected for Blender IK.
- `environment/trainer-direct/trainer-direct-source.glb`: untouched provider output, SHA256 `c3b5282f1d3d95128a1247a981c0df89fcb31880443de7ff4043e79bab8fcb29`.
- `webgl-*.png`, `webgl-results.json`: actual final-hash runtime renderer captures and deterministic playback checks.
- `walk-verification.json`: fresh final-GLB import, all 31 walk frames, foot/root/loop checks and idle preservation.
- `rig-contract.json`: exact leg bone names/rest transforms, axes convention, dimensions and source-distance phase guidance.

## Direct input and generation provenance

The input is the matching FireRed source `graphics/trainers/front_pics/red_front_pic.png`: one fully clothed trainer, 64×64 indexed pixels. Palette index 0 was composited over white, followed by an exact nearest-neighbor 8× resize. All 262,144 prepared output pixels were checked against the source/white composite; 859 visible source pixels constrain this reconstruction. No concept image was generated. `input-verification.json` and `environment/trainer-direct/manifest.json` preserve hashes and preparation details.

Source ROM SHA1 is `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`, matching source commit `c75f352304d529f6ba92d4f74b9cf8b5c3810788`.

Native `image_to_3d` job `997118f4-c40c-41da-adef-b775bc878a95` ran once, with safety enabled, from 23:21:19 to 23:27:42 UTC on 2026-09-08. Requested settings: 30,000 triangle budget, PBR textures, rig, A-pose normalization and basic Idle preset 0. No second generation, retexture, or provider animation job was submitted. Exact prompt/parameters, upload reference, result URL and process lifecycle are saved under `environment/trainer-direct/`.

The actual result has one mesh, one 24-bone skin, 31,278 exported vertices, 31,112 triangles and one embedded base-color image. It exceeded the requested triangle target slightly and did not supply a normal/roughness/metallic texture set. Requested settings are not treated as delivered features.

## Corrected export defects

The provider idle contained Hips scale 1.1765. The skill's local GLB fix normalizes that scale to 1 and divides the matching root translation accordingly. The semantically identified provider preset-0 Idle clip is named exactly `idle`; it is not an unrelated first-clip fallback.

The provider material defaulted to metallic and included whole-body emission. v1 removes emission, sets metallic=0 and roughness=0.8, normalizes specular color, and preserves the original base-color texture. This reduces plastic/gloss artifacts but cannot create missing cloth detail or physically separate skin, fabric and shoes.

Initial Blender measurements accidentally included an importer-created bone display mesh. Final measurements explicitly include only the skinned character. Raw render evidence is preserved under `raw-provider/`; it is not final candidate evidence.

## Locally authored walk

The authoring script derives hip/knee/ankle positions from the actual posed skeleton. It measures ankle-to-sole offsets from weighted skin vertices, fits each knee pole angle against the original knee, and solves two-bone ankle-target IK. It does not assume that local bone axes equal world axes.

A failed first test exposed Blender importer bone display lengths approximately 100× the child-joint spacing. Four thigh/shin lengths were repaired from measured child positions; the largest armature-space rest-matrix roundtrip difference is 0.001007 (centimeter-based rig coordinates). Knee calibration then matched within 0.8 mm. The rejected length-unfixed preview is retained separately and must not be used.

Walk is a one-second, 31-keyframe, in-place cycle with alternating stance/swing, 0.32 m ankle travel per leg and approximately 0.084 m foot lift. The upper body retains the source battle stance with one arm extended and one holding a ball. This is visibly functional leg locomotion, not a polished natural full-body walk.

Blender NLA re-export altered the idle timing during testing. The final GLB therefore retains the exact v1 mesh, skin, rest transforms and idle data, merging **only** the new walk tracks by matching bone names. `trainer-walk-blender-export.glb` is an intermediate, not the final runtime asset.

## Verification that ran

Fresh final-GLB Blender import:

- `idle` and `walk` both exist, with 24 bones and the intact skin.
- Original idle vertices match v1 exactly at all five sampled frames.
- Walk skin moves up to 0.3548 m; loop endpoints match exactly.
- Horizontal root travel is below 0.00000006 m.
- Left/right planted sole errors are at most 0.000520 / 0.000218 m.
- Maximum foot lifts are 0.08391 / 0.08410 m.
- Each ankle travels approximately 0.32 m through the stride.

Actual Electron/WebGL:

- Seven final-hash views rendered, including front/back and four walk phases.
- Explicit `idle` duration is 4.033333 seconds; `walk` is 1 second.
- Pausing at the same supplied time returns exactly the same bone transforms.
- Walk 0 and 1 second match exactly; 0 and 0.25 seconds differ.
- Actual GLB front/back images were inspected. Hat, red vest, dark shirt, blue jeans, shoes and backpack remain recognizable. The face, hands, faceted cloth, asymmetric stance and single-material appearance remain quality limitations.

Front is GLTF +Z and up is +Y. Preserve the full hierarchy and use an outer placement group. Initial idle height is 1.572857 model units, with a +0.010743 initial grounding offset. Walk soles are authored around Y=0. For source-distance synchronization, a nominal full cycle travels 0.64 model units; account for the actor's uniform scale before converting source world distance to walk phase. The idle itself is not perfectly foot-planted, so scene placement should handle its changing contact height.

## Reproduce local authoring and checks

From repository root, without making another generation request:

```sh
python3 outputs/pokemon-remake/verification/trainer-direct/correct_export.py
/Volumes/Blender/Blender.app/Contents/MacOS/Blender -b -P outputs/pokemon-remake/verification/trainer-direct/author_walk.py
python3 outputs/pokemon-remake/verification/trainer-direct/merge_walk.py
/Volumes/Blender/Blender.app/Contents/MacOS/Blender -b -P outputs/pokemon-remake/verification/trainer-direct/verify_walk.py
outputs/smb3-demo/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron outputs/pokemon-remake/verification/trainer-direct/webgl.cjs
```

The WebGL harness intentionally binds the reviewed hash. A changed export must receive new evidence rather than silently reusing this result. Regeneration is not required to use or inspect these saved artifacts.
