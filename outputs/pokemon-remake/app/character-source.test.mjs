import test from 'node:test';
import assert from 'node:assert/strict';
import {decodeCharacterSprite} from './character-source.mjs';

function memory({oneD = true, width16 = false} = {}) {
  const sprites = new Uint8Array(64 * 0x44), vram = new Uint8Array(0x8000), palette = new Uint8Array(512);
  const v = new DataView(sprites.buffer); sprites[0x3e] = 1;
  // 8x8 or 16x16 square, tile 4, palette bank 3.
  v.setUint16(2, width16 ? 0x4000 : 0, true); v.setUint16(4, 0x3004, true);
  palette[(3 * 16 + 1) * 2] = 31;
  return {sprites, vram, palette, oneD};
}
const at = (sprite, x, y) => [...sprite.rgba.slice((y * sprite.width + x) * 4, (y * sprite.width + x + 1) * 4)];

test('object tile base, palette bank, transparent zero and source flips', () => {
  const m = memory(); m.vram[4 * 32] = 1;
  const normal = decodeCharacterSprite(m, 0);
  assert.deepEqual(at(normal, 0, 0), [255,0,0,255]); assert.deepEqual(at(normal, 1, 0), [0,0,0,0]);
  new DataView(m.sprites.buffer).setUint16(2, 0x3000, true);
  const flipped = decodeCharacterSprite(m, 0);
  assert.deepEqual(at(flipped, 7, 7), [255,0,0,255]); assert.equal(flipped.opaquePixels, 1);
  assert.notEqual(normal.pixelHash, flipped.pixelHash);
});

test('1D and 2D mapping use the correct source tile row stride', () => {
  for (const oneD of [true, false]) {
    const m = memory({oneD, width16:true}); m.vram[(4 + (oneD ? 2 : 32)) * 32] = 0x10;
    const sprite = decodeCharacterSprite(m, 0);
    assert.deepEqual(at(sprite, 1, 8), [255,0,0,255]); assert.equal(sprite.opaquePixels, 1);
  }
});

test('native viewport invisibility does not discard active actors', () => {
  const m = memory(); m.sprites[0x3e] |= 4; m.vram[4 * 32] = 1;
  assert.equal(decodeCharacterSprite(m, 0).opaquePixels, 1);
  m.sprites[0x3e] = 0; assert.equal(decodeCharacterSprite(m, 0), null);
});

test('invalid and unsupported sprites do not acquire invented pixels', () => {
  const m = memory();
  for (const id of [-1, 64, 0.5, undefined]) assert.equal(decodeCharacterSprite(m, id), null);
  new DataView(m.sprites.buffer).setUint16(0, 0x100, true);
  assert.equal(decodeCharacterSprite(m, 0).unsupported, 'affine or 8bpp object');
});
