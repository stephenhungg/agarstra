import test from 'node:test';
import assert from 'node:assert/strict';
import { mkdtemp, writeFile, readFile, rm } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { NES, Controller } from '../vendor/jsnes/index.js';
import { RomAssetExtractor, recompose } from '../rom-extractor.js';
import { inspectRom, decodeTile } from '../ingest.mjs';
import { loadRom } from '../load-rom.mjs';
import { extract, normalizeInputs } from '../extract.mjs';
function fixture(){const b=Buffer.alloc(16+16384+8192);b.set([78,69,83,26,1,1]);b.set([0x4c,0,0x80],16);b[16+16384-4]=0;b[16+16384-3]=0x80;return b;}
test('qualification rejects unsupported formats rather than guessing',()=>{
 const b=fixture();assert.equal(inspectRom(b).mapper,0);
 for(const [offset,value,message] of [[7,8,/NES 2.0/],[5,0,/CHR-RAM/],[6,16,/Mapper 1/],[9,1,/PAL/],[6,4,/Trainer/],[12,1,/reserved/],[7,1,/VS/]]){const bad=Buffer.from(b);bad[offset]=value;assert.throws(()=>inspectRom(bad),message);}
 assert.throws(()=>inspectRom(b.subarray(0,40)),/Truncated/);assert.throws(()=>inspectRom(Buffer.alloc(4)),/iNES/);
});
test('2-bit tile decode retains plane ordering',()=>{const b=Buffer.alloc(16);b[0]=128;b[8]=64;assert.deepEqual(decodeTile(b).slice(0,8),[1,2,0,0,0,0,0,0]);});
test('input validation rejects unknown buttons and out-of-replay events',()=>{assert.throws(()=>normalizeInputs([{frame:3,button:'X',down:true}],10),/Invalid/);assert.throws(()=>normalizeInputs([{frame:10,button:'A',down:true}],10),/Invalid/);assert.equal(normalizeInputs([{frame:1,button:'a',down:false}],10)[0].button,'A');});
test('clean fixture extraction is reproducible and complete',async()=>{const dir=await mkdtemp(join(tmpdir(),'agarstra-extract-'));try{const rom=join(dir,'fixture.nes');await writeFile(rom,fixture());await extract({rom,out:join(dir,'a'),frames:3});await extract({rom,out:join(dir,'b'),frames:3});for(const name of ['source.json','catalog.json','capture.json','raw-tiles.json','replay.json','state.json'])assert.deepEqual(await readFile(join(dir,'a',name)),await readFile(join(dir,'b',name)));const tiles=JSON.parse(await readFile(join(dir,'a/raw-tiles.json')));assert.equal(tiles.length,512);assert.equal(tiles.at(-1).romOffset,16+16384+8192-16);assert.equal((await loadRom(rom)).header.mapper,0);}finally{await rm(dir,{recursive:true,force:true});}});
for(const path of (process.env.AGARSTRA_TEST_ROMS||'').split(',').filter(Boolean))test(`observer preserves gameplay and reconstructed frames: ${path}`,async()=>{
 const {bytes}=await loadRom(path);let actual;const baseline=new NES({emulateSound:false}),observed=new NES({emulateSound:false,onFrame:p=>actual=new Uint32Array(p)});baseline.loadROM(bytes);observed.loadROM(bytes);const extractor=new RomAssetExtractor(observed,bytes);
 for(let frame=0;frame<180;frame++){if(frame===60){baseline.buttonDown(1,Controller.BUTTON_START);observed.buttonDown(1,Controller.BUTTON_START);}if(frame===62){baseline.buttonUp(1,Controller.BUTTON_START);observed.buttonUp(1,Controller.BUTTON_START);}baseline.frame();observed.frame();assert.deepEqual(observed.cpu.mem,baseline.cpu.mem);assert.deepEqual(observed.ppu.spriteMem,baseline.ppu.spriteMem);assert.deepEqual(recompose(extractor.getFrame()),actual);}
 assert.deepEqual(observed.toJSON(),baseline.toJSON());assert.ok(extractor.assets.size>0);
});
function zip(entries){let offset=0;const locals=[],central=[];for(const [name,data] of entries){const n=Buffer.from(name);let crc=0xffffffff;for(const v of data){crc^=v;for(let i=0;i<8;i++)crc=(crc>>>1)^((crc&1)?0xedb88320:0);}crc=(crc^0xffffffff)>>>0;const l=Buffer.alloc(30);l.writeUInt32LE(0x04034b50);l.writeUInt32LE(crc,14);l.writeUInt32LE(data.length,18);l.writeUInt32LE(data.length,22);l.writeUInt16LE(n.length,26);locals.push(l,n,data);const c=Buffer.alloc(46);c.writeUInt32LE(0x02014b50);c.writeUInt32LE(crc,16);c.writeUInt32LE(data.length,20);c.writeUInt32LE(data.length,24);c.writeUInt16LE(n.length,28);c.writeUInt32LE(offset,42);central.push(c,n);offset+=l.length+n.length+data.length;}const cd=Buffer.concat(central),end=Buffer.alloc(22);end.writeUInt32LE(0x06054b50);end.writeUInt16LE(entries.length,8);end.writeUInt16LE(entries.length,10);end.writeUInt32LE(cd.length,12);end.writeUInt32LE(offset,16);return Buffer.concat([...locals,cd,end]);}
test('ZIP accepts one ROM, verifies CRC and rejects ambiguous archives',async()=>{const dir=await mkdtemp(join(tmpdir(),'agarstra-zip-'));try{const path=join(dir,'game.zip'),bytes=zip([['nested/game.nes',fixture()]]);await writeFile(path,bytes);assert.equal((await loadRom(path)).archiveMember,'nested/game.nes');bytes[100]^=1;await writeFile(path,bytes);await assert.rejects(()=>loadRom(path),/integrity/);await writeFile(path,zip([['a.nes',fixture()],['b.nes',fixture()]]));await assert.rejects(()=>loadRom(path),/exactly one/);}finally{await rm(dir,{recursive:true,force:true});}});
