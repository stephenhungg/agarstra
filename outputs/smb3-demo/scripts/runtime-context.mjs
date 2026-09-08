import { createHash } from 'node:crypto';
import { readFile, readdir } from 'node:fs/promises';
import { resolve, relative, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
export async function runtimeContext(root = resolve(dirname(fileURLToPath(import.meta.url)),'..')) {
  const files = {};
  async function walk(path) { for (const entry of await readdir(resolve(root,path),{withFileTypes:true})) { const child = `${path}/${entry.name}`; if(entry.isDirectory()) await walk(child); else if(entry.isFile()) files[child] = createHash('sha256').update(await readFile(resolve(root,child))).digest('hex'); else throw new Error(`Unsupported runtime path ${child}`); } }
  await walk('src');
  for(const path of ['package-lock.json','vite.config.js','electron.cjs','preload.cjs','index.html','scripts/runtime-context.mjs']) files[path] = createHash('sha256').update(await readFile(resolve(root,path))).digest('hex');
  const bytes = Buffer.from(JSON.stringify({schema:1,files:Object.fromEntries(Object.entries(files).sort(([a],[b])=>a.localeCompare(b)))})+'\n');
  return {bytes,sha256:createHash('sha256').update(bytes).digest('hex')};
}
if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) process.stdout.write((await runtimeContext()).bytes);
