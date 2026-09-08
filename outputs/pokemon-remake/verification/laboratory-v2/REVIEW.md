# Laboratory V2 Repair

**Status: changes required for the full photoreal target. The scoped vent repair is visibly improved.**

The exported GLB was freshly imported into Blender 4.5.0 and rendered from front, back and elevated gameplay review cameras. All three actual renders were opened and inspected. The blue open-looking recess is fully covered by a closed, subtly beveled red cap fitted to the measured vent rim. The cap preserves the building bounding box. No generated intermediary was used.

Roof-only material reassignment affects 25,552 gray upper-surface triangles: roughness 0.87, zero metallic, reduced dielectric specular. Source color and normal textures are retained. Reflections are less glossy, but the softened broad roof courses remain; this is not restored individual tile construction. Glazing distortions, narrow masonry bands and unverified rear-window details also remain. The cap paint is currently uniformly clean.

## Registration and technical evidence

Original mesh positions survive GLB export/reimport within 1.50e-7 normalized units. The v2 door measurement changes by at most 2.99e-8 normalized units. `door-anchor.json` retains the exact v1 integration anchors under `preservedIntegrationAnchors`; keep those values when swapping the asset. Ground entry in glTF scene/root coordinates remains **[-0.017930665984749794, -8.721854527493633e-8, 0.27358004450798035]**. After the original bottom-centering convention it remains **[0.000310337170958519, 0, 0.30705299973487854]**. Front is +Z; up is +Y. The source warp is PalletTown (16, 13), metatile 684. No runtime/config changes were made.

The exported asset contains 50,180 triangles: the original 49,992 plus 188 in the cap. Both meshes pass a diagnostic UV-seam weld with zero boundary, nonmanifold or degenerate elements. The actual exported meshes are not welded. v1 remains untouched.

`review.json` binds artifact, reference and render hashes; `geometry-comparison.json` and `door-anchor.json` contain numeric evidence. `models/laboratory-v2.blend` is the packed, editable reimported asset with review stage separated into its own collection. The cap is a distinct editable mesh. `repair.py`, `render_review.py`, `compare_geometry.py` and `measure_door.py` reproduce this pass using `/Volumes/Blender/Blender.app/Contents/MacOS/Blender --background --threads 4 --python-exit-code 1 --python <script>` in that order.

Root must inspect the actual town placement and perform independent review. Studio/elevated review renders and valid export alone do not grant acceptance.
