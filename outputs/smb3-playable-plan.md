# Super Mario Bros. 3 — Playable Photoreal Remaster Plan

## Target experience

Play World 1-1 as a richly lit miniature film set: chipped enamel pipes, fired-clay bricks, embossed question blocks, thick foliage, stitched fabric, and soft contact shadows. Preserve recognizable shapes and original gameplay timing. Toggle instantly between the NES image and the modern scene while the same emulator continues running.

Blender is the asset and material studio. Unreal Engine is the playable renderer. The original ROM, running in an emulator, remains authoritative for all gameplay. This is a staged implementation plan, not a claim that a modern renderer already exists.

The first acceptance milestone covers the first two screens of World 1-1. The completion target is all of World 1-1, including its reachable subareas and interactions. Other levels and the world map initially use the original renderer, with a clear coverage indicator. A bounded demo must not be presented as a complete-game conversion.

## Evidence and unresolved work

The supplied USA Rev 1 ROM boots and enters World 1-1. Two independent 2,100-frame scripts matched on CPU RAM, OAM, mapped-pattern-memory, and pixel hashes. Small Mario's visual position was tracked for 131 consecutive frames. His two 8×16 sprites occupied OAM slots 10 and 11 in that interval. Enemy sprite slots changed during the same run. The ROM uses mapper 4 and bank-switched graphics.

These checks establish repeatability of this sequence in JSNES, not accuracy against original hardware or full-game semantic understanding. Authoritative player/world coordinates, camera state, entity identities, power-up transitions, collision bounds, and the full level layout remain unverified. The existing trace records snapshots, not complete scanline-level graphics-bank events.

The current machine is an Apple M3 Max with 36 GB memory. Blender was not found on PATH; Unreal installation was not established. Check installed versions, Xcode compatibility, free disk space, and asset-import support before setup. No engine downloads or installs are part of this planning task.

## Architecture

```text
Controller / keyboard
          |
          v
Frame-numbered input ---> JSNES worker ---> Original image + original audio
                              |
                     Verified SMB3 adapter
                              |
                 Frame-numbered scene snapshots
                              |
                     Unreal renderer
                              ^
          Blender meshes / rigs / baked textures

Astra authoring tools -> inspect -> propose -> validate -> apply asset/mapping patch
```

For the initial implementation, keep the working JavaScript emulator in a local sidecar process and use a localhost connection to Unreal. Start with inspectable messages, measure costs, and introduce binary snapshots only if profiling justifies them. The sidecar receives frame-numbered input, advances the simulation at its native cadence, and emits snapshots. Bound queues, reject stale data, and pause visibly on disconnect. Presentation may skip obsolete visual snapshots; simulation must not silently skip game ticks. Profile the process boundary before committing more work to it.

Each snapshot includes schema version, ROM hash, emulator frame, mode, camera, stable entity IDs, world transforms, poses, terrain deltas, events, and confidence/provenance for inferred fields. Unverified fields are explicitly unknown. Do not include full memory dumps in the production hot path.

Unreal never adds movement, gameplay collisions, gravity, root motion, or damage. Characters are visual actors driven by emulator state. Dust, cloth motion, and debris are cosmetic. Keep original sound first; validate buffering, clock drift, and audio/video synchronization.

## 1. Build the playable instrument panel

Turn the headless probe into a continuously playable harness with keyboard/controller input, original display, audio, pause, frame step, reset, and named checkpoints. Record actual inputs with frame numbers. Check that checkpoint restore reproduces future state; the existing fresh-run check does not prove this.

Expose synchronized views of the original image, sprite records, candidate entities, and camera state. Keep the existing experiment as a regression fixture. Add recordings for walking, variable-height jumps, reversal/skidding, enemy contact, death, restart, and scrolling.

**Exit gate:** a person can play and reset; recordings and tested checkpoint restores reproduce the compared emulator state. Audio runs without persistent drift.

## 2. Recover the scene contract

