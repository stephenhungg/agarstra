# Direct sprite trainer experiment

One native `image_to_3d` job is running. No model quality or runtime readiness is claimed yet. This experiment uses the matching FireRed source trainer sprite directly, not a generated concept image. The playable app does not depend on this generation finishing.

The source PNG is the single fully clothed trainer in `graphics/trainers/front_pics/red_front_pic.png`, 64×64 indexed pixels. Palette index 0 is interpreted as transparency and composited over white. A nearest-neighbor 8× resize to 512×512 preserves visible source colors and silhouette exactly. `environment/trainer-direct/manifest.json` records ROM/source provenance, PNG hashes, preparation, style formula/token, the complete texture prompt and model parameters.

Job ID: `997118f4-c40c-41da-adef-b775bc878a95`. The initial CLI process is PID 98819; `submission.json` records its lifecycle and invocation. Do not rerun `launch.py` or create another job after a tool observation timeout. Inspect this saved job handle instead. Safety is enabled. If moderation rejects the request, stop; do not retry through another prompt/provider.

Requested output: one textured humanoid, 30,000 triangle remesh budget, PBR materials, A-pose normalization, full rig, basic animation preset 0 (`Idle`). The texture prompt preserves red/white cap, red vest, dark shirt, blue jeans and sneakers, with realistic cloth/denim/rubber. That request is not evidence that the mesh, skin or animation actually meets it.

`review_blender.py` is prepared to import the actual returned GLB, preserve the rig, record meshes/bones/clips/bounds and sampled deformation, render front/back views, and save the editable Blender inspection scene. It has not yet run because no result GLB has arrived. No walk/extra-animation generation is authorized for this pass.
