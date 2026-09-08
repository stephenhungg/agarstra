# Implementation Status: Prototype and Production

User-confirmed project status, September 8, 2026. This describes the Agarstra reference implementation, not universal support across ROMs. Reinspect current code and evidence before reporting new progress.

**We have an end-to-end prototype. The full high-fidelity production pipeline is incomplete.**

## Working today

- ROM → extracted graphics and game state, with source provenance.
- Parallel workers → Blender scripts → models and textures.
- Blender → GLB → playable renderer, driven by original gameplay.
- Basic animation, asset reload, technical validation, and app packaging.

These capabilities establish a working path through the system. Their existence does not prove complete game coverage, convincing animation, or shipping-quality art. Preserve the recorded scope of technical checks rather than applying an old pass to changed assets.

## Missing or incomplete

| Connection | Current limitation | Evidence needed to close it |
| --- | --- | --- |
| Visual reference → approved model | Workers do not automatically iterate against a concrete target. | A worker receives a target image and actual runtime captures, critiques visible differences, revises its source, and repeats until the scoped criteria pass. |
| Quality enforcement | Implemented in the SMB3 assembler, both GLB loaders/reload paths, and packaging. Existing assets remain unapproved. | Synthetic consumer tests verify missing/failed/stale rejection, runtime binding, exact-byte loading, revocation and rollback. Real art acceptance remains separate. |
| Character production | Deformation-ready topology, rigs, and convincing animation are incomplete. | Inspect exported deformation and motion in the playable camera across the required states; basic rigid-part clips alone do not establish this. |
| Game mapping | Reconstruction covers a limited area; forms, actions, and other scenes remain unsupported. | A scene/form/action coverage inventory backed by replay and interaction checks, with unsupported cases explicit. |
| Image-to-3D generation | Not implemented. | A real generation job whose result goes through editable cleanup, export, runtime inspection, and provenance recording. Do not describe Blender-script generation as image-to-3D. |
| Unreal integration | Not implemented; the current renderer is Three.js/Electron. | A playable Unreal integration driven by original simulation, with imported assets and verified state/timing correspondence. |

## Priority production connection

**Render → visual critique → revision → acceptance** is the largest missing connection. Prove it on a representative scoped asset/scene before scaling production. Return actual render evidence to the author, record actionable defects against a concrete target, and associate each review with current candidate hashes. Iterate within a bounded budget; an unmet criterion remains failed or pending when that budget ends.

Separate candidate builds from accepted release assets. Staging a failed candidate for inspection is allowed; promoting it as accepted is not. The SMB3 enforcement path is now implemented. Use its production assembler and package commands; candidate preview requires an explicit prototype profile. See `outputs/smb3-photoreal/PRODUCTION_PIPELINE.md` for its contract and commands.

The pipeline is not production-complete until it reliably produces assets that meet the requested shipping criteria. Packaging a technically working prototype is still useful and may be the requested deliverable; label it accurately.

Image-to-3D and Unreal are separate missing capabilities, not automatic prerequisites for fixing the review loop. Follow the user's chosen implementation scope and do not silently migrate the renderer or start external generation jobs merely because these gaps are listed.

## Skill tooling added in this overhaul

The skill now includes a portable hash-bound evidence checker and isolated accepted-bundle publisher, with synthetic regression tests. It verifies explicit technical/visual evidence contracts and labels prototype bundles separately. It does not inspect art or replace the author queue. The game now integrates this contract into assembly, runtime reload and packaging, including an actual JavaScript verifier check before assembler publication. A demonstrated real render/critique/revision/acceptance cycle remains production work. Do not mark the full pipeline complete because enforcement tests pass.

## Portable runner implementation

A portable supported-NES source-reconstruction runner now ships inside the skill. It was exercised from the downloaded ZIP in a separate directory on Mario Bros. (mapper 0), with no SMB3 state adapter or repository imports. It extracted 512 raw CHR tiles, observed 177 palette variants during a 300-frame replay, and built 170 nontransparent GLBs in Blender. The generated player passed exact source-frame comparison during tested title/gameplay states. Mapper 4 observer behavior is also tested on SMB3.

The default Codex authoring path was exercised with two independent jobs/four source tiles. Both first renders received revision feedback, both authors revised their scripts, and both subsequent renders passed source-relief inspection. This closes a runnable render/critique/revision loop for that narrow source-reconstruction scope, not semantic creature or photoreal asset production. The explicit `--author source` path performs deterministic relief generation without AI review.

Still unsupported: arbitrary Nintendo systems, general binary decompilation, automatic semantic object/scene recovery, and whole-character 3D inference. See [portable execution](portable-runner.md). Do not present the portable relief demonstration as the complete product promise.
