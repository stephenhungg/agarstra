import * as THREE from 'three';
import {createBattle} from '../../app/battle.js';
import {createGbaCore} from '../../runtime-core/browser-core.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
const renderer=new THREE.WebGLRenderer({canvas:document.querySelector('#world'),antialias:true});
renderer.setPixelRatio(1);renderer.setSize(innerWidth,innerHeight);renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;
const scene=new THREE.Scene();scene.background=new THREE.Color('#d4ddc8');
window.battleTest={ready:false,error:null};
try{
  const core=await createGbaCore(await window.testROM.load());const battle=await createBattle(renderer);scene.add(battle.group);battle.resize(innerWidth,innerHeight);battle.setVisible(true);
  async function load(name){const response=await fetch(new URL(`../../runtime-core/checkpoints/${name}.state`,import.meta.url));core.loadState(new Uint8Array(await response.arrayBuffer()));core.step(1,0);return paint();}
  function paint(){const snapshot=battle.update(core,readFireRedState(core));renderer.render(scene,battle.camera);return{frame:core.frame,hp:snapshot.battlers.map(b=>b.hp),menu:snapshot.menu,actors:battle.actorSnapshots,drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles,hud:document.querySelector('.rom-battle-hud').textContent};}
  window.battleTest={ready:true,error:null,load,paint,advance(n,keys){core.step(n,keys);return paint();},sourceImage(){const c=document.createElement('canvas');c.width=240;c.height=160;c.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(core.pixels()),240,160),0,0);return c.toDataURL();},get state(){return paint();}};
  await load('first-battle');
}catch(error){window.battleTest.error=error.stack;console.error(error);}