Use controlled checkpoint branches: idle versus right, short versus held jump, and stationary camera versus scrolling. Compare memory changes and inspect writes to promising locations. Validate candidate fields against multiple unseen recordings before assigning semantic names.

Separate world coordinates from screen coordinates. Reconstruct terrain from level/metatile data where verified; use observed nametable changes and a reviewed level-specific map as an explicit interim method. PPU tiles alone do not identify solid terrain, decorations, or hidden blocks. Test semantic classifications through game behavior.

Resolve replacement graphics using mapped CHR identity, palette, sprite size, tile grouping, and observed state. Instrument bank changes if end-of-frame snapshots lose necessary identity. Preserve stable enemy identities across OAM rearrangement. Prefer verified object records over heuristic sprite tracking when available.

Handle the status-bar split separately from the playfield. Initially match the original playfield framing instead of exposing unseen terrain through a wider camera.

**Exit gate:** the first two screens have stable Mario/enemy identities, terrain changes, and camera movement. Object lifetimes survive spawn/despawn and a tested death/restart. Unknown entities remain visible through an explicit original-graphics fallback.

## 3. Build the synchronized gray scene

Create a side-on orthographic scene with simple blocks, pipes, a player proxy, and enemy proxies. Use a single explicit NES-to-world scale. Keep gameplay on one plane; put environmental depth behind it.

Overlay the original image and projected debug anchors to inspect alignment. Use visual sprite bounds only as visual bounds; collision boxes require separate evidence. Align player feet and block surfaces, including scrolling and bump events. Toggle the two renderers at the same emulator frame.

**Exit gate:** the complete scoped segment is playable in gray geometry, the toggle does not reset or mutate the emulator, and projected anchors remain within one NES pixel on tested frames. This threshold applies to debug anchors, not photoreal character silhouettes.

## 4. Establish one production-quality Blender scene

Author a small reusable kit: ground, brick, question block, used block, pipe sections, background hills, foliage, coin, small Mario, and the first enemy. Survey the level before finalizing the full asset manifest.

Use coherent scale, pivots, UVs, naming, and export settings. Give each asset a source file, exported version, bounds, material slots, texture budget, and visual reference. Use image generation for concept exploration and material references; rigged geometry, clean topology, and consistent animation are separate tasks.

Material direction:

- Bricks: broad readable faces, small bevels, fine pores, restrained edge damage.
- Pipes: thick green enamel over metal, roughness variation, seams, dark interiors.
- Question blocks: warm metal or painted surfaces, embossed readable symbol, subtle emissive accent.
- Mario: recognizable proportions, fabric weave and seams, leather shoes, restrained skin shading.
- Environment: layered foliage and large hills that retain the original visual landmarks.

Complex Blender shader graphs are not a portable game material. Bake procedural details into base-color, roughness, metallic, normal, and optional occlusion textures; rebuild necessary effects in Unreal materials. Validate normal-map conventions, color spaces, tangent basis, scale, and the selected mesh/animation interchange on one asset before bulk export. Blender's glTF documentation describes the supported material mapping: https://docs.blender.org/manual/en/4.0/addons/import_export/scene_gltf2.html

Create standing, running, skid, rise, fall, landing, and death poses as required by the observed states. Emulator position drives the character root. Animation must react immediately to jump/collision events; foot placement and secondary motion must not delay gameplay.

**Exit gate:** one representative screen looks convincing during motion, and its imported materials and animation survive the actual playable build—not just a Blender render.

## 5. Light and optimize on the target machine

Use a strong natural key light, sky fill, restrained atmosphere, and careful contact shadows. Keep hazards and platform edges readable. Begin with economical geometry and shadows; compare software Lumen against baked lighting on the actual Mac before choosing the shipping profile. Avoid making advanced geometry features mandatory.

Epic currently documents software Lumen on Apple Silicon, hardware-ray-traced Lumen/MegaLights as unsupported on macOS, and Nanite/Virtual Shadow Maps as beta support on M2+. Verify the chosen engine version before setup: https://dev.epicgames.com/documentation/unreal-engine/macos-development-requirements-for-unreal-engine?lang=en-US

