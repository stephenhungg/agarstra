// BPRE English rev0, matching pret/pokefirered c75f3523.
// Read-only extraction of the current object image AFTER source animation/DMA.
// Sprite layout: include/sprite.h. Tile copies/flips: src/sprite.c.
export const CHARACTER_SOURCE = Object.freeze({
  romSHA1: '41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc',
  sprites: 0x0202063c, objVRAM: 0x06010000, objPalette: 0x05000200,
});
const sizes = [[[8,8],[16,16],[32,32],[64,64]], [[16,8],[32,8],[32,16],[64,32]], [[8,16],[8,32],[16,32],[32,64]]];

export function readCharacterMemory(core) {
  return {
    sprites: core.readBytes(CHARACTER_SOURCE.sprites, 64 * 0x44),
    vram: core.readBytes(CHARACTER_SOURCE.objVRAM, 0x8000),
    palette: core.readBytes(CHARACTER_SOURCE.objPalette, 512),
    oneD: Boolean(core.read16(0x04000000) & 64),
  };
}

export function decodeCharacterSprite(memory, spriteId) {
  if (!Number.isInteger(spriteId) || spriteId < 0 || spriteId >= 64) return null;
  const {sprites, vram, palette, oneD} = memory;
  const view = new DataView(sprites.buffer, sprites.byteOffset, sprites.byteLength), o = spriteId * 0x44;
  const a0 = view.getUint16(o, true), a1 = view.getUint16(o + 2, true), a2 = view.getUint16(o + 4, true);
  const dimensions = sizes[a0 >>> 14]?.[a1 >>> 14];
  if (!(sprites[o + 0x3e] & 1) || !dimensions) return null;
  // Standard overworld actors are non-affine 4bpp images. Fail visibly in the
  // report on unsupported forms instead of assigning another actor's pixels.
  if (a0 & 0x2100) return {unsupported: 'affine or 8bpp object', spriteId};
  const [width, height] = dimensions, tileNumber = a2 & 1023, paletteNumber = a2 >>> 12;
  const rgba = new Uint8Array(width * height * 4);
  let hash = 2166136261, opaquePixels = 0, bottom = -1;
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    const sx = a1 & 0x1000 ? width - 1 - x : x, sy = a1 & 0x2000 ? height - 1 - y : y;
    const tile = tileNumber + (sy >>> 3) * (oneD ? width / 8 : 32) + (sx >>> 3);
    const index = (vram[tile * 32 + (sy & 7) * 4 + ((sx & 7) >>> 1)] >>> ((sx & 1) * 4)) & 15;
    if (index) {
      const p = (paletteNumber * 16 + index) * 2, color = palette[p] | palette[p + 1] << 8, d = (y * width + x) * 4;
      rgba[d] = Math.round((color & 31) * 255 / 31);
      rgba[d + 1] = Math.round(((color >>> 5) & 31) * 255 / 31);
      rgba[d + 2] = Math.round(((color >>> 10) & 31) * 255 / 31);
      rgba[d + 3] = 255; opaquePixels++; bottom = y;
    }
  }
  for (const value of rgba) { hash ^= value; hash = Math.imul(hash, 16777619); }
  return {spriteId, width, height, rgba, opaquePixels, bottom,
    pixelHash: (hash >>> 0).toString(16).padStart(8, '0'),
    tileNumber, paletteNumber, hFlip: Boolean(a1 & 0x1000), vFlip: Boolean(a1 & 0x2000),
    animation: sprites[o + 0x2a], animationCommand: sprites[o + 0x2b],
    sourceAddress: CHARACTER_SOURCE.sprites + o,
    tileAddress: CHARACTER_SOURCE.objVRAM + tileNumber * 32,
    paletteAddress: CHARACTER_SOURCE.objPalette + paletteNumber * 32,
    imagesAddress: view.getUint32(o + 0x0c, true),
  };
}
