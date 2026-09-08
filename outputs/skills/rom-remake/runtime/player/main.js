import './style.css';
import { NES, Controller } from '../nes/vendor/jsnes/index.js';
import { inspectRom } from '../nes/ingest.mjs';
import { RomAssetExtractor } from '../nes/rom-extractor.js';
import { SourceRenderer } from './source-renderer.js';
import { setRomHash } from './production-gate.js';
const $ = id => document.getElementById(id);
let renderer = new SourceRenderer($('world')), nes, extractor, frame, running = false, sourceInfo, originalVisible=false, audioContext, audioNode, samples=[];
const keys = {ArrowUp:Controller.BUTTON_UP,ArrowDown:Controller.BUTTON_DOWN,ArrowLeft:Controller.BUTTON_LEFT,ArrowRight:Controller.BUTTON_RIGHT,KeyZ:Controller.BUTTON_A,KeyX:Controller.BUTTON_B,Enter:Controller.BUTTON_START,ShiftLeft:Controller.BUTTON_SELECT,ShiftRight:Controller.BUTTON_SELECT,Shift:Controller.BUTTON_SELECT};
const held = new Set(), padHeld=new Set();
function key(code, down) { if (!nes || !(code in keys)) return; if (down) held.add(code); else held.delete(code); updateButtons(); }
function updateButtons(){if(!nes)return;for(const button of new Set(Object.values(keys))) {const down=[...held].some(k=>keys[k]===button)||padHeld.has(button);nes[down?'buttonDown':'buttonUp'](1,button);}}
window.addEventListener('keydown',e=>{if(e.target instanceof HTMLInputElement||e.target instanceof HTMLButtonElement)return;if(e.code in keys){e.preventDefault();key(e.code,true);}});
window.addEventListener('keyup',e=>key(e.code,false));
window.addEventListener('blur',()=>{held.clear();padHeld.clear();updateButtons();});
for(const button of document.querySelectorAll('[data-key]')){button.onpointerdown=e=>{button.setPointerCapture(e.pointerId);key(button.dataset.key,true)};button.onpointerup=button.onpointercancel=()=>key(button.dataset.key,false);}
const context=$('original').getContext('2d'), image=context.createImageData(256,240);
function paint(pixels){for(let i=0;i<pixels.length;i++){const c=pixels[i],j=i*4;image.data[j]=c&255;image.data[j+1]=(c>>8)&255;image.data[j+2]=(c>>16)&255;image.data[j+3]=255;}context.putImageData(image,0,0);}
async function load(bytes,name){
 const hash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
 const data=new Uint8Array(bytes);inspectRom(data);
 const next=new NES({emulateSound:true,sampleRate:44100,onFrame:paint,onAudioSample:(l,r)=>{if(audioNode&&running){samples.push(l,r);if(samples.length>=2048){audioNode.port.postMessage({samples:Float32Array.from(samples)});samples=[];}}}});
 next.loadROM(data);const extraction=new RomAssetExtractor(next,data);
 running=false;renderer.dispose();renderer=new SourceRenderer($('world'));resize();nes=next;extractor=extraction;frame=null;held.clear();padHeld.clear();setRomHash(hash);sourceInfo={name,sha256:hash,mapper:(data[6]>>4)|(data[7]&240),prgBanks:data[4],chrBanks:data[5],profile:'prototype',scope:'PPU source tiles and original simulation; no semantic game adapter'};
 try{await renderer.reloadAssets();$('status').textContent=`${name} · ${renderer.getStats().loadedAssets} Blender candidate tiles loaded`;}catch(error){$('status').textContent=`${name} · extracted source fallback active · ${error.message}`;}
 running=true;$('pause').textContent='Pause';return sourceInfo;
}
$('rom').onchange=async e=>{const file=e.target.files[0];if(!file)return;try{await load(await file.arrayBuffer(),file.name)}catch(error){$('status').textContent=error.message;}};
$('pause').onclick=()=>{running=!running;$('pause').textContent=running?'Pause':'Resume';audioNode?.port.postMessage({flush:true});};
$('view').onclick=()=>{originalVisible=!originalVisible;$('original').hidden=!originalVisible;$('world').hidden=originalVisible;$('view').textContent=originalVisible?'Show reconstruction':'Show original';if(!originalVisible)resize();};
$('light').onclick=()=>{const day=renderer.mode!=='day';renderer.setLighting(day?'day':'source');$('light').textContent=day?'Studio lighting':'Source colors';};
$('reload').onclick=async()=>{try{await renderer.reloadAssets();$('status').textContent=`Reloaded ${renderer.getStats().loadedAssets} candidate tiles. Prototype only.`;}catch(e){$('status').textContent=`Reload rejected; previous assets preserved: ${e.message}`;}};
$('audio').onclick=async()=>{try{if(!audioContext){audioContext=new AudioContext({sampleRate:44100});await audioContext.audioWorklet.addModule(new URL('./audio-worklet.js',import.meta.url));audioNode=new AudioWorkletNode(audioContext,'nes-audio',{outputChannelCount:[2]});audioNode.connect(audioContext.destination);}await audioContext.resume();$('audio').textContent='Audio enabled';}catch(e){$('status').textContent=`Audio unavailable: ${e.message}`;}};
$('capture').onclick=()=>{if(!frame)return;const blob=new Blob([JSON.stringify({source:sourceInfo,frame},(_k,v)=>ArrayBuffer.isView(v)?Array.from(v):v)],{type:'application/json'});const link=document.createElement('a');link.href=URL.createObjectURL(blob);link.download='observed-capture.json';link.click();setTimeout(()=>URL.revokeObjectURL(link.href),1000);};
function resize(){const box=$('world').parentElement.getBoundingClientRect();renderer.resize(box.width,box.height);}new ResizeObserver(resize).observe($('world').parentElement);
function gamepad(){padHeld.clear();const pad=Array.from(navigator.getGamepads?.()||[]).find(Boolean);if(pad){for(const [index,button]of [[0,0],[1,1],[8,2],[9,3],[12,4],[13,5],[14,6],[15,7]])if(pad.buttons[index]?.pressed)padHeld.add(button);if(pad.axes[0]<-.4)padHeld.add(6);if(pad.axes[0]>.4)padHeld.add(7);if(pad.axes[1]<-.4)padHeld.add(4);if(pad.axes[1]>.4)padHeld.add(5);}updateButtons();}
let previous=performance.now(),accumulator=0, tick=0;
function animate(now){const delta=Math.min(now-previous,100);previous=now;if(running&&nes){accumulator+=delta;gamepad();try{let steps=0;while(accumulator>=1000/60&&steps++<4){nes.frame();accumulator-=1000/60;}frame=extractor.getFrame();if(frame){if(!originalVisible)renderer.update(frame);if(tick++%30===0)$('inspect').textContent=JSON.stringify({...sourceInfo,coverage:renderer.getStats(),exampleSource:frame.assets[0]?.romSources,observedVariants:extractor.assets.size},null,2);}}catch(e){running=false;$('status').textContent=`Emulation stopped: ${e.message}`;}}else accumulator=0;requestAnimationFrame(animate);}requestAnimationFrame(animate);
// Local diagnostic API for repeatable smoke tests; never fetches or bundles a ROM.
window.agarstra={load,step(count=1){for(let i=0;i<count;i++)nes.frame();frame=extractor.getFrame();renderer.update(frame);return renderer.getStats();},pause(){running=false;},button:key,get stats(){return renderer.getStats()},get frame(){return frame},get source(){return sourceInfo},verify(){return renderer.verifySourcePixels(nes.ppu.buffer)}};
