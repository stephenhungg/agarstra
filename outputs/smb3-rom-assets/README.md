# SMB3 ROM Asset Lab

A binary-backed extraction, editable Blender library, and playable replacement-rendering experiment for the supplied Super Mario Bros. 3 USA Rev 1 ROM.

## Open the results

- `catalog/index.html`: offline visual inventory, source images, binary offsets, and verification reports.
- `blender/rom-source-assets.blend`: all 5,531 unique raw CHR patterns (covering 8,192 physical tiles), 127 observed compositions, and 193 observed colored tile assets. The 320 colored entries also have individual GLBs.
- `blender/binary-defined-assets.blend`: 5,747 metatile compositions plus 474 clearly labeled diagnostic player previews. These are editable meshes, with source provenance on each object.
- `blender/worldmap-assets.blend`: 2,433 additional source-context map meshes, closing the 256-definition world-map gap.
- `../SMB3 Asset Lab.app`: playable local application. `Inspect live assets` shows exact CHR bytes, ROM offsets, palette colors, and the corresponding Blender mesh ID.

The original ROM supplies gameplay and audio. Graphics are substituted in the companion renderer through a source-identity registry. This is an asset replacement layer, not a new photoreal binary that runs on NES hardware.

## What “all assets” means here

| Evidence layer | Coverage |
|---|---|
| Physical graphics bytes | All 131,072 CHR bytes; all 8,192 8×8 tiles; 5,531 unique patterns and every duplicate alias |
| Binary-defined terrain | All 3,072 metatile definitions resolve: 2,816 level definitions produce 5,747 images; 256 map definitions produce 2,433 images in 33 conditional contexts |
| Player templates | All 81 templates and seven suit roots enumerated; 539 combinations have resolvable canonical pixels, yielding 474 previews |
| Observed gameplay | 860 captured frames; 127 composites and 193 colored source tile variants |
| Object definitions | 180 standard descriptors preserved, with unresolved bank/state/special-drawing requirements recorded |
| Source structure | 359 level layouts, 10,450 bank-resolved symbols, and 2,259 labeled byte-data blocks in the manifests |

Raw tile coverage is exhaustive. Semantic coverage is not: later animated level-bank phases, specialized enemy drawing routines, and reachable player animation combinations need further resolution. The diagnostic player collection deliberately retains this distinction. It must not be interpreted as a complete animation pack.

Photoreal geometry cannot be recovered from 2-bit pixels alone. These models preserve the source silhouette, color, placement, and provenance; they are source-aligned blockouts ready for deliberate reauthoring. Materials and topology remain editable.

## Verified evidence

- The referenced disassembly reassembled byte-for-byte into the supplied ROM: SHA-256 `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`.
- Every physical CHR tile losslessly re-encodes to its original bytes. Reopening the raw Blender library also verified all 5,531 unique meshes against all 8,192 physical aliases, plus all 320 observed colored meshes.
- Every delivered binary composition reassembles from its declared source tiles, palettes, and flips.
- The saved binary and world-map Blender libraries were reopened; actual mesh faces and materials reconstructed 1,835,264 and 622,848 source pixels respectively, with zero mismatches.
- Runtime extraction matched 1,150 tested frames, totaling 70,656,000 pixels, with zero mismatches. Instrumented and uninstrumented corrected emulation also matched RAM and framebuffer.
- Independent 48-case sprite addressing checks guard the 8×16 odd-bank bug found in the earlier emulator dependency.
- The native application checks source GLB loading, actual replacement instances, GPU source-pixel matching, movement, jump, reset, pause, audio initialization, and real keyboard events. See `verification/` for the packaged run.

These are measured checks of source assembly and selected runtime sequences, not a whole-game fidelity percentage or a photoreal quality score.

## Edit and reinsert

See `tools/EXPORTING.md`. Runtime replacement entries match immutable source bytes plus the captured palette and drawing kind. Editing an exported asset changes its appearance while retaining its source identity. Unknown variants and partially occluded source tiles retain an extracted per-tile fallback.

The application uses 193 observed 8×8 GLBs in its live lookup. The larger assembled Blender library is available for authoring and semantic mapping; its thousands of compositions are not automatically treated as validated live object replacements.

## Reproduce

- `catalog/README.md`: inventory, observed capture, binary composition, and verification commands.
- `tools/runtime/README.md`: independent runtime extraction and addressing checks.
- `tools/reconstruct_blender.py`: physical/observed source mesh and GLB generation.
- `tools/reconstruct_binary_library.py`: separate binary composition library.
- `tools/verify_binary_library.py`: reopen and rasterize actual saved meshes.
- `BINARY-RESEARCH.md`: exact-source offsets, structures, and build evidence.

The raw/observed Blender generator defaults to the compact runtime library. Use the separate binary and world-map generators for the larger composition libraries. The original ROM is supplied locally by the user and is not packaged with the application. Extracted graphics are included in this requested local asset deliverable.

Source structure credit: Southbird's SMB3 disassembly, commit `09b1bd81a788de8ceec664a34094e84ddb463117`. The corrected vendored JSNES source includes its Apache-2.0 license and patch notes. Three.js and Electron retain their own licenses. Original game artwork is Nintendo's work.
