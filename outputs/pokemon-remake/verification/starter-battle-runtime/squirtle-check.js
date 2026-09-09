import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {createBattle} from '../../app/battle.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
window.squirtleCheck={ready:false,error:null};
const checks=[];const check=(name,ok,detail)=>{checks.push({name,ok,...(detail===undefined?{}:{detail})});if(!ok)throw Error(name+' '+JSON.stringify(detail));};
const renderer=new THREE.WebGLRenderer({canvas:document.querySelector('#world'),antialias:true,preserveDrawingBuffer:true});renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();scene.background=new THREE.Color('#d7d8cc');const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(new RoomEnvironment(),.04).texture;scene.environmentIntensity=.65;pmrem.dispose();
const captures={};
try{
 const core=await createGbaCore(await window.auditROM.load()),battle=await createBattle(renderer);scene.add(battle.group);battle.resize(innerWidth,innerHeight);battle.setVisible(true);
 const checkpoint=new Uint8Array(await(await fetch('/core/checkpoints/first-battle.state')).arrayBuffer());core.loadState(checkpoint);core.step(1,0);
 const substitute=()=>{const state=readFireRedState(core);return{...state,battle:{...state.battle,battlers:state.battle.battlers.map(mon=>({...mon,species:7}))}}}; // Observation fixture only, never writes core RAM.
 const paint=(reader=core)=>battle.update(reader,substitute());
 const draw=()=>renderer.render(scene,battle.camera);
 const capture=name=>{draw();captures[name]=renderer.domElement.toDataURL('image/png');};
 const transforms=()=>{const values=[];for(const id of [0,1])battle.group.getObjectByName(`Battler ${id} species 7 candidate`)?.traverse(n=>values.push(n.name,...n.position,...n.quaternion,...n.scale));return JSON.stringify(values);};
 paint();const held=core.saveState(),deadline=performance.now()+45000;
 while(performance.now()<deadline&&(battle.report.arena.status==='loading'||Object.values(battle.report.models).some(m=>m.status==='loading')))await new Promise(r=>setTimeout(r,50));
 paint();draw();
 const reports=Object.values(battle.report.models);check('both actual species7 GLBs loaded with corrected hash',reports.length===2&&reports.every(r=>r.species===7&&r.status==='ready'&&r.model.sha256==='6cc80b3cb84aeec0e4f077b907ba324be38f2dec8ddbdb83244572214522114b'),reports);
 check('Tackle and Tail Whip clips exist in actual loaded GLB',reports.every(r=>r.model.availableActions.attack?.clip==='attack'&&r.model.availableActions.tailWhip?.clip==='tailWhip'));
 check('both visible source anchors use rigged Squirtle',battle.actorSnapshots.every(a=>{const expected=new THREE.Vector3(a.id===0?-4:4,-.04,a.id===0?3:-3).addScaledVector(new THREE.Vector3().setFromMatrixColumn(battle.camera.matrixWorld,0),a.sourceOffsets.x*.082).addScaledVector(new THREE.Vector3().setFromMatrixColumn(battle.camera.matrixWorld,1),-a.sourceOffsets.y*.082);return a.species===7&&a.presentation==='rigged-3d-candidate'&&a.visible&&new THREE.Vector3(...a.position).distanceTo(expected)<1e-8;}),battle.actorSnapshots);
 const dimensions=[];
 for(const id of [0,1]){const slot=battle.group.getObjectByName(`Battler ${id} species 7 candidate`),model=slot.children[0],forward=new THREE.Vector3(0,0,1).applyQuaternion(slot.quaternion);dimensions.push({id,height:reports[id].model.height*model.scale.y,forward:forward.toArray()});}
 check('normalized height is2.7 and actors face each other',dimensions.every(x=>Math.abs(x.height-2.7)<1e-8&&(x.id===0?x.forward[0]>0&&x.forward[2]<0:x.forward[0]<0&&x.forward[2]>0)),dimensions);
 const paused=transforms();for(let i=0;i<5;i++){paint();draw();}check('paused rendered skeleton remains identical',transforms()===paused);check('species substitution preserves original serialized ROM bytes',(()=>{const after=core.saveState();return held.every((v,i)=>v===after[i]);})());capture('squirtle-check-rest');
 const inputs=(await(await fetch('/core/checkpoints/battle-verification.json')).json()).attackInputs;let capturedAttack=false;
 for(const segment of inputs){for(let i=0;i<segment.frames;i++){core.step(1,segment.keys);paint();const event=battle.report.events.find(e=>e.action==='attack'&&e.battlerId===0);if(event&&core.frame>=event.frame+26){check('original Tackle signal selects actual Squirtle attack clip',battle.report.models[0].model.selectedClip==='attack'&&event.moveId===33,{event,clip:battle.report.models[0].model.selectedClip});capture('squirtle-check-tackle');capturedAttack=true;break;}}if(capturedAttack)break;}
 check('source Tackle event reached',capturedAttack);
 const nativeHeld=core.saveState(),baseFrame=core.frame+1;
 function signal(frame,active){return new Proxy(core,{get(target,key){if(key==='frame')return frame;if(key==='read8')return address=>address===0x02037ee1?Number(active):address===0x02037f1a?0:address===0x02037f1b?1:target.read8(address);if(key==='read16')return address=>address===0x02037f18?39:target.read16(address);const value=Reflect.get(target,key);return typeof value==='function'?value.bind(target):value;}});}
 paint(signal(baseFrame,false));paint(signal(baseFrame+1,true));paint(signal(baseFrame+24,true));draw();
 check('read-only Tail Whip fixture selects Tail Whip only',battle.report.models[0].model.selectedClip==='tailWhip'&&battle.report.models[0].model.event.action==='tailWhip',{clip:battle.report.models[0].model.selectedClip,event:battle.report.models[0].model.event});capture('squirtle-check-tail-whip');
 const tailPose=transforms();paint(signal(baseFrame+24,true));draw();check('paused Tail Whip does not retrigger or change pose',transforms()===tailPose);
 check('Tail Whip observer fixture never changes ROM bytes',(()=>{const after=core.saveState();return nativeHeld.every((v,i)=>v===after[i]);})());
 check('actual WebGL arena and creatures rendered',battle.report.arena.status==='ready'&&renderer.info.render.calls>0,{calls:renderer.info.render.calls,triangles:renderer.info.render.triangles});
 window.squirtleCheck={ready:true,error:null,passed:true,checks,captures,actors:battle.actorSnapshots,models:reports,dimensions,render:{calls:renderer.info.render.calls,triangles:renderer.info.render.triangles},limitations:['Both displayed species are substituted in a read-only observation fixture. Original ROM still contains Bulbasaur versus Charmander.','Tackle is driven by real original-ROM first-turn inputs; Tail Whip is an explicit read-only animation-signal fixture, not a Squirtle ROM playthrough.','No live app, shared manifest, source RAM or user save is modified.']};
}catch(error){window.squirtleCheck={ready:true,error:error.stack,passed:false,checks};console.error(error);}
