import fs from 'node:fs';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { verifyRegistry, parseDocument } from '../src/production-gate.js';
import { runtimeContext } from './runtime-context.mjs';

// Evidence paths must resolve to ordinary files inside their declared root.
export function fileReader(root) {
  const base = fs.realpathSync(root);
  return async (relative) => {
    if (typeof relative !== 'string' || path.isAbsolute(relative)) throw new Error('Unsafe evidence path');
    const resolved = fs.realpathSync(path.resolve(base, relative));
    if (!resolved.startsWith(base + path.sep) || !fs.statSync(resolved).isFile()) throw new Error(`Unsafe evidence path: ${relative}`);
    return new Uint8Array(fs.readFileSync(resolved));
  };
}

export async function preflight(dist, runtimeRoot, profile = 'production', built = true) {
  const context = await runtimeContext(runtimeRoot);
  if (built && !fs.readFileSync(path.join(dist, 'runtime-build.json')).equals(context.bytes)) {
    throw new Error('Production gate: stale runtime build; rebuild with current source');
  }
  if (built && parseDocument(fs.readFileSync(path.join(dist, 'build-profile.json'))).profile !== profile) {
    throw new Error('Production gate: build profile mismatch');
  }
  const result = {};
  for (const kind of ['photoreal', 'source']) {
    const prototypePath = path.join(dist, `assets/${kind}-prototype-registry.json`);
    const registryPath = profile === 'prototype' && fs.existsSync(prototypePath)
      ? prototypePath : path.join(dist, `assets/${kind}-registry.json`);
    const registry = parseDocument(fs.readFileSync(registryPath));
    await verifyRegistry(registry, fileReader(path.dirname(registryPath)), {
      profile, expectedRuntimeHash: context.sha256,
    });
    result[kind] = registry;
  }
  return result;
}

// Both paths live on the same volume. Retain the previous app until all checks
// pass, and restore it if publishing the staged app fails.
export function publish(stage, output, rename = fs.renameSync) {
  const backup = `${output}.previous-${process.pid}`;
  if (fs.existsSync(backup)) throw new Error(`Refusing existing backup: ${backup}`);
  const existed = fs.existsSync(output);
  if (existed) rename(output, backup);
  try { rename(stage, output); }
  catch (error) {
    if (existed) rename(backup, output);
    throw error;
  }
  if (existed) fs.rmSync(backup, { recursive: true, force: true });
}

export function inventory(root, { allowedModels }  = {}) {
  const files = {};
  function walk(relative = '') {
    for (const item of fs.readdirSync(path.join(root, relative), { withFileTypes: true })) {
      const name = relative ? `${relative}/${item.name}` : item.name;
      if (allowedModels && /\.(glb|gltf)$/i.test(name) && !allowedModels.has(name)) continue;
      if (item.isDirectory()) walk(name);
      else if (item.isFile()) files[name] = createHash('sha256').update(fs.readFileSync(path.join(root, name))).digest('hex');
      else throw new Error(`Package contains unsupported filesystem entry: ${name}`);
    }
  }
  walk();
  return JSON.stringify(Object.fromEntries(Object.entries(files).sort(([a], [b]) => a.localeCompare(b))));
}

export function pruneModels(root, allowedModels) {
  function walk(relative = '') {
    for (const item of fs.readdirSync(path.join(root, relative), { withFileTypes: true })) {
      const name = relative ? `${relative}/${item.name}` : item.name;
      if (item.isDirectory()) walk(name);
      else if (/\.(glb|gltf)$/i.test(name) && !allowedModels.has(name)) fs.unlinkSync(path.join(root, name));
    }
  }
  walk();
}

export function acceptedModels(dist, registries) {
  const allowed = new Set();
  for (const registry of Object.values(registries)) for (const entry of registry.entries) {
    const acceptance = parseDocument(fs.readFileSync(path.join(dist, 'assets', entry.bundle, 'acceptance.json')));
    for (const relative of Object.keys(acceptance.files)) {
      allowed.add(`assets/${entry.bundle}/${relative}`);
    }
  }
  return allowed;
}
