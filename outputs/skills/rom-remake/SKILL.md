---
name: rom-remake
description: Build and repair ROM-to-playable-3D remake pipelines, from provenance-linked graphics/state extraction through parallel Blender authoring, GLB rendering, animation, reload, visual revision and acceptance, validation, and app packaging. Use for ROM remakes and production-pipeline work, including high-fidelity workflows; not unrelated modeling or ordinary emulator use.
---

# ROM Remake

Build an inspectable chain from **ROM → extracted graphics and game state → parallel Blender-script workers → models/textures → GLB → playable renderer**, with original simulation controlling gameplay. Close the production loop with **render → visual critique → revision → acceptance**. Keep provenance attached through export, review, runtime mapping, and packaging.

A working transfer pipeline is a prototype, not proof of high-fidelity production. The Agarstra SMB3 implementation has an end-to-end prototype; visual iteration, character production, and game coverage remain incomplete. Production evidence enforcement is connected to the SMB3 assembler, reload, and packaging consumers; this does not grant artistic acceptance to existing candidates. Image-to-3D and Unreal integration are not implemented there. See [implementation status](references/implementation-status.md) for the dated baseline; verify current evidence before advancing its status.

## Execute a portable reconstruction

For a new supported NES ROM, start with the bundled [portable runner](references/portable-runner.md), not the hardcoded SMB3 project. `scripts/remake.py --rom PATH --out NEW_DIRECTORY` runs qualification, extraction, parallel Codex/Blender jobs, actual render review/revision, and a standalone playable source reconstruction. Read its dependencies and qualified scope first. Use `--author source` only when explicitly choosing a deterministic source-relief baseline. It does not implement arbitrary Nintendo decompilation or semantic whole-character modeling. Preserve that distinction when presenting results.

## Choose the actual deliverable

| User intent | Work and completion |
| --- | --- |
| Inspect, audit, plan, or fix this skill | Inspect relevant instructions/artifacts and produce that deliverable. Do not launch asset jobs or modify the game merely to update guidance. |
| Build/package a prototype | Prove the end-to-end path for the agreed scope; inspect visible import/state defects; validate and launch the package. Disclose art and coverage limitations. |
| Produce high-fidelity assets/a scene | Establish a concrete target; run the author/render/review/revision loop; meet the scoped visual and technical criteria in the actual playable view. |
| Make the production pipeline reliable | Implement the feedback and enforced promotion paths, demonstrate rejection of failed/missing/stale evidence, and repeat an accepted result on a representative independent case. One manually approved scene or more instructions alone is insufficient. |

Treat “boil the ocean” as a request for a thorough result within the identified deliverable, not permission to substitute a different game, migrate engines, or call a prototype production-complete. Preserve explicit user scope and existing authorization. Local reversible work and agent visual review do not inherently need user confirmation; ask only when a material unresolved choice requires it.

## Orient and select the next unmet dependency

Inspect the repository, running implementation, tools, latest manifests/reviews, and actual output. Identify ROM revision/hash, emulator, adapter, renderer, Blender executable/version, scene/form/action scope, intended quality, and package target. Reuse current verified evidence. Never assume a game-specific adapter works for another platform or revision.

For Agarstra/SMB3, read [the adapter](references/agarstra.md). For new games, generators, or renderers, read [adapter qualification](references/adapters.md). Read [game selection](references/game-selection.md) only if target selection is requested.

Maintain one compact production record: deliverable, active dependency, tool capabilities, artifact versions, coverage, evidence, unresolved defects, owners, and next action. Use the project's format rather than creating parallel tracking systems. Distinguish `implemented`, `verified for this scope`, `proposed`, and `blocked` capabilities. A written procedure is not implemented automation.

Route only into the references needed for current work:

| Work | Operational reference |
| --- | --- |
| Source extraction, provenance, semantic state, simulation contract | [Pipeline contracts](references/pipeline-contracts.md) |
| Parallel authoring, build queue, artifact ownership, retry/resume | [Worker orchestration](references/worker-orchestration.md) |
| Target images, model/character production, visual feedback and iteration | [Visual production](references/visual-quality.md) |
| Task cards, defects, candidate and scene reviews | [Production contracts](references/production-contracts.md) |
| Machine verification of hash-bound evidence and staged accepted bundles | [Evidence gate](references/evidence-gate.md) |
| Gameplay integration, animation, reload, performance and packaging | [Runtime delivery](references/runtime-delivery.md) |

## Production dependencies

1. **Source meaning:** establish reproducible graphics/state evidence and explicit uncertain/unsupported mappings. Tiles are drawing fragments, not necessarily objects; authored geometry is not extracted geometry.
2. **Shared target and interchange:** settle camera, source/world coordinates, units, pivots, facing, material/export conventions, and required states. Prove one asset loads correctly in the target renderer. For high fidelity, also establish an inspectable target image and acceptance criteria before scaling.
3. **Author and render:** dispatch bounded workers with source IDs, target references, isolated paths and resource budgets. Return actual render feedback to authors; a syntactically valid Blender script is not an accepted model.
4. **Critique and revise:** inspect against the target at gameplay scale and in motion. Record localized defects and revise the relevant source. Escalate the modeling method when iterations stop improving the defect. Keep failed candidates out of accepted releases.
5. **Integrate and accept:** original simulation owns position, collision, AI, rules, events and timing. Inspect imported assets, required forms/actions, composition and motion in the actual runtime. Separate asset acceptance from scene acceptance.
6. **Validate and package:** exercise the scoped replay, reload and failure paths; build and launch the package independently of development services. Report exact supported coverage and remaining limitations.

Resume at the earliest failed dependency that blocks the user's outcome. Do not restart extraction or broaden a swarm when evidence points to a specific art, export, mapping, or promotion defect. A prototype may use basic rigid-part animation; a high-fidelity organic character needs topology/rig/motion that meets its actual target.

## Enforce accepted versions

Use distinct candidate and accepted locations. Bind reviews to the exact candidate artifacts and context: target references, runtime build/source, camera/lighting configuration, replay and acceptance contract. Changed inputs invalidate affected evidence. Required checks with `fail`, `pending`, absent results, or stale hashes cannot pass promotion.

The bundled `scripts/evidence_gate.py` verifies declared evidence and can create an isolated accepted bundle. Read its documented schema and run its tests before adopting it. It does **not** judge visual quality, authenticate a reviewer's observation, or retrofit the existing game assembler. Reviewers must inspect actual images/motion; never generate positive review records merely to satisfy the checker.

For a reliable production-pipeline request, connect a tested gate to every accepted registry/assembly/package path, including rebuild and reload paths that can change a release asset. Candidate preview stays available separately. Demonstrate that bypass paths cannot silently admit a failed candidate. A manually curated manifest is an interim delivery method, not automated quality enforcement.

## Completion and reporting

Report the deliverable, runnable artifact or changed skill, evidence actually run, source/scene/form/action coverage, visual status, and next unresolved dependency. Link the launch command, editable sources and verification records when applicable.

Do not equate model counts, texture sizes, clip names, passing technical tests, or a package with shipping quality. Define any requested fidelity percentage by dimension and denominator; a 2D ROM contains no hidden photoreal ground truth. Preserve a useful last working artifact when a method or dependency fails and leave resumable state rather than manufacturing acceptance.
