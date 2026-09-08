// Candidate-only player. Production acceptance is never inferred from this registry.
let romHash = null;
export function setRomHash(hash) { romHash = hash; }
export const runtimeProfile = () => 'prototype';
export async function fetchRegistry(path) {
  const url = new URL(path, location.href);
  const response = await fetch(url, {cache:'no-store'});
  if (!response.ok) throw new Error(`Candidate registry unavailable (${response.status})`);
  let doc; try { doc = await response.json(); } catch { throw new Error('No candidate registry installed for this workspace'); }
  if (doc.profile !== 'prototype') throw new Error('This portable player requires an explicit prototype registry');
  if (!romHash || doc.romSha256 !== romHash) throw new Error('Candidate registry belongs to a different ROM');
  const entries = doc.assets;
  if (!Array.isArray(entries)) throw new Error('Invalid candidate registry');
  const loaded = new Map();
  for (const entry of entries) {
    if (!entry.id || loaded.has(entry.id) || entry.width !== 8 || entry.height !== 8 || !entry.source?.sourceIdentity) throw new Error('Invalid or duplicate source tile');
    const target = new URL(entry.path, url);
    if (!target.href.startsWith(new URL('.',url).href)) throw new Error('Asset path escapes candidate directory');
    const result = await fetch(target,{cache:'no-store'});
    if (!result.ok) throw new Error(`Candidate missing: ${entry.id}`);
    const bytes = await result.arrayBuffer();
    if (new DataView(bytes).getUint32(0,true)!==0x46546c67) throw new Error('Invalid GLB');
    if (entry.sha256) {
      const hash = Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),x=>x.toString(16).padStart(2,'0')).join('');
      if(hash!==entry.sha256) throw new Error(`Candidate changed: ${entry.id}`);
    }
    loaded.set(entry.id,{entry,bytes});
  }
  return loaded;
}
export function parseVerifiedGLB(loader,bytes) { return new Promise((resolve,reject)=>loader.parse(bytes,'',resolve,reject)); }
