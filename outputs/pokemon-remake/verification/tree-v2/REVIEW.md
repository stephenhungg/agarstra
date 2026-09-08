# Tree v2 — broader silhouette candidate; visual changes required

The revision improves the compact broadleaf silhouette and repeat budget, but **does not pass the photoreal shading target**. The actual Three.js group render is too dark. Leaves still read as large angular blades, and the bark remains too uniform despite its restored normal map. Do not interpret the technical checks as automatic promotion over v1.

## Changes and provenance

The existing `environment/tree/tree.blend` and its author scripts were inspected alongside the actual Pallet Town source image, the town runtime capture, and the earlier generated botanical reference. No generator, new download, or paid job was used for v2.

The existing generated branch scaffold is retained and widened in its upper region. Sixty new tapered branch extensions share vertices with that scaffold; 480 sprigs attach to their terminal branch vertices. The previous foliage is replaced by 3,840 broader curved leaf blades distributed through a rounded crown. New twigs have a geometric attachment to the scaffold, while overlapping branch junction surfaces are not remeshed into a fully manifold botanical structure.

The original embedded bark maps were extracted byte-for-byte from v1. Base-color luminance is remapped to brown, preserving the generated detail, and the normal map is retained at reduced strength. Bark maps are 2K. Leaves use a locally authored 512px vein image with per-leaf tint; these are not photographic leaf scans. Both leaf sides remain opaque, and physical leaf transmission is absent.

The first export dropped the bark normal map and was rendered before that material issue was corrected. Its exact artifact and views are preserved in `first-export/`. The top-level images and metadata correspond to the final corrected export listed below.

## Measured comparison at height 3.8

| Property | V1 | V2 |
|---|---:|---:|
| Height | 3.8 after uniform scale | 3.8 natively |
| Width | 2.684 | 3.591 |
| Depth | 1.995 | 3.499 |
| Triangles per tree | 61,526 | 43,886 |
| Tree triangles for 29 instances | 1,784,254 | 1,272,694 |
| Tree meshes/materials | 2 / 2 | 2 / 2 |

V2 is 11,334,056 bytes with all three image maps embedded. Its trunk root is at ground origin, GLTF +Y up. The crown is intentionally asymmetric; use uniform scaling if the final runtime height changes. Source collision remains owned by the original ROM; this wider visual crown is not a new collision volume.

## Visual review

Actual exported GLBs were used for the front, back, gameplay-angle, and same-camera comparison images. `comparison-v1-left-v2-right.png` uses the same light rig and camera with both trees at height 3.8; v1 is on the left and v2 on the right.

The broader and deeper v2 crown is clear. Brown replaces the mossy green trunk color. However, the larger leaves have conspicuous polygon edges and insufficient material variation, especially in close view. The canopy is overly dense and dark in the Three.js render. Several old bare branch stubs remain visible below it. The new bark is too evenly brown and does not reproduce the fine fissures and color variation of the botanical target. There is no wind motion.

The 29-tree scene shows the broader crowns merging into a continuous perimeter, closer to the source's dense boundary arrangement. It also amplifies the dark foliage problem. This scene contains only trees and a plain ground, so it cannot certify sightlines, path occlusion, building overlap, or final town lighting. Those must be checked by the scene integration owner.

The next visual pass should calibrate leaf albedo and transmission in the actual Three.js lighting, refine the blade silhouette and scale variation, and restore richer bark structure without returning to a green trunk. It should compare against these same views before any promotion.

## Technical evidence

- `export-inspection.json`: actual GLB reimport; exact dimensions, 43,886 triangles, two materials, embedded base/normal/leaf maps, and no external resources.
- `runtime-29.json` / `runtime-29.png`: actual Three.js load of 29 source-positioned instances at 1280×900 with shadows enabled. Observed visible-pass counts: 59 draws and 1,272,696 triangles including the plain ground. Three unique geometries are shared across the instances and ground.
- The isolated synchronous `gl.finish` timing sample recorded median 0.4 ms and p95 0.9 ms over 45 warmed renders on this host. This is not a full-game FPS result; it excludes the original core, terrain, buildings, characters, and other app work. Visible draw counters exclude the additional shadow pass.
- `verify_tree.py` / `verify.log`: repeatable fresh import and render sequence.
- `environment/tree-v2/author_tree.py`: seeded local construction and export.
- `actual-export-review.blend`: editable actual GLB reimport with the review stage.

Final GLB SHA256: `a3e36ae2253ac7a34a73b83ce3ac94ffc584dda1e95dc58d5e0bfde963272aea`.

Preserved v1 SHA256: `0488d72b777a728a65c0789d9688a75f125c9a7ba49fb1f402ba07f4a948193b`.
