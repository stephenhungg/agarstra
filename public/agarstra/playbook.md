# agarstra — The playbook

Old worlds. New dimensions.

A reusable agent skill for turning ROM graphics and verified game state into editable Blender assets and playable 3D remakes. The original game remains in charge of movement, collisions, rules, and timing.

## Start here

Download `agarstra-rom-remake.zip` from the landing page. Extract the `rom-remake` folder into your agent's skills directory. In Codex, that is normally `~/.codex/skills/`. Then invoke `$rom-remake` from the repository where you want to work.

Example request:

> Use $rom-remake to inspect my local ROM and existing project. Establish a provenance-linked, playable prototype for one bounded scene. Keep original gameplay authoritative, and record what is and is not verified.

Bring your own ROM, a compatible emulator/game adapter, and Blender when you are ready to author assets. The skill coordinates the workflow; the download is not a universal converter, hosted service, emulator, or bundled game. Its SMB3 notes describe the reference implementation, not dependencies every project must use.

## The connected workflow

1. Extract graphics and game state, keeping source hashes, byte/bank references and reproducible observations.
2. Give parallel workers bounded asset tasks with shared scale, pivots and references.
3. Build editable Blender sources, textures and GLB exports.
4. Render with the original simulation controlling gameplay.
5. Inspect actual images and motion, revise candidates and record version-bound acceptance.
6. Validate reload, controls, coverage and the packaged app.

## What works today

The reference prototype connects ROM extraction, source provenance, parallel Blender authoring, GLB import, original-gameplay-driven rendering, basic animation, reload, technical checks and local app packaging.

## What remains in development

The complete high-fidelity production pipeline is unfinished. Workers do not yet reliably iterate against a concrete visual target; the existing app's asset consumers still need quality enforcement. Character deformation and animation, complete game mapping, image-to-3D generation and Unreal integration remain incomplete or unimplemented.

The skill now supplies a tested evidence-gate helper. It checks content hashes and declared review evidence, but does not itself inspect artwork or automatically modify an existing game's build system.

## Two different outcomes

A prototype proves the path is connected. A production result also needs the actual render → critique → revision → acceptance loop, enforced at asset integration, reload and packaging. Technical pass counts are not a visual-quality score.

## About the landing-page imagery

The illustrated worlds were generated through Higgsfield as original concept art. They are visual explorations, not screenshots or promises of automatic output. The separately labeled prototype capture shows the actual local SMB3 implementation. No game ROM is included in this download.
