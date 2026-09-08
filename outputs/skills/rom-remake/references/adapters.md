# Qualifying Source, Generation, and Renderer Adapters

A skill coordinates tools; it does not supply every game decoder, emulator, model generator, or engine bridge. Keep a capability table in the project record with tool/version/path, implemented operation, tested scope, evidence, and unsupported cases.

## New ROM or revision

1. Identify platform/revision/hash and a compatible local emulator/core. Verify ROM loading and a reproducible scene before mapping state. Preserve the input and handle extracted archive members explicitly.
2. Inspect available documentation, source/disassembly matches and emulator hooks. A same-named game or similar mapper is not evidence that memory addresses are valid. If relying on a reconstructed source build, verify its byte/hash correspondence and record the revision.
3. Prove observer noninterference and representative graphics extraction. Test bank/palette/priority behavior appropriate to the platform; a shared implementation bug can fool a parity test, so add a separate conformance case where evidence warrants it.
4. Recover a minimal semantic contract: actor position/identity, camera, state/pose, relevant events and scene changes. Validate across held input, idle, transitions, reset and restore. Expand from actual supported cases, not a tile inventory.
5. Prove one source object maps to one candidate replacement and survives export, playback and a reset. Only then estimate larger conversion scope.

Report unknown fields explicitly. A framebuffer-only integration can prove synchronized presentation but cannot support claims of semantic object replacement until the missing adapter is implemented.

## Source-to-authored identity

Preserve original byte/bank evidence separately from semantic inference and artistic interpretation. Generator inputs, prompts, reference image hashes, model/service version where available, job IDs, output hashes, and cleanup/build scripts belong to authored provenance. They do not turn generated topology into ROM-extracted geometry.

## Image-to-3D path, when requested or justified

Check that a real callable service or local runtime is available, supports the needed outputs, and fits authorized cost/hardware constraints. An installed name or documentation link does not prove a working endpoint. Do not substitute a different provider silently when it materially changes cost or workflow.

Use a concrete reference that resolves the target silhouette and material design. Run a bounded candidate experiment; inspect hidden sides, topology, UVs, texture artifacts, scale and export. Clean up/remesh/retopologize as needed, build a suitable rig for organic motion, and compare in the actual runtime against the same target used for other modeling methods. A generated GLB is still a candidate, not a production-ready character.

Retain an editable Blender source and reproducible import/cleanup/export steps. Record generated and manually authored parts distinctly. Report actual job output and limitations rather than claiming image-to-3D because an agent wrote a Blender script.

## New renderer or Unreal integration

Preserve an existing functioning renderer unless replacement is within scope. For a requested engine bridge, first verify the installed engine/toolchain and a representative GLB/material/animation import; do not assume interchange features survive intact.

Implement the [runtime contract](pipeline-contracts.md) using the chosen engine's supported interface. Keep simulation authoritative, presentation queues bounded, reset epochs explicit, and original audio synchronized. Test coordinate conversion and one entity before duplicating the whole scene. Verify input, pause, restart, missing assets and disconnect handling.

Use the same recorded state/replay and acceptance camera to compare renderers. Re-review affected visuals after renderer/lighting changes; a Three.js review does not approve an Unreal build. Measure the actual target hardware before committing to advanced rendering features. Engine integration is complete only with a playable tested package or the narrower artifact the user requested, not an architecture diagram.

Image-to-3D and Unreal are independent capabilities. Neither is a shortcut around render/review/revision, and neither is automatically required to repair that loop.
