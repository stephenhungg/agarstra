# FireRed source verification

The pinned decompilation built successfully without an external base ROM. Its resulting 16 MiB ROM exactly matches the user-supplied English FireRed 1.0 ROM: SHA-1 `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`.

## Provenance

- [pret/pokefirered](https://github.com/pret/pokefirered), commit `c75f352304d529f6ba92d4f74b9cf8b5c3810788`.
- [Official build instructions](https://github.com/pret/pokefirered/blob/c75f352304d529f6ba92d4f74b9cf8b5c3810788/INSTALL.md).
- [pret/agbcc](https://github.com/pret/agbcc), commit `da598c1d918402c42c0c0d7128ba14567f3175e9`.
- Arm GNU Toolchain 13.2.Rel1 for macOS arm64, downloaded from Arm into the project's work directory. No global toolchain installation or shell-profile changes.

## Available data

- `build-verification.json`: hashes, compiler versions, build log and ELF locations.
- `firered-symbols.json`: 54,248 ELF symbols tied to the matching ROM SHA-1. These are source-verified addresses, not heuristic guesses.
- `source-maps.json`: original raw little-endian map words, decoded metatile IDs, collision/elevation fields, events and source paths for Pallet Town, Route 1, both player-house floors, and Oak's lab.
- `PalletTown-source.png` and `Route1-source.png`: static map layers, excluding NPCs and tile animation. These previews show source geometry only, not the remake's art.

The complete checkout remains at `work/pokemon/source/pokefirered`. Source creature front/back sprites, palette files, tilesets, scripts and event structures are directly available there. `include/global.fieldmap.h` documents runtime `ObjectEvent` and `PlayerAvatar` offsets.

## Reproduce using the existing isolated dependencies

From `work/pokemon/source`, use:

```sh
export PATH="$PWD/arm-gnu-toolchain-13.2.Rel1-darwin-arm64-arm-none-eabi/bin:$PATH"
(cd agbcc && ./build.sh && ./install.sh ../pokefirered)
(cd pokefirered && make -j8 compare)
python3 export_source.py
python3 render_source_maps.py
```

Verified result: `pokefirered.gba: OK`.

This source match establishes a reliable input and symbols for the emulator bridge. It does not establish that runtime integration or photorealistic reconstruction has been completed.
