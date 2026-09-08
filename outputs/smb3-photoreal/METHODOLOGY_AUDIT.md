# SMB3 Reconstruction Methodology Audit

September 8, 2026 · Read-only implementation audit, current 0.4 assets and runtime

**The central failure was the production loop: we optimized for completed scripts, exported meshes and working integration before establishing an acceptable visual target.** Concurrency accelerated that loop. It did not supply missing art direction, character construction or visual acceptance criteria.

This audit inspected worker prompts and selected execution logs, authoring scripts, material helpers, build and promotion code, semantic mapping, animation generation, recorded reviews, current runtime screenshots and Blender contact sheets. External sources below establish relevant graphics and production principles. Visual descriptions are reviewer judgments; code behavior and counts are directly verified. No new model-generation benchmark or frame-by-frame gait measurement was performed.

**What we actually built**

The implemented path is ROM/PPU extraction → source-specific object interpretation → text-directed Blender Python authoring → procedural geometry and baked material swatches → structural validation and contact sheets → GLB replacement renderer in Three.js, with the original ROM running gameplay in JSNES. A later pass added rigid-part animation.

The current registry contains 73 models across 25 families. Five character models contain 17 animation clips. All 25 recorded family reviews have `photorealApproved: false`. The original 24 author jobs did run concurrently; their output was first-pass asset scripts. A generated-image-to-3D hero workflow and Unreal integration are not present in the delivered pipeline.

