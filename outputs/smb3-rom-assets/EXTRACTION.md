# Frame-correct SMB3 asset extraction

This extracts actual NES assets at the moment the installed emulator renders them. It does not classify anonymous tile numbers or guess modern geometry.

## API

```js
import { NES } from './vendor/jsnes/index.js';
import { RomAssetExtractor, recompose } from './extractor.js';
const nes = new NES({onFrame: pixels => {/* original packed BBGGRR frame */}});
nes.loadROM(romBytes);
// Boot first if desired, then attach. A load/reset creates a new PPU: attach again.
const extractor = new RomAssetExtractor(nes, romBytes);
nes.frame();
const frame = extractor.getFrame();
const independentlyRasterizedPixels = recompose(frame);
```

- `assets`: immutable copied raw 16-byte CHR tile data, 64 two-bit pixel indices, exact four-color palette, RGBA, and all matching original ROM byte offsets / 1KB banks. Identity includes complete CHR content and palette, not transient tile number. Duplicate ROM content retains all possible source offsets in `romSources`; those are content aliases, not proof a bank was active. Each frame asset additionally exposes `mappedSources`, the physical CHR objects actually used during that frame, resolved by the mapper’s Tile-object identity. One content ID can list multiple active sources if identical bytes were drawn from different banks in the same frame. Runtime IDs remain unchanged.
- `backgroundTiles`: actual 8×8 placements, per-instance palette and nametable coordinates, and `rowMask` for scanline clipping. Coordinates are framebuffer coordinates with y downward. All 240 scanlines, including HUD, are captured.
- `sprites`: evaluated 8×8 / 8×16 sprite instances, screen coordinates, attributes, palette, flips, priority, display-half asset identities, and actual visible scanlines. `halves` already selects the correct source half for vertical flips; apply each half's vertical pixel flip and horizontal flip when composing an atlas.
- `operations`: ordered background scanline drawing, background compositing, and sprite drawing. This preserves scanline bank changes, transparency, clipping, OAM priority, and the eight-sprite scanline limit. `recompose()` reads these and raw extracted assets; it never reads the emulator framebuffer.
- Packed palette colors use `0x00BBGGRR`. RGBA is conventional byte order. Color index0 has alpha0; use `frame.clearColor` for the universal backdrop.

Hooks wrap PPU entrypoints and always call their originals. They read the tiles actually used by `renderBgScanline` and the per-scanline secondary OAM used by sprite rendering. They do not replace emulator frame output. Cached tile content relies on immutable CHR-ROM Tile objects; CHR-RAM is explicitly rejected. This is tested for the supplied SMB3 MMC3 ROM, not a universal emulator renderer contract.

## Corrected upstream sprite bug

The installed JSNES2.1 source had an 8×16 sprite address error:

```
odd tile top: (tile & 0xfe) - 1 + 256  // wrong: low bit cleared, then subtracts again
odd tile top: (tile & 0xfe) + 256      // corrected
```

`vendor/jsnes/ppu/index.js` corrects that line. All other vendor code is copied from the installed dependency; its MIT license is included. The extractor uses the corrected address formula. An earlier seven-frame parity check matched the buggy emulator and therefore did not establish correct sprite appearance. That result is superseded by the corrected tests below. The separate synthetic conformance test prevents agreement between two implementations sharing this address error from being mistaken for correctness.

## Verification

- `node conformance.mjs`: 48 direct synthetic cases / 6,144 sprite pixels cover even/odd pattern-table selection, both halves, horizontal/vertical flips, and priority variants.
- `node test.mjs`: seven selected boot/play/jump/scroll snapshots, zero full-frame mismatch and all CHR sources resolved.
- `node verify.mjs`: 1,150 frames / 70,656,000 framebuffer pixels reconstructed exactly, zero mismatch. Covers jump, scroll, goomba stomp, both initial coin blocks, death and map return. RAM and framebuffer also match a separate uninstrumented corrected emulator on every frame. All observed CHR assets resolve to ROM bytes.

`provenance.mjs` additionally verifies active source bytes across 220 frames and tests the same nonempty CHR pattern from two distinct physical banks: the stable content ID stays the same while frame-local mapped sources change correctly.

See `conformance.json`, `results.json`, and `verification.json` for measured output. These numbers establish pixel extraction/recomposition correctness for the tested sequences, not photoreal quality or whole-game coverage.
