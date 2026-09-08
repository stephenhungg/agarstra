const { app, BrowserWindow, ipcMain, dialog, Menu } = require("electron");
const fs = require("node:fs");
const path = require("node:path");
const { execFileSync } = require("node:child_process");
const crypto = require("node:crypto");

const profileFile = path.join(__dirname, "release-profile.json");
const packagedProfile = fs.existsSync(profileFile) ? JSON.parse(fs.readFileSync(profileFile, "utf8")).profile : null;
if (packagedProfile && !["production", "prototype"].includes(packagedProfile)) throw new Error("Invalid package release profile");
const assetProfile = packagedProfile || (process.argv.includes("--prototype") ? "prototype" : "production");
const applicationName = assetProfile === "prototype" ? "SMB3 Asset Lab Prototype" : "SMB3 Asset Lab";
app.setName(applicationName);
const smoke = process.argv.includes("--smoke");
const capturePath =
  process.env.DEMO_CAPTURE_DIR ||
  path.resolve(__dirname, "../../work/demo-tests");
const expectedHash =
  "4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579";
let win;

function readROM(file) {
  let bytes;
  if (path.extname(file).toLowerCase() === ".zip") {
    const entries = execFileSync("/usr/bin/unzip", ["-Z1", file], {
      encoding: "utf8",
      maxBuffer: 1024 * 1024,
    }).split("\n");
    const entry = entries.find((n) => /\.nes$/i.test(n));
    if (!entry) throw new Error("This archive contains no .nes ROM.");
    bytes = execFileSync("/usr/bin/unzip", ["-p", file, entry], {
      maxBuffer: 8 * 1024 * 1024,
    });
  } else bytes = fs.readFileSync(file);
  if (
    bytes.length < 16 ||
    bytes.toString("ascii", 0, 3) !== "NES" ||
    bytes[3] !== 26
  )
    throw new Error("This is not an iNES ROM.");
  const hash = crypto.createHash("sha256").update(bytes).digest("hex");
  if (hash !== expectedHash)
    throw new Error(
      "This demo is mapped to Super Mario Bros. 3 (USA) (Rev 1). Please select that ROM.",
    );
  return { bytes: Array.from(bytes), name: path.basename(file), hash };
}

ipcMain.handle("rom:default", () => {
  const candidates = [
    "/Users/stephenhung/Downloads/Super Mario Bros. 3.zip",
    path.resolve(__dirname, "../../work/rom-experiment/smb3.nes"),
  ];
  const file = candidates.find((f) => fs.existsSync(f));
  if (!file) return null;
  return readROM(file);
});
ipcMain.handle("rom:choose", async () => {
  const { canceled, filePaths } = await dialog.showOpenDialog(win, {
    title: "Choose your Super Mario Bros. 3 ROM",
    properties: ["openFile"],
    filters: [{ name: "NES ROM or ZIP", extensions: ["nes", "zip"] }],
  });
  return canceled ? null : readROM(filePaths[0]);
});
ipcMain.handle("window:fullscreen", () => {
  win.setFullScreen(!win.isFullScreen());
  return win.isFullScreen();
});

