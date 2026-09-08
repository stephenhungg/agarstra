# Portable NES candidate player

This directory must remain beside `../nes`, which provides the portable JSNES runtime, its Apache-2.0 license, qualification rules, and source extraction. No game ROM is included. It is a standalone Vite/Three application, not the SMB3 demo and not a semantic game adapter.

```sh
npm install
npm run dev
```

Open the local URL, choose a supported user-supplied `.nes` file, and press Enter to start. Keyboard, standard gamepad, and pointer controls drive the original JSNES simulation. All 240 scanlines are reconstructed from observed PPU source tiles and sprite operations; the framebuffer is used only by the separate Original view and diagnostic comparison. Audio starts only after Enable audio.

Supported qualification: NTSC iNES, NROM/mapper 0 or MMC3/mapper 4, immutable CHR-ROM. NES 2.0, other consoles/mappers, CHR-RAM, trainers, PAL, ambiguous headers, and truncated files fail explicitly. Mapper compatibility does not establish every game's correctness.

## Candidate registry

`public/assets/source-registry.json` contains:

```json
{"profile":"prototype","romSha256":"exact ROM SHA-256","assets":[{"id":"unique tile ID","path":"models/tile.glb","width":8,"height":8,"sha256":"optional candidate byte hash","source":{"sourceIdentity":"full extractor asset ID"}}]}
```

GLB coordinates represent an 8×8 tile at x=0…0.5 and y=0…−0.5 in glTF XY; its top-left is the origin. Preserve one source pixel per 1/16 world unit. Registry identities include CHR bytes, palette, and background/sprite kind. Loaders verify all entries before replacing the active registry. A failed reload preserves the previous candidate set. A different ROM never reuses these candidates. This is explicitly a prototype path, not production acceptance.

Unobserved tile/palette variants and partially occluded draws use exact extracted tile fragments. This preserves gameplay presentation as new content appears, but those fallbacks are not Blender models and should never be counted as completed semantic assets. The provenance panel reports fallback versus GLB counts and ROM byte locations. Export observed asset capture records the current source frame for further authoring.

```sh
npm test
npm run build
# Optional browser smoke: install Playwright in the containing workspace first.
ROM_PATH=/path/to/user.nes PLAYER_URL=http://127.0.0.1:5173 node tests/browser-smoke.mjs
```

The smoke checks full-frame exact-color parity, original/reconstruction switching, reload preservation, and browser errors. It does not certify model aesthetics, deformation/animation quality, complete game coverage, or production approval.

When packaging the skill, exclude node_modules and dist. Keep the sibling NES vendor license and source. The inherited source renderer was adapted from this repository's source-renderer implementation, replacing its SMB3-height crop with full PPU clip metadata and a ROM-bound candidate registry.
