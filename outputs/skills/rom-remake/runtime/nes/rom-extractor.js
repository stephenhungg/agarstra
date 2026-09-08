/** Frame-correct immutable CHR extraction for the installed JSNES 2.1 PPU. */
const hex = (bytes) =>
  Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
const encode = (pix) => {
  const b = new Uint8Array(16);
  for (let y = 0; y < 8; y++)
    for (let x = 0; x < 8; x++) {
      let c = pix[y * 8 + x];
      b[y] |= (c & 1) << (7 - x);
      b[y + 8] |= ((c >> 1) & 1) << (7 - x);
    }
  return b;
};
export class RomAssetExtractor {
  constructor(nes, romBytes) {
    this.nes = nes;
    this.tileAssets = new WeakMap();
    this.tileSources = new WeakMap();
    this.assets = new Map();
    this.romTiles = new Map();
    this.frameNumber = 0;
    const rom = new Uint8Array(romBytes),
      start = 16 + (rom[6] & 4 ? 512 : 0) + rom[4] * 16384,
      end = start + rom[5] * 8192;
    if (!rom[5])
      throw new Error(
        "This extractor requires immutable CHR-ROM; CHR-RAM cache invalidation is not implemented.",
      );
    for (let offset = start; offset < end; offset += 16) {
      const key = hex(rom.subarray(offset, offset + 16));
      if (!this.romTiles.has(key)) this.romTiles.set(key, []);
      this.romTiles
        .get(key)
        .push({
          tileIndex: (offset - start) / 16,
          romOffset: offset,
          chrOffset: offset - start,
          bank1k: Math.floor((offset - start) / 1024),
        });
    }
    // Mapper0/MMC3 installs these exact Tile objects into PPU slots by reference.
    // Equal CHR bytes in another bank are aliases, not evidence that bank was used.
    for (let bank4k = 0; bank4k < nes.rom.vromTile.length; bank4k++)
      for (let index = 0; index < nes.rom.vromTile[bank4k].length; index++) {
        const tileIndex = bank4k * 256 + index,
          chrOffset = tileIndex * 16;
        this.tileSources.set(nes.rom.vromTile[bank4k][index], {
          tileIndex,
          romOffset: start + chrOffset,
          chrOffset,
          bank1k: Math.floor(chrOffset / 1024),
          bank4k,
        });
      }
    this.attach();
  }
  recordUse(asset, tile) {
    this.current.assetIds.add(asset.id);
    const source = this.tileSources.get(tile);
    if (source) {
      let mapped = this.current.mappedSources.get(asset.id);
      if (!mapped) {
        mapped = new Map();
        this.current.mappedSources.set(asset.id, mapped);
      }
      mapped.set(source.tileIndex, source);
    }
    return asset;
  }
  asset(tile, palette, kind) {
    // Qualified mappers map immutable CHR-ROM Tile objects by reference; cache per object + palette.
    // Do not use this cache for CHR-RAM games whose tile objects mutate in place.
    const cacheKey = kind + ":" + palette.join(",");
    let variants = this.tileAssets.get(tile);
    if (!variants) {
      variants = new Map();
      this.tileAssets.set(tile, variants);
    }
    const cached = variants.get(cacheKey);
    if (cached) return this.recordUse(cached, tile);
    const bytes = encode(tile.pix),
      raw = hex(bytes),
      pal = Array.from(palette),
      id =
        raw +
        ":" +
        pal.map((c) => c.toString(16).padStart(6, "0")).join("") +
        ":" +
        kind;
    let a = this.assets.get(id);
    if (!a) {
      const pixels = new Uint8Array(tile.pix),
        rgba = new Uint8Array(256);
      for (let i = 0; i < 64; i++) {
        const c = pal[pixels[i]],
          j = i * 4;
        rgba[j] = c & 255;
        rgba[j + 1] = (c >> 8) & 255;
        rgba[j + 2] = (c >> 16) & 255;
        rgba[j + 3] = pixels[i] === 0 ? 0 : 255;
      }
      a = {
        id,
        chrBytes: bytes,
        palette: pal,
        pixels,
        rgba,
        kind,
        romSources: this.romTiles.get(raw) || [],
      };
      this.assets.set(id, a);
    }
    variants.set(cacheKey, a);
    return this.recordUse(a, tile);
  }
  attach() {
    const p = this.nes.ppu,
      self = this;
    if (p.__romAssetExtractor)
      throw new Error("Extractor already attached to this PPU");
    p.__romAssetExtractor = this;
    const wrap = (name, fn) => {
      const original = p[name];
      p[name] = function (...args) {
        return fn.call(this, original, args);
      };
    };
    wrap("startFrame", function (original, args) {
      const result = original.apply(this, args);
      const clearColor =
        this.f_dispType === 0
          ? this.imgPalette[0]
          : { 0: 0, 1: 0x00ff00, 2: 0x0000ff, 4: 0xff0000 }[this.f_color] || 0;
      self.current = {
        frame: ++self.frameNumber,
        clearColor,
        operations: [],
        assetIds: new Set(),
        mappedSources: new Map(),
        background: new Map(),
        spriteInstances: new Map(),
      };
      return result;
    });
    wrap("renderBgScanline", function (original, [buffered, scan]) {
      if (!self.current) return original.call(this, buffered, scan);
      const fineY = this.cntFV,
        fineX = this.regFH,
        palette = Array.from(this.imgPalette),
        regHT = this.regHT,
        cntVT = this.cntVT,
        cntV = this.cntV,
        regH = this.regH,
        regS = this.regS;
      const valid = scan < 240 && scan - fineY >= 0 && scan >= 0;
      const result = original.call(this, buffered, scan);
      if (valid) {
        const rows = [];
        for (let i = 0; i < 32; i++) {
          const tile = this.scantile[i];
          if (!tile) continue;
          const att = this.attrib[i],
            asset = self.asset(tile, palette.slice(att, att + 4), "background"),
            x = i * 8 - fineX,
            y = scan - fineY;
          rows.push({ x, assetId: asset.id, sourceY: fineY });
          const id = `${x},${y},${asset.id}`;
          if (!self.current.background.has(id)) {
            const col = (regHT + i) % 32,
              ntH = (regH + Math.floor((regHT + i) / 32)) % 2,
              table = this.ntable1[cntV * 2 + ntH];
            self.current.background.set(id, {
              id,
              x,
              y,
              width: 8,
              height: 8,
              assetId: asset.id,
              rowMask: 0,
              attribute: att,
              paletteIndex: att / 4,
              nametable: table,
              tileColumn: col,
              tileRow: cntVT,
              patternTable: regS,
            });
          }
          self.current.background.get(id).rowMask |= 1 << fineY;
        }
        self.current.operations.push({
          kind: "background",
          scan,
          buffered,
          rows,
        });
      }
      return result;
    });
    wrap("renderFramePartially", function (original, [start, count]) {
      if (
        self.current &&
        this.f_spVisibility !== 1 &&
        this.f_bgVisibility === 1
      )
        self.current.operations.push({ kind: "compose", start, count });
      return original.call(this, start, count);
    });
    wrap(
      "renderSpritesPartially",
      function (original, [start, count, priority]) {
        if (!self.current) return original.call(this, start, count, priority);
        if (priority === 0 && this.f_bgVisibility === 1)
          self.current.operations.push({ kind: "compose", start, count });
        if (this.f_spVisibility === 1) {
          const rows = [];
          for (
            let scan = Math.max(0, start);
            scan < Math.min(240, start + count);
            scan++
          )
            for (let i = 0; i < this.scanlineSpriteCount[scan]; i++) {
              const base = scan * 32 + i * 4,
                sy = this.scanlineSecondaryOAM[base] + 1,
                t = this.scanlineSecondaryOAM[base + 1],
                att = this.scanlineSecondaryOAM[base + 2],
                x = this.scanlineSecondaryOAM[base + 3],
                flipY = !!(att & 128),
                flipX = !!(att & 64),
                height = this.f_spriteSize ? 16 : 8;
              if (((att >> 5) & 1) !== priority) continue;
              const fineY = scan - sy;
              if (fineY < 0 || fineY >= height) continue;
              let idx, sourceY;
              if (height === 8) {
                idx = t + (this.f_spPatternTable ? 256 : 0);
                sourceY = flipY ? 7 - fineY : fineY;
              } else {
                const top = t & 1 ? (t & 0xfe) + 256 : t & 0xfe,
                  half = fineY < 8 ? 0 : 1;
                idx = top + (flipY ? 1 - half : half);
                sourceY = flipY ? 7 - (fineY % 8) : fineY % 8;
              }
              const palAdd = (att & 3) * 4,
                asset = self.asset(
                  this.ptTile[idx],
                  this.sprPalette.slice(palAdd, palAdd + 4),
                  "sprite",
                );
              const row = {
                scan,
                x,
                sourceY,
                assetId: asset.id,
                flipX,
                priorityIndex: i,
              };
              rows.push(row);
              const key = `${x},${sy},${t},${att},${height}`;
              if (!self.current.spriteInstances.has(key))
                self.current.spriteInstances.set(key, {
                  id: key,
                  x,
                  y: sy,
                  width: 8,
                  height,
                  tileNumber: t,
                  attributes: att,
                  paletteIndex: att & 3,
                  flipX,
                  flipY,
                  backgroundPriority: priority,
                  halves: {},
                  visibleScanlines: [],
                });
              const instance = self.current.spriteInstances.get(key);
              instance.halves[Math.floor(fineY / 8)] = asset.id;
              if (!instance.visibleScanlines.includes(scan))
                instance.visibleScanlines.push(scan);
            }
          self.current.operations.push({ kind: "sprites", rows });
        }
        return original.call(this, start, count, priority);
      },
    );
    wrap("endFrame", function (original, args) {
      if (self.current) {
        const c = self.current;
        self.latest = {
          frame: c.frame,
          width: 256,
          height: 240,
          clearColor: c.clearColor,
          assets: [...c.assetIds].map((id) => ({
            ...self.assets.get(id),
            mappedSources: [...(c.mappedSources.get(id)?.values() || [])],
          })),
          backgroundTiles: [...c.background.values()],
          sprites: [...c.spriteInstances.values()],
          operations: c.operations,
          clip: {
            left:
              this.clipToTvSize ||
              this.f_bgClipping === 0 ||
              this.f_spClipping === 0,
            right: this.clipToTvSize,
            vertical: this.clipToTvSize,
          },
        };
      }
      return original.apply(this, args);
    });
  }
  getFrame() {
    return this.latest;
  }
}
/** Independent rasterization from extracted 2-bit CHR assets, no framebuffer reads. */
export function recompose(frame) {
  const output = new Uint32Array(256 * 240).fill(frame.clearColor),
    background = new Uint32Array(256 * 240),
    priority = new Uint16Array(256 * 240).fill(65),
    assets = new Map(frame.assets.map((a) => [a.id, a]));
  for (const op of frame.operations) {
    if (op.kind === "background")
      for (const row of op.rows) {
        const a = assets.get(row.assetId);
        for (let sx = 0; sx < 8; sx++) {
          const x = row.x + sx;
          if (x < 0 || x >= 256) continue;
          const c = a.pixels[row.sourceY * 8 + sx];
          if (c) {
            const at = op.scan * 256 + x;
            (op.buffered ? background : output)[at] = a.palette[c];
            priority[at] |= 256;
          }
        }
      }
    else if (op.kind === "compose") {
      const end = Math.min(240, op.start + op.count);
      for (let y = Math.max(0, op.start); y < end; y++)
        for (let x = 0; x < 256; x++) {
          const at = y * 256 + x;
          if (priority[at] > 255) output[at] = background[at];
        }
    } else if (op.kind === "sprites")
      for (const row of op.rows) {
        const a = assets.get(row.assetId);
        for (let sx = 0; sx < 8; sx++) {
          const x = row.x + sx;
          if (x < 0 || x >= 256) continue;
          const at = row.scan * 256 + x,
            c = a.pixels[row.sourceY * 8 + (row.flipX ? 7 - sx : sx)];
          if (c && row.priorityIndex <= (priority[at] & 255)) {
            output[at] = a.palette[c];
            priority[at] = (priority[at] & 0xf00) | row.priorityIndex;
          }
        }
      }
  }
  if (frame.clip.left)
    for (let y = 0; y < 240; y++) output.fill(0, y * 256, y * 256 + 8);
  if (frame.clip.right)
    for (let y = 0; y < 240; y++) output.fill(0, y * 256 + 248, y * 256 + 256);
  if (frame.clip.vertical) {
    output.fill(0, 0, 8 * 256);
    output.fill(0, 232 * 256);
  }
  return output;
}
