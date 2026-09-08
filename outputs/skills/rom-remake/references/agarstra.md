# Agarstra SMB3 Adapter

Implementation audit: September 8, 2026. Verify current code and evidence before relying on this snapshot. This adapter describes a working prototype and incomplete production automation; see [implementation status](implementation-status.md).

## Locate and preserve

Checkout: `/Users/stephenhung/Documents/GitHub/agarstra`. The installed `~/.codex/skills/rom-remake` is a symlink to `outputs/skills/rom-remake` here; edit the repository copy rather than maintaining two divergent skills.

- `outputs/smb3-rom-assets/`: extraction, source catalogs, provenance and verification.
- `outputs/smb3-photoreal/`: authored scripts, families, model/animation library, runtime registry, reviews and tools.
- `outputs/smb3-demo/`: JSNES + Three.js + Electron app.
- `work/photoreal-swarm/`: isolated author jobs, prompts, process logs and queue state.
- `outputs/smb3-photoreal/METHODOLOGY_AUDIT.md`: evidence-backed art/production diagnosis.

The root Next.js/Fabrica app is separate; preserve it. Legacy `outputs/` and `work/` under `/Users/stephenhung/Documents/Codex/2026-09-08/o` are compatibility symlinks, not independent copies. The source ROM is external at `/Users/stephenhung/Downloads/Super Mario Bros. 3.zip`; keep it external to a distributable package.

## Source adapter boundaries

`rom-extractor.js` hooks the corrected vendored JSNES PPU. Immutable CHR-ROM and mapper-installed Tile identity are assumptions; CHR-RAM is explicitly rejected. `romSources` records content aliases while `mappedSources` records the active physical source. Do not collapse those meanings or reuse the observer hooks unchanged with another core/version.

Read `outputs/smb3-rom-assets/EXTRACTION.md` for actual API and conformance/replay commands. The binary manifest extractor at `work/asset-map-v2/extract_manifest.py` asserts byte identity with an assembled Southbird disassembly and consumes assembler symbols; it is not a general ROM CLI.

`src/semantic-scene.js` binds its addresses/definitions to Southbird commit `09b1bd81a788de8ceec664a34094e84ddb463117`. Current mapping uses tileset 1, layout pointer `0xbb82`, camera Y239 and the World 1-1 SRAM grid. Boot uses a fixed 1390-frame input sequence. Different revisions/scenes require evidence, not copied addresses.

Coverage must be read from the active renderer: the legacy `GameBridge.coverage` opening bound X≤256 is not the photoreal renderer's scope. Its semantic path supports the horizontally mapped World 1-1 overworld grid (up to 15 screens) with per-object unknown fallbacks. This is not complete interaction/visual coverage: subareas, other layouts, vertical camera positions, world map, forms and actions remain unsupported or unverified. A supported grid is not proof of a completed level.

## Current asset/animation status

The audited library contains 73 model candidates across 25 families, with all recorded family photoreal reviews false. Five animated GLBs contain 17 rigid-part clips. Recount when reporting current numbers. The runtime uses a supported subset rather than the complete library. Original simulation still drives animation time and actor motion; preserve that separation.

No image-to-3D generator or Unreal integration is implemented. This is a macOS Electron/Three.js prototype; do not describe it as a portable engine-independent implementation merely because the skill supports adapter selection.

## Existing commands and their actual meaning

Run from the checkout, substituting real family/model/report IDs. Inspect scripts before invoking mutating commands.

