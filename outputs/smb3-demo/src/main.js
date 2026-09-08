import { runtimeProfile, reloadTogether } from "./production-gate.js";
import "./style.css";
import { GameBridge, NES_FPS } from "./bridge.js";
import { WorldRenderer } from "./source-renderer.js";
import { PhotorealRenderer } from "./photoreal-renderer.js";
import { SourcePatchOverlay } from "./source-patches.js";
import { recompose } from "./rom-extractor.js";
import { Controller } from "./vendor/jsnes/index.js";

const $ = (id) => document.getElementById(id);
const original = $("original"),
  reference = $("reference");
const originalContext = original.getContext("2d", { alpha: false });
const referenceContext = reference.getContext("2d", { alpha: false });
const frameImage = originalContext.createImageData(256, 240);
const rgba = new Uint32Array(frameImage.data.buffer);
let resolveReady, rejectReady;
window.demoReady = new Promise((resolve, reject) => {
  resolveReady = resolve;
  rejectReady = reject;
});
window.demoReady.catch(() => {});
let bridge,
  world,
  photoWorld,
  sourcePatches,
  renderStyle = "photoreal",
  ready = false,
  started = false,
  paused = true,
  originalMode = false,
  soundEnabled = false;
let audioContext,
  audioNode,
  audioChunk = new Float32Array(1024),
  audioIndex = 0;
let accumulator = 0,
  lastTick = 0,
  fpsFrames = 0,
  fpsEpoch = 0,
  measuredFPS = 0,
  renderCount = 0;
let loading = false,
  currentLighting = "day",
  forcedOriginal = false,
  coverageBlocked = false,
  lastRemodeledMode = "level";
const keyboard = new Map(),
  gamepadHeld = new Set();
const mappings = {
  ArrowLeft: "LEFT",
  ArrowRight: "RIGHT",
  ArrowUp: "UP",
  ArrowDown: "DOWN",
  KeyX: "A",
  Space: "A",
  KeyZ: "B",
  ShiftLeft: "B",
  Enter: "START",
  ShiftRight: "SELECT",
};

