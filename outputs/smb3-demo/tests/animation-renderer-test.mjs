import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {PhotorealRenderer,advanceSourceClock,createSourceAnimation,resetSourceAnimation,sourceAnimationState,unresolvedSourceObject,updateSourceAnimation} from '../src/photoreal-renderer.js';

const assets=path.resolve(process.argv[2]||new URL('../public/assets/photoreal',import.meta.url).pathname);
const authoredManifest=JSON.parse(fs.readFileSync(new URL('../../smb3-photoreal/animated/manifest.json',import.meta.url),'utf8'));
const projectRoot=new URL('../../../',import.meta.url).pathname;
const cases={
 'mario-body':['idle','walk','run','jump-rise','jump-fall','death'],
 goomba:['idle','walk','squash'],
 'koopa-green':['idle','walk','shell'],
 'koopa-red':['idle','walk','shell'],
 'piranha-plant':['idle','bite'],
};

// Keep the actual exported node transforms, accessors, binary data and animation
// channels. Only omit material textures because this test has no browser Image.
async function loadAnimationGLB(filename){
 const bytes=fs.readFileSync(filename),jsonLength=bytes.readUInt32LE(12);
 const document=JSON.parse(bytes.subarray(20,20+jsonLength));
 document.materials=(document.materials||[]).map(m=>({name:m.name,pbrMetallicRoughness:{baseColorFactor:[1,1,1,1]}}));
 delete document.images;delete document.textures;delete document.samplers;
 delete document.extensionsUsed;delete document.extensionsRequired;
 const json=Buffer.from(JSON.stringify(document)),padded=Buffer.alloc(Math.ceil(json.length/4)*4,32);json.copy(padded);
 const remaining=bytes.subarray(20+jsonLength),result=Buffer.alloc(20+padded.length+remaining.length);
 result.writeUInt32LE(0x46546c67,0);result.writeUInt32LE(2,4);result.writeUInt32LE(result.length,8);result.writeUInt32LE(padded.length,12);result.writeUInt32LE(0x4e4f534a,16);padded.copy(result,20);remaining.copy(result,20+padded.length);
 return new GLTFLoader().parseAsync(result.buffer.slice(result.byteOffset,result.byteOffset+result.byteLength),'');
}

