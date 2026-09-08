import { buildSemanticScene } from "./semantic-scene.js";
import { RomAssetExtractor } from "./rom-extractor.js";
import { NES, Controller } from "./vendor/jsnes/index.js";

/** SMB3 World 1 adapter. ROM remains authoritative; this is presentation data. */
export class GameBridge {
  constructor({ onFrame = () => {}, onAudioSample = () => {} } = {}) {
    this.onFrame = onFrame;
    this.onAudioSample = onAudioSample;
    this.frame = 0;
    this.cameraX = 0;
    this.lastScroll = 0;
    this.booting = false;
    this.nes = new NES({
      emulateSound: true,
      sampleRate: 44100,
      onFrame: (pixels) => {
        this.pixels = pixels;
        if (!this.booting) this.onFrame(pixels);
      },
      onAudioSample: (left, right) => {
        if (!this.booting) this.onAudioSample(left, right);
      },
      onError: (error) => {
        throw new Error(error);
      },
    });
    this.installScrollProbe();
  }
  installScrollProbe() {
    const ppu = this.nes.ppu;
    const original = ppu.scrollWrite.bind(ppu);
    ppu.scrollWrite = (value) => {
      // SMB3 restores scroll to zero for its status bar. Capture playfield write.
      if (ppu.firstWrite && !this.gotScroll) {
        this.renderScroll = value;
        this.gotScroll = true;
      }
      return original(value);
    };
  }
  load(bytes) {
    this.rom = new Uint8Array(bytes);
    this.nes.loadROM(this.rom);
    this.installScrollProbe();
    this.frame = 0;
    this.cameraX = 0;
    this.lastScroll = 0;
    this.renderScroll = 0;
    this.ready = false;
    this.levelSignature = null;
    this.extractor = null;
    this.previousEntities = [];
    this.nextEntityId = 1;
  }
  button(name, down) {
    const key = Controller["BUTTON_" + name.toUpperCase()];
    if (key === undefined) throw new Error("Unknown NES button: " + name);
    this.nes[down ? "buttonDown" : "buttonUp"](1, key);
  }
  bootToLevel() {
    if (this.ready && this.extractor) return this.getScene();
    this.booting = true;
    const actions = {
      300: ["START", true],
      302: ["START", false],
      600: ["START", true],
      602: ["START", false],
      900: ["A", true],
      902: ["A", false],
      1000: ["RIGHT", true],
      1002: ["RIGHT", false],
      1100: ["UP", true],
      1102: ["UP", false],
      1200: ["A", true],
      1202: ["A", false],
    };
    try {
      while (this.frame <= 1390) {
        const action = actions[this.frame];
        if (action) this.button(...action);
        // Capture the existing final boot frame instead of advancing an extra tick.
        if (this.frame === 1390 && !this.extractor)
          this.extractor = new RomAssetExtractor(this.nes, this.rom);
        this.step();
      }
      this.cameraX = 0;
      this.lastScroll = this.renderScroll;
      this.ready = true;
      this.levelSignature = [0x61, 0x62, 0x65, 0x66]
        .map((a) => this.nes.cpu.mem[a])
        .join(":");
    } finally {
      this.booting = false;
    }
    if (this.pixels) this.onFrame(this.pixels);
    return this.getScene();
  }
  reset() {
    if (!this.rom) return;
    this.load(this.rom);
    return this.bootToLevel();
  }
  step() {
    this.gotScroll = false;
    this.nes.frame();
    this.frame++;
    if (this.ready && this.gotScroll) {
      let delta = this.renderScroll - this.lastScroll;
      if (delta > 128) delta -= 256;
      if (delta < -128) delta += 256;
      this.cameraX = Math.max(0, this.cameraX + delta);
    }
    this.lastScroll = this.renderScroll;
    this.scene = null;
  }
  getScene() {
    if (this.scene) return this.scene;
    const ram = this.nes.cpu.mem,
      ppu = this.nes.ppu,
      raw = ppu.spriteMem;
    const spriteHeight = ppu.f_spriteSize ? 16 : 8;
    const sprites = [];
    for (let slot = 0; slot < 64; slot++) {
      const i = slot * 4,
        y = raw[i] + 1;
      if (y >= 192 || y < 1) continue;
      sprites.push({
        slot,
        x: raw[i + 3],
        y,
        tile: raw[i + 1],
        attributes: raw[i + 2],
        width: 8,
        height: spriteHeight,
        isPlayer: slot >= 8 && slot <= 11,
      });
    }
    // Small Mario uses 10/11; the upper pair 8/9 becomes visible after growth.
    const mario = sprites.filter((s) => s.isPlayer);
    const x = mario.length ? Math.min(...mario.map((s) => s.x)) : ram[0x90];
    const y = mario.length ? Math.min(...mario.map((s) => s.y)) : 192;
    const height = mario.length
      ? Math.max(...mario.map((s) => s.y + s.height)) - y
      : 16;
    const player = {
      id: "mario",
      type: "player",
      x: x + this.cameraX,
      y,
      screenX: x,
      worldX: ram[0x90] + ram[0x75] * 256,
      width: 16,
      height,
      visible: mario.length > 0,
      flipX: mario.length ? !(mario[0].attributes & 64) : false,
      facing: mario.length && mario[0].attributes & 64 ? 1 : -1,
      pose: mario[0]?.tile ?? 0,
    };
    const others = sprites.filter((s) => !s.isPlayer),
      grouped = [],
      used = new Set();
    for (const s of others) {
      if (used.has(s.slot)) continue;
      used.add(s.slot);
      const partner = others.find(
        (t) =>
          !used.has(t.slot) &&
          t.y === s.y &&
          Math.abs(t.x - s.x) === 8 &&
          (t.attributes & 3) === (s.attributes & 3),
      );
      if (partner) used.add(partner.slot);
      const tile = s.tile,
        type = [217, 219, 221, 223].includes(tile)
          ? "goomba"
          : tile === 235
            ? "goomba-flat"
            : [91, 105, 93, 107].includes(tile)
              ? "score"
              : [73, 77, 79].includes(tile)
                ? "coin"
                : tile === 119
                  ? "bouncing-block"
                  : "enemy";
      const e = {
        x: Math.min(s.x, partner?.x ?? s.x) + this.cameraX,
        y: s.y,
        width: partner ? 16 : 8,
        height: spriteHeight,
        type,
        tile,
        flipX: !!(s.attributes & 64),
      };
      const prev = this.previousEntities
        .filter((p) => p.type === type && !p.matched)
        .sort(
          (a, b) =>
            Math.hypot(a.x - e.x, a.y - e.y) - Math.hypot(b.x - e.x, b.y - e.y),
        )[0];
      if (prev && Math.hypot(prev.x - e.x, prev.y - e.y) < 32) {
        e.id = prev.id;
        prev.matched = true;
      } else e.id = "entity-" + this.nextEntityId++;
      grouped.push(e);
    }
    this.previousEntities = grouped.map((e) => ({ ...e }));
    // This level uses horizontally mirrored nametables and a streamed 256px ring.
    // y=239 scroll wraps into physical nametable1, making row0 begin at screen y2.
    const table = ppu.nameTable[1],
      tiles = [];
    const start = Math.floor(this.cameraX / 16) * 16;
    for (let wx = start; wx < start + 272; wx += 16) {
      const col = (((wx / 8) % 32) + 32) % 32;
      for (let row = 0; row < 24; row += 2) {
        const tile = table.tile[row * 32 + col],
          attribute = table.attrib[row * 32 + col];
        let type = null;
        if (row === 22 && [0x01, 0x0a].includes(tile)) type = "ground";
        else if ([0x98, 0x48, 0x4c].includes(tile)) type = "question";
        else if (tile === 0xd8) type = "used-block";
        else if ([0x68, 0x6a, 0x6e, 0x0f, 0x1a, 0x1c].includes(tile))
          type = "hill";
        else if (tile === 0x50) type = "bush";
        else if ([0x00, 0x03, 0x12, 0x37, 0x3c].includes(tile))
          type = "platform";
        else if ([0x28, 0x2d, 0x2f].includes(tile)) type = "cloud";
        if (type)
          tiles.push({
            id: `${wx}:${row}`,
            x: wx,
            y: row * 8 + 2,
            width: 16,
            height: 16,
            type,
            tile,
            attribute,
          });
      }
    }
    // Read-only, ROM-specific mode evidence. Verified through collision death and map return.
    const signature = [0x61, 0x62, 0x65, 0x66].map((a) => ram[a]).join(":");
    const mapFlag = ram[0xf4] === 1 && signature !== this.levelSignature;
    const dead = ram[0xf1] === 1 && ram[0x4e4] === 1;
    const sameLevel = signature === this.levelSignature;
    let mode = !this.ready
      ? "boot"
      : mapFlag
        ? "worldmap"
        : dead
          ? "death"
          : sameLevel && player.visible
            ? "level"
            : "transition";
    const supported =
      mode === "level" && sameLevel && this.cameraX <= 256 && height <= 32;
    const coverage = {
      supported,
      region: "world-1-1-opening",
      maxCameraX: 256,
      reason: supported
        ? "Mapped opening area"
        : mode !== "level"
          ? mode
          : !sameLevel
            ? "Unmapped level"
            : "Beyond verified opening area",
      confidence: "experimental ROM-specific RAM and PPU adapter",
    };
    player.power = height > 16 ? "large" : "small";
    player.dying = dead;
    const scene = {
      frame: this.frame,
      extraction: this.extractor?.getFrame(),
      cameraX: this.cameraX,
      camera: { x: this.cameraX, y: 0 },
      player,
      entities: grouped,
      sprites,
      tiles,
      terrain: tiles,
      mode,
      coverage,
      playfieldHeight: 192,
      screenWidth: 256,
      screenHeight: 240,
      stats: {
        spriteCount: sprites.length,
        entityCount: grouped.length,
        terrainCount: tiles.length,
      },
      limitations: [
        "world 1-1 visual mapping is experimental",
        "enemy identity uses spatial tracking",
        "unmapped tiles retain no 3D replacement",
      ],
    };
    scene.semantic = buildSemanticScene(this, scene);
    return (this.scene = scene);
  }
}
export const NES_FPS = 60.0988;
export const FRAME_FORMAT =
  "Uint32 packed 0x00BBGGRR; OR 0xff000000 before writing a little-endian RGBA ImageData buffer";
