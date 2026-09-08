import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { fetchRegistry, parseVerifiedGLB, runtimeProfile } from "./production-gate.js";
const SCALE = 1 / 16,
  WIDTH = 256,
  HEIGHT = 240;
const keyRow = (id, x, scan, flip = false, sourceY = 0) =>
  `${id}|${x}|${scan}|${+flip}|${sourceY}`;

/** Source asset placement, never an emulator-framebuffer texture. */
export class SourceRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: false,
      alpha: false,
      powerPreference: "high-performance",
    });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.renderer.toneMapping = THREE.NoToneMapping;
    this.renderer.autoClear = false;
    this.scene = new THREE.Scene();
    this.camera = new THREE.OrthographicCamera(0, 16, 15, 0, 0.01, 50);
    this.camera.position.z = 20;
    this.assets = new Map();
    this.registry = new Map();
    this.prototypes = new Map();
    this.batches = new Map();
    this.fallbacks = [];
    this.last = null;
    this.mode = "source";
    this.owner = new Int32Array(WIDTH * HEIGHT);
    this.bgOwner = new Int32Array(WIDTH * HEIGHT);
    this.priority = new Uint16Array(WIDTH * HEIGHT);
    this.geometry = new THREE.PlaneGeometry(0.5, 0.5);
    this.ambient = new THREE.HemisphereLight(0xffffff, 0x687078, 2);
    this.sun = new THREE.DirectionalLight(0xfff1d6, 2);
    this.sun.position.set(-4, 15, 20);
    this.scene.add(this.ambient, this.sun);
    this.stats = {
      registryEntries: 0,
      loadedAssets: 0,
      loadFailures: 0,
      sourceInstances: 0,
      registryHits: 0,
      blenderInstances: 0,
      fallbackInstances: 0,
      partialMasks: 0,
      unseenAssets: 0,
      maskSource: "none",
    };
    this.resize(canvas.clientWidth || 1024, canvas.clientHeight || 768);
  }
  async prepareAssets() {
    const generation = this.assetGeneration = (this.assetGeneration || 0) + 1;
    const verified = await fetchRegistry('assets/source-registry.json');
    const registry = new Map(), prototypes = new Map();
    try {
      for (const {entry,bytes} of verified.values()) {
        if (runtimeProfile() === 'prototype' && (entry.width !== 8 || entry.height !== 8 || !entry.source?.sourceIdentity)) continue;
        if (entry.width !== 8 || entry.height !== 8 || !entry.source?.sourceIdentity)
          throw new Error('Source registry requires reviewed 8x8 source identity');
        if (registry.has(entry.source.sourceIdentity)) throw new Error('Duplicate source mapping');
        const gltf = await parseVerifiedGLB(new GLTFLoader(),bytes);
              gltf.scene.updateMatrixWorld(true);
              const parts = [];
              gltf.scene.traverse((object) => {
                if (!object.isMesh) return;
                const geometry = object.geometry
                  .clone()
                  .applyMatrix4(object.matrixWorld);
                const source = Array.isArray(object.material)
                  ? object.material
                  : [object.material];
                const exact = source.map(
                  (m) =>
                    new THREE.MeshBasicMaterial({
                      color: m.color.clone(),
                      map: m.map || null,
                      vertexColors: m.vertexColors,
                      side: THREE.DoubleSide,
                      toneMapped: false,
                    }),
                );
                const physical = source.map((m) => {
                  const n = m.clone();
                  n.side = THREE.DoubleSide;
                  return n;
                });
                parts.push({
                  geometry,
                  exact: exact.length === 1 ? exact[0] : exact,
                  physical: physical.length === 1 ? physical[0] : physical,
                });
              });

        registry.set(entry.source.sourceIdentity,entry);
        prototypes.set(entry.source.sourceIdentity,parts);
      }
    } catch (error) {
      this.disposePrototypes(prototypes);
      throw error;
    }
    const validate = () => { if (generation !== this.assetGeneration) throw new Error('Superseded source release'); };
    const commit = () => {
      validate();
      for (const batch of this.batches.values()) for (const mesh of batch.meshes) { this.scene.remove(mesh); mesh.dispose(); }
      this.batches.clear();
      this.disposePrototypes(this.prototypes);
      this.registry = registry;
      this.prototypes = prototypes;
      Object.assign(this.stats,{registryEntries:registry.size,loadedAssets:prototypes.size,loadFailures:0});
      delete this.stats.registryError;
      if (this.last) this.update(this.last,0);
      return this.getStats();
    };
    commit.validate = validate;
    commit.dispose = () => this.disposePrototypes(prototypes);
    return commit;
  }
  disposePrototypes(prototypes) {
    for (const parts of prototypes.values()) for (const part of parts) {
      part.geometry.dispose();
      for (const material of [part.exact,part.physical].flat()) material.dispose();
    }
  }
  async init() { return this.reloadAssets(); }
  getStats() { return {...this.stats}; }
  async reloadAssets() {
    if (this.assetReload) return this.assetReload;
    this.assetReload = (async () => {
      try { const commit = await this.prepareAssets(); return commit(); }
      catch (error) { this.stats.registryError = error.message; throw error; }
      finally { this.assetReload = null; }
    })();
    return this.assetReload;
  }
  verifySourcePixels(reference) {
    const renderer = this.renderer,
      size = renderer.getSize(new THREE.Vector2()),
      ratio = renderer.getPixelRatio(),
      mode = this.mode;
    const pixels = new Uint8Array(WIDTH * HEIGHT * 4);
    let mismatches = 0,
      maxChannelError = 0,
      firstMismatch = null;
    try {
      renderer.setPixelRatio(1);
      renderer.setSize(WIDTH, HEIGHT, false);
      this.setLighting("source");
      this.render();
      const gl = renderer.getContext();
      gl.readPixels(0, 0, WIDTH, HEIGHT, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      for (let y = 0; y < HEIGHT; y++)
        for (let x = 0; x < WIDTH; x++) {
          const at = ((HEIGHT - 1 - y) * WIDTH + x) * 4,
            expected = reference[y * WIDTH + x];
          let error = 0;
          for (let c = 0; c < 3; c++)
            error = Math.max(
              error,
              Math.abs(pixels[at + c] - ((expected >>> (8 * c)) & 255)),
            );
          if (error) {
            mismatches++;
            maxChannelError = Math.max(maxChannelError, error);
            firstMismatch ??= {
              x,
              y,
              actual: Array.from(pixels.slice(at, at + 3)),
              expected: [
                expected & 255,
                (expected >> 8) & 255,
                (expected >> 16) & 255,
              ],
            };
          }
        }
    } finally {
      renderer.setPixelRatio(ratio);
      renderer.setSize(size.x, size.y, false);
      this.setLighting(mode);
      this.render();
    }
    return {
      pixels: WIDTH * HEIGHT,
      mismatches,
      maxChannelError,
      firstMismatch,
    };
  }
  setLighting(mode) {
    this.mode = mode === "day" || mode === "dusk" ? mode : "source";
    this.sun.color.set(mode === "dusk" ? 0xffbe87 : 0xfff1d6);
    this.sun.intensity = mode === "dusk" ? 1.2 : 2;
    this.ambient.intensity = mode === "dusk" ? 1 : 2;
    for (const batch of this.batches.values())
      for (let i = 0; i < batch.meshes.length; i++)
        batch.meshes[i].material =
          this.mode === "source"
            ? batch.parts[i].exact
            : batch.parts[i].physical;
    if (this.last) this.render();
  }
  resize(w, h) {
    this.renderer.setSize(Math.max(1, w), Math.max(1, h), false);
    this.width = w;
    this.height = h;
    if (this.last) this.render();
  }
  buildDraws(frame) {
    const draws = [],
      bg = new Map(),
      sprites = new Map();
    const add = (a) => {
      a.index = draws.length + 1;
      a.mask = new Uint8Array(64);
      a.asset = this.assets.get(a.assetId);
      if (!a.asset) return null;
      draws.push(a);
      return a;
    };
    for (const tile of frame.backgroundTiles || []) {
      if (
        tile.y >= HEIGHT ||
        tile.y + 8 <= 0 ||
        tile.x >= WIDTH ||
        tile.x + 8 <= 0
      )
        continue;
      const d = add({
        ...tile,
        flipX: false,
        flipY: false,
        kind: "background",
      });
      if (d) bg.set(`${tile.assetId}|${tile.x}|${tile.y}`, d);
    }
    for (const sprite of frame.sprites || []) {
      for (const [halfText, assetId] of Object.entries(sprite.halves || {})) {
        const half = Number(halfText),
          y = sprite.y + half * 8;
        if (y >= HEIGHT || y + 8 <= 0 || sprite.x >= WIDTH || sprite.x + 8 <= 0)
          continue;
        const d = add({
          assetId,
          spriteKey: sprite.id,
          x: sprite.x,
          y,
          flipX: sprite.flipX,
          flipY: sprite.flipY,
          kind: "sprite",
          backgroundPriority: sprite.backgroundPriority,
          visibleScanlines: sprite.visibleScanlines,
        });
        if (!d) continue;
        for (let row = 0; row < 8; row++) {
          const scan = y + row;
          if (!sprite.visibleScanlines.includes(scan)) continue;
          const sy = sprite.flipY ? 7 - row : row;
          const key = keyRow(assetId, sprite.x, scan, sprite.flipX, sy);
          if (!sprites.has(key)) sprites.set(key, d);
        }
      }
    }
    return { draws, bg, sprites };
  }
  visibleMasks(frame, draws, bg, sprites) {
    this.owner.fill(0);
    this.bgOwner.fill(0);
    this.priority.fill(65);
    if (frame.operations?.length) {
      this.stats.maskSource = "ppu-operations";
      for (const op of frame.operations) {
        if (op.kind === "background" && op.scan >= 0 && op.scan < HEIGHT) {
          for (const row of op.rows) {
            const d = bg.get(
              `${row.assetId}|${row.x}|${op.scan - row.sourceY}`,
            );
            if (!d) continue;
            for (let sx = 0; sx < 8; sx++) {
              const x = row.x + sx;
              if (x < 0 || x >= WIDTH) continue;
              const c = d.asset.pixels
                ? d.asset.pixels[row.sourceY * 8 + sx]
                : d.asset.rgba[(row.sourceY * 8 + sx) * 4 + 3];
              if (c) {
                const at = op.scan * WIDTH + x;
                (op.buffered ? this.bgOwner : this.owner)[at] = d.index;
                this.priority[at] |= 256;
              }
            }
          }
        } else if (op.kind === "compose") {
          for (
            let y = Math.max(0, op.start),
              end = Math.min(HEIGHT, op.start + op.count);
            y < end;
            y++
          )
            for (let x = 0; x < WIDTH; x++) {
              const at = y * WIDTH + x;
              if (this.priority[at] > 255) this.owner[at] = this.bgOwner[at];
            }
        } else if (op.kind === "sprites") {
          for (const row of op.rows) {
            if (row.scan < 0 || row.scan >= HEIGHT) continue;
            const d = sprites.get(
              keyRow(row.assetId, row.x, row.scan, row.flipX, row.sourceY),
            );
            if (!d) continue;
            for (let sx = 0; sx < 8; sx++) {
              const x = row.x + sx;
              if (x < 0 || x >= WIDTH) continue;
              const source = row.sourceY * 8 + (row.flipX ? 7 - sx : sx);
              const c = d.asset.pixels
                ? d.asset.pixels[source]
                : d.asset.rgba[source * 4 + 3];
              const at = row.scan * WIDTH + x;
              if (c && row.priorityIndex <= (this.priority[at] & 255)) {
                this.owner[at] = d.index;
                this.priority[at] =
                  (this.priority[at] & 0xf00) | row.priorityIndex;
              }
            }
          }
        }
      }
      for (let y = frame.clip?.vertical ? 8 : 0; y < HEIGHT - (frame.clip?.vertical ? 8 : 0); y++)
        for (let x = frame.clip?.left ? 8 : 0; x < WIDTH - (frame.clip?.right ? 8 : 0); x++) {
          const d = draws[this.owner[y * WIDTH + x] - 1];
          if (d) {
            const lx = x - d.x,
              ly = y - d.y;
            if (lx >= 0 && lx < 8 && ly >= 0 && ly < 8) d.mask[ly * 8 + lx] = 1;
          }
        }
    } else {
      this.stats.maskSource = "instance-masks";
      for (const d of draws)
        for (let y = 0; y < 8; y++) {
          if (d.kind === "background" && !(d.rowMask & (1 << y))) continue;
          if (d.kind === "sprite" && !d.visibleScanlines.includes(d.y + y))
            continue;
          for (let x = 0; x < 8; x++) {
            if (
              d.x + x < (frame.clip?.left ? 8 : 0) ||
              d.x + x >= WIDTH - (frame.clip?.right ? 8 : 0) ||
              d.y + y < (frame.clip?.vertical ? 8 : 0) ||
              d.y + y >= HEIGHT - (frame.clip?.vertical ? 8 : 0)
            )
              continue;
            const source = (d.flipY ? 7 - y : y) * 8 + (d.flipX ? 7 - x : x);
            if (d.asset.rgba[source * 4 + 3]) d.mask[y * 8 + x] = 1;
          }
        }
    }
  }
  batchFor(id) {
    let batch = this.batches.get(id);
    if (batch) return batch;
    const parts = this.prototypes.get(id);
    if (!parts) return null;
    const meshes = parts.map((p) => {
      const m = new THREE.InstancedMesh(
        p.geometry,
        this.mode === "source" ? p.exact : p.physical,
        1024,
      );
      m.instanceMatrix.setUsage(THREE.DynamicDrawUsage);
      m.frustumCulled = false;
      m.count = 0;
      this.scene.add(m);
      return m;
    });
    batch = { parts, meshes, count: 0 };
    this.batches.set(id, batch);
    return batch;
  }
  fallback(draw, slot) {
    let f = this.fallbacks[slot];
    if (!f) {
      const pixels = new Uint8Array(256);
      const texture = new THREE.DataTexture(pixels, 8, 8, THREE.RGBAFormat);
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.magFilter = THREE.NearestFilter;
      texture.minFilter = THREE.NearestFilter;
      texture.generateMipmaps = false;
      texture.flipY = true;
      const material = new THREE.MeshBasicMaterial({
        map: texture,
        transparent: false,
        alphaTest: 0.5,
        toneMapped: false,
        side: THREE.DoubleSide,
      });
      const mesh = new THREE.Mesh(this.geometry, material);
      mesh.frustumCulled = false;
      this.scene.add(mesh);
      f = { mesh, texture, pixels };
      this.fallbacks.push(f);
    }
    const a = draw.asset.rgba;
    for (let y = 0; y < 8; y++)
      for (let x = 0; x < 8; x++) {
        const target = (y * 8 + x) * 4,
          source =
            ((draw.flipY ? 7 - y : y) * 8 + (draw.flipX ? 7 - x : x)) * 4;
        f.pixels[target] = a[source];
        f.pixels[target + 1] = a[source + 1];
        f.pixels[target + 2] = a[source + 2];
        f.pixels[target + 3] = draw.mask[y * 8 + x] ? a[source + 3] : 0;
      }
    f.texture.needsUpdate = true;
    f.mesh.position.set(
      (draw.x + 4) * SCALE,
      15 - (draw.y + 4) * SCALE,
      draw.kind === "sprite" ? 0.15 : 0.07,
    );
    f.mesh.visible = true;
  }
  update(scene, dt = 0) {
    const frame = scene?.extraction || scene;
    if (!frame?.assets) return;
    this.last = scene;
    for (const a of frame.assets) this.assets.set(a.id, a);
    const { draws, bg, sprites } = this.buildDraws(frame);
    this.visibleMasks(frame, draws, bg, sprites);
    for (const batch of this.batches.values()) batch.count = 0;
    for (const f of this.fallbacks) f.mesh.visible = false;
    Object.assign(this.stats, {
      sourceInstances: draws.length,
      registryHits: 0,
      blenderInstances: 0,
      fallbackInstances: 0,
      partialMasks: 0,
      unseenAssets: 0,
      frame: frame.frame,
      currentAssets: frame.assets.length,
    });
    const matrix = new THREE.Matrix4();
    let fallbackCount = 0;
    for (const d of draws) {
      let visible = 0,
        opaque = 0;
      for (let y = 0; y < 8; y++)
        for (let x = 0; x < 8; x++) {
          visible += d.mask[y * 8 + x];
          const source = (d.flipY ? 7 - y : y) * 8 + (d.flipX ? 7 - x : x);
          if (d.asset.rgba[source * 4 + 3]) opaque++;
        }
      if (!visible) continue;
      if (this.registry.has(d.assetId)) this.stats.registryHits++;
      else this.stats.unseenAssets++;
      const partial = visible < opaque;
      if (partial) this.stats.partialMasks++;
      const batch = !partial ? this.batchFor(d.assetId) : null;
      if (batch && batch.meshes.length && batch.count < 1024) {
        const sx = d.flipX ? -1 : 1,
          sy = d.flipY ? -1 : 1;
        matrix.makeScale(sx, sy, 1);
        matrix.setPosition(
          (d.x + (d.flipX ? 8 : 0)) * SCALE,
          15 - (d.y + (d.flipY ? 8 : 0)) * SCALE,
          d.kind === "sprite" ? 0.1 : 0,
        );
        for (const mesh of batch.meshes) mesh.setMatrixAt(batch.count, matrix);
        batch.count++;
        this.stats.blenderInstances++;
      } else {
        this.fallback(d, fallbackCount++);
        this.stats.fallbackInstances++;
      }
    }
    for (const batch of this.batches.values())
      for (const mesh of batch.meshes) {
        mesh.count = batch.count;
        mesh.visible = batch.count > 0;
        mesh.instanceMatrix.needsUpdate = true;
      }
    this.clearColor = frame.clearColor;
    this.render();
  }
  render() {
    const r = this.renderer;
    r.setScissorTest(false);
    r.setClearColor(0x000000, 1);
    r.clear(true, true, true);
    const size = r.getSize(new THREE.Vector2());
    const c = this.clearColor || 0;
    this.scene.background = null;
    r.setScissor(
      Math.round((size.x * (this.last?.clip?.left ? 8 : 0)) / 256),
      Math.round(size.y * (this.last?.clip?.vertical ? 8 : 0) / 240),
      Math.round(size.x * (256 - (this.last?.clip?.left ? 8 : 0) - (this.last?.clip?.right ? 8 : 0)) / 256),
      Math.round(size.y * (240 - (this.last?.clip?.vertical ? 16 : 0)) / 240),
    );
    r.setScissorTest(true);
    r.setClearColor(
      new THREE.Color(
        (c & 255) / 255,
        ((c >> 8) & 255) / 255,
        ((c >> 16) & 255) / 255,
      ).convertSRGBToLinear(),
      1,
    );
    r.clear(true, true, true);
    r.render(this.scene, this.camera);
    r.setScissorTest(false);
  }
  dispose() {
    for (const batch of this.batches.values())
      for (const m of batch.meshes) m.dispose();
    for (const parts of this.prototypes.values())
      for (const p of parts) {
        p.geometry.dispose();
        for (const m of [
          ...(Array.isArray(p.exact) ? p.exact : [p.exact]),
          ...(Array.isArray(p.physical) ? p.physical : [p.physical]),
        ])
          m.dispose();
      }
    for (const f of this.fallbacks) {
      f.texture.dispose();
      f.mesh.material.dispose();
    }
    this.geometry.dispose();
    this.renderer.dispose();
  }
}
export { SourceRenderer as WorldRenderer };
