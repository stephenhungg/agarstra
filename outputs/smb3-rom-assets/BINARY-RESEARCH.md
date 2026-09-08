# Binary-backed SMB3 asset structures

## Exact-ROM proof

The supplied ROM and the unchanged Southbird disassembly assembled locally are **byte-for-byte identical**, including the iNES header, PRG, and CHR.

- SHA-256: `4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579`
- Total: 393,232 bytes; PRG: 262,144 bytes; CHR: 131,072 bytes / 8,192 8×8 patterns.
- Disassembly: https://github.com/captainsouthbird/smb3 , commit `09b1bd81a788de8ceec664a34094e84ddb463117`.
- NESASM: https://github.com/camsaul/nesasm , commit `229033a4b76466b447ad47704808a4d03c493cee`.
- Native build: `make CFLAGS='-O2 -Wall -Wno-int-conversion'`; the compatibility flag suppresses an old C pointer/integer diagnostic. No source edits to either upstream were needed.
- Assembly: `../nesasm/nesasm smb3.asm`. Output: `smb3/smb3.nes`, `smb3/smb3.fns`. Assembly log has two passes and no errors.

This establishes exact version correspondence; it does not mean every data label is a standalone visual asset.

## Produced manifests

`binary-asset-manifest.json`:

- 12 complete, 1,024-byte metatile tables, covering 19 tileset indices through shared tables: 3,072 physical definitions.
- All 81 player composite templates (six 8×16 sprites each), their bank offsets, and seven power-up root banks.
- Six 36-byte standard descriptor tables for each of five object groups; 180 standard object IDs.
- 190 named object constants, including special controllers through ID `$D6`; aliases and undefined holes mean this is not 190 unique visual characters.
- 359 source-declared level-layout streams with exact ROM ranges and nine-byte headers.
- 16 palette sets; 23 background bank selection pairs.

`all-byte-data-labels.json`: 2,259 labeled byte-data blocks with original bytes, source lines, CPU addresses, PRG banks, and ROM offsets. These include specialized drawing data outside the default object compositor.

`symbol-bank-map.json`: 10,450 source labels with bank-resolved physical addresses.

`extract_manifest.py` reproduces all three directly from the proven ROM and assembled symbols.

## Metatile layout (verified)

Physical ROM offsets include the 16-byte iNES header:

| Tileset group | ROM offset |
|---|---:|
| TS0 | `0x18010` |
| TS14 | `0x1A010` |
| TS18 | `0x1C010` |
| TS1 / Plains | `0x1E010` |
| TS3 | `0x20010` |
| TS4, TS12 | `0x22010` |
| TS6, TS7, TS8 | `0x24010` |
| TS5, TS11, TS13 | `0x26010` |
| TS9 | `0x28010` |
| TS2 | `0x2A010` |
| TS15, TS16, TS17 | `0x2C010` |
| TS10 | `0x2E010` |

For metatile `t`, the four pattern IDs are `[table[t], table[256+t], table[512+t], table[768+t]]` in **upper-left, lower-left, upper-right, lower-right** order. Palette index is `t >> 6`. Pattern IDs alone are not global CHR identities: resolve through active MMC3 background banks.

The `sourceNames` field contains source constants/descriptions when defined, e.g. pipes, cloud segments, question blocks, platform corners. Unknown names remain unknown; they are not guessed from image appearance.

## Full World 1-1 reconstruction (verified)

- `W101L`: CPU `$BB82`, PRG bank 15, ROM `0x1FB92`.
- Entire stream: 273 bytes (next `W101_BonusL` begins at ROM `0x1FCA3`).
- Header: `93 BC 06 C0 EA 80 81 01 00`.
- Alternate-layout pointer: `$BC93`; alternate object pointer: `$C006`.
- Header byte 4 low nibble: 10, meaning 11 horizontal screens.
- Byte 5 bits 0–2: background palette 0; bits 3–4: sprite palette selection 0 (set row 8).
- Byte 7 low five bits: background-bank preset 1.
- Preset 1: bank bases `$08` and `$60`, measured in 1 KB CHR units; MMC3 background registers select 2 KB chunks. Animated graphics can change the second chunk later.
- `PalSet_Plains`: CPU `$AC92`, bank 27, ROM `0x36CA2`; first background palette row is `3C 0F 30 3C 3C 0F 36 27 3C 0F 2A 1A 3C 0F 31 21`.
- `W101O`: CPU `$C527`, bank 6, ROM `0xC537`. Enemy/object placement data is a leading byte, object-ID/x-column/y-row triples, then `$FF`.

