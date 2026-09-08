# Charmander existing creator asset — changes required

The actual shipped GLB imports with its 60-bone skin and animation intact. It is **not approved for photoreal presentation or battle animation**. No model or material changes were made during this review.

The source is the creator-provided Charmander rig, not generated geometry and not geometry extracted from the ROM. The existing CC BY-NC 4.0 attribution remains required:

> Charmander rig created by Milos Cerny and downloaded at http://www.miloscerny.com/
> 3D model created by Guilherme Lauck https://sketchfab.com/guilauck

## Animation findings

The single clip is named `Armature|Take 001|BaseLayer`. Its GLB key times run from **0.0333333 to 6.7 seconds**, corresponding to Blender frames 1–201 at 30 fps. There are 180 channels for 60 bones. Only 35 local rotation channels change materially; the right arm and right leg stay essentially fixed while multiple left-side controls, head, tail, belly, and one eye move in separate intervals. This pattern is consistent with a **rig/control demonstration**, an inference from the actual channels and sampled poses. The source name does not identify the intended action.

- Frame 51 / 1.7 s: the head tilts sharply backward, the neck stretches, and the throat has visibly compressed/stretched surface detail. This is not a suitable idle pose.
- Frame 151 / 5.0333333 s: the left shoulder/arm moves from the initial pose, while the right side remains largely fixed. This does not establish a battle action.
- Frames 1, 101, and 201 are effectively the same arms-out pose. Matching loop endpoints alone does not make the intermediate movement a valid idle.
- No validated idle, attack, hit, faint, or locomotion segment was identified. Do not rename or randomly autoplay the full clip as any of these.

For an explicit **static asset inspection preview only**, evaluate the original clip at `1 / 30` second and pause it. That is the verified initial pose, not a finished battle stance. The runtime should keep its existing source sprite candidate until authored battle poses/clips are reviewed. If cloning this skinned asset later, preserve its armature hierarchy and skin bindings; move and scale an outer actor group rather than individual joints.

## Skin verification

The script opened the creator-derived source Blender file, sampled its evaluated mesh, reimported the actual GLB into a fresh scene, and compared both at frames 1, 26, 51, 76, 101, 126, 151, 176, and 201. Exported vertices were matched to nearest source vertices in the initial world-space pose, then that correspondence was held fixed. Coincident source vertices can make this correspondence ambiguous; these are sampled geometric checks, not a proof of every interpolated frame.

The source has 6,997 vertices; UV seams produce 7,767 exported vertices. The original exporter reduced 711 vertices with more than four nonzero influences to four. The largest discarded source weight sum is 0.121971. Exported weight sums are normalized within 1.24e-7 and all checked weights are finite.

Maximum frame-1 correspondence error is 0.00000367 model units. The largest sampled deformation difference is **0.00392847**, at frame 51, approximately **0.66% of the resting model height**; the mean difference at that frame is 0.00001195. The skin does not explode or separate in the inspected renders, but weight trimming is not lossless. The awkward frame-51 neck motion is also present in the source-driven pose and is not explained by weight trimming alone.

## Orientation and appearance

Facing direction is **GLTF scene +Z**, with **+Y up**, after preserving all shipped node transforms. Blender's imported equivalent faces -Y with +Z up. The GLB has an existing Armature root rotation and 0.01 scale; do not strip those transforms or apply another centimeter conversion. Rest height is 0.595469 scene units. Feet extend to GLTF Y approximately -0.001271, so an outer placement group may apply +0.001271 vertically before any whole-actor scaling.

The actual GLB front/back renders show overly glossy skin with coarse scale detail, a stiff arms-out stance, dark eyes without convincing depth, and a solid orange textured tail tip rather than a luminous, animated flame. The rear view retains skin and tail geometry, but confirms that the flame problem is not just front-view occlusion. The material contains no emissive flame treatment. No photoreal/source-identity acceptance is implied by successful skin import.

## Evidence

- `glb-frame-1-front.png`: actual reimport, initial pose.
- `glb-frame-51-front.png`: actual reimport, head/neck deformation.
- `glb-frame-151-front.png`: actual reimport, shoulder/arm displacement.
- `glb-frame-1-back.png`: actual reimport, back and tail.
- `reimport-review.blend`: editable reimport with camera, neutral stage, original clip, and packed textures.
- `skin-verification.json`: source/export sampled geometry comparisons.
- `glb-structure.json`: direct GLB animation and weight-accessor inspection.
- `verify_export.py` and `skin-verification.log`: reproducible Blender check and completed run.

Verified GLB SHA256: `95ea02802032e55fcaaa06d8f6b53df89b5bf130b1bb22787ab5d399c9e7a3f0`.
