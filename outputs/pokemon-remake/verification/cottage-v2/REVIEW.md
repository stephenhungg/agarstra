# Cottage V2 Review

**Source-layout improvement confirmed; photoreal changes still required.** One authorized Hunyuan3D PBR job produced this candidate. V1 remains unchanged.

The actual mesh preserves the revised reference’s left-hand entrance, roof ridge parallel to the facade, long horizontal front eave, pale blue siding, three upper windows, and two lower-right windows. The prior right-hand entrance, front-facing gable, and porch canopy are gone. This is a substantially better match to `source/PalletTown-source.png`.

## Door anchor for integration

The following coordinates are in the original **glTF scene/root space after node transforms**, before runtime centering or scaling. Front is **+Z**; up is **+Y**.

| Point | X | Y | Z |
|---|---:|---:|---:|
| Ground entry | -0.1785757 | 0.0000000 | 0.2211020 |
| Visible threshold | -0.1785757 | 0.0408533 | 0.2211020 |
| Ground entry after bottom-centering | -0.1859927 | 0.0000000 | 0.2299855 |

The estimate comes from 323 brown base-color triangles on the lower front facade. Its center lies at **29.612% of total asset width**, compared with the original doorway’s **30%** position: tile-center x=6.5 within house extent x=5..10 (exclusive right edge). Projecting the measured threshold into `front.png` places it at approximately pixel `(361.86, 961.29)`, at the bottom of the visible wooden door. The trim and step extend beyond the detected leaf; this is an entrance anchor, not collision geometry.

For original asset coordinates, place the model with `translation = targetDoorWorld - rotation(scale × anchor)`. If runtime code first subtracts the model’s bottom-center, use the bottom-centered anchor instead. Keep scale uniform. `door-anchor.json` records both forms, the normalization offset, projected review coordinates, sampling method, and uncertainty. The integration owner subsequently verified both source door anchors at runtime grid coordinates `(6, 7)` and `(15, 7)`, plus actual house entry into `PalletTown_PlayersHouse_1F`. The current matching-hash `verification/workbench/results.json` and workbench screenshot were inspected. The image-fraction comparison uses tile edges; runtime uses integer tile-center coordinates. This asset task did not edit the app.

## Visual findings

- `front.png`: the source-facing layout is much closer, and the facade is cleaner than V1. The roof still has softened, fused grooves and broad glossy highlights rather than the reference’s crisp terracotta construction.
- `back.png`: the rear is a complete closed volume with six generated windows. Those windows are inferred, not established by the single reference or ROM view. No duplicated rear door or missing wall was observed.
- `gameplay.png`: the long roof/eave silhouette and left entrance survive the elevated camera. This is a representative review camera, not the live town render.
- Glazing has tree/sky reflections baked into opaque base-color textures. Those reflections remain fixed across views and need separate material treatment for photoreal acceptance.

## Technical result

The original generated GLB contains **49,998 triangles**, one mesh/material, and three embedded 4096×4096 PBR maps. The editable `.blend` packs all three maps. A diagnostic weld of UV duplicates gives 24,833 vertices with zero boundary edges, nonmanifold edges, or degenerate faces; the asset itself was not welded or changed.

Imported Blender dimensions are **0.912268 × 0.578227 × 0.700651** units. These are normalized source units, not verified meters. The model root is grounded with a small horizontal offset from its bounding-box center. No deformation or scale correction was applied.

`review.json` records current hashes, checks, defects, and the single generation receipt. `mesh-inspection.json` records exact bounds and camera settings; `export.json` records the GLB material/export checks. Reproduce images with `render_review.py` and the anchor estimate with `measure_door.py`.

Source-driven staging, doorway registration, and actual original-game house entry have now passed in the integration owner’s matching-hash workbench report. The town capture shows the corrected source-facing silhouette. Roof construction and window/material response still need revision before this candidate can be promoted as photoreal; the full scene remains unfinished.
