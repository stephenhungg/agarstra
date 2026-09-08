# Portable NES extraction

No repository paths, game addresses, ROM files, network calls, or npm dependencies are required. Node.js 22+ runs the CLI:

```sh
node extract.mjs --rom /path/to/game.nes --out /path/to/output --frames 300
node extract.mjs --rom /path/to/game.zip --out /path/to/output --frames 900 --inputs /path/to/replay.json
```

Supported scope: NTSC iNES cartridges with immutable CHR-ROM, mapper 0 (NROM) or 4 (MMC3). Other formats, mappers, CHR-RAM, trainers, ambiguous headers, PAL, NES 2.0, and VS/PlayChoice are rejected before emulation. Support is an emulator/extraction capability, not automatic semantic game understanding. Qualification regression evidence uses two cartridge revisions; arbitrary cartridges on these mappers may still expose emulator defects. ZIP must contain exactly one `.nes` entry; stored/deflate entries are supported and CRC is checked without extracting archive paths.

Inputs are zero-based frame events applied before `nes.frame()`:

```json
{"events":[{"frame":120,"button":"START","down":true,"player":1},{"frame":122,"button":"START","down":false,"player":1}]}
```

Buttons: A, B, SELECT, START, UP, DOWN, LEFT, RIGHT. With no inputs, the game runs its own boot/attract sequence. The extractor does not guess which button sequence reaches gameplay.

Outputs:

- `source.json`: ROM SHA-256, header, mapper, extraction scope and limitations. No absolute ROM path.
- `raw-tiles.json`: every 16-byte CHR tile, original ROM/CHR offset, bank, source hash, decoded 2-bit pixels. Duplicate bytes retain distinct offsets.
- `catalog.json`: every observed palette/kind variant, pixels/RGBA, all possible matching source locations. `id` is a short SHA-256 of `sourceAssetId`; the latter is the immutable observer identity. Aliases are not claimed as observed bank use.
- `capture.json`: final frame's draw operations, background tile rows, sprite instances, active tile assets and exact mapped sources where mapper object identity establishes them. This is PPU drawing state, not inferred gameplay semantics.
- `replay.json`: normalized inputs, per-frame framebuffer/RAM/OAM hashes and independent extracted-asset recomposition hashes/mismatch counts. A mismatch is reported honestly, not silently marked accepted.
- `state.json`: final JSNES serialized simulation state for inspection/resume. It does not replace the source ROM.

Only captured states contribute palette variants; unvisited scenes and actions require additional replays. The raw tile inventory covers all declared CHR bytes, not all game resources. Audio, compressed PRG graphics, semantic level data and source-code recovery are not implemented.

Tests:

```sh
node --test tests/extraction.test.mjs
AGARSTRA_TEST_ROMS=/path/first.nes,/path/second.nes node --test tests/extraction.test.mjs
```

The optional real-ROM test compares observed and unobserved emulator state, RAM, OAM and extracted-frame recomposition. Test ROMs remain external. Vendored JSNES Apache-2.0 license and local sprite patch are in `vendor/jsnes/LICENSE` and `vendor/jsnes/PATCHES.md`.