const matrices=model=>{model.updateMatrixWorld(true);const values=[];model.traverse(n=>values.push(...n.matrix.elements));return values;};
const maxDifference=(a,b)=>Math.max(0,...a.map((v,i)=>Math.abs(v-b[i])));
const sources={idle:{velocity:{x:0,y:0}},walk:{velocity:{x:1.1,y:0}},run:{velocity:{x:2.8,y:0}},'jump-rise':{inAir:true,velocity:{x:2,y:-3}},'jump-fall':{inAir:true,velocity:{x:2,y:2}},death:{dying:true,velocity:{x:0,y:-3}},squash:{squashed:true,state:'squashed'},shell:{state:'shelled'},bite:{frame:1,velocity:{x:0,y:.1}}};
const results=[];
for(const [id,expected]of Object.entries(cases)){
 const gltf=await loadAnimationGLB(path.join(assets,`${id}.glb`)),model=gltf.scene;
 const sourceAsset=authoredManifest.assets.find(a=>a.asset_id===id);assert(sourceAsset?.sourcePath,`${id} retains source-model provenance`);
 const sourceModel=await loadAnimationGLB(path.resolve(projectRoot,sourceAsset.sourcePath));
 const sourceBounds=new THREE.Box3().setFromObject(sourceModel.scene,true),animatedBounds=new THREE.Box3().setFromObject(model,true);
 const bindBoundsMaxError=Math.max(...['min','max'].flatMap(key=>['x','y','z'].map(axis=>Math.abs(sourceBounds[key][axis]-animatedBounds[key][axis]))));
 assert(bindBoundsMaxError<1e-5,`${id} exported rest bounds preserve the original asset: ${bindBoundsMaxError}`);
 assert.deepEqual(gltf.animations.map(c=>c.name).sort(),[...expected].sort(),`${id} has its authored clips`);
 const animation=createSourceAnimation(model,gltf.animations),type=id.startsWith('mario')?'player':id.startsWith('koopa')?'koopa':id==='piranha-plant'?'piranha':'goomba';
 const originalPosition=model.position.clone(),originalScale=model.scale.clone(),originalRotation=model.quaternion.clone();
 let animatedMaxDelta=0;
 const states=[];
 for(const state of expected){
  resetSourceAnimation(animation);
  const source={type,...sources[state]};
  assert.equal(sourceAnimationState(source),state);
  const first=updateSourceAnimation(animation,source,0);assert.equal(first.clip,state);
  const before=matrices(model);
  for(let frame=0;frame<12;frame++)updateSourceAnimation(animation,source,1/60.0988);
  const after=matrices(model);animatedMaxDelta=Math.max(animatedMaxDelta,maxDifference(before,after));
  const pausedTime=animation.actions.get(state).time;
  for(let redraw=0;redraw<20;redraw++)updateSourceAnimation(animation,source,0);
  assert.deepEqual(matrices(model),after,`${id}:${state} pause preserves every node transform`);
  assert.equal(animation.actions.get(state).time,pausedTime,`${id}:${state} pause preserves clip time`);
  if(!['idle','walk','run','bite'].includes(state)){
   updateSourceAnimation(animation,source,3);
   const action=animation.actions.get(state);assert(action.paused,`${id}:${state} clamps at last pose`);assert.equal(action.time,action.getClip().duration);
  }
  states.push({state,duration:animation.actions.get(state).getClip().duration});
  assert(model.position.equals(originalPosition)&&model.scale.equals(originalScale)&&model.quaternion.equals(originalRotation),`${id}:${state} never moves/scales/rotates the level placement root`);
 }
 assert(animatedMaxDelta>1e-4,`${id} actually changes node transforms`);
 const sequence=()=>{resetSourceAnimation(animation);for(const state of expected){const source={type,...sources[state]};for(let frame=0;frame<8;frame++)updateSourceAnimation(animation,source,1/60.0988);}return matrices(model);};
 assert.deepEqual(sequence(),sequence(),`${id} reset and replay is deterministic`);
 results.push({id,clips:states,animatedMaxDelta,bindBoundsMaxError,deterministicReset:true,pauseFrozen:true,placementRootPreserved:true});
}
const clock={frame:null,time:0};assert.deepEqual(advanceSourceClock(clock,100,1),{dt:0,reset:false});
assert.equal(advanceSourceClock(clock,101).dt,1/60.0988);const held=clock.time;
assert.equal(advanceSourceClock(clock,101,1).dt,0);assert.equal(clock.time,held);
assert(advanceSourceClock(clock,10).reset);assert.equal(clock.time,0);
const unresolved=unresolvedSourceObject({id:'unknown-score',type:'score',x:250,y:185,width:24,height:12,source:{idAddress:0x671}},null,0);
assert.deepEqual(unresolved.screenRect,{x:250,y:185,width:6,height:7});assert.equal(unresolved.source.idAddress,0x671);
assert.equal(unresolvedSourceObject({x:290,y:20,width:8,height:8},null,0),null);
assert.equal(sourceAnimationState({type:'koopa',state:'kicked',velocity:{x:4}}),'shell');
assert.equal(sourceAnimationState({type:'player',dying:true,inAir:true,velocity:{y:-3}}),'death');
// Exercise renderer coverage decisions without requiring a WebGL context.
const headless=Object.create(PhotorealRenderer.prototype),position=()=>({position:{x:0}});
Object.assign(headless,{sourceClock:{frame:null,time:0},frame:0,stats:{},instances:new Map(),models:new Map(),camera:position(),sun:{...position(),target:position()},fill:position(),sky:position(),skyGradient:position(),backdrops:[],render(){}});
headless.update({frame:100,semantic:{cameraX:0,objects:[{id:'source-cell',type:'unknown',x:32,y:48,width:16,height:16,source:{metatileIds:[0xfc],sramAddresses:[0x6123]}}],entities:[],supported:false,renderable:true,mode:'death'}},1/60);
assert.equal(headless.stats.needsOriginal,false,'an unknown object in a mapped death scene must not replace the complete remodeled frame');
assert.equal(headless.stats.unresolvedObjects.length,1);assert.deepEqual(headless.stats.unresolvedObjects[0].source.metatileIds,[0xfc]);
headless.update({frame:101,semantic:{cameraX:0,objects:[],entities:[],supported:false,renderable:false,mode:'unmapped'}},1/60);
assert.equal(headless.stats.needsOriginal,true,'an unmapped scene reports capability honestly');
const result={passed:true,assetDirectory:assets,models:results,checks:['actual exported GLB channels parsed and played by THREE.AnimationMixer','idle and movement loops','source-driven jump/death/squash/shell/bite selection','once poses clamp','pause freezes transforms and fades','reset reproduces identical transforms','clips preserve level placement root','emulated-frame clock independent of redraw cadence','clipped unresolved object regions retain source IDs']};
console.log(JSON.stringify(result,null,2));
fs.writeFileSync(new URL('../../smb3-photoreal/verification/animation-renderer.json',import.meta.url),JSON.stringify(result,null,2)+'\n');