function showFrame(pixels) {
  for (let i = 0; i < 61440; i++) rgba[i] = (pixels[i] | 0xff000000) >>> 0;
  originalContext.putImageData(frameImage, 0, 0);
  referenceContext.putImageData(frameImage, 0, 0);
}
function sample(left, right) {
  if (!soundEnabled || paused || !audioNode) return;
  audioChunk[audioIndex++] = left;
  audioChunk[audioIndex++] = right;
  if (audioIndex === audioChunk.length) {
    audioNode.port.postMessage({ samples: audioChunk }, [audioChunk.buffer]);
    audioChunk = new Float32Array(1024);
    audioIndex = 0;
  }
}
function flushAudio() {
  audioIndex = 0;
  audioNode?.port.postMessage({ flush: true });
}
async function enableAudio() {
  if (!audioContext) {
    audioContext = new AudioContext({
      sampleRate: 44100,
      latencyHint: "interactive",
    });
    await audioContext.audioWorklet.addModule(
      new URL("./audio-worklet.js", import.meta.url),
    );
    audioNode = new AudioWorkletNode(audioContext, "nes-audio", {
      numberOfInputs: 0,
      numberOfOutputs: 1,
      outputChannelCount: [2],
    });
    const gain = audioContext.createGain();
    gain.gain.value = 0.55;
    audioNode.connect(gain);
    gain.connect(audioContext.destination);
  }
  await audioContext.resume();
}
async function setSound(value) {
  try {
    if (value) await enableAudio();
    soundEnabled = value;
    flushAudio();
    $("sound-state").textContent = value ? "ON" : "OFF";
    $("sound").setAttribute("aria-pressed", String(value));
  } catch (error) {
    console.error("Audio unavailable", error);
    soundEnabled = false;
    $("sound-state").textContent = "UNAVAILABLE";
  }
}
function releaseInputs() {
  if (bridge)
    for (const name of new Set(Object.values(mappings)))
      bridge.button(name, false);
  keyboard.clear();
  gamepadHeld.clear();
}
function syncInputs() {
  if (!bridge) return;
  const active = new Set([...keyboard.values(), ...gamepadHeld]);
  for (const name of new Set(Object.values(mappings)))
    bridge.button(name, active.has(name));
}
function setPaused(value) {
  if (!value && coverageBlocked && renderStyle === "photoreal" && !originalMode) value = true;
  paused = value;
  accumulator = 0;
  lastTick = performance.now();
  if (value) {
    releaseInputs();
    flushAudio();
  }
  $("pause-pill").hidden = !value || !started;
  $("pause").textContent = value ? "Resume" : "Pause";
}
function setMode(value) {
  originalMode = value;
  const showOriginal = value || forcedOriginal;
  original.hidden = !showOriginal;
  $("world").hidden = showOriginal || renderStyle !== "source";
  $("photoreal").hidden = showOriginal || renderStyle !== "photoreal";
  $("source-patches").hidden = showOriginal || renderStyle !== "photoreal" || coverageBlocked || !sourcePatches?.stats.pixelCount;
  $("coverage-overlay").hidden = showOriginal || renderStyle !== "photoreal" || !coverageBlocked;
  $("modern-mode").classList.toggle(
    "selected",
    !value && renderStyle === "photoreal",
  );
  $("source-mode").classList.toggle(
    "selected",
    !value && renderStyle === "source",
  );
  $("original-mode").classList.toggle("selected", value);
  $("render-label").textContent = showOriginal
    ? "ORIGINAL"
    : renderStyle === "photoreal"
      ? "REMODELED"
      : "SOURCE 3D";
  return originalMode;
}
function setStyle(value) {
  renderStyle = value;
  forcedOriginal = false;
  setMode(false);
  draw();
}
function setLighting(value) {
  currentLighting = value;
  world?.setLighting(value);
  photoWorld?.setLighting(value === "source" ? "day" : value);
  $("daylight").classList.toggle("selected", value === "day");
  $("dusk").classList.toggle("selected", value === "dusk");
  $("source-colors").classList.toggle("selected", value === "source");
}
function draw(dt = 0) {
  if (!ready) return;
  const scene = bridge.getScene();
  const renderable = scene.semantic?.renderable ?? scene.semantic?.supported;
  if (renderStyle === "photoreal" && !originalMode && renderable) {
    photoWorld.update(scene, dt);
    lastRemodeledMode = scene.semantic.mode;
    sourcePatches.update(scene.extraction, photoWorld.getStats().unresolvedObjects || [], scene.semantic.cameraX);
  }
  const blocked = renderStyle === "photoreal" && !originalMode && !renderable;
  if (coverageBlocked !== blocked) {
    coverageBlocked = blocked;
    if (blocked && started && !paused) setPaused(true);
    $("coverage-title").textContent = lastRemodeledMode === "death" ? "Try again." : "More of the world awaits.";
    $("coverage-message").textContent = "This area is not remodeled yet. Replay World 1–1, or continue in the original view.";
    setMode(originalMode);
  }
  const unsupported = renderStyle === "source" && !scene.extraction;
  if (forcedOriginal !== unsupported) {
    forcedOriginal = unsupported;
    setMode(originalMode);
  }
  $("scene-label").textContent = coverageBlocked ? "END OF REMODELED AREA" : unsupported
    ? scene.mode === "worldmap"
      ? "WORLD MAP · R TO RESTART DEMO"
      : scene.mode === "death"
        ? "TRY AGAIN · R TO RESTART"
        : "ORIGINAL VIEW · R TO RESTART DEMO"
    : scene.mode === "worldmap"
      ? "WORLD MAP"
      : scene.mode === "death"
        ? "TRY AGAIN · R TO RESTART"
        : "WORLD 1–1";
  if (!originalMode && !forcedOriginal) {
    if (renderStyle === "source") world.update(scene, dt);
  }
  $("source-patches").hidden = originalMode || forcedOriginal || renderStyle !== "photoreal" || coverageBlocked || !sourcePatches.stats.pixelCount;
  if (!originalMode && !forcedOriginal && renderStyle === "photoreal")
    $("render-label").textContent = !coverageBlocked && sourcePatches.stats.objectCount ? "REMODELED · SOURCE DETAILS" : "REMODELED";
  if (coverageBlocked) $("pause-pill").hidden = true;
  $("frame").textContent = `frame ${scene.frame.toLocaleString()}`;
  renderCount++;
}
function advance(frames, buttons = []) {
  for (const b of buttons) bridge.button(b, true);
  for (let i = 0; i < frames; i++) {
    if (coverageBlocked && renderStyle === "photoreal" && !originalMode) break;
    bridge.step();
    draw(1 / NES_FPS);
  }
  for (const b of buttons) bridge.button(b, false);
  return bridge.getScene();
}
function padInput(pads = navigator.getGamepads?.() || []) {
  const p = Array.from(pads).find(Boolean);
  if (!p) {
    if (gamepadHeld.size) {
      gamepadHeld.clear();
      syncInputs();
    }
    return;
  }
  const active = new Set();
  if (p.axes[0] < -0.35 || p.buttons[14]?.pressed) active.add("LEFT");
  if (p.axes[0] > 0.35 || p.buttons[15]?.pressed) active.add("RIGHT");
  if (p.axes[1] < -0.35 || p.buttons[12]?.pressed) active.add("UP");
  if (p.axes[1] > 0.35 || p.buttons[13]?.pressed) active.add("DOWN");
  if (p.buttons[0]?.pressed) active.add("A");
  if (p.buttons[1]?.pressed || p.buttons[2]?.pressed) active.add("B");
  if (p.buttons[9]?.pressed) active.add("START");
  gamepadHeld.clear();
  for (const b of active) gamepadHeld.add(b);
  syncInputs();
}
function tick(now) {
  requestAnimationFrame(tick);
  if (!ready || loading) {
    lastTick = now;
    return;
  }
  const elapsed = lastTick ? now - lastTick : 0;
  lastTick = now;
  if (!paused) {
    // Long desktop suspension pauses wall-clock catch-up; no emulated tick is skipped.
    if (elapsed > 250) {
      accumulator = 0;
      flushAudio();
    } else accumulator += elapsed;
    padInput();
    let count = 0;
    while (accumulator >= 1000 / NES_FPS && count < 8) {
      bridge.step();
      accumulator -= 1000 / NES_FPS;
      count++;
    }
  }
  draw(paused ? 0 : Math.min(elapsed / 1000, 0.05));
  fpsFrames++;
  if (now - fpsEpoch >= 1000) {
    measuredFPS = Math.round((fpsFrames * 1000) / (now - fpsEpoch));
    $("fps").textContent = `${measuredFPS} fps`;
    fpsFrames = 0;
    fpsEpoch = now;
  }
}
function resize() {
  const box = $("stage").getBoundingClientRect();
  world?.resize(box.width, box.height);
  photoWorld?.resize(box.width, box.height);
  draw();
}
async function loadGame(data) {
  if (!data) return;
  loading = true;
  ready = false;
  releaseInputs();
  flushAudio();
  $("loading-overlay").hidden = false;
  $("choose-rom").hidden = true;
  $("loading-text").textContent = "Opening World 1…";
  // Paint the progress state before the bounded emulator boot.
  await new Promise((r) => setTimeout(r, 35));
  bridge = new GameBridge({ onFrame: showFrame, onAudioSample: sample });
  bridge.load(new Uint8Array(data.bytes));
  bridge.bootToLevel();
  ready = true;
  loading = false;
  started = false;
  paused = true;
  forcedOriginal = false;
  accumulator = 0;
  $("connection").textContent = "LOCAL ROM CONNECTED";
  $("loading-overlay").hidden = true;
  $("start-overlay").hidden = false;
  $("pause-pill").hidden = true;
  setMode(false);
  setPaused(true);
  draw();
  resolveReady();
}
async function restart() {
  if (!ready || loading) return;
  const wasStarted = started;
  setPaused(true);
  loading = true;
  $("loading-text").textContent = "Back to the first jump…";
  $("loading-overlay").hidden = false;
  await new Promise((r) => setTimeout(r, 25));
  bridge.reset();
  photoWorld.resetAnimation?.();
  coverageBlocked = false;
  loading = false;
  forcedOriginal = false;
  setMode(originalMode);
  draw();
  $("loading-overlay").hidden = true;
  if (wasStarted) {
    started = true;
    $("start-overlay").hidden = true;
    setPaused(false);
  } else setPaused(true);
}
function start() {
  if (!ready) return;
  started = true;
  $("start-overlay").hidden = true;
  setPaused(false);
  $("stage").focus();
}
function showError(error) {
  console.error(error);
  loading = false;
  $("loading-overlay").hidden = false;
  $("loading-text").textContent = error.message || String(error);
  $("choose-rom").hidden = false;
  $("connection").textContent = "ROM NEEDED";
  document.querySelector(".loader").style.display = "none";
}

