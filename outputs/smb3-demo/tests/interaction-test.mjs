import { readROM } from "./read-rom.mjs";
import assert from "node:assert/strict";
import fs from "node:fs";
import { GameBridge } from "../src/bridge.js";
const b = new GameBridge();
b.load(readROM());
b.bootToLevel();
const actions = {
  9: ["RIGHT", true],
  39: ["A", true],
  69: ["A", false],
  95: ["RIGHT", false],
  160: ["LEFT", true],
  180: ["LEFT", false],
  230: ["A", true],
  260: ["A", false],
  340: ["RIGHT", true],
  353: ["RIGHT", false],
  420: ["A", true],
  450: ["A", false],
};
const seen = new Set();
let coinFrames = 0,
  bounceFrames = 0;
for (let i = 0; i < 550; i++) {
  if (actions[i]) b.button(...actions[i]);
  b.step();
  let s = b.getScene();
  assert.equal(
    s.mode,
    "level",
    `stomping or releasing controls must not trigger map fallback at ${i}`,
  );
  assert.equal(s.coverage.supported, true);
  for (const e of s.entities) seen.add(e.type);
  if (s.entities.some((e) => e.type === "coin")) coinFrames++;
  if (s.entities.some((e) => e.type === "bouncing-block")) bounceFrames++;
  if (i >= 253)
    assert(
      s.tiles.some(
        (t) => t.x === 176 && t.y === 114 && t.type === "used-block",
      ),
    );
  if (i >= 443)
    assert(
      s.tiles.some(
        (t) => t.x === 192 && t.y === 114 && t.type === "used-block",
      ),
    );
  if (i >= 242 && i <= 252)
    assert(
      s.entities.some((e) => e.type === "bouncing-block" && e.x === 176),
      "block remains represented throughout bump",
    );
}
for (const t of ["coin", "score", "goomba-flat", "bouncing-block"])
  assert(seen.has(t));
console.log(
  JSON.stringify({
    passed: true,
    frames: 550,
    coinFrames,
    bounceFrames,
    seen: [...seen],
    checks: [
      "two actual coin blocks hit",
      "used blocks stay visible",
      "bouncing block replaces temporarily removed tile",
      "coins and floating score classified",
      "no false worldmap after stomp/release",
    ],
  }),
);
