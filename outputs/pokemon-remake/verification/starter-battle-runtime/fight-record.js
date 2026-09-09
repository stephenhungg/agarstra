import * as THREE from 'three';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {createBattle} from '../../app/battle.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
window.fightRecord={ready:false,error:null};
try{
 const renderer=new THREE.WebGLRenderer({canvas:document.querySelector('#world'),antialias:true});renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
 const scene=new THREE.Scene();scene.background=new THREE.Color('#d7d8cc');const generator=new THREE.PMREMGenerator(renderer);scene.environment=generator.fromScene(new RoomEnvironment(),.04).texture;scene.environmentIntensity=.65;generator.dispose();
 const core=await createGbaCore(await window.auditROM.load());const battle=await createBattle(renderer);scene.add(battle.group);battle.resize(innerWidth,innerHeight);battle.setVisible(true);
 const checkpoint=new Uint8Array(await(await fetch('/core/checkpoints/first-battle.state')).arrayBuffer());
 const replay=await(await fetch('/core/checkpoints/battle-verification.json')).json();const keys=replay.attackInputs.flatMap(segment=>Array(segment.frames).fill(segment.keys));let index=0;
 const paint=()=>{battle.update(core,readFireRedState(core));renderer.render(scene,battle.camera);};
 core.loadState(checkpoint);core.step(1,0);paint();
 const deadline=performance.now()+40000;
 while(performance.now()<deadline&&(battle.report.arena.status==='loading'||Object.values(battle.report.models).some(m=>m.status==='loading')))await new Promise(r=>setTimeout(r,50));
 if(battle.report.arena.status!=='ready'||![0,1].every(id=>battle.report.models[id]?.status==='ready'))throw Error('Both 3D starters and arena must load before recording');
 core.loadState(checkpoint);paint();
 window.fightRecord={ready:true,error:null,advance(frames=3){for(let n=0;n<frames&&index<keys.length;n++){core.step(1,keys[index++]);battle.update(core,readFireRedState(core));}renderer.render(scene,battle.camera);return{frame:core.frame,index,hp:readFireRedState(core).battle.battlers.map(b=>b.hp),events:battle.report.events,actors:battle.actorSnapshots};},get status(){return{frame:core.frame,models:battle.report.models,arena:battle.report.arena,events:battle.report.events};}};
}catch(error){window.fightRecord.error=error.stack;console.error(error);}
