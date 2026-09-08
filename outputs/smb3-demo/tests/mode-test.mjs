import { readROM } from "./read-rom.mjs";
import assert from "node:assert/strict";
import fs from "node:fs";
import { GameBridge } from "../src/bridge.js";
const rom = readROM();
const bridge = new GameBridge();
bridge.load(rom);
bridge.bootToLevel();
assert.equal(bridge.getScene().mode, "level");
assert.equal(bridge.getScene().coverage.supported, true);
bridge.button("RIGHT", true);
const modes = new Set();
for (let i = 0; i < 600; i++) {
  bridge.step();
  const scene = bridge.getScene();
  modes.add(scene.mode);
  if (scene.mode !== "level") assert.equal(scene.coverage.supported, false);
  if (i === 100) assert.equal(scene.mode, "death");
  if (i === 500) assert.equal(scene.mode, "worldmap");
}
assert(modes.has("death"));
assert(modes.has("worldmap"));
bridge.reset();
assert.equal(bridge.getScene().mode, "level");
assert.equal(bridge.getScene().coverage.supported, true);
// A second emulator with the prototype scroll handler validates the observer has no effects.
const control = new GameBridge();
control.load(rom);
control.nes.ppu.scrollWrite = Object.getPrototypeOf(
  control.nes.ppu,
).scrollWrite.bind(control.nes.ppu);
control.bootToLevel();
for (let i = 0; i < 160; i++) {
  if (i === 9) {
    bridge.button("RIGHT", true);
    control.button("RIGHT", true);
  }
  if (i === 39) {
    bridge.button("A", true);
    control.button("A", true);
  }
  if (i === 69) {
    bridge.button("A", false);
    control.button("A", false);
  }
  bridge.step();
  control.step();
  assert.deepEqual(
    bridge.nes.cpu.mem.slice(0, 2048),
    control.nes.cpu.mem.slice(0, 2048),
  );
  assert.deepEqual(bridge.pixels, control.pixels);
}
console.log(
  JSON.stringify({
    passed: true,
    modes: [...modes],
    observerMatchesUninstrumentedFrames: 160,
    checks: [
      "death coverage fallback",
      "worldmap coverage fallback",
      "reset coverage restoration",
      "scroll hook does not affect RAM or rendered frames",
    ],
  }),
);
