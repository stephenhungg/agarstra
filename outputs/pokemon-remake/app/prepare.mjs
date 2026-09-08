import fs from 'node:fs';
import path from 'node:path';
const base=path.dirname(new URL(import.meta.url).pathname);
fs.cpSync(path.resolve(base,'../runtime-core'),path.join(base,'public/core'),{recursive:true});
const models=path.resolve(base,'../models');
for(const name of fs.readdirSync(models))if(name.endsWith('.glb'))fs.copyFileSync(path.join(models,name),path.join(base,'public/models',name));
fs.copyFileSync(path.resolve(base,'../source/scene-layout.json'),path.join(base,'public/scene-layout.json'));
fs.copyFileSync(path.resolve(base,'../design/runtime-candidates.json'),path.join(base,'public/runtime-candidates.json'));
const tree=path.resolve(base,'../environment/tree/tree.glb');
if(fs.existsSync(tree))fs.copyFileSync(tree,path.join(base,'public/models/tree.glb'));
fs.cpSync(path.resolve(base,'../environment/terrain'),path.join(base,'public/terrain'),{recursive:true});

fs.cpSync(path.resolve(base,'../environment/daylight'),path.join(base,'public/daylight'),{recursive:true});
