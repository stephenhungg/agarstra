# SMB3 Asset Lab

A playable local ROM asset-replacement experiment. The corrected vendored NES emulator owns gameplay and audio. An instrumented PPU extracts actual CHR data, bank provenance, palettes, evaluated sprites, and draw operations. The Three.js renderer matches those source identities to editable Blender GLBs.

## Play

Open `../SMB3 Asset Lab Prototype.app`, or run `npm run start:prototype` here. Production is the default for ordinary builds and packaging; the current legacy assets lack production acceptance and are rejected there. The app loads the supplied `Super Mario Bros. 3.zip` from Downloads on this machine. The chooser accepts the same USA Rev 1 ROM as `.nes` or `.zip`; the full ROM is not bundled.

- Arrows: move. X or Space: jump. Z or left Shift: run/grab.
- Tab: original/remodeled view. P: pause/resume. R: restart World 1-1.
- Enter: original Start. Standard gamepad input is implemented; a physical controller has not been tested.
- ROM colors: exact source colors. Daylight / Dusk: physical material lighting.
- Inspect live assets: source bytes, palette, ROM offset, and matching Blender mesh ID.
- Verify current frame: independently rebuild all 61,440 original pixels from extracted assets and draw operations.
- Reload Blender edits: reload exported GLBs without advancing the paused game.

The source view shows the 256×192 playfield; the original view and side reference retain the full 256×240 frame and HUD. The reference is rendered by the emulator. The source view uses separate meshes and individual source-tile fallbacks, not a framebuffer texture.

## Remodeled view (0.4)

The 24-process GPT-6 Astra authoring run produced 71 model candidates. One integration job added cloud and green platform assets, bringing the library to 73 models in 25 editable Blender files. The asset gallery, build sources, material helper, queue, and hash-matched reviews are in `../smb3-photoreal/`.

The runtime reads World 1-1's actual SRAM level grid and object state, backed by a byte-identical disassembly rebuild. It places whole ground sections, hills, blocks, pipes, clouds, colored platforms, collectibles, enemies, and Mario. The renderer loads only its 23 supported runtime model IDs; the remaining library is available for further mapping. The animated model variants contain named glTF clips and editable Blender NLA tracks. Source velocity, airborne state, death, squash, and shell state select the applicable pose. Playback advances with emulated frames, so pause and reset also apply to animation. The NES retains physics, collisions, timing, sound, and gameplay.

Death keeps rendering the verified 3D level. Missing individual replacements use only that object’s exact source pixels over the remodeled scene. Leaving the mapped area pauses on the last 3D frame with Replay and Continue in original view choices; it never silently replaces the whole remodeled screen. Model existence does not imply that every object in every level is mapped. Power-up costume variants and special effects need further work. Characters are stylized; foliage and material realism remain art-direction work. This is a local Blender/Three.js playable experiment, not a finished Unreal remake or a measured 95% fidelity result.

## Coverage

The runtime registry contains 193 colored 8×8 Blender assets captured in opening-level scenarios. Rendering follows current PPU placements rather than an invented level or tile-number-only mapping. Uncatalogued variants remain visible through original extracted tile images; partially masked assets also use per-tile masks to preserve priority and clipping. The original simulation remains authoritative through scrolling and death. In remodeled mode, an unmapped transition pauses the demo for an explicit replay/original-view choice; the whole game has not been visually validated.

The larger asset database and editable Blender libraries are in `../smb3-rom-assets/`. All 8,192 physical graphics tiles have been inventoried; full semantic object and animation coverage remains incomplete. The Source 3D library contains literal source-aligned extrusions. The Remodeled view uses separate whole-object PBR models with authored geometry and baked maps; quality varies and is not approved as photoreal. There is no embedded model API or Unreal integration in this build.

## Development and checks

Node.js, npm, and macOS Apple Silicon are required for the supplied desktop runtime.

```sh
npm install
npm test
npm run build:prototype
npm run smoke:prototype
npm run package:prototype
npm run test:enforcement
```

Set `NES_ROM` for adapter tests to a local copy of the same ROM revision. Desktop smoke reads the default Downloads archive. `DEMO_CAPTURE_DIR` overrides smoke screenshots/results. The `package:prototype` command rebuilds and writes `../SMB3 Asset Lab Prototype.app`, verifies evidence/profile/bytes, and checks its ad-hoc signature. `package` is production-only and currently rejects the unapproved registries before touching the existing app. See [production enforcement](../smb3-photoreal/PRODUCTION_PIPELINE.md) for accepted-bundle preparation and assembly.

Adapter checks cover deterministic replay, observer noninterference, scrolling, death/map states, boot timing, and both initial coin blocks. Native smoke checks imported source meshes, independent recomposition, GPU source colors, replacement reload, inspector provenance, input, audio initialization, and renderer switching. Runtime extraction tools and their longer replay/conformance reports are in the sibling asset deliverable.

The displayed frame rate is presentation rate; it is not an input-latency benchmark. Losing focus pauses play. Original audio initialization is automated; listening quality and physical gamepad behavior still need human checks.

## Source layout

- `src/vendor/jsnes/`: corrected emulator, license, and sprite-addressing patch notes.
- `src/rom-extractor.js`: read-only PPU capture and independent recomposition.
- `src/bridge.js`: ROM boot, input, simulation, and extraction integration.
- `src/semantic-scene.js`: source-defined whole-object scene from level SRAM and object state.
- `src/photoreal-renderer.js`: whole-object PBR models, presentation rig, lighting, pooling, and explicit coverage fallback.
- `src/source-renderer.js`: exact-identity GLB lookup, instancing, visibility masks, and source fallbacks.
- `src/source-patches.js`: individual missing-object overlays using the tested PPU visibility masks.
- `src/main.js`: playback, audio, keyboard/gamepad input, inspector, and smoke checks.
- `public/assets/source-registry.json` and `source-glb/`: stable replacement mapping and exported meshes.
- `electron.cjs` / `preload.cjs`: local desktop shell, ROM picker, native integration checks.

JSNES: Apache-2.0. Three.js and Electron: MIT. Original game assets remain Nintendo's work. This local experiment operates on the user-supplied ROM.

## Editable animation assets

See `../smb3-photoreal/animated/README.md` and `animated-library.blend` for the animated variants. Static source family libraries remain available as the modeling originals. These are rigid-part joint animations, not a complete skinned character or facial animation system.

## Production boundary

Both GLB renderers require hash-bound evidence in production. Reload stages complete replacement maps and revokes removed IDs; rejected releases preserve the last working state. Production builds cannot be downgraded with a URL parameter. Prototype preview is an explicitly compiled profile. Asset acceptance does not establish scene-level or artistic readiness.
