# Runtime Integration, Reload, and Delivery

Read alongside the frame/state contract in [pipeline contracts](pipeline-contracts.md). Prefer the existing renderer and mappings when they already satisfy the requested scope.

## GLB integration

Verify actual imported geometry, bounds, axes, pivots, facing, UVs, normals, material channels, transparency and clips. Bake unsupported procedural shaders into portable textures; retain editable Blender sources and import/export versions. Inspect at runtime camera distance with the actual lighting, not only in a normalized studio contact sheet.

Use stable source mappings and explicit form/orientation/state variants. Preserve proportions; arbitrary independent XYZ stretching can turn valid models into the wrong objects. For repeated terrain, use modular pieces/tiling matched to verified level shapes. Distinguish foreground/HUD from playfield and background; do not infer collision from visible tiles.

Candidate and accepted registries must remain distinguishable. If existing compilation writes directly over runtime assets, stage the candidate elsewhere first. For production delivery, wire verified acceptance into the actual consumers; a helper that the assembler never calls does not enforce anything.

## Original gameplay and basic animation

The original simulation owns movement, collisions, AI, gravity, damage, state changes and sound timing. Renderer motion is cosmetic and must not add a competing simulation or duplicate root movement. Give snapshots session/epoch plus frame numbers so reset/save-state restore cannot be rejected as stale forever.

Select supported poses/clips from verified source state. Rigid-part clips can satisfy a prototype; deformation/rig/animation quality for a polished organic character is evaluated under [visual production](visual-quality.md). In either case test pause, frame step, replay, facing and relevant transitions. Avoid guessing unsupported forms from a single default model.

If coverage ends, use explicit local source-graphics fallback or a visible pause/original-view choice consistent with the project. Do not present a frozen frame as ongoing gameplay or silently claim unsupported scenes are remodeled. Test fallback on a real unhandled transition.

## Reload as a transaction

Load and validate new assets in staging before changing live references. Preserve entity identity, transform, current pose/time and simulation state. Swap references only after success, then dispose obsolete resources with correct ownership; shared geometry/materials may have multiple users. Release stale async requests if a newer reload/reset supersedes them.

On missing/corrupt files, incompatible clips or rejected acceptance, keep the last good asset and report the failure. Production reload paths obey acceptance rules; candidate inspection uses a separate labeled mode. Verify repeated reloads do not multiply mixers/listeners, reset gameplay or grow resource counts without bound.

## Technical evidence

Use the requested scope to choose a replay with relevant camera, spawn/despawn, interactions, forms, death/reset and scene changes. Compare authoritative state with replacement rendering enabled/disabled where feasible. Record ROM/emulator hashes and input/frame sequence. Do not confuse matching two implementations with conformance if both share the same untested assumption.

Check controls, pause/reset/restore, original/remake toggle when present, graphics/animation imports, valid and failed reload, fallback, and audio synchronization. Automated audio initialization is not a listening test; simulated gamepad events are not physical-controller verification.

Measure frame-time distribution on stated hardware, viewport and route. Distinguish presentation FPS, simulation rate and input latency. Report cold startup/asset loading separately from warmed-up play. A headless emulator benchmark is not a renderer benchmark.

## Package and launch

Create the requested local app package with the accepted assets for its declared profile, runtime dependencies, controls and visible scope/status. Prototype packages may contain technically valid candidates only when clearly labeled as such; never mark their visual status accepted. Production packages must consume exact accepted versions and verify manifests at their actual entrypoints.

Keep the user's source ROM external unless distribution scope explicitly permits bundling. Preserve required dependency licenses and patches. Resolve packaged paths independently of the development working directory; verify the ROM chooser/hash handling, normal launch, play, reset and exit without a development server/editor. Check that packaging did not copy stale assets or depend on transient build paths.

Deliver the launch path/command, editable sources, package version/hashes, tested route, acceptance profile, and known unsupported scenes/forms/actions. Do not conflate a successful package build with a successful fresh launch. Local packaging does not authorize external publication.
