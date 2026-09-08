import test from 'node:test';
import assert from 'node:assert/strict';
import {fetchRegistry,setRomHash} from '../production-gate.js';
globalThis.location={href:'http://localhost:4317/'};
const glb=new Uint8Array(12);new DataView(glb.buffer).setUint32(0,0x46546c67,true);
const entry={id:'tile',width:8,height:8,path:'models/tile.glb',source:{sourceIdentity:'source'}};
function serve(doc,asset=glb){globalThis.fetch=async url=>new Response(String(url).endsWith('.json')?JSON.stringify(doc):asset)}
test('candidate loader binds registry to ROM and exact bytes',async()=>{setRomHash('rom');serve({profile:'prototype',romSha256:'rom',assets:[entry]});assert.equal((await fetchRegistry('assets/source-registry.json')).size,1);serve({profile:'prototype',romSha256:'other',assets:[entry]});await assert.rejects(fetchRegistry('assets/source-registry.json'),/different ROM/);serve({profile:'production',romSha256:'rom',assets:[entry]});await assert.rejects(fetchRegistry('assets/source-registry.json'),/prototype/);serve({profile:'prototype',romSha256:'rom',assets:[{...entry,sha256:'wrong'}]});await assert.rejects(fetchRegistry('assets/source-registry.json'),/changed/);});
test('candidate loader rejects escape and duplicate IDs',async()=>{setRomHash('rom');serve({profile:'prototype',romSha256:'rom',assets:[{...entry,path:'../../outside.glb'}]});await assert.rejects(fetchRegistry('assets/source-registry.json'),/escapes/);serve({profile:'prototype',romSha256:'rom',assets:[entry,entry]});await assert.rejects(fetchRegistry('assets/source-registry.json'),/duplicate/);});
