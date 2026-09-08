# Local patch

Source: installed jsnes npm package version2.1.0, copied from src/ with LICENSE.

Changed ppu/index.js renderSpritesPartially 8×16 sprite top selection from:

`topTileNum - 1 + 256`

to:

`topTileNum + 256`

`topTileNum` is already `sprTile & 0xfe`, so subtracting one reads the preceding tile. Pattern table bit0 adds256 after the low bit is cleared. See ../../conformance.mjs for known-pattern validation independent of emulator framebuffer parity.
