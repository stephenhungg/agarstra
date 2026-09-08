import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {createRequire} from 'node:module';
import {GbaAdapter} from '../../runtime-core/gba-adapter.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
const require=createRequire(import.meta.url),store=require('../../app/progress-store.cjs');
const dir=path.dirname(fileURLToPath(import.meta.url)),root=path.resolve(dir,'../../../..'),temp=fs.mkdtempSync(path.join(dir,'.progress-test-')),file=path.join(temp,'save.json');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const checkpoint=fs.readFileSync(path.join(root,'outputs/pokemon-remake/runtime-core/checkpoints/pallet-town.state'));
const checks=[];let reference,restored,resumed,core;
function check(name,fn){try{const detail=fn();checks.push({name,passed:true,...(detail===undefined?{}:{detail})});}catch(e){checks.push({name,passed:false,error:e.message});throw e;}}
function rejectsRecord(name,change,pattern){const record=JSON.parse(validRecord);change(record);fs.writeFileSync(file,JSON.stringify(record));check(name,()=>assert.throws(()=>store.load(file),pattern));}
let validRecord;
try{
 check('absent progress returns null',()=>assert.equal(store.load(file),null));
 const saved=store.save(file,checkpoint);validRecord=fs.readFileSync(file);
 check('exact snapshot byte roundtrip',()=>{const loaded=store.load(file);assert.deepEqual(Buffer.from(loaded.bytes),checkpoint);assert.equal(loaded.savedAt,saved.savedAt);return{bytes:checkpoint.length,sha256:sha(loaded.bytes)}});
 check('atomic save leaves no temporary file',()=>assert.equal(fs.existsSync(file+'.tmp'),false));
 check('record declares expected ROM and version',()=>{const r=JSON.parse(validRecord);assert.equal(r.romSHA1,'41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc');assert.equal(r.version,1);});
 for(const [name,invalid]of [['short snapshot',checkpoint.subarray(0,100)],['wrong-length snapshot',Buffer.alloc(checkpoint.length+1)],['wrong magic',Buffer.from(checkpoint)]]){
  if(name==='wrong magic')invalid.writeUInt32LE(0,0);
  check(`save rejects ${name} without replacing valid progress`,()=>{assert.throws(()=>store.save(file,invalid),/Invalid FireRed snapshot/);assert.deepEqual(fs.readFileSync(file),validRecord);});
 }
 rejectsRecord('corrupt checksum rejected',r=>r.sha256='0'.repeat(64),/checksum mismatch/);
 rejectsRecord('changed payload rejected',r=>{const b=Buffer.from(r.state,'base64');b[0x30000]^=1;r.state=b.toString('base64')},/checksum mismatch/);
 rejectsRecord('truncated stored state rejected',r=>r.state=checkpoint.subarray(0,100).toString('base64'),/Invalid FireRed snapshot/);
 rejectsRecord('invalid stored magic rejected',r=>{const b=Buffer.from(checkpoint);b[0]^=1;r.state=b.toString('base64');r.sha256=sha(b)},/Invalid FireRed snapshot/);
 rejectsRecord('foreign ROM record rejected',r=>r.romSHA1='0'.repeat(40),/different ROM/);
 rejectsRecord('unsupported record version rejected',r=>r.version=2,/different ROM/);
 fs.writeFileSync(file,'{broken');check('invalid JSON rejected',()=>assert.throws(()=>store.load(file),SyntaxError));
 fs.writeFileSync(file,validRecord);
 const bridge=path.join(root,'work/pokemon/bridge-probe/'),rom=fs.readFileSync(path.join(root,'work/pokemon/rom/firered-user.gba'));
 const newCore=async()=>new GbaAdapter(await require(bridge+'mgba.cjs')({locateFile:p=>bridge+'package/dist/mgba/'+p}),rom);
 const compact=s=>({frame:s.frame,map:s.map,player:s.player,battle:s.battle,phase:s.phase});
 core=await newCore();core.loadState(checkpoint);reference=compact(readFireRedState(core));core.destroy();core=null;
 core=await newCore();core.loadState(store.load(file).bytes);restored=compact(readFireRedState(core));
 check('fresh GbaAdapter restores exact observed source state',()=>assert.deepEqual(restored,reference));
 check('fresh restore is Pallet Town with expected source player',()=>{assert.equal(restored.map.name,'PalletTown');assert.equal(restored.map.group,3);assert.equal(restored.map.number,0);assert.equal(restored.player.worldX,6);assert.equal(restored.player.worldY,8);assert.equal(restored.player.facing,'down');return{map:restored.map,player:restored.player};});
 const badROM=Buffer.from(checkpoint);badROM[8]^=1;check('GbaAdapter rejects wrong embedded ROM identity',()=>assert.throws(()=>core.loadState(badROM),/different ROM/));
 core.step(1,0);resumed=compact(readFireRedState(core));check('first redraw frame resumes same map and player location',()=>{assert.equal(resumed.frame,restored.frame+1);assert.equal(resumed.map.name,restored.map.name);assert.equal(resumed.player.worldX,restored.player.worldX);assert.equal(resumed.player.worldY,restored.player.worldY)});
}catch(e){console.error(e.stack);process.exitCode=1;}finally{
 core?.destroy();fs.rmSync(temp,{recursive:true,force:true});
 const report={passed:checks.every(c=>c.passed)&&!process.exitCode,checkedAt:new Date().toISOString(),storeSHA256:sha(fs.readFileSync(path.join(root,'outputs/pokemon-remake/app/progress-store.cjs'))),checkpointSHA256:sha(checkpoint),checks,reference,restored,resumed,limitations:['Verifies store and real native-core restoration. Electron keyboard/button interaction is owned by the root integration test.','Store validation covers size, magic, envelope ROM/version and checksum; GbaAdapter separately verifies embedded ROM identity. It is not a semantic validator of every internal emulator field.','A source redraw advances one native frame; exact byte preservation refers to file roundtrip, not the post-redraw core serialization.','No user progress file or shared smoke-test save is modified. Temporary fixture is removed.']};
 fs.writeFileSync(path.join(dir,'progress-store-results.json'),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:report.passed,checks:checks.length,failed:checks.filter(c=>!c.passed),restored},null,2));
}
