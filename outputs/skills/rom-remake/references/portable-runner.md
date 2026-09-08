# Portable NES execution

This skill now includes a runnable, project-independent NES source-reconstruction pipeline. It does not require the Agarstra checkout, SMB3 memory addresses, an existing game disassembly, or a bundled ROM.

## Qualified scope

- NTSC iNES, immutable CHR-ROM, mapper 0 (NROM) and mapper 4 (MMC3).
- `.nes` or a ZIP containing exactly one NES ROM.
- Complete raw CHR tile extraction; palette variants observed during a configurable input replay.
- Original emulator-driven gameplay and PPU placement, with editable Blender source-relief GLBs.
- Parallel Codex author jobs, actual Blender renders, independent image reviews and bounded revision, when `--author codex` is used.
- The explicit `--author source` path builds faithful relief geometry without AI author/review calls.

This is **not** generic Nintendo decompilation, semantic object recovery, or automatic photoreal character production. Unsupported systems, CHR-RAM, unqualified mappers and NES2 inputs are rejected. Unobserved palette variants use explicit source-tile fallback. A passed source-reconstruction review does not grant the production acceptance required by the SMB3 release gate.

## Run in a clean workspace

Requirements: Python 3.10+, Node.js 22+, npm, Blender 4.5, and an authenticated Codex CLI for AI authoring. First run downloads the player's pinned Vite/Three dependencies through npm. Linux/macOS process handling is supported by the coordinator; the tested host is macOS.

```sh
python3 /path/to/rom-remake/scripts/remake.py \
  --rom /path/to/game.nes \
  --out /path/to/new-remake \
  --blender /path/to/Blender \
  --codex /path/to/codex \
  --workers 2
```

Default authoring is Codex. It receives extracted target images and source identities, edits an isolated Blender script, and gets actual rendered feedback from an independent reviewer. Defaults are two concurrent jobs and three author/build/review attempts. Exhausted visual revisions stop publication. Receipts record candidate hashes, script hashes, review outcomes and logs; they are prototype workflow evidence, not production approval records.

For a deterministic first qualification, explicitly choose `--author source`. Add `--frames 600 --inputs /path/to/replay.json` to visit gameplay. Input events use zero-based frame numbers:

```json
{"events":[
  {"frame":120,"button":"START","down":true},
  {"frame":122,"button":"START","down":false}
]}
```

Buttons: A, B, START, SELECT, UP, DOWN, LEFT, RIGHT; optional player is 1 or 2. A supplied replay must fit the requested frame count. No default game-specific start sequence is invented.

`--max-assets N` deliberately limits the generated prototype subset. Omit it to build every observed nontransparent palette variant. `--resume` requires matching ROM/replay/template/toolchain inputs and validates cached output bytes. Changed inputs require a new output directory. Failed builds preserve existing published assets. Publication uses immutable model releases and an atomic registry pointer.

## Play and inspect

The final command prints the independent player's launch command:

```sh
npm --prefix /path/to/new-remake/runtime/player run dev
```

Open its local URL and choose the original `.nes` file. The web build contains no full ROM. Use Enter to start, arrows to move, Z/A and X/B as shown by the player, toggle original/reconstruction, enable audio, and reload candidates. See the player's README for exact controls.

The output contains:

- `run.json`: current state, exact input/template fingerprints, scope and limitations.
- `extracted/`: raw tiles, observed catalog, source/header provenance, replay hashes and emulator capture/state. Keep these game-derived local artifacts separate from the reusable skill download.
- `jobs/<id>/`: extracted target PNG, task and IDs, editable `build.py`, Blender logs/library/GLBs/render, author/reviewer records and resumable receipt.
- `runtime/player/`: independent browser app, asset registry and production web build.

A screenshot matching the original proves source preservation, not newly inferred 3D character quality. Test gameplay after pressing Start, not only the title screen. Inspect both actual model counts and fallback counts.

## Tests

```sh
node --test /path/to/rom-remake/runtime/nes/tests/*.test.mjs
python3 -m unittest discover -s /path/to/rom-remake/runtime/tests
npm --prefix /path/to/rom-remake/runtime/player test
```

Optional real-ROM observer tests use environment variables documented in `runtime/nes/README.md`; test fixtures never ship ROMs. Browser smoke requires Playwright and a local player server. Generated code is executable code: Codex authors operate in isolated job directories; the central coordinator bounds Blender concurrency and terminates timed-out process groups.
