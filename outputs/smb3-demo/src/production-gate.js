/** Portable evidence verifier. Approval is an attestation, never inferred from a model. */
const need = (ok, message) => { if (!ok) throw new Error(`Production gate: ${message}`); };
const object = value => value !== null && typeof value === 'object' && !Array.isArray(value);
const text = value => typeof value === 'string' && value.trim().length > 0;
export const sha256 = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256', bytes))].map(x => x.toString(16).padStart(2, '0')).join('');
export function safePath(path) {
  need(text(path) && !/[\\:%?#\x00-\x20]/.test(path) && !path.startsWith('/') && path.split('/').every(p => p && p !== '.' && p !== '..'), 'unsafe relative path');
  return path;
}
// JSON.parse silently accepts duplicate keys. Token walk rejects them before parsing.
export function parseDocument(bytes) {
  const source = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
  const tokens = source.match(/"(?:[^"\\]|\\.)*"|[{}\[\],:]|[^\s{}\[\],:]+/g) || [];
  let at = 0;
  function walk() {
    const token = tokens[at++];
    if (token === '{') {
      const keys = new Set();
      if (tokens[at] === '}') { at++; return; }
      while (at < tokens.length) {
        const key = JSON.parse(tokens[at++]);
        need(!keys.has(key), 'duplicate JSON key'); keys.add(key);
        need(tokens[at++] === ':', 'invalid JSON'); walk();
        if (tokens[at++] === '}') return;
      }
    } else if (token === '[') {
      if (tokens[at] === ']') { at++; return; }
      while (at < tokens.length) { walk(); if (tokens[at++] === ']') return; }
    }
  }
  walk();
  const value = JSON.parse(source);
  need(object(value), 'expected JSON object');
  return value;
}
function names(value, label) {
  need(Array.isArray(value) && value.length && value.every(text) && new Set(value).size === value.length, `${label}: expected unique IDs`); return value;
}
export function validateGLB(bytes) {
  const view = new DataView(bytes.buffer, bytes.byteOffset, bytes.byteLength);
  need(bytes.length >= 20 && view.getUint32(0,true) === 0x46546c67 && view.getUint32(4,true) === 2 && view.getUint32(8,true) === bytes.length, 'invalid GLB');
  need(view.getUint32(16,true) === 0x4e4f534a, 'GLB missing JSON');
  const length = view.getUint32(12,true); need(length + 20 <= bytes.length, 'truncated GLB');
  const json = parseDocument(bytes.slice(20,20 + length));
  // Network dependencies are prohibited: parse exactly the approved self-contained bytes.
  function scan(value) { if (!value || typeof value !== 'object') return; for (const [key,item] of Object.entries(value)) { need(key !== 'uri', 'GLB external/data URI dependency prohibited; embed resources'); scan(item); } }
  scan(json); return bytes;
}
export async function verifyRegistry(registry, readBytes, {profile = 'production', expectedRuntimeHash} = {}) {
  need(profile === 'production' || profile === 'prototype', 'unknown profile');
  if (profile === 'prototype') {
    const entries = Array.isArray(registry) ? registry : registry.entries || registry.models;
    need(Array.isArray(entries), 'missing prototype entries');
    const result = new Map();
    for (const entry of entries) { const id = entry.id || entry.assetId; need(text(id) && !result.has(id), 'duplicate/missing asset ID'); const bytes = new Uint8Array(await readBytes(safePath(entry.path || entry.glb))); result.set(id,{entry,bytes}); }
    return result;
  }
  need(registry.schemaVersion === 2 && registry.profile === 'production' && Array.isArray(registry.entries), 'explicit production registry required');
  need(typeof expectedRuntimeHash === 'string' && /^[0-9a-f]{64}$/.test(expectedRuntimeHash), 'running runtime hash required');
  need(registry.runtime_sha256 === expectedRuntimeHash, 'registry runtime mismatch');
  const result = new Map();
  for (const entry of registry.entries) {
    need(text(entry.id) && !result.has(entry.id), 'duplicate/missing asset ID');
    const base = safePath(entry.bundle), collected = new Map();
    async function read(path) { safePath(path); const bytes = new Uint8Array(await readBytes(`${base}/${path}`)); collected.set(path,bytes); return bytes; }
    async function doc(path) { const bytes = await read(path), value = parseDocument(bytes); need(value.schema === 1, `${path}: expected schema 1`); return [value,bytes]; }
    async function pins(entries, prefix) {
      need(object(entries) && Object.keys(entries).length, 'missing pinned files');
      for (const [id,pin] of Object.entries(entries)) { need(text(id) && object(pin), 'invalid pin'); const path = safePath(pin.path); need(path !== 'manifest.json' && path !== 'report.json', 'reserved payload path'); const bytes = await read(`${prefix}/${path}`); need(await sha256(bytes) === pin.sha256, `${id}: stale file hash`); }
    }
    const [candidate, candidateBytes] = await doc('candidate/manifest.json');
    const [contract, contractBytes] = await doc('contract.json');
    need(text(candidate.id) && text(candidate.author), 'candidate identity missing');
    need(object(candidate.runtime_entry) && text(candidate.runtime_entry.id) && text(candidate.runtime_entry.artifact), 'candidate runtime entry missing');
    for (const [key,value] of Object.entries(candidate.runtime_entry)) need(JSON.stringify(entry[key]) === JSON.stringify(value), 'registry runtime mapping differs from reviewed candidate'); names(candidate.source_ids,'source IDs');
    for (const key of ['required_artifacts','required_context','technical_checks','visual_checks']) names(contract[key],key);
    need(['target','runtime','camera','replay'].every(key => contract.required_context.includes(key)), 'missing production context');
    for (const kind of ['artifacts','context']) { await pins(candidate[kind],'candidate'); need(contract[`required_${kind}`].every(key => key in candidate[kind]), `missing ${kind}`); }
    need(candidate.context.runtime.sha256 === expectedRuntimeHash, 'reviewed runtime differs from running runtime');
    const candidateHash = await sha256(candidateBytes), contractHash = await sha256(contractBytes);
    for (const kind of ['technical','visual']) {
      const [report] = await doc(`reviews/${kind}/report.json`);
      need(report.candidate_sha256 === candidateHash && report.contract_sha256 === contractHash, `${kind}: stale review pins`);
      need(text(report.reviewer) && report.inspected === true && report.verdict === 'pass' && Array.isArray(report.blockers) && report.blockers.length === 0, `${kind}: failed review`);
      need(kind !== 'visual' || report.reviewer.trim().toLowerCase() !== candidate.author.trim().toLowerCase(), 'independent visual reviewer required');
      await pins(report.evidence,`reviews/${kind}`);
      need(object(report.checks) && contract[`${kind}_checks`].every(key => key in report.checks), `${kind}: missing checks`);
      for (const check of Object.values(report.checks)) { need(object(check) && check.status === 'pass' && text(check.reason), `${kind}: failed check`); need(names(check.evidence,'evidence').every(key => key in report.evidence), 'unknown evidence'); }
    }
    const [acceptance] = await doc('acceptance.json'); collected.delete('acceptance.json');
    need(acceptance.profile === 'production' && acceptance.status === 'production-evidence-accepted' && acceptance.candidate_id === candidate.id && acceptance.candidate_sha256 === candidateHash && acceptance.contract_sha256 === contractHash && acceptance.artistic_quality_evaluated_by_checker === false, 'invalid acceptance record');
    need(object(acceptance.files) && Object.keys(acceptance.files).length === collected.size, 'acceptance inventory mismatch');
    for (const [path,bytes] of collected) need(acceptance.files[path] === await sha256(bytes), 'acceptance file mismatch');
    need(Object.keys(entry).every(key => ['bundle','path','sha256','quality'].includes(key) || key in candidate.runtime_entry), 'unreviewed registry metadata');
    const artifact = candidate.artifacts[entry.artifact];
    need(artifact && entry.path === `${base}/candidate/${artifact.path}` && entry.sha256 === artifact.sha256, 'registry artifact mismatch');
    const bytes = collected.get(`candidate/${artifact.path}`); validateGLB(bytes);
    result.set(entry.id,{entry,bytes,candidate});
  }
  return result;
}
export function runtimeProfile() { return typeof __ASSET_BUILD_PROFILE__ !== 'undefined' && __ASSET_BUILD_PROFILE__ === 'prototype' ? 'prototype' : 'production'; }
export async function fetchRegistry(path) {
  const url = new URL(path,document.baseURI);
  const read = async href => { const response = await fetch(href,{cache:'no-store'}); need(response.ok, `HTTP ${response.status}`); return new Uint8Array(await response.arrayBuffer()); };
  let registry;
  if (runtimeProfile() === 'prototype' && path.endsWith('-registry.json')) {
    try { registry = parseDocument(await read(new URL(path.split('/').pop().replace('-registry.json','-prototype-registry.json'),url))); } catch { /* explicit prototype may use existing legacy registry */ }
  }
  registry ||= parseDocument(await read(url));
  return verifyRegistry(registry,path => read(new URL(safePath(path),url)),{profile:runtimeProfile(),expectedRuntimeHash:__ASSET_RUNTIME_SHA256__});
}
export const parseVerifiedGLB = (loader,bytes) => loader.parseAsync(bytes.buffer.slice(bytes.byteOffset,bytes.byteOffset + bytes.byteLength),'');

/** Stage all renderers before any live swap. Failed or superseded releases cannot partially publish. */
export async function reloadTogether(renderers) {
  const staged = await Promise.allSettled(renderers.map(renderer => renderer.prepareAssets()));
  const commits = staged.filter(item => item.status === 'fulfilled').map(item => item.value);
  const failure = staged.find(item => item.status === 'rejected');
  try {
    if (failure) throw failure.reason;
    for (const commit of commits) commit.validate?.();
  } catch (error) { for (const commit of commits) commit.dispose?.(); throw error; }
  return commits.map(commit => commit());
}