The distinction matters: the ROM supplies discrete pixel patterns, object state and game rules. NES pattern tiles contain two-bit color indices, not hidden realistic geometry, anatomy or material measurements. Those properties need a new authored interpretation. Better binary extraction improves source correspondence but cannot uniquely recover that interpretation. [NESdev pattern-table documentation](https://www.nesdev.org/wiki/CHR)

RTX Remix is a useful architectural comparison, with an important difference: its runtime can capture geometry, cameras and lighting from supported older 3D games. Our NES source does not provide those scene inputs. We must build that scene layer ourselves. [NVIDIA runtime explanation](https://www.nvidia.com/en-us/geforce/news/rtx-remix-runtime-open-source-download/)

**Ranked causes and concrete evidence**

| Priority | Finding | Evidence and visible consequence |
| --- | --- | --- |
| 1 | Visual approval did not control promotion. | [build_queue.py:25](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools/build_queue.py:25) validates structure; line 34 marks a build done while inspection is pending. [assemble_runtime.py:13](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools/assemble_runtime.py:13) admits done builds without checking visual approval. Reviews correctly identified miniature/figurine characteristics, but those findings did not block delivery. |
| 2 | Authors were denied their own render-and-revise loop. | The Mario worker prompt explicitly forbids running Blender and requests completion within one focused turn. Syntax correctness was the immediate completion criterion. Central rendering existed, and some later refinements happened, but there was no repeated author → actual runtime image → critique → revised model loop until the target was met. |
| 3 | Detail was added before form was solved. | [Mario source:250](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/sources/character-kit-1.py:250) builds a multipart character; its manifest acknowledges overlapping anatomical joins and absent deformation weights. The preview visibly exposes segmented shoulders and assembled facial parts. Separate stitching and boot details are more developed than the complete figure. At gameplay size, that small detail contributes little while silhouette and proportion dominate. |
| 4 | Generic material recipes substituted for material-specific design. | [Mario source:152](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/sources/character-kit-1.py:152) derives skin, hair, whites, iris and pupil from the leather recipe, with different parameters. [pbr_common.py:45](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools/pbr_common.py:45) primarily varies color, roughness and bump with noise; line 72 bakes a flat swatch. Portable PBR maps exist, but they do not encode object-specific folds, anatomical detail, coherent wear or correct optical structure. |
| 5 | Runtime assembly changes the visual design. | [photoreal-renderer.js:220](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-demo/src/photoreal-renderer.js:220) independently scales environment X/Y to source rectangles. Characters preserve aspect ratio but fit inside their source box. Scenery uses a few depth layers. The current image shows a large shrub dome replacing the original multi-peak grouping, a small Mario, opaque cloud geometry and a thin repeating ground strip. |
| 6 | Animation was added after static model construction. | [animate_characters.py:89](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools/animate_characters.py:89) groups rigid parts into pivots. Walk/run uses opposing limb rotations; there are no articulated knee/elbow chains or skin weights. The Piranha bite scales its existing head. Clips are real, but the current construction limits expressive motion. Foot slipping is a risk inferred from the algorithm, not a measured result of this audit. |
| 7 | Evaluation used a different view and a different success criterion. | [style.json](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/design/style.json) requests a three-quarter presentation and a side-view runtime. Contact sheets normalize objects independently and use a raised camera with studio lighting. Runtime checks establish loading, drawing, timing and state selection. They do not establish visual quality, planted feet, material plausibility or resemblance at gameplay size. |

**Why valid PBR assets still look like toys**

PBR defines how material parameters interact with light. It also supports deliberately non-photoreal imagery. Epic's documentation explicitly makes that distinction and recommends physically meaningful material inputs. Accordingly, the existence of roughness and normal maps is not evidence of realism. Shared noise can provide useful variation, but the current recipe cannot repair disconnected shoulders, an oversized foliage mass or weak facial construction. [Epic's PBR guidance](https://dev.epicgames.com/documentation/en-us/unreal-engine/physically-based-materials-in-unreal-engine)

The exported material path is a strength: maps are packed and visible in actual GLB renders. There is no evidence here that a general loss of textures during export explains the whole result. The current renderer also has shadows, tone mapping and environment lighting. The problem is how those tools and assets work together. Switching engines alone would preserve the weak geometry, proportions and motion.

Valve's game-art guidance emphasizes recognizable silhouettes and controlled value contrast. Its relevance here is readability, not adopting Dota's art style. We prioritized stitches, leaf counts and surface noise before verifying the broad shapes and character emphasis at the camera distance the player actually sees. [Valve's character-art guide](https://help.steampowered.com/en/faqs/view/0688-7692-4D5A-1935)

**Fidelity also has unresolved semantic gaps**

Mario's suit is extracted but the renderer chooses the same body model regardless of suit. Pipe orientation and rim information are extracted but are not applied by the generic pipe placement path. Ducking, skidding, carrying and flight are outside the current pose vocabulary. These are concrete source-fidelity gaps, independently of whether the artwork looks good. World-map coverage also remains incomplete.

The death fallback repair was valid: a missing object should not silently replace an entire remodeled frame. But preserving the current scene in 3D only repairs continuity. It does not improve the underlying art.

**What should survive**

Keep the emulator, source provenance, object-state adapter, exact sprite ownership, deterministic animation clock, GLB loading and reload, editable Blender files, packed textures, batching, resumable queue and structural regression checks. These are useful foundations. Relabel their outputs as technical evidence; the 39 passing app checks should never have been used to imply that the visual complaint was resolved.

**A better production experiment**

1. Establish one target frame and a short gameplay sequence: idle, walk, accelerate, jump, land, stomp and death. Fix camera, framing, lighting direction, material palette and relative visual proportions first. Decide explicitly how close the art must stay to the source silhouette while preserving original collision and timing.
2. Build one Mario, one Goomba and one screen of environment. Review plain shaded silhouettes at actual runtime size before textures. Then review material separation and lighting in the runtime. The hero must remain readable against the scenery.
3. Build deformation-ready character topology and the required rig before final detail. Author strong poses and transitions; inspect joints, contact, weight and stride against ROM travel. Blender skinning uses bone influence over vertices, which is the missing capability in the current rigid-part body. Gameplay variables can then drive blending between authored motions. [Blender armature deformation](https://docs.blender.org/manual/en/4.1/animation/armatures/skinning/parenting.html), [Epic animation blending](https://dev.epicgames.com/documentation/en-us/unreal-engine/blend-spaces-in-unreal-engine)
4. Keep procedural generation for tasks it demonstrably handles well: modular props, repeated terrain details, variations and export automation. For difficult organic forms, compare a carefully authored/sculpted model with a reference-conditioned 3D candidate on the same target and review process. Do not assume either wins before inspection.
5. Make visual acceptance mandatory for release. Require current asset hashes, runtime captures at agreed camera size, source-shape review and the motion sequence. A failed gate returns to the author with specific visible defects. Technical validation remains a separate required gate.
6. Scale the accepted construction patterns. Parallel workers can then make bounded variants, materials, topology cleanup, rigs and independent visual reviews using a proven exemplar. Measure accepted integrated assets per unit effort, rather than script completion or raw model count.

Reference-conditioned generation is a credible experiment, not a guaranteed rescue. Microsoft's TRELLIS.2 documents image-to-3D and material generation; its listed local requirements include Linux, CUDA and an NVIDIA GPU with at least 24 GB memory. Its published timing is hardware-specific and is not a benchmark of our Mac, characters or end-to-end asset readiness. No such job was launched during this audit. [Microsoft TRELLIS.2](https://github.com/microsoft/TRELLIS.2)

“95% fidelity” needs a definition before it can be an acceptance target. Keep source behavior and coverage, silhouette/identity, visual believability, animation quality and frame performance as separate measures. There is no photoreal ground-truth image hidden in this ROM against which a universal 95% score can be computed.

**Evidence inspected**

- [Current gameplay capture](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/verification/animated-live/demo.png)
- [Mario, cap and boot contact sheet](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/families/character-kit-1/preview.png)
- [Goomba and Koopa contact sheet](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/families/creatures-1/preview.png)
- [Animation pose contact sheet](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/animated/pose-contact-sheet.png)
- [All recorded family reviews](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/visual-review.json)
- [Technical smoke results](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/verification/animated-live/smoke-results.json)
- [Extraction verification](/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-rom-assets/EXTRACTION.md)

The recommended next deliverable is one visually accepted playable scene. Further catalog expansion should wait for that acceptance.
