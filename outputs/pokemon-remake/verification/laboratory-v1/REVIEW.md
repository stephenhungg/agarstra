# Laboratory V1 Review

**Status: changes required.** The source layout largely survived, but the actual 3D reconstruction failed parts of the inspected reference. It is suitable for explicitly labeled staging, not photoreal release approval.

One source-conditioned native image-generation call created `environment/laboratory/laboratory-reference-v1.png`. After inspecting it, one authorized Hunyuan3D PBR job produced `models/laboratory-v1.glb`. No paid retry or creature generation occurred. The original map composite and exact 35 source metatile IDs are recorded in `environment/laboratory/source-contract.json`; the source door is metatile **684** at **(16, 13)**.

## What survived

The actual front render retains the low broad yellow building, broad gray roof, red roof vent on the right, four circular upper windows, two lower rectangular window groups, and central green entrance. The rear is a complete closed volume rather than an open front-only shell. The source’s central door placement is preserved closely.

## What failed

The reference’s capped red roof ventilator became a **blue recessed/open-looking top** in the mesh. This is prominent from the elevated camera and must be repaired. The roof’s individual tile construction softened into broad horizontal strips, masonry detail reads as narrow bands, and the glazing has exaggerated irregular reflective shapes. Rear windows and their black center panels are unverified generated details; the dark panels do not imply holes in the mesh.

`front.png`, `back.png`, and `gameplay.png` were all opened and inspected. The elevated image is a representative review camera, not proof of quality in the integrated town view. All three renders and the source/reference hashes are bound in `review.json`.

## Door anchor

Coordinates below are **glTF scene/root coordinates after node transforms**, before runtime centering or scaling. Front is **+Z** and up is **+Y**.

| Point | X | Y | Z |
|---|---:|---:|---:|
| Ground entry | -0.017930666 | approximately 0 | 0.273580045 |
| Visible threshold | -0.017930666 | 0.024536919 | 0.273580045 |
| Ground entry after bottom-centering | 0.000310337 | 0 | 0.307053000 |

The estimate uses 155 green facade triangles. The doorway lies at **50.0323% of asset width**, compared with the source’s centered 50% position. Its threshold projects to approximately `(497.47, 921.17)` in `front.png`, at the lower green entrance. `door-anchor.json` contains the full measured bounds, sampling method, normalization offset, and projection evidence.

For uncentered asset coordinates, use `translation = targetDoorWorld - rotation(scale × anchor)` with target source warp `(16, 13)`. If the importer first bottom-centers the model, use the bottom-centered anchor. Keep scale uniform and leave gameplay collision/warps with the original simulation. The integration owner still needs to test actual laboratory entry.

## Technical evidence and limits

The GLB contains **49,992 triangles**, one mesh/material, and three embedded 4096×4096 PBR maps. `models/laboratory-v1.blend` packs these textures and separates the review stage from the imported candidate. Blender import, save, and all renders completed successfully. A diagnostic weld of UV duplicates produced 24,984 vertices with zero boundary edges, nonmanifold edges, or degenerate faces; the actual asset was not welded or altered.

Imported Blender dimensions are **0.961246 × 0.708144 × 0.473638** normalized units. Those units are not established meters. “Editable” means an imported triangular mesh; the building’s architectural components remain fused.

Repair the vent cap and material/construction defects locally, re-export, and obtain an independent review of the actual town render. Technical import success and recognizable window layout do not override the failed construction/material checks.
