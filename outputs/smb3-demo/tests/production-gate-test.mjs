import assert from 'node:assert/strict';
import {verifyRegistry,parseDocument,validateGLB} from '../src/production-gate.js';
import {productionFixture} from './production-fixture.mjs';
let passed=0;
async function test(name,run){await run();passed++;console.log(`ok ${name}`);}
const verify=f=>verifyRegistry(f.registry,f.readBytes,{expectedRuntimeHash:f.runtimeHash});
await test('accepted exact GLB bytes returned',async()=>{const f=await productionFixture();const map=await verify(f);assert.deepEqual(map.get('ground-grass').bytes,f.files.get('accepted/test/candidate/model.glb'));});
for(const [name,change] of [
 ['missing profile',f=>delete f.registry.profile],
 ['prototype profile',f=>f.registry.profile='prototype'],
 ['stale runtime',f=>f.runtimeHash='f'.repeat(64)],
 ['changed GLB',f=>f.files.get('accepted/test/candidate/model.glb')[24]^=1],
 ['missing visual',f=>f.files.delete('accepted/test/reviews/visual/report.json')],
 ['changed evidence',f=>f.files.set('accepted/test/reviews/visual/capture.txt',f.encode('changed'))],
 ['semantic remap',f=>f.registry.entries[0].id='unreviewed-id'],
 ['wrong GLB path',f=>f.registry.entries[0].path='other.glb'],
 ['unsafe bundle',f=>f.registry.entries[0].bundle='../escape'],
 ['duplicate ID',f=>f.registry.entries.push(f.registry.entries[0])],
 ['failed visual',f=>{const p='accepted/test/reviews/visual/report.json';const d=JSON.parse(new TextDecoder().decode(f.files.get(p)));d.verdict='fail';f.files.set(p,f.encode(d));}],
 ['self review',f=>{const p='accepted/test/reviews/visual/report.json';const d=JSON.parse(new TextDecoder().decode(f.files.get(p)));d.reviewer='fixture-author';f.files.set(p,f.encode(d));}],
]) await test(name,async()=>{const f=await productionFixture();change(f);await assert.rejects(()=>verify(f));});
await test('empty release supports full revocation',async()=>{const f=await productionFixture();f.registry.entries=[];assert.equal((await verify(f)).size,0);});
await test('default profile rejects legacy',async()=>{await assert.rejects(()=>verifyRegistry({entries:[]},async()=>new Uint8Array()));});
await test('explicit prototype allows legacy',async()=>{assert.equal((await verifyRegistry({entries:[]},async()=>new Uint8Array(),{profile:'prototype'})).size,0);});
await test('duplicate JSON keys rejected',async()=>{assert.throws(()=>parseDocument(new TextEncoder().encode('{"schema":1,"schema":1}')));});
console.log(`${passed} production gate tests passed`);
