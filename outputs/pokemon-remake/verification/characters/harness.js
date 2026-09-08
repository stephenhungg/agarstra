import * as THREE from 'three';
import {createCharacters} from '../../app/characters.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
import {createDialogOverlay} from '../../app/dialog.js';
const view=document.querySelector('#view'), renderer=new THREE.WebGLRenderer({antialias:false,preserveDrawingBuffer:true});
renderer.setSize(1100,780);renderer.setPixelRatio(1);view.appendChild(renderer.domElement);
const scene=new THREE.Scene();scene.background=new THREE.Color('#253b30');
const camera=new THREE.OrthographicCamera(-9,9,6.38,-6.38,.1,120);
const grid=new THREE.GridHelper(50,50,0x688676,0x435e4e);grid.position.set(12,-.02,12);scene.add(grid);
const chars=await createCharacters();scene.add(chars.group);
const dialog=createDialogOverlay(view);
const core=await createGbaCore(new Uint8Array(await(await fetch('/rom')).arrayBuffer()));
function paint(){
 const state=readFireRedState(core),before=core.state.slice();
 chars.update(core,state,{visible:true,playerModelVisible:false,groundHeight:0});
 const cx=state.player?.worldX??8,cz=state.player?.worldY??8;
 camera.position.set(cx,18,cz+20);camera.lookAt(cx,0,cz);camera.updateMatrixWorld();
 renderer.render(scene,camera);const d=dialog.update(core,state);
 document.querySelector('#source').getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(core.pixels()),240,160),0,0);
 document.querySelector('#label').textContent=`${state.map?.name} · frame ${state.frame} · ${state.player?.facing??state.phase}`;
 return {state,report:structuredClone(typeof chars.report==='function'?chars.report():chars.report),dialog:d,readOnly:before.every((v,i)=>v===core.state[i]),drawCalls:renderer.info.render.calls};
}
window.showFixture=async path=>{core.loadState(new Uint8Array(await(await fetch(path)).arrayBuffer()));core.step(1,0);return paint();};
window.move=(keys=128,frames=20)=>{const before=paint();const samples=[];for(let i=0;i<frames;i++){core.step(1,keys);samples.push(paint());}return{before,samples};};
window.transitions=async()=>{
 const records=await(await fetch('../interiors/transition-replays.json')).json(),results=[];
 for(const r of records){core.loadState(new Uint8Array(await(await fetch(`/fixture/${r.start}.state`)).arrayBuffer()));const visited=[];let readonly=true;
 for(const s of r.suffix)for(let i=0;i<s.frames;i++){core.step(1,s.keys);const p=paint();readonly&&=p.readOnly;const key=p.state.phase+':'+p.state.map?.name;if(visited.at(-1)?.key!==key)visited.push({key,frame:p.state.frame,report:p.report,objects:p.state.objectEvents});}
 const target=new Uint8Array(await(await fetch(`/fixture/${r.target}.state`)).arrayBuffer()),actual=core.saveState();
 results.push({start:r.start,target:r.target,visited,readOnly:readonly,gameplayMemoryExact:actual.slice(0x800).every((v,i)=>v===target[i+0x800]),final:paint()});
 }return results;
};
window.ready=true;
// These are presentation-only synthetic state variants; the native core is never written.
window.lifecycle=()=>{
 const state=readFireRedState(core),before=core.saveState();const checks=[];
 const snap=()=>structuredClone(chars.report),apply=(s,opts={})=>{chars.update(core,s,{groundHeight:0,...opts});return snap();};
 const original=apply(state),target=state.objectEvents.find(o=>!o.hidden&&!o.isPlayer)??state.player;
 let disposed=0;for(const child of chars.group.children)child.material.map.addEventListener('dispose',()=>disposed++);
 const hidden=structuredClone(state);hidden.objectEvents.find(o=>o.id===target.id).hidden=true;
 const hiddenReport=apply(hidden);checks.push({name:'synthetic script hide retires actor and texture',passed:!hiddenReport.actors.some(a=>a.id===target.id)&&disposed===1});apply(state);
 const oldKey=chars.report.actors.find(a=>a.id===target.id).key;
 const reused=structuredClone(state);reused.objectEvents.find(o=>o.id===target.id).graphicsId+=1;
 const reusedReport=apply(reused);checks.push({name:'synthetic graphics change gives reused slot a new lifetime',passed:reusedReport.actors.some(a=>a.id===target.id&&a.key!==oldKey)&&!reusedReport.actors.some(a=>a.key===oldKey)});apply(state);
 const modeled=apply(state,{playerModelVisible:true});checks.push({name:'model substitution removes only player fallback',passed:!modeled.actors.some(a=>a.isPlayer)&&modeled.actors.length===original.actors.filter(a=>!a.isPlayer).length});apply(state);
 let retired=0;const count=chars.group.children.length;for(const child of chars.group.children)child.material.map.addEventListener('dispose',()=>retired++);
 const off=apply(state,{visible:false});checks.push({name:'presentation hide clears actors and disposes every texture',passed:off.actors.length===0&&chars.group.children.length===0&&retired===count});
 const restored=apply(state);checks.push({name:'restoration recreates all source lifetimes',passed:JSON.stringify(restored.actors)===JSON.stringify(original.actors)});
 const after=core.saveState();checks.push({name:'synthetic state tests leave native core byte-identical',passed:before.every((v,i)=>v===after[i])});paint();return{synthetic:true,checks,passed:checks.every(c=>c.passed)};
};
