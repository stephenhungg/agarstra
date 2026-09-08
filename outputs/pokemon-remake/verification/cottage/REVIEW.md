# Cottage Candidate Review

**Status: changes required.** This is a successfully imported, editable candidate, not an accepted photoreal recreation of the Pallet Town player house.

The original `models/cottage.glb` remains unchanged. `models/cottage.blend` contains its imported mesh and packed textures, plus a separately named review stage and three cameras. The model is one fused triangular mesh; “editable” does not mean its windows, door, gutters, roof tiles, and walls are separate architectural components.

## Inspected evidence

- `front.png`: the generated cottage reference is recognizable, including the right-side door and porch, upper front window, side windows, and terracotta roof. Roof tiles and ridge caps are swollen and irregular, porch tiles look wrinkled, and timber/window edges are softened. Bright glossy roof streaks differ from the restrained material response of `references/cottage-v1.png`.
- `back.png`: a complete closed rear volume exists, with a continuous roof and blank rear/left walls. There are no obvious missing faces or duplicated front door. These unseen walls are generated assumptions; no supplied reference establishes their correctness.
- `gameplay.png`: the elevated orthographic view remains recognizable, but the soft, glossy roof occupies most of the silhouette. This is a review camera, not a substitute for inspecting the integrated town view.
- `source/PalletTown-source.png`: the intended player house has its doorway left of center, at source tile x=6 within the building’s x=5..9 footprint. The candidate door is on the right. The source also has a different roof ridge/eave/front silhouette; the candidate puts a triangular gable at the front. These are blocking source-identity problems already present in the generated reference.

## Technical and placement findings

The import has 49,970 triangles, 40,356 raw vertices, and three packed 4096×4096 maps: base color, normal, and metallic/roughness. A diagnostic weld of UV-seam duplicates produced 24,793 vertices and found zero boundary edges, nonmanifold edges, or degenerate faces. The actual asset was not welded or otherwise altered.

Blender bounds are **0.709469 × 0.786045 × 0.777041** units. The source root is at `(0, 0, 0)`, with its base effectively at zero. Its horizontal bottom-center is `(-0.0311105, 0.0347605)`, offset `0.0466492` from the origin. Front is Blender `-Y`; up is `+Z`. The original glTF equivalents are front `+Z`, up `+Y`.

These are normalized source units, not established physical meters. A hypothetical six-meter height would require uniform scale `7.7216`; that number is illustrative, not an approved gameplay scale. No scale change or footprint deformation was applied. Door/collision registration must be solved explicitly rather than stretching this building until its bounding box fits.

## Required revision

Correct the source-aligned facade, entrance anchor, and roof orientation first. Rebuild the roof as clean construction geometry, then repair roughness, normals, and smeared surface detail under comparable lighting. Specify rear construction if those views are reachable. Re-export and inspect the corrected asset in the actual town camera before promotion.

`review.json` records the reviewed hashes, individual checks, defects, placement findings, and limitations. `mesh-inspection.json` records import measurements and camera/render settings. Reproduce these Blender views with `render_review.py`; the script reads the existing GLB and never overwrites it.
