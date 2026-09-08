import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { productionFixture } from './production-fixture.mjs';
import { runtimeContext } from '../scripts/runtime-context.mjs';
import { publish, fileReader, inventory, preflight, pruneModels, acceptedModels } from '../scripts/package-gate.mjs';

const temp = fs.mkdtempSync(path.join(os.tmpdir(), 'smb3-package-test-'));
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
try {
  const output = path.join(temp, 'game.app');
  const stage = path.join(temp, 'staged.app');
  fs.mkdirSync(output); fs.writeFileSync(path.join(output, 'version'), 'old');
  fs.mkdirSync(stage); fs.writeFileSync(path.join(stage, 'version'), 'new');
  assert.throws(() => publish(stage, output, (from, to) => {
    if (from === stage) throw new Error('simulated publish failure');
    fs.renameSync(from, to);
  }), /simulated publish failure/);
  assert.equal(fs.readFileSync(path.join(output, 'version'), 'utf8'), 'old');
  publish(stage, output);
  assert.equal(fs.readFileSync(path.join(output, 'version'), 'utf8'), 'new');
  fs.mkdirSync(path.join(output, 'releases/old'), { recursive: true });
  fs.writeFileSync(path.join(output, 'releases/old/rejected.glb'), 'unapproved');
  pruneModels(output, new Set());
  assert.equal(fs.existsSync(path.join(output, 'releases/old/rejected.glb')), false);
  const before = inventory(output);
  fs.writeFileSync(path.join(output, 'version'), 'tampered');
  assert.notEqual(inventory(output), before);
  const read = fileReader(output);
  await assert.rejects(() => read('../outside'));
  fs.symlinkSync('/etc/hosts', path.join(output, 'external'));
  await assert.rejects(() => read('external'), /Unsafe/);
  // Exercise the real production command against the current unreviewed legacy
  // inventory. It must fail before invoking platform tools or changing the app.
  const legacy = JSON.parse(fs.readFileSync(path.join(root, 'public/assets/photoreal-registry.json')));
  if (legacy.schemaVersion !== 2 || legacy.profile !== 'production') {
    const result = spawnSync(process.execPath, ['scripts/package.mjs', '--preflight'], { cwd: root, encoding: 'utf8' });
    assert.notEqual(result.status, 0, 'legacy registry was accepted by package entrypoint');
    assert.match(result.stderr, /production|registry|schema|approval/i);
  }
  const distribution = path.join(temp, 'dist');
  fs.mkdirSync(path.join(distribution, 'assets'), { recursive: true });
  const context = await runtimeContext(root);
  const emptyRegistry = { schemaVersion: 2, profile: 'production', runtime_sha256: context.sha256, entries: [] };
  for (const kind of ['photoreal', 'source']) fs.writeFileSync(path.join(distribution, `assets/${kind}-registry.json`), JSON.stringify(emptyRegistry));
  fs.writeFileSync(path.join(distribution, 'runtime-build.json'), context.bytes);
  fs.writeFileSync(path.join(distribution, 'build-profile.json'), JSON.stringify({ profile: 'production' }));
  await preflight(distribution, root); // Explicit empty accepted scope is valid.
  fs.writeFileSync(path.join(distribution, 'runtime-build.json'), '{}');
  await assert.rejects(() => preflight(distribution, root), /stale runtime build/);
  fs.writeFileSync(path.join(distribution, 'runtime-build.json'), context.bytes);
  fs.writeFileSync(path.join(distribution, 'build-profile.json'), JSON.stringify({ profile: 'prototype' }));
  await assert.rejects(() => preflight(distribution, root), /build profile mismatch/);
  fs.writeFileSync(path.join(distribution, 'build-profile.json'), JSON.stringify({ profile: 'production' }));
  const photoPath = path.join(distribution, 'assets/photoreal-registry.json');
  fs.writeFileSync(photoPath, JSON.stringify({ ...emptyRegistry, runtime_sha256: '0'.repeat(64) }));
  await assert.rejects(() => preflight(distribution, root), /runtime mismatch/);
  fs.writeFileSync(photoPath, JSON.stringify({ ...emptyRegistry, entries: [{ id: 'unreviewed', bundle: 'accepted/unreviewed' }] }));
  await assert.rejects(() => preflight(distribution, root), /ENOENT/);
  const fixture = await productionFixture(context.bytes);
  for (const [relative, bytes] of fixture.files) {
    const file = path.join(distribution, 'assets', relative);
    fs.mkdirSync(path.dirname(file), { recursive: true }); fs.writeFileSync(file, bytes);
  }
  fs.writeFileSync(photoPath, JSON.stringify(fixture.registry));
  const accepted = await preflight(distribution, root);
  assert.equal(acceptedModels(distribution, accepted).has('assets/accepted/test/candidate/model.glb'), true);
  const reportPath = path.join(distribution, 'assets/accepted/test/reviews/visual/report.json');
  const report = JSON.parse(fs.readFileSync(reportPath));
  fs.writeFileSync(reportPath, JSON.stringify({ ...report, verdict: 'fail' }));
  await assert.rejects(() => preflight(distribution, root), /failed review/);
  fs.writeFileSync(reportPath, JSON.stringify(report));
  fs.appendFileSync(path.join(distribution, 'assets/accepted/test/candidate/model.glb'), 'changed');
  await assert.rejects(() => preflight(distribution, root), /stale file hash/);
  console.log('package publication rollback, containment, and entrypoint rejection passed');
} finally { fs.rmSync(temp, { recursive: true, force: true }); }