$("play").addEventListener("click", () => {
  start();
  setSound(true);
});
$("pause").addEventListener("click", () => {
  if (!started) start();
  else setPaused(!paused);
});
$("restart").addEventListener("click", restart);
$("coverage-retry").addEventListener("click", restart);
$("coverage-original").addEventListener("click", () => {
  setMode(true);
  coverageBlocked = false;
  setPaused(false);
  draw();
});
$("original-mode").addEventListener("click", () => setMode(true));
$("modern-mode").addEventListener("click", () => setStyle("photoreal"));
$("source-mode").addEventListener("click", () => setStyle("source"));
$("daylight").addEventListener("click", () => setLighting("day"));
$("dusk").addEventListener("click", () => setLighting("dusk"));
$("source-colors").addEventListener("click", () => {
  setStyle("source");
  setLighting("source");
});
$("sound").addEventListener("click", () => setSound(!soundEnabled));
$("fullscreen").addEventListener("click", () => window.desktop.fullscreen());
$("choose-rom").addEventListener("click", async () => {
  try {
    await loadGame(await window.desktop.chooseROM());
  } catch (error) {
    showError(error);
  }
});
document.addEventListener("keydown", (event) => {
  if ($("asset-dialog").open) return;
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  if (["Tab", "KeyP", "KeyR", ...Object.keys(mappings)].includes(event.code))
    event.preventDefault();
  if (event.repeat) return;
  if (event.code === "Tab") {
    setMode(!originalMode);
    return;
  }
  if (event.code === "KeyP") {
    if (!started) start();
    else setPaused(!paused);
    return;
  }
  if (event.code === "KeyR") {
    restart();
    return;
  }
  const name = mappings[event.code];
  if (!name || !ready || loading) return;
  if (!started) {
    start();
    setSound(true);
    if (name === "START") return;
  }
  if (paused) return;
  keyboard.set(event.code, name);
  syncInputs();
});
document.addEventListener("keyup", (event) => {
  if (keyboard.delete(event.code)) syncInputs();
});
window.addEventListener("blur", () => {
  if (started && ready) setPaused(true);
});
window.addEventListener("resize", resize);
new ResizeObserver(resize).observe($("stage"));

