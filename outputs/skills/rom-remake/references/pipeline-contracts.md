# Pipeline Contracts

Adapt these records to the project's existing formats. They specify required evidence relationships, not an executable schema or universal emulator API.

## Provenance chain

Maintain this inspectable chain:

`ROM hash → extraction/observation → source composite/state field → authored Blender script → build outputs → GLB version → runtime mapping → tested package`

A source record carries:

- Stable source ID, ROM SHA-256/revision, platform and extraction tool version.
- Evidence kind: `extracted`, `observed`, or `inferred`; confidence and known ambiguity.
- For direct extraction: file byte range, bank/address interpretation, palette and assembly information as applicable.
- For observations: emulator/version/configuration, replay/input hash, frame or interval, relevant memory/PPU/object evidence and capture path.
- Result path/hash, source dimensions and variants; tested coverage.

Do not invent byte offsets for runtime observations. Explain any CPU/PPU-to-file mapping rather than treating those address spaces as interchangeable. A state field should cite the experiment/replay that supports its meaning and its untested transitions.

An authored asset record carries source IDs plus authoring method, script path/hash, Blender version/build command, units/pivots, `.blend`, textures, exported GLB and hashes, variant/clip mapping, and deliberate departures from source. Label new geometry/materials `authored`, not ROM-extracted. Changing an input invalidates the affected downstream evidence; rebuild/retest that path rather than all unrelated assets.

## Worker handoff

```text
Task: bounded family/responsibility and expected output.
Source: manifest IDs, assembled graphics, observed forms/states.
Shared contract: units, axes, facing, pivots, camera, material/export conventions.
Ownership: isolated script/output paths; files not owned; integration owner.
Dependencies: accepted shared helpers or prerequisite outputs.
Budget: geometry/textures and available build resources.
Return: Blender script, editable source, textures, GLB, asset manifest, preview,
        reproducible command, tests run, unsupported variants, concrete defects.
Feedback: actual render/runtime capture returned to author for revision.
```

Author workers may run concurrently. One integration owner merges manifests and runtime mappings; a coordinated Blender queue limits local resource use. Resume completed jobs using current hashes and status, not merely the presence of a file.

## Runtime snapshot

Record schema version, ROM hash, simulation session/epoch, frame number, mode, camera and coordinate convention. Each entity needs a stable ID/lifetime, source mapping ID, world/screen transform as appropriate, facing/form/pose, visibility and relevant events. Unknown fields stay unknown.

Frame ordering is scoped to the session/epoch so reset or save-state restore cannot be rejected as stale forever. Visual interpolation may smooth presentation but cannot change authoritative simulation state. Keep original audio on the simulation clock and verify synchronization when audio is supported.

## Evidence by stage

| Stage | Observable check |
| --- | --- |
| Extraction | Recompose representative source graphics or compare known source bytes; every mapped output has valid evidence links. |
| State | A repeatable input sequence yields matching tested state; include relevant camera/spawn/despawn/reset transitions. |
| Authoring | Run a worker's script in Blender; inspect output and confirm source IDs survive its manifest handoff. |
| Export | Load the GLB in the target renderer; verify textures, scale, orientation, and required clips. |
| Gameplay | Exercise the scoped route; compare authoritative state with replacement rendering enabled/disabled where possible. |
| Animation | Capture relevant transitions and pause/frame-step/replay; verify no duplicate root movement. |
| Reload | Replace an asset during play, then attempt a malformed/missing replacement; preserve simulation and last good output. |
| Packaging | Fresh local launch without development services; select expected ROM, play, reset, and inspect coverage/status. |

Record exact artifact versions and actual pass/fail/not-tested status. A technical prototype can be packaged with disclosed visual limitations. A polished release additionally needs the requested visual acceptance evidence; do not relabel one as the other.

## Coverage and claim boundaries

Track scene/area × entity/form × action/transition coverage with `unknown`, `observed`, `mapped`, and `verified` status plus evidence IDs. Include entry/exit conditions and the replay that exercises them. Separate visual replacement coverage from source-state extraction and original simulation coverage: the emulator running the whole game does not mean the remake covers it.

For a named bounded scene, define relevant entrances/exits, subareas and state transitions from the actual game. For a battle, include the scoped participants, menus/actions, damage/state changes and agreed outcomes. Do not add every possible outcome by default, but do not silently omit a required one. Inspect existing context/save states before asking about ambiguous boundaries; adapter qualification can continue independently.

Verify provenance joins before release: runtime mapping IDs resolve to authored manifests, their source IDs resolve to the source inventory, and cited observations/byte ranges resolve to the correct ROM revision. For each required GLB, inspect embedded source/family extras when the exporter supports them; a sidecar alone does not prove those properties survived export. Keep unsupported mappings visible in coverage and fallback behavior rather than assigning a convenient known ID.
