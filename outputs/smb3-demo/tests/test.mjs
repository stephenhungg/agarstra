import { readROM } from "./read-rom.mjs";
import assert from "node:assert/strict";
import fs from "node:fs";
import crypto from "node:crypto";
import { GameBridge } from "../src/bridge.js";
const rom = readROM();
const digest = (bytes) =>
  crypto.createHash("sha256").update(bytes).digest("hex");
function run() {
  let callbacks = 0,
    audioCallbacks = 0;
  const b = new GameBridge({
    onFrame: () => callbacks++,
    onAudioSample: () => audioCallbacks++,
  });
  b.load(rom);
  b.bootToLevel();
  assert.equal(b.frame, 1391, "extraction must capture the final boot frame without adding a tick");
  assert(b.getScene().extraction?.assets.length > 0, "initial boot frame has actual extracted assets");
  b.bootToLevel();
  assert.equal(b.frame, 1391, "repeated boot is idempotent");
  assert.equal(callbacks, 1);
  assert.equal(audioCallbacks, 0);
  let s = b.getScene();
  assert.equal(s.player.x, 24);
  assert.equal(s.player.y, 162);
  assert.equal(s.cameraX, 0);
  assert.equal(s.tiles.filter((t) => t.type === "question").length, 4);
  assert(s.tiles.some((t) => t.type === "ground" && t.y === 178));
  let maxCamera = 0,
    minY = 162;
  const states = [];
  for (let i = 0; i < 220; i++) {
    if (i === 9) b.button("RIGHT", true);
    if (i === 39) b.button("A", true);
    if (i === 69) b.button("A", false);
    b.step();
    s = b.getScene();
    maxCamera = Math.max(maxCamera, s.cameraX);
    minY = Math.min(minY, s.player.y);
    assert(Number.isFinite(s.player.x));
    assert(s.cameraX >= 0);
    states.push(digest(Buffer.from(b.nes.cpu.mem.slice(0, 2048))));
  }
  assert(minY < 120, "jump changes actual Mario y");
  assert(maxCamera > 100, "scroll captured");
  assert(callbacks === 221);
  assert(audioCallbacks > 0);
  b.reset();
  assert.equal(b.getScene().player.x, 24);
  assert.equal(b.getScene().player.y, 162);
  return { states, maxCamera, minY };
}
const a = run(),
  b = run();
assert.deepEqual(a, b);
console.log(
  JSON.stringify(
    {
      passed: true,
      deterministicFrames: a.states.length,
      maxCamera: a.maxCamera,
      minMarioY: a.minY,
      checks: [
        "boot",
        "frame and audio callback gating",
        "Mario OAM position",
        "question block and floor extraction",
        "jump",
        "scroll",
        "reset",
        "deterministic replay",
      ],
    },
    null,
    2,
  ),
);