function inspectAssets() {
  if (!ready) return;
  setPaused(true);
  const frame = bridge.extractor.getFrame(),
    grid = $("asset-grid");
  grid.replaceChildren();
  $("asset-summary").textContent =
    `Frame ${bridge.frame.toLocaleString()} · ${frame.assets.length} bank-and-palette-specific tile assets · ${frame.backgroundTiles.length} background placements · ${frame.sprites.length} hardware sprites. Click any tile for ROM provenance.`;
  for (const asset of frame.assets) {
    const button = document.createElement("button");
    button.className = "asset-cell";
    button.title = asset.kind;
    button.dataset.kind = asset.kind;
    button.setAttribute("aria-pressed", "false");
    const canvas = document.createElement("canvas");
    canvas.width = canvas.height = 8;
    const ctx = canvas.getContext("2d"),
      data = ctx.createImageData(8, 8);
    data.data.set(asset.rgba);
    ctx.putImageData(data, 0, 0);
    button.append(canvas);
    button.addEventListener("click", () => {
      for (const sibling of grid.children)
        sibling.setAttribute("aria-pressed", "false");
      button.setAttribute("aria-pressed", "true");
      const z = $("asset-zoom").getContext("2d");
      z.putImageData(data, 0, 0);
      const mapped = asset.mappedSources || [];
      const first = mapped[0] || asset.romSources[0];
      $("asset-provenance").textContent = [
        `Kind: ${asset.kind}`,
        `Blender mesh: ${world.registry.get(asset.id)?.assetId || "uncatalogued · source fallback"}`,
        `${mapped.length ? "Mapped" : "Matching"} CHR tiles: ${mapped.length ? mapped.map((s) => s.tileIndex).join(", ") : first?.tileIndex}`,
        `ROM offset: 0x${first?.romOffset.toString(16).toUpperCase()}`,
        ...(mapped.length > 1
          ? [
              `All mapped ROM offsets: ${mapped.map((s) => "0x" + s.romOffset.toString(16).toUpperCase()).join(", ")}`,
            ]
          : []),
        `1 KB CHR bank${mapped.length > 1 ? "s" : ""}: ${mapped.length ? [...new Set(mapped.map((s) => s.bank1k))].join(", ") : first?.bank1k}`,
        `Mapped copies this frame: ${mapped.length}`,
        `Identical ROM copies: ${asset.romSources.length}`,
        `Raw bytes:`,
        Array.from(asset.chrBytes, (v) => v.toString(16).padStart(2, "0")).join(
          " ",
        ),
        `Palette:`,
        asset.palette
          .map(
            (c) =>
              "#" +
              [c & 255, (c >> 8) & 255, (c >> 16) & 255]
                .map((v) => v.toString(16).padStart(2, "0"))
                .join(""),
          )
          .join(" "),
      ].join("\n");
    });
    grid.append(button);
  }
  $("asset-dialog").showModal();
  (
    grid.querySelector('[data-kind="sprite"]') || grid.firstElementChild
  )?.click();
}
$("inspect-assets").addEventListener("click", inspectAssets);
$("close-assets").addEventListener("click", () => $("asset-dialog").close());
$("reload-assets").addEventListener("click", async () => {
  if (!ready) return;
  setPaused(true);
  const button = $("reload-assets");
  button.disabled = true;
  try {
    const [stats] = await reloadTogether([world,photoWorld]);
    $("verification-label").textContent =
      `Reloaded ${stats.loadedAssets} Blender assets · ${stats.loadFailures} errors`;
    draw();
  } catch (error) {
    $("verification-label").textContent = `Asset release rejected; previous release retained: ${error.message}`;
  } finally {
    button.disabled = false;
  }
});
$("verify-assets").addEventListener("click", () => {
  if (!ready) return;
  setPaused(true);
  const decoded = recompose(bridge.extractor.getFrame());
  let bad = 0;
  for (let i = 0; i < decoded.length; i++)
    if (decoded[i] !== bridge.pixels[i]) bad++;
  $("verification-label").textContent =
    `Frame ${bridge.frame}: ${bad === 0 ? "61,440 / 61,440 pixels match" : bad + " pixel differences"}`;
});

