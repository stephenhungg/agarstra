# Charmander v2 — verified idle candidate, visual changes required

This version is usable for **candidate runtime integration with the explicitly authored `idle` clip**. It is not approved as a photoreal or source-identity match. The original v1 model remains unchanged.

## What changed

The creator's 60-bone skin and geometry are preserved. The old rig demonstration action is removed from v2. After inspecting world-space bone axes and shoulder/elbow/wrist positions, both arms were lowered and bent into a symmetric open-hand stance. This avoids interpreting the original left-only control demonstration as gameplay animation.

The new `idle` is a three-second loop at 30 fps, with keys from 0 to 90. Chest rotation is at most 0.7 degrees in total, with small compensating head and arm movement. Legs and actor root remain unchanged. The motion is intentionally restrained; no attack, hit, faint, walking, facial, or flame clips are included.

Normal strength is reduced from 0.65 to 0.18. The original roughness image is remapped into 0.62–0.86, reducing the wet plastic highlights. The original base-color texture is retained, so its coarse scale pattern remains visible.

Only fully distal terminal-tail triangles receive a separate emissive material. The selection is constrained by inspected Tail5 orientation and its isolated spatial region; no body, limb, or main tail faces receive full-body emission. The exact selection and thresholds are recorded in `authoring.json`. This is a localized material treatment of existing geometry, not a flame simulation.

## Actual export verification

The shipped GLB was imported into a fresh Blender scene and evaluated at all 91 frame boundaries. It contains exactly one animation named `idle`, with a zero-second start and a three-second end. All 60 skin bones and 13,760 triangles survive export. The skin is split into two material primitives.

- 1,132 foot vertices have **zero measured travel** throughout the loop.
- Root matrices have **zero measured change**.
- Frame 90 closes on frame 0 with **zero measured vertex error**.
- Maximum idle vertex displacement is **0.004175 model units**, approximately 0.7% of resting height.
- Seven samples compared against the authored Blender skin have maximum error **0.000277 model units**. This uses nearest initial-pose vertex correspondence and can be ambiguous for coincident source vertices; the export still limits skin influences to four.
- Actual exported front, back, inhale, and exhale renders were inspected. No detached skin, exploded geometry, foot sliding, or old demonstration motion appears in those samples.

## Remaining visual defects

The bent-arm stance and reduced gloss are improvements, but the existing mesh still has stylized skull, dark eyes, horns, and teeth that have not passed source-identity review. Slight shoulder/underarm pinching remains. Coarse scales are baked into the original color map. The luminous tail tip still has a solid silhouette and a hard material boundary; it needs a proper flame treatment. These limitations are visible in the saved renders and should remain explicit in the runtime candidate label.

## Runtime contract

Load `models/charmander-existing-v2.glb` and bind only `idle`. Seek or loop it with the source-owned clock; pausing gameplay should freeze the clip time. Use the existing asset hierarchy, skin bindings, root rotation, and 0.01 scale. Place and scale an outer actor group instead of modifying the rig.

Facing is **GLTF scene +Z**, with **+Y up**. Grounding correction is +0.001270899 on Y before whole-actor scaling. All-frame GLTF bounds are:

```
min [-0.2380258, -0.0012709, -0.5193805]
max [ 0.2380238,  0.5949160,  0.1390561]
```

This asset review does not certify the app's actual camera, battle layout, pause, or reset behavior; the runtime owner must verify those after integration.

## Provenance and files

This is an adaptation of an existing licensed creator asset, not a new generation or ROM-extracted geometry. Preserve CC BY-NC 4.0 and the required attribution:

> Charmander rig created by Milos Cerny and downloaded at http://www.miloscerny.com/
> 3D model created by Guilherme Lauck https://sketchfab.com/guilauck

The adjacent `models/charmander-existing-v2.license.txt` records source, license, credit, and modifications. The editable source is `models/charmander-existing-v2.blend`; `actual-export-review.blend` contains the actual GLB reimport and review stage. `author_candidate.py`, `verify_candidate.py`, their logs, `rig-inspection.json`, `authoring.json`, and `verification.json` reproduce the construction and checks.

GLB SHA256: `ad78d6f71b421d5f3ce534806b2f816d160647be282276152dca03a25c6ce7e6`.

Preserved v1 SHA256: `95ea02802032e55fcaaa06d8f6b53df89b5bf130b1bb22787ab5d399c9e7a3f0`.