app.whenReady().then(async () => {
  Menu.setApplicationMenu(
    Menu.buildFromTemplate([
      {
        label: app.name,
        submenu: [{ role: "about" }, { type: "separator" }, { role: "quit" }],
      },
      {
        label: "View",
        submenu: [{ role: "togglefullscreen" }, { role: "toggleDevTools" }],
      },
    ]),
  );
  win = new BrowserWindow({
    width: 1440,
    height: 990,
    minWidth: 980,
    minHeight: 730,
    backgroundColor: "#101613",
    title: applicationName,
    titleBarStyle: "hiddenInset",
    trafficLightPosition: { x: 22, y: 24 },
    webPreferences: {
      preload: path.join(__dirname, "preload.cjs"),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });
  win.webContents.setWindowOpenHandler(() => ({ action: "deny" }));
  win.webContents.on("will-navigate", (e) => e.preventDefault());
  win.webContents.on("console-message", (event) =>
    process.stdout.write(`[renderer] ${event.message}\n`),
  );
  win.webContents.on("render-process-gone", (_e, details) =>
    console.error("Renderer ended:", details),
  );
  await win.loadFile(path.join(__dirname, "dist/index.html"), { query: { profile: assetProfile } });
  if (smoke) {
    try {
      const result = await win.webContents.executeJavaScript(
        "window.demoReady.then(() => window.demo.runSmoke())",
      );
      fs.mkdirSync(capturePath, { recursive: true });
      await new Promise((r) => setTimeout(r, 1000));
      const screenshot = await win.webContents.capturePage();
      fs.writeFileSync(path.join(capturePath, "demo.png"), screenshot.toPNG());
      await win.webContents.executeJavaScript(
        'window.demo.setLighting("dusk")',
      );
      await new Promise((r) => setTimeout(r, 150));
      fs.writeFileSync(
        path.join(capturePath, "dusk.png"),
        (await win.webContents.capturePage()).toPNG(),
      );
      await win.webContents.executeJavaScript('(async()=>{window.demo.setLighting("day");await window.demo.reset();window.demo.pause();window.demo.advance(30,["RIGHT"]);})()');
      await new Promise(r => setTimeout(r, 80));
      fs.writeFileSync(path.join(capturePath, "walk-a.png"), (await win.webContents.capturePage()).toPNG());
      await win.webContents.executeJavaScript('window.demo.advance(12,["RIGHT"])');
      await new Promise(r => setTimeout(r, 80));
      fs.writeFileSync(path.join(capturePath, "walk-b.png"), (await win.webContents.capturePage()).toPNG());
      await win.webContents.executeJavaScript('(async()=>{await window.demo.reset();window.demo.pause();window.demo.advance(500,["RIGHT"]);})()');
      await new Promise(r => setTimeout(r, 80));
      fs.writeFileSync(path.join(capturePath, "replay-choice.png"), (await win.webContents.capturePage()).toPNG());
      await win.webContents.executeJavaScript(
        'window.demo.setLighting("day"); window.demo.reset()',
      );
      app.focus({ steal: true });
      win.show();
      win.focus();
      win.webContents.focus();
      await new Promise(r => setTimeout(r, 100));
      await win.webContents.executeJavaScript('window.demo.resume()');
      const liveBefore = await win.webContents.executeJavaScript(
        "window.demo.status()",
      );
      win.webContents.sendInputEvent({ type: "keyDown", keyCode: "Right" });
      await new Promise((r) => setTimeout(r, 350));
      win.webContents.sendInputEvent({ type: "keyUp", keyCode: "Right" });
      win.webContents.sendInputEvent({ type: "keyDown", keyCode: "X" });
      await new Promise((r) => setTimeout(r, 170));
      win.webContents.sendInputEvent({ type: "keyUp", keyCode: "X" });
      win.webContents.sendInputEvent({ type: "keyDown", keyCode: "P" });
      win.webContents.sendInputEvent({ type: "keyUp", keyCode: "P" });
      await new Promise((r) => setTimeout(r, 80));
      const liveAfter = await win.webContents.executeJavaScript(
        "window.demo.status()",
      );
      result.checks.push({
        name: "native keyboard drives live simulation",
        ok:
          liveAfter.frame > liveBefore.frame &&
          liveAfter.scene.player.screenX > liveBefore.scene.player.screenX &&
          liveAfter.scene.player.y < liveBefore.scene.player.y,
        detail: {
          before: {
            frame: liveBefore.frame,
            x: liveBefore.scene.player.screenX,
            y: liveBefore.scene.player.y,
          },
          after: {
            frame: liveAfter.frame,
            x: liveAfter.scene.player.screenX,
            y: liveAfter.scene.player.y,
          },
        },
      });
      result.checks.push({ name: "native P key pauses", ok: liveAfter.paused });
      win.webContents.sendInputEvent({ type: "keyDown", keyCode: "Tab" });
      win.webContents.sendInputEvent({ type: "keyUp", keyCode: "Tab" });
      await new Promise((r) => setTimeout(r, 80));
      const toggled = await win.webContents.executeJavaScript(
        "window.demo.status()",
      );
      result.checks.push({
        name: "native Tab key changes view without advancing paused ROM",
        ok: toggled.originalMode && toggled.frame === liveAfter.frame,
      });
      fs.writeFileSync(
        path.join(capturePath, "original.png"),
        (await win.webContents.capturePage()).toPNG(),
      );
      await win.webContents.executeJavaScript(
        'document.getElementById("verify-assets").click()',
      );
      const verified = await win.webContents.executeJavaScript(
        'document.getElementById("verification-label").textContent',
      );
      result.checks.push({
        name: "verify button checks current extracted frame",
        ok: verified.includes("61,440 / 61,440 pixels match"),
        detail: verified,
      });
      await win.webContents.executeJavaScript(
        'document.getElementById("inspect-assets").click()',
      );
      await new Promise((r) => setTimeout(r, 100));
      fs.writeFileSync(
        path.join(capturePath, "asset-inspector.png"),
        (await win.webContents.capturePage()).toPNG(),
      );
      await win.webContents.executeJavaScript(
        'document.getElementById("close-assets").click()',
      );
      // Local live-scene throughput sample, after correctness checks/captures.
      app.focus({ steal: true });
      win.focus();
      win.webContents.focus();
      await new Promise(r => setTimeout(r, 100));
      // No input-latency or fixed refresh-rate assertion is made here.
      // A desktop focus change intentionally pauses gameplay. Record interrupted
      // attempts and reacquire focus; never count an interrupted interval as a
      // continuous gameplay sample or silently resume inside the measured window.
      result.performanceAttempts = [];
      for (let attempt = 0; attempt < 3; attempt++) {
        app.focus({ steal: true });
        win.focus();
        win.webContents.focus();
        await new Promise(r => setTimeout(r, 100));
        result.performance = await win.webContents.executeJavaScript(`
        (async () => {
          const demo = window.demo;
          demo.pause();
          demo.setMode(false);
          demo.setStyle("photoreal");
          demo.setLighting("day");
          await demo.reset();
          demo.start();
          const renderer = demo.photoWorld.renderer;
          const gl = renderer.getContext();
          const debug = gl.getExtension("WEBGL_debug_renderer_info");
          const metadata = {
            userAgent: navigator.userAgent,
            devicePixelRatio: window.devicePixelRatio,
            canvasWidth: renderer.domElement.width,
            canvasHeight: renderer.domElement.height,
            webglVersion: gl.getParameter(gl.VERSION),
            vendor: gl.getParameter(debug ? debug.UNMASKED_VENDOR_WEBGL : gl.VENDOR),
            renderer: gl.getParameter(debug ? debug.UNMASKED_RENDERER_WEBGL : gl.RENDERER),
          };
          const compact = () => {
            const s = demo.status();
            return { frame: s.frame, paused: s.paused, originalMode: s.originalMode,
              forcedOriginal: s.forcedOriginal, renderStyle: s.renderStyle,
              mode: s.scene.mode, cameraX: s.scene.cameraX,
              semanticSupported: s.scene.semanticSummary?.supported,
              needsOriginal: s.remodeled?.needsOriginal };
          };
          const focusLosses = [];
          const onBlur = () => focusLosses.push(performance.now());
          window.addEventListener("blur", onBlur);
          const focusedAtStart = document.hasFocus();
          const before = compact();
          const intervals = [], drawCalls = [], triangles = [], states = [before];
          const startTime = performance.now();
          let previous = startTime, lastState = startTime, timeoutExpired = false;
          await new Promise(resolve => {
            let raf;
            const deadline = setTimeout(() => {
              timeoutExpired = true;
              cancelAnimationFrame(raf);
              resolve();
            }, 10000);
            function sample(now) {
              intervals.push(now - previous);
              previous = now;
              drawCalls.push(renderer.info.render.calls);
              triangles.push(renderer.info.render.triangles);
              if (now - lastState >= 250) { states.push(compact()); lastState = now; }
              if (now - startTime >= 3000) { clearTimeout(deadline); resolve(); }
              else raf = requestAnimationFrame(sample);
            }
            raf = requestAnimationFrame(sample);
          });
          window.removeEventListener("blur", onBlur);
          const wallTimeMs = performance.now() - startTime;
          const after = compact();
          states.push(after);
          demo.pause();
          const restored = compact();
          const quantile = (values, q) => {
            if (!values.length) return null;
            const sorted = [...values].sort((a,b) => a-b);
            return sorted[Math.max(0, Math.ceil(q * sorted.length) - 1)];
          };
          return {
            scope: "Local live idle opening-level remodeled scene; not input latency or whole-game benchmark",
            targetWallTimeMs: 3000, wallTimeMs, timeoutExpired,
            focusedAtStart, focusLosses: focusLosses.map(time => time - startTime),
            emulatedFrames: after.frame - before.frame,
            emulatedFramesPerSecond: (after.frame - before.frame) * 1000 / wallTimeMs,
            rafSamples: intervals.length,
            rafCallbacksPerSecond: intervals.length * 1000 / wallTimeMs,
            frameIntervalMs: { median: quantile(intervals, .5), p95: quantile(intervals, .95), samples: intervals },
            drawCalls: { median: quantile(drawCalls, .5), max: quantile(drawCalls, 1) },
            triangles: { median: quantile(triangles, .5), max: quantile(triangles, 1) },
            metadata, before, after, restored, stateSamples: states,
            stayedInRemodeledLevel: states.every(s => !s.paused && !s.originalMode &&
              !s.forcedOriginal && s.renderStyle === "photoreal" &&
              s.mode === "level" && s.semanticSupported && !s.needsOriginal),
          };
        })()
      `);
        result.performanceAttempts.push(result.performance);
        if (result.performance.focusedAtStart && result.performance.focusLosses.length === 0) break;
      }
      result.checks.push({
        name: "local performance sample advances opening level without fallback",
        ok: result.performance.focusedAtStart && result.performance.focusLosses.length === 0 &&
          !result.performance.timeoutExpired &&
          result.performance.emulatedFrames > 0 &&
          result.performance.stayedInRemodeledLevel &&
          result.performance.restored.paused &&
          !result.performance.restored.originalMode,
        detail: {
          frames: result.performance.emulatedFrames,
          wallTimeMs: result.performance.wallTimeMs,
          stayedInRemodeledLevel: result.performance.stayedInRemodeledLevel,
        },
      });
      result.passed = result.checks.every((c) => c.ok);
      fs.writeFileSync(
        path.join(capturePath, "smoke-results.json"),
        JSON.stringify(result, null, 2),
      );
      console.log(
        "SMOKE_RESULT",
        JSON.stringify({
          passed: result.passed,
          checks: result.checks,
          renderer: result.renderer,
        }),
      );
      app.exit(result.passed ? 0 : 1);
    } catch (err) {
      console.error("SMOKE_FAILED", err);
      app.exit(1);
    }
  }
});
app.on("window-all-closed", () => app.quit());
