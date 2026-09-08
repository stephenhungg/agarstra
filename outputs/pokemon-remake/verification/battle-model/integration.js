import * as THREE from 'three';
import {createBattle} from '../../app/battle.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
window.integration={ready:false,error:null};
const assert=(ok,message)=>{if(!ok)throw new Error(message);};
try{
  const renderer=new THREE.WebGLRenderer({canvas:document.querySelector('#world'),antialias:true,preserveDrawingBuffer:true});renderer.setSize(innerWidth,innerHeight);renderer.setPixelRatio(1);renderer.toneMapping=THREE.ACESFilmicToneMapping;
  const scene=new THREE.Scene();scene.background=new THREE.Color('#d4ddc8');
  const core=await createGbaCore(await window.testROM.load());
  const checkpoint=new Uint8Array(await(await fetch('/runtime-core/checkpoints/first-battle.state')).arrayBuffer());core.loadState(checkpoint);
  const battle=await createBattle(renderer);scene.add(battle.group);battle.resize(innerWidth,innerHeight);
  const paint=(input=core)=>{const s=battle.update(input,readFireRedState(core));renderer.render(scene,battle.camera);return s;};
  const matrices=()=>{const result=[];battle.group.getObjectByName('Opponent Charmander candidate').traverse(n=>{result.push(n.name,...n.position,...n.quaternion,...n.scale);});return JSON.stringify(result);};
  const checks=[];const check=(name,ok,detail)=>{checks.push({name,ok,detail});assert(ok,name);};
  const before=core.saveState();paint();
  for(let i=0;i<400&&battle.report.modelLoadStatus==='loading';i++){await new Promise(r=>setTimeout(r,25));paint();}
  check('actual reviewed v2 loads with expected SHA and idle',battle.report.modelLoadStatus==='ready'&&battle.report.creatureModel.sha256==='ad78d6f71b421d5f3ce534806b2f816d160647be282276152dca03a25c6ce7e6'&&battle.report.creatureModel.selectedClip==='idle',battle.report);
  const initial=battle.actorSnapshots,opponent=initial.find(x=>x.id===1),player=initial.find(x=>x.id===0);
  check('only opponent Charmander uses 3D; Bulbasaur remains source sprite',opponent.presentation==='rigged-3d-candidate'&&player.presentation==='source-sprite'&&opponent.visible&&player.visible,initial);
  check('3D anchor is fixed stage coordinate',opponent.position.every((x,i)=>Math.abs(x-[4,-.04,-3][i])<1e-6),opponent.position);
  const paused=matrices();for(let i=0;i<8;i++)paint();
  check('paused source frame freezes complete model transforms',matrices()===paused);
  const afterReads=core.saveState();check('presentation/load does not mutate serialized core',before.every((v,i)=>v===afterReads[i]));
  core.step(45,0);paint();check('authored idle responds to source frame advancement',matrices()!==paused);
  check('animation clock is exactly source frame / native FPS',Math.abs(battle.report.creatureModel.sourceSeconds-core.frame/59.7275)<1e-10);
  core.loadState(checkpoint);const source=paint();check('checkpoint reset restores model transforms',matrices()===paused);
  const spriteId=source.battlers.find(x=>x.id===1).sprite.spriteId;
  const modifiedRead=(hidden=false)=>new Proxy(core,{get(target,prop){if(prop==='readBytes')return(address,length)=>{const bytes=target.readBytes(address,length);if(address===0x0202063c){const copy=new Uint8Array(bytes),view=new DataView(copy.buffer);view.setInt16(spriteId*0x44+0x24,12,true);view.setInt16(spriteId*0x44+0x26,-6,true);if(hidden)copy[spriteId*0x44+0x3e]|=4;return copy;}return bytes;};const value=Reflect.get(target,prop);return typeof value==='function'?value.bind(target):value;}});
  paint(modifiedRead());const shifted=battle.actorSnapshots.find(x=>x.id===1),up=new THREE.Vector3().setFromMatrixColumn(battle.camera.matrixWorld,1),right=new THREE.Vector3().setFromMatrixColumn(battle.camera.matrixWorld,0),expected=new THREE.Vector3(4,-.04,-3).addScaledVector(right,12*.082).addScaledVector(up,6*.082);
  check('source x2/y2 offsets map directly without captured animation baseline',new THREE.Vector3(...shifted.position).distanceTo(expected)<1e-8,shifted);
  paint(modifiedRead(true));check('source hide flag hides 3D candidate',!battle.actorSnapshots.find(x=>x.id===1).visible);
  paint();check('source show restores 3D candidate',battle.actorSnapshots.find(x=>x.id===1).visible);
  // Force an actual loader failure without altering any source core memory.
  const normalFetch=window.fetch;window.fetch=(url,...args)=>String(url).includes('charmander-existing-v2.glb')?Promise.resolve(new Response('fixture unavailable',{status:503})):normalFetch(url,...args);
  const failed=await createBattle(renderer);failed.update(core,readFireRedState(core));
  for(let i=0;i<40&&failed.report.modelLoadStatus==='loading';i++)await new Promise(r=>setTimeout(r,10));
  failed.update(core,readFireRedState(core));
  check('model failure records error and keeps original cutout',failed.report.modelLoadStatus==='failed'&&failed.report.modelError.includes('503')&&failed.actorSnapshots.find(x=>x.id===1).presentation==='source-sprite'&&failed.actorSnapshots.find(x=>x.id===1).visible,failed.report.modelError);
  failed.dispose();window.fetch=normalFetch;paint();
  window.integration={ready:true,error:null,passed:checks.every(x=>x.ok),checks,report:JSON.parse(JSON.stringify(battle.report)),actors:battle.actorSnapshots,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};
}catch(error){window.integration.error=error.stack;console.error(error);}
