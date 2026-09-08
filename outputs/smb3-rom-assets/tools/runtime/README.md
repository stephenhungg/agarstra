# Runtime extraction verification

These tools use the delivered app's corrected, licensed JSNES source and extractor under the sibling `smb3-demo/src/` directory. Keep the `smb3-demo` and `smb3-rom-assets` folders together. No npm dependencies are required for these Node scripts. ZIP input additionally requires `unzip` on PATH.

Run from any working directory:

```sh
node /path/to/smb3-rom-assets/tools/runtime/conformance.mjs
node /path/to/smb3-rom-assets/tools/runtime/test.mjs /path/to/SuperMarioBros3.nes
node /path/to/smb3-rom-assets/tools/runtime/verify.mjs /path/to/SuperMarioBros3.zip
```

Alternatively set `NES_ROM` to the ROM path. No ROM is included.

- `conformance.mjs` checks48 synthetic cases /6144 pixels against the explicit NES8×16 address/flip formula. It needs no ROM.
- `test.mjs` checks seven actual game snapshots against independent recomposition from CHR bytes, palettes and captured draw operations.
- `provenance.mjs ROM_PATH` checks exact active bank provenance by Tile-object identity, including byte-identical aliases used in different frames and together. It also byte-verifies every active source over 220 live frames.
- `verify.mjs` checks1150 frames /70,656,000 pixels across jump, scroll, stomp, coin blocks, death and map return. It additionally compares instrumented against uninstrumented corrected emulation, including RAM, and verifies every frame asset’s `mappedSources` against raw ROM bytes.

Each script writes its JSON result beside itself. A passing recomposition test establishes exact extraction for those sequences. It does not establish whole-game coverage or photoreal quality. The previous unpatched emulator's malformed odd-bank8×16 addressing was corrected before these results; synthetic conformance separately guards that mistake.

`romSources` contains all byte-identical physical aliases. `mappedSources` contains only exact physical sources actually used in that frame. Do not label the first alias as an active bank. One shared content ID can have multiple active mapped sources.