function sceneSummary() {
  const s = bridge?.getScene();
  if (!s) return s;
  const { extraction, semantic, ...rest } = s;
  return {
    ...rest,
    semanticSummary: semantic
      ? {
          supported: semantic.supported,
          renderable: semantic.renderable,
          objects: semantic.objects.length,
          entities: semantic.entities.length,
          unknown: semantic.unknown.length,
          coverage: semantic.coverage,
        }
      : null,
    extractionSummary: extraction
      ? {
          frame: extraction.frame,
          assets: extraction.assets.length,
          backgroundTiles: extraction.backgroundTiles.length,
          sprites: extraction.sprites.length,
        }
      : null,
  };
}
window.demo = {
  get ready() {
    return ready;
  },
  get bridge() {
    return bridge;
  },
  get world() {
    return world;
  },
  get photoWorld() {
    return photoWorld;
  },
  start,
  pause: () => setPaused(true),
  resume: () => setPaused(false),
  reset: restart,
  setMode,
  setStyle,
  setLighting,
  setSound,
  advance,
  status: () => ({
    ready,
    started,
    paused,
    originalMode,
    renderStyle,
    forcedOriginal,
    coverageBlocked,
    currentLighting,
    soundEnabled,
    audioState: audioContext?.state,
    frame: bridge?.frame,
    scene: sceneSummary(),
    assets: Object.keys(world?.models || {}),
    fps: measuredFPS,
    renderer: world?.renderer.info.render,
    remodeled: photoWorld?.getStats?.(),
    sourcePatches: sourcePatches?.stats,
  }),
  async runSmoke() {
    setPaused(true);
    setStyle("source");
    started = true;
    $("start-overlay").hidden = true;
    $("pause-pill").hidden = true;
    const results = [];
    const check = (name, ok, detail) => results.push({ name, ok, detail });
    const initial = bridge.getScene();
    check(
      "booted to level",
      initial.player.visible && initial.player.screenX === 24,
      { frame: initial.frame, x: initial.player.screenX, y: initial.player.y },
    );
    keyboard.set("ArrowRight", "RIGHT");
    syncInputs();
    padInput([{ axes: [1, 0], buttons: [] }]);
    padInput([]);
    check(
      "gamepad disconnect preserves held keyboard input",
      bridge.nes.controllers[1].state[Controller.BUTTON_RIGHT] === 0x41,
    );
    keyboard.clear();
    syncInputs();
    padInput([{ axes: [1, 0], buttons: [] }]);
    padInput([]);
    check(
      "gamepad disconnect releases its held input",
      bridge.nes.controllers[1].state[Controller.BUTTON_RIGHT] === 0x40,
    );
    const before = bridge.frame;
    setMode(true);
    check(
      "original toggle preserves simulation",
      bridge.frame === before && !original.hidden,
    );
    setMode(false);
    check("modern toggle restores canvas", !$("world").hidden);
    const walk = advance(20, ["RIGHT"]);
    check(
      "right input moves original player",
      walk.player.screenX > initial.player.screenX,
      { from: initial.player.screenX, to: walk.player.screenX },
    );
    const jump = advance(18, ["RIGHT", "A"]);
    check("jump raises original player", jump.player.y < initial.player.y, {
      from: initial.player.y,
      to: jump.player.y,
    });
    const stateFrame = bridge.frame;
    setLighting("dusk");
    check(
      "lighting preserves simulation",
      bridge.frame === stateFrame && world.mode === "dusk",
    );
    setLighting("day");
    bridge.reset();
    draw();
    const reset = bridge.getScene();
    check(
      "reset reproduces start",
      reset.player.screenX === initial.player.screenX &&
        reset.player.y === initial.player.y,
    );
    const pauseFrame = bridge.frame;
    await new Promise((r) => setTimeout(r, 120));
    check("pause holds simulation", bridge.frame === pauseFrame);
    const audit = world.getStats?.() || world.stats || {};
    check(
      "source-linked Blender assets loaded",
      (audit.loadedAssets || audit.registryLoaded || 0) > 100,
      audit,
    );
    check(
      "Blender replacements reinserted into live frame",
      audit.blenderInstances > 100 && audit.loadFailures === 0,
      audit,
    );
    const frame = bridge.extractor.getFrame(),
      rebuilt = recompose(frame);
    let mismatch = 0;
    for (let i = 0; i < rebuilt.length; i++)
      if (rebuilt[i] !== bridge.pixels[i]) mismatch++;
    check("independent extracted-frame recomposition matches", mismatch === 0, {
      pixels: rebuilt.length,
      mismatches: mismatch,
    });
    const gpu = world.verifySourcePixels(bridge.pixels);
    check(
      "GPU source view matches original playfield",
      gpu.mismatches === 0,
      gpu,
    );
    const reloadFrame = bridge.frame;
    await world.reloadAssets();
    check(
      "reload Blender replacements preserves simulation",
      bridge.frame === reloadFrame &&
        world.stats.loadedAssets === 193 &&
        world.stats.loadFailures === 0,
    );
    inspectAssets();
    check(
      "live asset inspector exposes ROM provenance",
      $("asset-grid").children.length === frame.assets.length &&
        $("asset-provenance").textContent.includes("ROM offset: 0x"),
    );
    $("asset-dialog").close();
    check(
      "WebGL produces draw calls",
      world.renderer.info.render.calls > 0,
      world.renderer.info.render,
    );
    await setSound(true);
    check(
      "audio worklet starts",
      soundEnabled && audioContext?.state === "running",
    );
    await setSound(false);
    setLighting("source");
    // Leave a real recorded jump on screen for the captured visual check.
    advance(20, ["RIGHT"]);
    advance(18, ["RIGHT", "A"]);
    draw(0);
    const movingGpu = world.verifySourcePixels(bridge.pixels);
    check(
      "GPU source view preserves moving sprite composition",
      movingGpu.mismatches === 0,
      movingGpu,
    );
    const sourceFrame = bridge.frame;
    setStyle("photoreal");
    setLighting("day");
    draw();
    const photoAudit = photoWorld.getStats();
    check(
      "whole-object remodel uses original semantic scene",
      bridge.frame === sourceFrame && bridge.getScene().semantic.supported,
      {
        frame: sourceFrame,
        objects: bridge.getScene().semantic.objects.length,
      },
    );
    check(
      "remodeled Blender assets loaded",
      photoAudit.loadedModels >= 8 && photoAudit.loadFailures === 0,
      photoAudit,
    );
    check(
      "remodeled renderer draws real geometry",
      photoWorld.renderer.info.render.calls > 0,
      photoWorld.renderer.info.render,
    );
    check(
      "every visible opening-scene object has a replacement",
      !photoAudit.needsOriginal && photoAudit.missingModels.length === 0 && !forcedOriginal,
      { missing: photoAudit.missingModels, fallback: forcedOriginal },
    );
    const cloud = photoWorld.models.get("cloud");
    photoWorld.models.delete("cloud");
    for (const [key, instance] of photoWorld.instances) {
      if (instance.modelId === "cloud") {
        photoWorld.actorRoot.remove(instance.group);
        photoWorld.instances.delete(key);
      }
    }
    draw();
    check("missing replacement preserves 3D and uses only source object pixels", !forcedOriginal && original.hidden && !$("photoreal").hidden && sourcePatches.stats.pixelCount > 0 && sourcePatches.stats.pixelCount < 4096);
    if (cloud) photoWorld.models.set("cloud", cloud);
    draw();
    check("restored replacement resumes remodel without advancing ROM", !forcedOriginal && bridge.frame === sourceFrame);
    check("opening characters contain real exported animation clips", ["mario-body", "goomba"].every(id => photoWorld.models.get(id)?.clips.length >= 3));
    bridge.reset();
    photoWorld.resetAnimation();
    draw();
    advance(30, ["RIGHT"]);
    const walking = photoWorld.getStats().animation;
    check("Mario and Goomba play walk clips from ROM movement", walking.states.some(s => s.id === "player" && ["walk", "run"].includes(s.clip)) && walking.states.some(s => s.modelId === "goomba" && s.clip === "walk"), walking.states);
    const frozenFrame = bridge.frame;
    const clipTimes = () => JSON.stringify(photoWorld.getStats().animation.states.map(s => [s.id, s.clip, s.time]));
    const beforePause = clipTimes();
    await new Promise(r => setTimeout(r, 90));
    draw();
    check("paused game freezes exported animation clips", bridge.frame === frozenFrame && clipTimes() === beforePause);
    advance(18, ["RIGHT", "A"]);
    check("jump selects an airborne clip", photoWorld.getStats().animation.states.some(s => s.id === "player" && s.clip.startsWith("jump-")));
    bridge.reset();
    photoWorld.resetAnimation();
    draw();
    advance(100, ["RIGHT"]);
    const dying = bridge.getScene();
    check("death stays in the remodeled level", dying.semantic.mode === "death" && dying.semantic.renderable && !forcedOriginal && original.hidden && !$("photoreal").hidden);
    check("Mario plays an exported death pose", photoWorld.getStats().animation.states.some(s => s.id === "player" && s.clip === "death"));
    advance(260);
    check("unmapped transition pauses on 3D with an explicit choice", coverageBlocked && paused && !$("coverage-overlay").hidden && original.hidden && !forcedOriginal);
    const boundaryFrame = bridge.frame;
    setMode(true);
    draw();
    check("original view remains an explicit user choice", !original.hidden && bridge.frame === boundaryFrame);
    setStyle("photoreal");
    await restart();
    setPaused(true);
    check("retry restores the animated level", !coverageBlocked && original.hidden && bridge.getScene().semantic.renderable);
    advance(20, ["RIGHT"]);
    advance(18, ["RIGHT", "A"]);
    $("pause-pill").hidden = true;
    return {
      passed: results.every((r) => r.ok),
      checks: results,
      frame: bridge.frame,
      scene: sceneSummary(),
      renderer: {
        calls: world.renderer.info.render.calls,
        triangles: world.renderer.info.render.triangles,
      },
      scope:
        "ROM-driven whole-object reconstruction with shared baked PBR materials; broader semantic and art coverage remains tracked",
    };
  },
};

async function init() {
  $("verification-label").textContent = runtimeProfile() === "prototype" ? "prototype mode · assets have not passed production acceptance" : "production mode · verifying accepted asset evidence";
  world = new WorldRenderer($("world"));
  photoWorld = new PhotorealRenderer($("photoreal"));
  sourcePatches = new SourcePatchOverlay($("source-patches"));
  setLighting(currentLighting);
  resize();
  fpsEpoch = performance.now();
  requestAnimationFrame(tick);
  const assetsReady = reloadTogether([world,photoWorld]);
  const rom = await window.desktop.defaultROM();
  await assetsReady;
  if (rom) await loadGame(rom);
  else
    showError(
      new Error("Choose Super Mario Bros. 3 (USA) (Rev 1) to enter World 1."),
    );
}
init().catch((error) => {
  showError(error);
  rejectReady(error);
});
