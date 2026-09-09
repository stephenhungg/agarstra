import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {createBattle} from '../../app/battle.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';

window.starterAudit={ready:false,error:null};
const renderer=new THREE.WebGLRenderer({canvas:document.querySelector('#world'),antialias:true,preserveDrawingBuffer:true});
renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);
renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();scene.background=new THREE.Color('#d7d8cc');
const environment=new THREE.PMREMGenerator(renderer);scene.environment=environment.fromScene(new RoomEnvironment(),.04).texture;
scene.environmentIntensity=.65;environment.dispose();
const realFetch=globalThis.fetch.bind(globalThis);
// An intentional delayed asset makes the paused-load regression reproducible.
globalThis.fetch=async(...args)=>{if(String(args[0]).includes('charmander-battle-v3.glb'))await new Promise(r=>setTimeout(r,900));return realFetch(...args);};
const checks=[];const check=(name,ok,detail)=>{checks.push({name,ok,...(detail===undefined?{}:{detail})});};
const delay=ms=>new Promise(r=>setTimeout(r,ms));
try{
  const core=await createGbaCore(await window.auditROM.load());
  const battle=await createBattle(renderer);scene.add(battle.group);battle.resize(innerWidth,innerHeight);battle.setVisible(true);
  const checkpoint=new Uint8Array(await(await realFetch('/core/checkpoints/first-battle.state')).arrayBuffer());
  const replay=await(await realFetch('/core/checkpoints/battle-verification.json')).json();
  const paint=()=>battle.update(core,readFireRedState(core));
  const draw=()=>renderer.render(scene,battle.camera);
  core.loadState(checkpoint);core.step(1,0);paint();draw();
  const heldFrame=core.frame;
  check('pending model leaves live source sprite',battle.actorSnapshots.some(a=>a.id===1&&a.visible&&a.presentation==='source-sprite'));
  const deadline=performance.now()+45000;
  while(performance.now()<deadline&&(battle.report.arena.status==='loading'||Object.values(battle.report.models).some(m=>m.status==='loading')))await delay(50);
  draw();
  check('paused late GLB load does not step source',core.frame===heldFrame,{before:heldFrame,after:core.frame});
  check('late Charmander appears without a new paint call',battle.actorSnapshots.some(a=>a.id===1&&a.visible&&a.presentation==='rigged-3d-candidate'),battle.actorSnapshots);
  check('arena loads exact registered bytes',battle.report.arena.status==='ready',battle.report.arena);
  check('scene submits real WebGL geometry',renderer.info.render.calls>0&&renderer.info.render.triangles>70000,{calls:renderer.info.render.calls,triangles:renderer.info.render.triangles});
  const sourceBefore=core.saveState();paint();draw();paint();draw();
  const sourceAfter=core.saveState();
  check('repeated paused paint preserves complete source bytes',sourceBefore.length===sourceAfter.length&&sourceBefore.every((v,i)=>v===sourceAfter[i]));
  const loadedActors=battle.actorSnapshots;
  check('3D actors keep fixed stage anchors and original offsets',loadedActors.filter(a=>a.presentation!=='source-sprite').every(a=>Math.abs(a.position[0]-(a.id&1?4:-4)-a.sourceOffsets.x*.082)<.001),loadedActors);
  const sourceFrames=[],captures={};
  const capture=name=>{draw();captures[name]=renderer.domElement.toDataURL('image/png');};
  capture('paused-loaded-battle');
  function replayAttack(capturePoses){
    core.loadState(checkpoint);paint();const eventStart=battle.report.events.length,seen=new Set();
    for(const segment of replay.attackInputs)for(let i=0;i<segment.frames;i++){
      core.step(1,segment.keys);paint();
      if(capturePoses)for(const event of battle.report.events.slice(eventStart))if(core.frame===event.frame+8&&!seen.has(event.id)){
        seen.add(event.id);capture(`${event.action}-${event.battlerId}-${event.frame}`);sourceFrames.push({frame:core.frame,event,actors:battle.actorSnapshots});
      }
    }
    return {events:battle.report.events.slice(eventStart),bytes:core.saveState(),hp:readFireRedState(core).battle.battlers.map(b=>b.hp)};
  }
  const first=replayAttack(true),second=replayAttack(false);
  check('real first turn changes source HP to 11 and 14',String(first.hp)==='11,14',first.hp);
  check('checkpoint replay preserves full emulator bytes',first.bytes.length===second.bytes.length&&first.bytes.every((v,i)=>v===second.bytes[i]));
  check('checkpoint replay reproduces action event frames',JSON.stringify(first.events)===JSON.stringify(second.events),first.events);
  check('native attack and hit signals are both observed',first.events.some(e=>e.action==='attack')&&first.events.some(e=>e.action==='hit'));
  core.loadState(checkpoint);core.step(12,1);core.step(40,0);paint();draw();
  check('native Fight opens original move selection',battle.snapshot.menu?.mode==='moves',battle.snapshot.menu);capture('native-move-menu');
  window.starterAudit={ready:true,error:null,checks,passed:checks.every(c=>c.ok),captures,sourceFrames,
    report:battle.report,actors:battle.actorSnapshots,events:first.events,
    finalHP:first.hp,frame:core.frame,render:{calls:renderer.info.render.calls,triangles:renderer.info.render.triangles},
    resize(width,height){renderer.setSize(width,height);battle.resize(width,height);draw();return{position:battle.camera.position.toArray(),frustum:[battle.camera.left,battle.camera.right,battle.camera.top,battle.camera.bottom],actors:battle.actorSnapshots};}};
}catch(error){window.starterAudit.error=error.stack;console.error(error);}
