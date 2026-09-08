# Trainer v3 relaxed-arm candidate

This candidate lowers the upper arms and relaxes both elbows for overworld presentation. The walk adds a modest opposing arm swing. It is an isolated alternative to v2, not an accepted art release or a gameplay integration change.

## Provenance and ownership

- Source: the canonical `trainer-direct-v2.glb`, SHA256 `fd14343ce1c070bdd3bd51c6c01b8c871bf26f81f7206c57466bb33270c1fe74`.
- The underlying provider-generated character was conditioned on the extracted FireRed trainer sprite; it is not recovered ROM geometry. Existing attribution and licensing remain applicable.
- Output: `../../models/trainer-direct-v3.glb` and a Blender-reimported editable `../../models/trainer-direct-v3.blend`.
- No original file, gameplay simulation, avatar module, camera, or main application was modified.

## Reproduction

From any working directory:

```sh
"$BLENDER" --background --python /path/to/verification/trainer-relaxed/relax.py
"$BLENDER" --background --python /path/to/verification/trainer-relaxed/verify.py
NODE_PATH="$TRAINER_NODE_MODULES" "$TRAINER_NODE_MODULES/electron/dist/Electron.app/Contents/MacOS/Electron" /path/to/verification/trainer-relaxed/webgl.cjs
```

Set `TRAINER_SOURCE_GLB` to the verified v2 GLB when the worktree copy is older. Set `BLENDER` to Blender 4.5 and `TRAINER_NODE_MODULES` to the existing app's `node_modules` (containing Three.js and Electron). The scripts resolve asset/output paths from their own locations. The source is hash checked. The author script directly edits only the four arm/forearm rotation channels using Blender's quaternion math, then imports the resulting GLB into Blender. This deliberately avoids a full Blender animation re-export changing the original idle timing. `relax.py` is the authoritative reproducible source; the `.blend` is the reimported inspection/editing scene.

## Verification actually run

- Reimport into Blender 4.5: valid mesh and 24-bone rig.
- `verify.py`: 4,839 leg/foot vertices match v2 exactly at five idle samples and all 31 walk frames; maximum error 0.0. Full deformed walk loop endpoint error 0.0.
- The author script asserts every original binary byte outside the changed rotation data is unchanged. Mesh, skin, textures, root, hips, legs, feet, hands, and existing animation timestamps are preserved. Dense samples are appended only for the four walk arm channels.
- Actual Three.js GLTFLoader/WebGL rendering through Electron: nine front/side idle/walk images. Both clips have 72 tracks, 24 bones, idle duration 4.0333333015441895 seconds, walk duration 1 second. Exact repeated-time pose and walk-loop pose checks pass.
- Reviewed front/side idle, side walk at 0.25 seconds, and front walk at 0.75 seconds: arms sit beside the torso, elbows bend softly, shoulders remain connected, identity/clothing remain readable. No obvious detached shoulder or gross mesh collapse in these images.

## Integration contract

Use the v3 GLB URL in the existing avatar loader. Keep clips `idle` and `walk`, +Y up / +Z facing forward, the existing uniform 1.4-world-unit height target, dynamic foot grounding, source-frame animation clock, and source-position stride calibration. Idle frame-zero height is approximately 1.572858 model units; a fixed 1.4 target implies uniform scale approximately 0.890099. The lower body and stride remain exactly v2, so do not recalibrate movement speed. The GLB hash and current evidence are in `report.json` and `deformation-verification.json`.

## Limitations

The original crouched battle-like idle stance, oversized hat/head, low-detail faceted geometry, open-hand gesture and held Poké Ball remain. Wrists/fingers were not remodeled; some hand angles remain stylized. This improves the raised-arm defect only. Actual map-camera readability, transitions, dialogue, and source-driven movement require integration-owner checks. These isolated renders and sampled tests do not claim continuous gameplay or photoreal acceptance.