| Operation | Command | Meaning |
| --- | --- | --- |
| Selected author jobs | `python3 outputs/smb3-photoreal/tools/swarm.py author --families FAMILY_ID --workers N` | First-draft author path; adapt feedback/target behavior before using for iterative production. |
| Central build queue | `python3 outputs/smb3-photoreal/tools/build_queue.py --families FAMILY_ID --max-wait 1800` | Candidate build, structural validation and contact sheet. Inspect job state even after exit zero. |
| Structural model check | `python3 outputs/smb3-photoreal/tools/validate_models.py MODEL.glb --out REPORT.json` | Checks actual GLB buffers/material/provenance structure. |
| Legacy visual flag | Same validator plus `--spec SPEC.json --review REVIEW.json --require-photoreal` | Per-file hash-bound review; see format below. Does not prove review observation. |
| Runtime tests | `npm test --prefix outputs/smb3-demo` | Current technical tests, not artistic approval. |
| Runtime build/smoke | `npm run build --prefix outputs/smb3-demo`, then `npm run smoke --prefix outputs/smb3-demo` | Native smoke requires app focus; inspect `electron.cjs` for capture paths and ROM loading. |
| Local package | `npm run package:prototype --prefix outputs/smb3-demo` | Builds the explicitly labeled prototype app. Production `package` rejects unaccepted registries; launch packages separately to verify them. |

`tools/render_family.py`, invoked by Blender with `-- --family FAMILY_DIR --samples 24`, produces normalized contact sheets. They do not preserve gameplay scale or demonstrate deformation/motion. Use runtime captures for acceptance.

Discover the actual executables before use: the old Blender path was `/Volumes/Blender/Blender.app/Contents/MacOS/Blender`; the author CLI is project-local under `work/photoreal-swarm/runtime/`. Local packaging uses macOS `ditto`, `sips`, `iconutil`, `plutil` and ad-hoc `codesign`. Verify availability; this is not implemented Linux/Windows packaging.

## Gaps to fix when implementing production enforcement

1. `swarm.py` defaults to 24 authors, forbids Blender execution in prompts and asks for one focused turn. Completion checks exit status, `build.py` presence and Python parsing. Provide target images and render/revision feedback rather than rerunning its default swarm.
2. `build_queue.py` uses two Blender slots; keep one queue instance. It sets `phase: done` while `visualReview` is still pending and omits the validator's review/spec flags. It can exit zero with failed jobs. Read `build-status.json` and its actual evidence.
3. Cache keys cover build/render scripts but omit some shared helpers, style/reference/job inputs and Blender version. Include transitive build/context inputs before treating cached output as current.
4. `assemble_runtime.py` now defaults to production and requires a release plan of accepted bundles. It reruns the Python evidence gate and actual JavaScript consumer verifier, binds the current runtime, stages immutable releases, and atomically changes the registry pointer. `--include-rendering` requires explicit `--profile prototype` and writes a separate preview registry.
5. Both renderers now parse exact verified bytes and reload complete staged maps. Removed assets are revoked; failed or superseded reloads preserve the previous release. Shared UI reload stages both consumers before commit.
6. Production packaging validates both registries, current source/build/profile, and staged bytes before publication. Prototype packages are separate and labeled. See `outputs/smb3-photoreal/PRODUCTION_PIPELINE.md` for the current runbook and evidence limitations.

When asked only to package the existing prototype, preserve its disclosed quality status and run the appropriate technical/package checks. A high-fidelity production task instead needs the feedback loop and acceptance enforced in these consumers.

## Legacy validator schema and migration seam

Read `tools/VALIDATION.md` before generating a spec or review. The spec has `familyId`, `requiredNodeNames`, and `requiredSourceAssetIds`; embed family/source IDs in GLB extras as well as sidecars.

The legacy review is `{assetSHA256, approved, reviewer, checks}` with true checks named `silhouette`, `materialResponse`, `lighting`, `runtimeReadability`, and `notPixelExtrusion`. A single review is applied to all model arguments: invoke it per asset. It has no target/render/context dependency hashes or actual evidence paths. Never fabricate this record to bypass the visual flag.

The portable [evidence gate](evidence-gate.md) uses a different explicit contract. Do not pass its reports directly to the legacy validator. Preserve native structural checks, collect their results as technical evidence, and adapt the accepted-bundle output into staged registries. Add consumer rejection tests before declaring migration complete. Neither contract mechanically proves artistic judgment.
