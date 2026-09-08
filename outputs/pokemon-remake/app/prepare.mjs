import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const base=path.dirname(new URL(import.meta.url).pathname);
// Build-time checkpoint integrity. The catalog declares the selected startup checkpoint.
const checkpointDir=path.resolve(base,'../runtime-core/checkpoints');
const catalog=JSON.parse(fs.readFileSync(path.join(checkpointDir,'catalog.json'),'utf8'));
if(!catalog.entries.some(item=>item.id===catalog.default))throw Error('Default checkpoint is not in the catalog');
for(const item of catalog.entries){
  const bytes=fs.readFileSync(path.join(checkpointDir,item.file));
  if(bytes.length!==397312||bytes.readUInt32LE(0)!==0x0100000b||crypto.createHash('sha256').update(bytes).digest('hex')!==item.sha256)throw Error(`Checkpoint integrity failed: ${item.id}`);
}
if(process.argv.includes('--check-checkpoints')){
  console.log(JSON.stringify({passed:true,default:catalog.default,checkpoints:catalog.entries.map(({id,sha256})=>({id,sha256}))},null,2));
}else{
fs.cpSync(path.resolve(base,'../runtime-core'),path.join(base,'public/core'),{recursive:true});
const models=path.resolve(base,'../models');
for(const name of fs.readdirSync(models))if(name.endsWith('.glb'))fs.copyFileSync(path.join(models,name),path.join(base,'public/models',name));
fs.copyFileSync(path.resolve(base,'../source/scene-layout.json'),path.join(base,'public/scene-layout.json'));
fs.copyFileSync(path.resolve(base,'../design/runtime-candidates.json'),path.join(base,'public/runtime-candidates.json'));
const tree=path.resolve(base,'../environment/tree/tree.glb');
if(fs.existsSync(tree))fs.copyFileSync(tree,path.join(base,'public/models/tree.glb'));
fs.cpSync(path.resolve(base,'../environment/terrain'),path.join(base,'public/terrain'),{recursive:true});

fs.cpSync(path.resolve(base,'../environment/daylight'),path.join(base,'public/daylight'),{recursive:true});
}