### Prefer the original loader to a partial decompressor

The original level loader at `PRG/prg030.asm:4173` interprets each initial three-byte record. Byte 0 high three bits select a generator family; byte 0 low five bits provide row information. Byte 1 gives screen/column. Byte 2 high nibble chooses variable-size versus fixed-size construction; generator-specific code can consume additional bytes. `$E0` family records establish junctions. `$FF` terminates.

Therefore **do not split the entire stream into fixed triples**. Reimplementing a few generator shapes will silently corrupt later records. Either port every relevant original generator or execute the original loader in the emulator.

The loader already expands the complete active level into SRAM `Tile_Mem`, starting at `$6000`. For horizontal levels, each screen is 27 rows × 16 columns = `$1B0` bytes. The authoritative address is:

```
0x6000 + floor(tileX / 16) * 0x1B0 + tileY * 16 + (tileX % 16)
```

World coordinates are `tileX*16`, `tileY*16`. Subtract the actual rendered camera offsets to get screen coordinates. The vertical camera is a word composed of `Level_VertScrollH` at `$0542` and `Level_VertScroll` at `$0543`; do not assume a fixed zero-Y origin. Source: `Tile_Mem_Addr` and `LoadLevel_Set_TileMemAddr` in `prg030.asm`. Vertical levels use a different 15-row screen organization.

The full active map is available before traversing the entire level. Runtime block mutations update SRAM; preserve those updates when replacing visuals.

## Player reconstruction (verified)

- `SPPF_Offsets`: ROM `0x3AC10`, 81 bytes.
- `SPPF_Table`: ROM `0x3AC61`, 81 × 6 bytes.
- `Player_FramePageOff`: ROM `0x3AE47`, 81 bytes.
- `Player_PUpRootPage`: ROM `0x3AEA8`, seven bytes: `50 54 54 00 50 40 44` for Small, Big, Fire, Leaf, Frog, Tanooki, Hammer.
- Sprite pattern `$F1` is a hidden-sprite sentinel.
- Positions are upper row `(0,0),(8,0),(16,0)` and lower row `(0,16),(8,16),(16,16)` before facing/special adjustments.
- Odd patterns below `$40`: global CHR pattern indices are `(suitRoot + framePageOffset)*64 + (pattern & 0xFE)` and the next pattern for the lower 8×8 half.
- Patterns `$40+` address other MMC3 sprite-bank slots and require that bank context; the Kuribo shoe is one reason blindly assuming the player bank fails.
- The compositor mirrors repeated patterns and has extra logic for facing, somersault, Kuribo shoe, hiding and special states. Source: `Player_Draw` in `PRG/prg029.asm`.

81 is a shared template count. Combining all seven suits with all templates mechanically creates invalid animations; action-selection tables determine reachable combinations.

## Standard and special object rendering

Five groups of 36 standard objects live in PRG banks 1–5. CPU addresses within each bank:

- Attributes 1/2/3: `$A0D8`, `$A0FC`, `$A120`.
- Pattern-table selector: `$A144`.
- Kill action: `$A168`.
- Pattern-start offsets: `$A18C`.
- Pattern data: `$A1B0` plus the per-object start offset.

Typical frames use pairs of 8×16 sprite patterns. The manifests expose original descriptors and bytes, not invented geometry. Giant enemies and multiple specialized routines do not follow the generic pair layout; some pattern data begins with a jump instruction. Special controllers above `$B3` are not all visible objects.

A comprehensive reconstruction pipeline must combine:

1. Exhaustive raw CHR extraction.
2. Verified metatile/player/default-object descriptors.
3. Specialized source draw routines and their labeled data.
4. State/bank-aware composition checks against emulator output.

The exact source reconstruction makes (3) tractable, but the current manifest does not falsely claim every code-driven animation has already been turned into a standalone model.

## Credits

Source analysis and semantic names use the Southbird SMB3 disassembly: https://www.sonicepoch.com/sm3mix/ and https://github.com/captainsouthbird/smb3 . Preserve this credit in derivative technical work.
