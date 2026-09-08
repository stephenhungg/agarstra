// Direct adapter for @wasm-gaming/mgba-wasm@0.1.1, mGBA c034660f.
// The ROM remains the sole authority for game logic. Reads are immutable snapshots.
export const Keys = Object.freeze({ A:1, B:2, Select:4, Start:8, Right:16, Left:32, Up:64, Down:128, R:256, L:512 });
const regions = [
  [0x02000000, 0x40000, 0x21000, 'EWRAM'],
  [0x03000000, 0x8000, 0x19000, 'IWRAM'],
  [0x04000000, 0x400, 0x400, 'IO'],
  [0x05000000, 0x400, 0x800, 'palette'],
  [0x06000000, 0x18000, 0x1000, 'VRAM'],
  [0x07000000, 0x400, 0xc00, 'OAM'],
];

export class GbaAdapter {
  constructor(module, rom) {
    this.m = module;
    this.rom = new Uint8Array(rom);
    this.m._mgbawasm_init();
    this.m._mgbawasm_set_log_level(1);
    const ptr = this.m._malloc(this.rom.length);
    this.m.HEAPU8.set(this.rom, ptr);
    const ok = this.m._mgbawasm_load(ptr, this.rom.length, 0, 0, 0, 0, 1);
    this.m._free(ptr);
    if (!ok) throw new Error('mGBA ROM load failed');
    this.stateSize = this.m._mgbawasm_state_size();
    if (this.stateSize !== 0x61000) throw new Error('Unsupported mGBA state layout');
    this.statePtr = this.m._malloc(this.stateSize);
    this.audioPtr = this.m._malloc(8192 * 4);
    this.keys = 0;
    this.snapshot();
    this.identity = this.state.slice(8, 12); // mGBA ROM CRC32
  }
  get frame() { return this.m._mgbawasm_frame_counter(); }
  get fps() { return this.m._mgbawasm_framerate_micro() / 1e6; }
  get width() { return this.m._mgbawasm_video_width(); }
  get height() { return this.m._mgbawasm_video_height(); }
  setKeys(mask) { this.keys = mask & 1023; this.m._mgbawasm_set_keys(this.keys); }
  step(frames = 1, keys = this.keys) {
    if (!Number.isInteger(frames) || frames < 0) throw new Error('frames must be a non-negative integer');
    this.setKeys(keys);
    const audio = [];
    for (let i = 0; i < frames; i++) {
      this.m._mgbawasm_run_frame();
      audio.push(...this.drainAudio());
    }
    this.snapshot();
    return { frame: this.frame, audio };
  }
  pixels() {
    const ptr = this.m._mgbawasm_video_ptr();
    return this.m.HEAPU8.slice(ptr, ptr + this.width * this.height * 4);
  }
  drainAudio() {
    const chunks = [];
    let count;
    while ((count = this.m._mgbawasm_read_audio(this.audioPtr, 8192)) > 0) {
      chunks.push({ sampleRate: this.m._mgbawasm_sample_rate(), samples: this.m.HEAP16.slice(this.audioPtr / 2, this.audioPtr / 2 + count * 2) });
    }
    return chunks;
  }
  snapshot() {
    // mGBA leaves reserved fields untouched; its serialized layout requires zeroes.
    this.m.HEAPU8.fill(0, this.statePtr, this.statePtr + this.stateSize);
    if (!this.m._mgbawasm_state_save(this.statePtr)) throw new Error('mGBA snapshot failed');
    this.state = this.m.HEAPU8.slice(this.statePtr, this.statePtr + this.stateSize);
    this.view = new DataView(this.state.buffer);
    if (this.view.getUint32(0, true) !== 0x0100000b) throw new Error('Unsupported mGBA state magic');
    return this.state;
  }
  readBytes(address, length) {
    if (!Number.isInteger(address) || !Number.isInteger(length) || length < 0) throw new RangeError('Invalid memory range');
    if (address >= 0x08000000 && address + length <= 0x08000000 + this.rom.length) return this.rom.slice(address - 0x08000000, address - 0x08000000 + length);
    for (const [base, size, offset] of regions) {
      if (address >= base && address + length <= base + size) return this.state.slice(offset + address - base, offset + address - base + length);
    }
    throw new RangeError(`Unmapped snapshot range 0x${address.toString(16)} + ${length}`);
  }
  read8(address) { return this.readBytes(address, 1)[0]; }
  read16(address) { return new DataView(this.readBytes(address, 2).buffer).getUint16(0, true); }
  read32(address) { return new DataView(this.readBytes(address, 4).buffer).getUint32(0, true); }
  saveState() { return this.snapshot().slice(); }
  loadState(bytes) {
    if (bytes.length !== this.stateSize || this.identity.some((v, i) => v !== bytes[i + 8])) throw new Error('State belongs to a different ROM or version');
    this.m.HEAPU8.set(bytes, this.statePtr);
    if (!this.m._mgbawasm_state_load(this.statePtr)) throw new Error('mGBA state restore failed');
    this.setKeys(0);
    this.drainAudio();
    this.snapshot();
    // Pixels update only on the next source frame; do not claim old pixels are restored.
  }
  saveSram() {
    const length = this.m._mgbawasm_sram_save();
    const ptr = this.m._mgbawasm_sram_ptr();
    return this.m.HEAPU8.slice(ptr, ptr + length);
  }
  loadSram(bytes) {
    const ptr = this.m._malloc(bytes.length);
    this.m.HEAPU8.set(bytes, ptr);
    const ok = this.m._mgbawasm_sram_load(ptr, bytes.length);
    this.m._free(ptr);
    if (!ok) throw new Error('SRAM load failed');
  }
  destroy() {
    this.m._free(this.statePtr); this.m._free(this.audioPtr); this.m._mgbawasm_unload();
  }
}
