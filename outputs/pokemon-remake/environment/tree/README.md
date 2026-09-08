# Pallet Town Broadleaf Tree Candidate

`tree.glb` is the runtime candidate: 5 m tall, bottom-centered, glTF Y-up, two meshes/materials, 61,526 triangles. Its size is approximately 43 MB, including three 4096 px provider PBR textures. Reuse its geometry/materials between instances; runtime performance has not been measured.

One built-in imagegen reference and one paid native Higgsfield Hunyuan3D v3 job were used. The provider returned a bare trunk/branch scaffold despite the leafy reference. The final asset retains that generated scaffold, reduces its bark topology, and adds 7,200 individually curved leaf blades and 900 twig sprays in Blender. Foliage colors are vertex attributes, so the export uses two draw primitives and no alpha sorting.

This is **not photoreal-approved**. Front, rear and elevated views of the reimported GLB were inspected. The crown is too tufted compared with the reference; lower branch stubs and unusually green upper bark remain visible. Leaves lack vein textures and translucency. The asset is static. Runtime camera, lighting, repetition and performance still require review. See `visual-review.json`.

`tree.blend` contains editable geometry and the inspection setup. The inspection floor/lights/camera are excluded from `tree.glb`. `tree-hunyuan-source.glb` preserves the unmodified provider result. `generation-job.json` and `reference-prompt.txt` preserve generation provenance.

To reproduce the local modeling pass, run `inspect_tree.py`, then `add_foliage.py`, then `finalize_tree.py` with Blender in that order. The scripts currently target the project checkout at `/Users/stephenhung/Documents/GitHub/agarstra`. They overwrite the corresponding tree candidate and evidence inside this directory; do not run `finalize_tree.py` twice on an already finalized scene.