The initial target is 1080p output at 60 fps on this machine. Treat 16.7 ms as a frame-time budget, not an achievement. Measure GPU and CPU work separately, plus input-to-visible-update latency, bridge delay, audio synchronization, and sustained frame pacing. Headless emulator throughput cannot predict the result. Use a fixed reproducible route and at least five minutes of warmed-up play. Record cold-start shader/asset stalls separately.

Instance repeated blocks, use texture atlases and sensible detail levels, pool transient visuals, preload the scoped segment, and reduce expensive shadows/reflections before sacrificing gameplay visibility. No generative-model calls in the rendering loop. Epic's Lumen guide explains why quality settings and internal resolution need explicit budgets: https://dev.epicgames.com/documentation/en-us/unreal-engine/lumen-performance-guide-for-unreal-engine

**Exit gate:** report actual frame-time distribution and input latency. Meet the chosen target or explicitly revise visual settings and rerun; do not substitute average FPS for stable frame pacing.

## 6. Put Astra inside the product

Provide bounded tools to inspect a checkpoint, compare traces, inspect an entity, select assets, modify material parameters, preview a patch, and run a replay check. Changes produce versioned patches with rollback. Keep model execution outside live gameplay timing.

First verify access to an actual callable Astra API/runtime and the event's supported capabilities. Development access to a model does not establish permission or API availability for embedding it in a product. Do not label a different backend as Astra.

The reliable live task is a real material or asset adjustment against prepared content: pause, ask for aged enamel pipes with less glare, inspect the current material, apply bounded changes, render a preview, verify unchanged gameplay state, resume. A live autonomous entity investigation is a stretch goal after bounded edits work reliably. Log tool actions, timing, and validation for the judging evidence.

**Exit gate:** a real model request causes a validated, reversible scene change. Be explicit about prepared assets and live work. Failure leaves a playable last-known-good scene.

## 7. Complete World 1-1 and package the demo

Inventory and cover every reachable entity, power-up/transformation, breakable and hidden interaction, death/respawn, pipe transition/subarea, scrolling section, and level exit. Expand the art manifest based on this inventory. Keep title and map in original mode until separately covered.

Package a launchable local build with ROM selection/hash check, controller help, quality settings, reset/checkpoints, coverage indication, and the original/remaster toggle. Keep the source ROM external to the application bundle. Verify a clean launch without the development editor and run the full acceptance route.

Demo order: original gameplay; toggle mid-jump; traverse the photoreal scene; show a known interaction; perform one real Astra edit; resume; show measured verification/performance briefly.

## Scope and sequencing

Critical path: playable harness → verified scene contract → gray renderer → one polished screen → complete scoped segment → complete World 1-1 → packaged build. Asset look development can run alongside adapter work after scale and pivots are agreed. Astra tools can run alongside art after the scene patch format exists. Avoid duplicate competing runtime implementations.

If time is short, cut wider level coverage, alternate art styles, free cameras, elaborate cloth, and live asset generation. Preserve playability, alignment, one exceptional screen, honest coverage, and a real model-powered edit. A short competition deadline is not enough evidence to promise full World 1-1 fidelity or autonomous conversion.

## Definition of done

- A launchable playable build, not a cinematic or replay-only viewer.
- Documented scope and all critical interactions covered within it.
- Original/remaster toggle preserves the same running simulation.
- Replays detect no renderer-induced emulator-state divergence.
- Visual anchors and interaction readability checked through scrolling and transitions.
- Materials and animation verified in the shipped renderer.
- Measured frame pacing, bridge delay, and input/audio behavior on the named machine.
- Real, reversible Astra functionality if the required backend is available.
- `.blend` sources, runtime project, mappings, fixtures, and reproducible build instructions delivered.

The first implementation task is the interactive emulator harness and synchronized gray renderer. That proves the playable foundation before detailed asset production.
