import { SourceRenderer } from './source-renderer.js';

// Reuse the source renderer's tested PPU ownership rules without creating a WebGL renderer.
export function rasterizeSourcePatches(frame, objects, cameraX = 0) {
  const width = 256, height = 192, pixels = new Uint8ClampedArray(width * height * 4);
  if (!frame || !objects.length) return { pixels, pixelCount: 0, objectCount: 0 };
  const decoder = {
    assets: new Map(frame.assets.map(a => [a.id, a])), stats: {},
    owner: new Int32Array(width * height), bgOwner: new Int32Array(width * height),
    priority: new Uint16Array(width * height),
  };
  const { draws, bg, sprites } = SourceRenderer.prototype.buildDraws.call(decoder, frame);
  SourceRenderer.prototype.visibleMasks.call(decoder, frame, draws, bg, sprites);
  const regions = objects.map(o => ({
    rect: o.screenRect || { x: o.x - cameraX, y: o.y, width: o.width, height: o.height },
    kind: o.cells?.length || ['ground','cloud','pipe','hill','bush','platform','question','brick','used-block'].includes(o.type) ? 'background' : 'sprite',
    spriteKeys: Array.isArray(o.source?.spriteKeys) ? new Set(o.source.spriteKeys) : null,
  }));
  for (const d of draws) {
    const selected = regions.filter(o => o.kind === d.kind &&
      (!o.spriteKeys || o.spriteKeys.has(d.spriteKey)) &&
      d.x < o.rect.x + o.rect.width && d.x + 8 > o.rect.x &&
      d.y < o.rect.y + o.rect.height && d.y + 8 > o.rect.y);
    if (!selected.length) continue;
    for (let ly = 0; ly < 8; ly++) for (let lx = 0; lx < 8; lx++) {
      const x = d.x + lx, y = d.y + ly;
      if (!d.mask[ly * 8 + lx] || !selected.some(o => x >= o.rect.x &&
        x < o.rect.x + o.rect.width && y >= o.rect.y && y < o.rect.y + o.rect.height)) continue;
      const source = ((d.flipY ? 7 - ly : ly) * 8 + (d.flipX ? 7 - lx : lx)) * 4;
      pixels.set(d.asset.rgba.subarray(source, source + 4), (y * width + x) * 4);
    }
  }
  let pixelCount = 0;
  for (let i = 3; i < pixels.length; i += 4) if (pixels[i]) pixelCount++;
  return { pixels, pixelCount, objectCount: objects.length };
}

export class SourcePatchOverlay {
  constructor(canvas) {
    this.canvas = canvas;
    this.context = canvas.getContext('2d');
    this.stats = { pixelCount: 0, objectCount: 0 };
  }
  update(frame, objects, cameraX) {
    const key = JSON.stringify(objects.map(o => [o.id, o.screenRect, o.x, o.y, o.width, o.height]));
    if (this.last === frame && this.key === key) return this.stats;
    this.last = frame; this.key = key;
    const result = rasterizeSourcePatches(frame, objects, cameraX);
    this.context.putImageData(new ImageData(result.pixels, 256, 192), 0, 0);
    this.stats = { pixelCount: result.pixelCount, objectCount: result.objectCount };
    return this.stats;
  }
}
