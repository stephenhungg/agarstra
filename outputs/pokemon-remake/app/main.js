import './style.css';
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {createTown} from './town.js';
import {createAvatar} from './avatar.js';
import {createCharacters} from './characters.js';
import {createGameCamera} from './game-camera.js';
import {createRoute1} from './route1.js';
import {createDialogOverlay} from './dialog.js';
import {createBattle} from './battle.js';
import {createInteriors} from './interiors.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
import {HDRLoader} from 'three/addons/loaders/HDRLoader.js';
const el=id=>document.getElementById(id);
const renderer=new THREE.WebGLRenderer({canvas:el('world'),antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.05;renderer.shadowMap.enabled=true;renderer.shadowMap.type=THREE.PCFSoftShadowMap;
const scene=new THREE.Scene();scene.background=new THREE.Color('#d9ded0');const camera=new THREE.PerspectiveCamera(35,1,.1,200);const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.maxPolarAngle=Math.PI*.49;controls.minDistance=4;controls.maxDistance=40;
function resetCamera(){camera.position.set(12,9,14);controls.target.set(0,3,0);controls.update()}resetCamera();
const pmrem=new THREE.PMREMGenerator(renderer);scene.environment=pmrem.fromScene(new RoomEnvironment(),.04).texture;scene.environmentIntensity=.65;pmrem.dispose();
const sun=new THREE.DirectionalLight('#fff1da',3);sun.position.set(-9,15,8);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);Object.assign(sun.shadow.camera,{left:-12,right:12,top:12,bottom:-12,near:1,far:50});sun.shadow.bias=-.00015;sun.shadow.normalBias=.018;scene.add(sun);scene.add(new THREE.HemisphereLight('#d9e6f1','#a0a58c',.4));
const ground=new THREE.Mesh(new THREE.PlaneGeometry(200,200),new THREE.MeshStandardMaterial({color:'#d9ded0',roughness:1}));ground.rotation.x=-Math.PI/2;ground.receiveShadow=true;scene.add(ground);
const gameplayCamera=createGameCamera(renderer.domElement);
let route1=null,avatar=null;
const characters=createCharacters();scene.add(characters.group);characters.group.visible=false;
let forceOriginal=false,autoPaused=false,notice='',noticeUntil=0;
function showNotice(text){notice=text;noticeUntil=performance.now()+3000;el('play-status').textContent=text;}
let town=null,battle=null,interiors=null,dialog=null,candidates=null,viewMode='town',reviewing=false;
let asset=null,assetReport=null,core=null,audio=null,observer=null,paused=false,sound=false,ready=false,keys=0,error=null,last=performance.now(),accum=0;
async function loadAsset(){try{candidates=await(await fetch(new URL('runtime-candidates.json',document.baseURI))).json();const file=candidates.cottage.file;const response=await fetch(new URL(`models/${file}`,document.baseURI));if(!response.ok)throw Error('Cottage asset unavailable');const data=await response.arrayBuffer();const sha256=[...new Uint8Array(await crypto.subtle.digest('SHA-256',data))].map(v=>v.toString(16).padStart(2,'0')).join('');if(sha256!==candidates.cottage.sha256)throw Error('Candidate asset hash mismatch');const gltf=await new GLTFLoader().parseAsync(data,'');asset=gltf.scene;asset.updateMatrixWorld(true);const box=new THREE.Box3().setFromObject(asset),size=box.getSize(new THREE.Vector3()),center=box.getCenter(new THREE.Vector3());const scale=7/size.y;asset.scale.setScalar(scale);asset.position.set(-center.x*scale,-box.min.y*scale,-center.z*scale);let meshes=0,triangles=0,maps=0;asset.traverse(o=>{if(o.isMesh){meshes++;triangles+=(o.geometry.index?.count||o.geometry.attributes.position.count)/3;o.castShadow=true;o.receiveShadow=true;for(const mat of Array.isArray(o.material)?o.material:[o.material]){if(mat.map){maps++;mat.map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy())}}}});scene.add(asset);assetReport={file,sha256,version:candidates.cottage.version,status:candidates.cottage.status,meshes,triangles,maps,bounds:size.toArray(),clips:gltf.animations.map(a=>a.name)};el('asset').textContent=`Cottage v${candidates.cottage.version} · ${Math.round(triangles).toLocaleString()} triangles`;el('asset-message').hidden=true;}catch(e){error=e.message;el('asset-message').textContent=`Asset loading failed: ${e.message}`;el('asset').textContent='Candidate unavailable';console.error(e);}}
const daylightLoad=new HDRLoader().loadAsync(new URL('daylight/daylight.hdr',document.baseURI).href).then(hdr=>{
  const generator=new THREE.PMREMGenerator(renderer);const target=generator.fromEquirectangular(hdr);
  scene.environment.dispose();scene.environment=target.texture;scene.environmentIntensity=.55;hdr.dispose();generator.dispose();
}).catch(e=>console.error('Outdoor lighting unavailable',e));
const assetLoad=loadAsset();
const townLoad=assetLoad.then(async()=>{if(!asset)return;town=await createTown(renderer,asset,candidates);scene.add(town.group);town.group.visible=false;setView('town')}).catch(e=>{error=`Town assets: ${e.message}`;el('asset-message').hidden=false;el('asset-message').textContent=error;console.error(e);});
function setView(mode){viewMode=mode;if(asset)asset.visible=mode==='asset';if(town)town.group.visible=mode==='town';ground.visible=mode==='asset';controls.maxDistance=mode==='town'?70:40;sun.position.set(mode==='town'?0:-9,mode==='town'?24:15,mode==='town'?20:8);sun.target.position.set(mode==='town'?12:0,0,mode==='town'?10:0);scene.add(sun.target);const b=mode==='town'?22:12;Object.assign(sun.shadow.camera,{left:-b,right:b,top:b,bottom:-b,far:80});sun.shadow.camera.updateProjectionMatrix();if(mode==='town'){camera.position.set(27,30,40);controls.target.set(11.5,0,9.5)}else{resetCamera()}controls.update();el('view').textContent=mode==='town'?'Inspect cottage':'Show town';el('scene-title').textContent=mode==='town'?'Pallet Town, from the source.':'A place worth returning to.';el('scene-caption').textContent=mode==='town'?'Arrows move · X interact · drag to look, release to return':'Inspect the real exported mesh. Drag to orbit · scroll to inspect.';}
el('view').onclick=()=>{setView(viewMode==='town'?'asset':'town');paint();};
async function loadCheckpoint(name='pallet-town',{redraw=true}={}){if(!['pallet-town','post-starter-pallet','post-starter-ready','route1-entry','first-battle','first-attack'].includes(name))throw Error('Unknown checkpoint');pause(true);keys=0;const r=await fetch(new URL(`core/checkpoints/${name}.state`,document.baseURI));if(!r.ok)throw Error('Pallet checkpoint unavailable');core.loadState(new Uint8Array(await r.arrayBuffer()));if(redraw)core.step(1,0);gameplayCamera.reset();paint();pause(false);}
el('checkpoint').hidden=false;el('checkpoint').onclick=()=>loadCheckpoint(el('checkpoint-select').value);
el('show-source').onclick=()=>{document.body.classList.toggle('show-source');resize();};
const nativeContext=el('live-native').getContext('2d');
const sourceContext=el('source').getContext('2d');const image=new ImageData(240,160);
function paint(){
  if(!core)return;
  image.data.set(core.pixels());sourceContext.putImageData(image,0,0);nativeContext.putImageData(image,0,0);
  el('frame').textContent=`Frame ${core.frame.toLocaleString()} · ${paused?'paused':'running'}`;
  if(!observer)return;
  const state=observer(core),inBattle=Boolean(state.battle.active&&viewMode==='town');
  const inRoute=Boolean(!inBattle&&viewMode==='town'&&state.map?.name==='Route1'&&route1);
  const inInterior=Boolean(!inBattle&&viewMode==='town'&&interiors?.supports(state.map?.name));
  if(route1){route1.setPlayerModelVisible(Boolean(avatar));route1.group.visible=inRoute;if(inRoute)route1.update(state);}
  if(interiors){interiors.setVisible(inInterior);if(inInterior)interiors.update(core,state);}
  if(battle){battle.update(core,state);battle.setVisible(inBattle);}
  controls.enabled=viewMode==='asset'&&!reviewing;
  town?.setPlayerModelVisible(Boolean(avatar));interiors?.setPlayerModelVisible(Boolean(avatar));
  if(town&&viewMode==='town'&&!inBattle&&!inInterior&&!inRoute){
    town.update(state);town.group.visible=true;
    const supported=state.map?.name==='PalletTown';el('coverage').hidden=supported;
    el('coverage').textContent=`3D scene not built for ${state.map?.name||'this game state'}. Showing the last Pallet Town view. The original game and dialog continue; source view is available above.`;
  }else{if(town)town.group.visible=false;el('coverage').hidden=true;}
  let dialogState=null;
  if(dialog){dialogState=dialog.update(core,state);dialog.setVisible(viewMode!=='asset');}
  document.querySelector('.look footer').hidden=Boolean(inBattle||dialogState?.dialog);
  el('state').textContent=inBattle?'Battle':state.map?.name||'Opening / menus';
  const unsupported=state.map?.name!=='PalletTown'&&!inInterior&&!inBattle&&!inRoute;
  const native=forceOriginal||(viewMode==='town'&&(unsupported||state.phase==='transition-or-menu'));
  el('live-native').hidden=!native;document.querySelector('.look').classList.toggle('native-active',native);
  if(dialog)dialog.setVisible(!native&&viewMode!=='asset');if(native&&battle)battle.setVisible(false);
  el('play-status').textContent=performance.now()<noticeUntil?notice:paused?'Paused':native?'Original graphics · gameplay continues':inBattle?'Battle':inInterior?'Inside':'Exploring';
  el('resume-overlay').hidden=!paused||reviewing;
  avatar?.update(state,{visible:!native&&!inBattle&&viewMode==='town'&&state.player?.graphicsId===0,groundHeight:inInterior?0:-.005});
  town?.setSourceCharactersVisible(true);route1?.setSourceCharactersVisible(true);interiors?.setSourceCharactersVisible(true);
  characters.update(core,state,{visible:!native&&!inBattle&&viewMode==='town',playerModelVisible:Boolean(avatar?.group.visible),modelGraphicsIds:inInterior?[92,94]:[],groundHeight:o=>inInterior?(o.graphicsId===92?.82:o.graphicsId===94?.78:0):-.005});
  gameplayCamera.setEnabled(viewMode==='town'&&!inBattle&&!native);
  if(viewMode==='town'&&!inBattle)gameplayCamera.update(state,{interior:inInterior});
  if(viewMode==='town'){el('scene-title').textContent=inBattle?'A battle from the cartridge.':inInterior?'Inside Pallet Town.':inRoute?'Route 1.':'Pallet Town, from the source.';}
}
function pause(value=!paused){paused=value;if(!paused&&sound)audio?.resume();accum=0;if(paused)audio?.pause();el('pause').textContent=paused?'Resume':'Pause';paint();}
el('pause').onclick=()=>pause();el('reset-camera').onclick=()=>{setView(viewMode);paint();};el('sound').onclick=async()=>{sound=!sound;if(sound)await audio.resume();else audio.pause();el('sound').textContent=sound?'Sound on':'Sound off'};
el('resume-overlay').onclick=()=>{autoPaused=false;pause(false);el('world').focus();};
el('play-town').onclick=async()=>{setView('town');forceOriginal=false;await loadCheckpoint('post-starter-ready');el('world').focus();};
el('play-battle').onclick=async()=>{setView('town');forceOriginal=false;await loadCheckpoint('first-battle');el('world').focus();};
el('original-toggle').onclick=()=>{forceOriginal=!forceOriginal;el('original-toggle').textContent=forceOriginal?'3D view':'Original view';paint();};
el('quick-save').onclick=async()=>{try{await window.nativeROM.saveProgress(core.saveState());showNotice('Progress saved');}catch(e){showNotice(e.message);}};
el('quick-load').onclick=async()=>{try{const saved=await window.nativeROM.loadProgress();if(!saved){showNotice('No saved progress yet');return;}pause(true);keys=0;core.loadState(saved.bytes);core.step(1,0);setView('town');pause(false);el('world').focus();}catch(e){showNotice(e.message);}};
const keymap={KeyX:1,Space:1,KeyZ:2,ShiftLeft:4,ShiftRight:4,Enter:8,ArrowRight:16,ArrowLeft:32,ArrowUp:64,ArrowDown:128,KeyS:256,KeyA:512};
addEventListener('keydown',e=>{if(e.target.closest?.('select,input,textarea'))return;if(e.code==='KeyP'&&!e.repeat){pause();e.preventDefault()}if(keymap[e.code]){keys|=keymap[e.code];e.preventDefault()}});addEventListener('keyup',e=>{if(keymap[e.code]){keys&=~keymap[e.code];e.preventDefault()}});addEventListener('blur',()=>{keys=0;if(core&&!reviewing&&!paused){autoPaused=true;pause(true)}});addEventListener('focus',()=>{if(autoPaused){autoPaused=false;pause(false)}});
function resize(){const c=el('world'),w=c.clientWidth,h=c.clientHeight;renderer.setSize(w,h,false);camera.aspect=w/h;camera.updateProjectionMatrix();battle?.resize(w,h);interiors?.resize(w,h);route1?.resize(w,h);gameplayCamera.resize(w,h)}addEventListener('resize',resize);resize();
function activeCamera(){return viewMode==='asset'?camera:battle?.group.visible?battle.camera:gameplayCamera.camera;}
function frame(now){const dt=Math.min((now-last)/1000,.1);last=now;if(core&&!paused){accum+=dt;let steps=0;while(accum>=1/core.fps&&steps++<6){const r=core.step(1,keys);if(sound)audio.push(r.audio);accum-=1/core.fps;}paint()}gameplayCamera.tick(dt);if(controls.enabled)controls.update();renderer.render(scene,activeCamera());requestAnimationFrame(frame)}requestAnimationFrame(frame);
async function init(){try{for(const b of document.querySelectorAll('.playbar button'))b.disabled=true;const {bytes,sha1}=await window.nativeROM.load();const {createGbaCore,GbaAudio}=await import(/* @vite-ignore */new URL('core/browser-core.mjs',document.baseURI).href);core=await createGbaCore(bytes);audio=new GbaAudio();el('hash').textContent=`${sha1.slice(0,12)}… verified`;el('rom-status').textContent='LOCAL ROM VERIFIED';core.step(800);observer=(await import(/* @vite-ignore */new URL('core/firered-state.mjs',document.baseURI).href)).readFireRedState;await townLoad;await daylightLoad;battle=await createBattle(renderer);scene.add(battle.group);battle.setVisible(false);interiors=await createInteriors(renderer);scene.add(interiors.group);interiors.setVisible(false);try{route1=await createRoute1(renderer);scene.add(route1.group);}catch(e){console.error('Route1 candidate unavailable',e);}if(candidates?.trainer){try{avatar=await createAvatar(renderer,candidates.trainer);scene.add(avatar.group);}catch(e){console.error(e);}}dialog=createDialogOverlay(document.querySelector('.look'));resize();await loadCheckpoint('post-starter-ready');paint();ready=true;for(const b of document.querySelectorAll('.playbar button'))b.disabled=false;el('world').focus();}catch(e){error=e.message;el('rom-status').textContent=error;el('frame').textContent=error;console.error(e)}}

async function captureScenario(name){
  setView('town');
  await loadCheckpoint(['first-battle','first-attack','route1-entry','post-starter-pallet'].includes(name)?name:'pallet-town');pause(true);
  if(name==='interior'){core.step(160,64);}
  if(name==='laboratory'){await loadCheckpoint('post-starter-ready');pause(true);core.step(160,64);}
  if(name==='dialog'){
    for(const [frames,mask] of [[40,32],[16,0],[3,64],[12,0],[3,1],[4,0],[200,0]])core.step(frames,mask);
  }
  if(name==='moves'){await loadCheckpoint('first-battle');pause(true);core.step(12,1);core.step(40,0);}
  paint();renderer.render(scene,activeCamera());return window.review.state;
}
async function verifyGameplayCamera(check){
  await loadCheckpoint('post-starter-pallet',{redraw:false});pause(true);
  const before=gameplayCamera.report;
  check('gameplay camera is orthographic with a north-up home angle',activeCamera().isOrthographicCamera&&!controls.enabled);
  const c=activeCamera(),p=observer(core).player;
  const center=new THREE.Vector3(p.worldX,0,p.worldY).project(c),north=new THREE.Vector3(p.worldX,0,p.worldY-1).project(c),east=new THREE.Vector3(p.worldX+1,0,p.worldY).project(c);
  check('source north projects up and east projects right without diagonal skew',north.y>center.y&&Math.abs(north.x-center.x)<1e-6&&east.x>center.x&&Math.abs(east.y-center.y)<1e-6);
  const route=await(await fetch(new URL('core/checkpoints/route1-entry.provenance.json',document.baseURI))).json();
  let replayFrame=route.startFrame;const start=core.frame;
  for(const input of route.inputs){const end=replayFrame+input.frames;if(end>start){core.step(end-Math.max(start,replayFrame),input.keys);paint();}replayFrame=end;}
  check('native walk from Pallet switches to Route 1 without reset',observer(core).map?.name==='Route1'&&core.frame===route.endFrame&&route1.group.visible&&!town.group.visible&&el('live-native').hidden,{frame:core.frame,map:observer(core).map?.name});
  check('home heading and zoom survive map transition',gameplayCamera.report.quaternion.every((v,i)=>Math.abs(v-before.quaternion[i])<1e-8)&&gameplayCamera.report.zoom===before.zoom);
  check('Route 1 uses source-positioned player model',avatar?.group.visible&&Math.abs(avatar.group.position.x-observer(core).player.worldX)<1e-6&&Math.abs(avatar.group.position.z-observer(core).player.worldY)<1e-6);
  const first=JSON.stringify(gameplayCamera.report);paint();paint();check('paused camera has no drift',JSON.stringify(gameplayCamera.report)===first);
  await loadCheckpoint('post-starter-ready');pause(true);core.step(160,64);paint();
  const labState=observer(core),props=labState.objectEvents.filter(o=>!o.hidden&&[92,94].includes(o.graphicsId));
  check('lab retains existing 3D props alongside source NPCs',labState.map?.name==='PalletTown_ProfessorOaksLab'&&props.length>0&&props.every(o=>interiors.report.actorPositions.some(a=>a.id===o.id&&a.visible))&&characters.report.actors.some(a=>!a.isPlayer&&a.visible),{map:labState.map?.name,props:props.length,npcs:characters.report.actors.length});
  await loadCheckpoint('pallet-town');pause(true);
}
async function verifyPresentation(check){
  await loadCheckpoint();pause(true);
  for(const [frames,mask] of [[40,32],[16,0],[3,64],[12,0],[3,1],[4,0]])core.step(frames,mask);
  paint();const partial=dialog.report()?.dialog?.text;
  check('partial source dialog rendered over town',partial==='A’s ho'&&!document.querySelector('.rom-dialog-card').hidden,{partial});
  core.step(200,0);paint();check('dialog completion follows source printer',dialog.report()?.dialog?.text==='A’s house',{text:dialog.report()?.dialog?.text});
  core.step(8,1);core.step(30,0);paint();check('native confirm dismisses dialog',!dialog.report()?.dialog);
  await loadCheckpoint('first-battle');pause(true);paint();
  check('battle routes to dedicated scene and camera',battle.group.visible&&!town.group.visible&&!interiors.group.visible&&activeCamera()===battle.camera);
  check('battle command menu renders native commands',battle.snapshot.menu?.mode==='actions'&&document.querySelectorAll('.rom-battle-option').length===4);
  check('battle health matches native RAM',JSON.stringify(battle.snapshot.battlers.map(b=>b.hp))==='[20,18]');
  core.step(12,1);core.step(40,0);paint();
  check('native Fight input opens rendered move menu',battle.snapshot.menu?.mode==='moves'&&document.querySelector('.rom-battle-options')?.textContent.includes('TACKLE'));
  // Replay starts at the exact saved frame: a redraw step would advance RNG.
  await loadCheckpoint('first-battle',{redraw:false});pause(true);
  const replay=await(await fetch(new URL('core/checkpoints/battle-verification.json',document.baseURI))).json();
  for(const segment of replay.attackInputs){core.step(segment.frames,segment.keys);paint();}
  check('integrated first attack resolves source HP',JSON.stringify(battle.snapshot.battlers.map(b=>b.hp))==='[11,14]',battle.snapshot.battlers.map(b=>b.hp));
  const held=core.frame;paint();paint();check('paused rendering does not step game',core.frame===held);
  await loadCheckpoint();pause(true);paint();
  check('checkpoint reset clears battle and dialog overlays',!battle.group.visible&&!interiors.group.visible&&town.group.visible&&!dialog.report()?.dialog);
  if(avatar){check('rigged trainer replaces player marker',avatar.group.visible&&avatar.report.skinnedMeshes>0&&!town.actorPositions.find(a=>a.id===observer(core).player.id)?.visible);const feetBefore=JSON.stringify(avatar.report.feet);core.step(12,16);paint();check('source movement selects walk clip and changes feet',avatar.report.clips.includes('walk')&&avatar.report.mode==='walk'&&JSON.stringify(avatar.report.feet)!==feetBefore,structuredClone(avatar.report));const heldAvatar=JSON.stringify(avatar.report);paint();paint();check('paused trainer pose is stable',JSON.stringify(avatar.report)===heldAvatar);await loadCheckpoint();pause(true);paint();check('trainer returns to idle on checkpoint reset',avatar.report.mode==='idle');}
}
window.review={get ready(){return ready},get state(){return {camera:{...gameplayCamera.report,active:viewMode==='asset'?'inspection':battle?.group.visible?'battle':'gameplay',orbitEnabled:controls.enabled},frame:core?.frame,paused,assetReport,error,characters:characters.report,avatar:avatar?.report,avatarPosition:avatar?.group.position.toArray(),avatarVisible:avatar?.group.visible,route1:route1?.report,route1Visible:route1?.group.visible,battle:battle?.report,battleState:battle?.snapshot?{active:battle.snapshot.active,menu:battle.snapshot.menu,battlers:battle.snapshot.battlers.map(({sprite,...mon})=>({...mon,sprite:sprite?{visible:sprite.visible,width:sprite.width,height:sprite.height,pixelHash:sprite.pixelHash}:null}))}:null,interiors:interiors?.report,dialog:dialog?.report(),semantic:observer&&core?observer(core):null}},pause,loadCheckpoint,captureScenario,advance(n,mask=0){pause(true);core.step(n,mask);paint();return this.state},async verify(){pause(true);await townLoad;reviewing=true;controls.enableDamping=false;controls.enabled=false;setView('town');await loadCheckpoint();pause(true);const checks=[];const check=(name,ok,detail)=>checks.push({name,ok,...(detail?{detail}: {})});check('verified FireRed running',core?.read32(0x080000ac)===0x45525042);const before=core.frame;core.step(5);check('original simulation steps exactly',core.frame===before+5);check('original pixels rendered',new Set(core.pixels()).size>16);const saved=core.saveState();core.step(2,16);const a=core.pixels();core.loadState(saved);core.step(2,16);check('source state replay deterministic',(()=>{const b=core.pixels();return a.every((v,i)=>v===b[i])})());paint();renderer.render(scene,activeCamera());check('WebGL renderer active',renderer.info.render.calls>0);check('actual textured cottage mesh loaded',Boolean(assetReport&&assetReport.meshes>0&&assetReport.maps>0),assetReport);check('Pallet Town checkpoint observed',observer(core).map?.name==='PalletTown');const posBefore=observer(core).player?.worldX;core.step(16,16);paint();const posAfter=observer(core).player?.worldX;check('controller input moves source player',Number.isFinite(posBefore)&&posAfter>posBefore,{before:posBefore,after:posAfter});const player=observer(core).player,display=avatar?.group.visible?avatar.group.position:town?.playerPosition;check('3D player follows source coordinates',!!display&&Math.abs(display.x-player.worldX)<.001&&Math.abs(display.z-player.worldY)<.001);check('generated tree loaded',town?.report.trees.loaded);const sourceActors=observer(core).objectEvents.filter(o=>!o.hidden);check('3D actors survive source viewport culling',sourceActors.every(o=>o.isPlayer&&avatar?avatar.group.visible:characters.report.actors.some(a=>a.id===o.id&&a.visible)),{sourceActors:sourceActors.length,renderedActors:characters.report.actors.filter(a=>a.visible).length});check('house doorway anchors match source warps',town.report.houses.every(h=>h.runtimeDoor&&Math.abs(h.runtimeDoor[0]-h.sourceDoor[0])<.001&&Math.abs(h.runtimeDoor[2]-h.sourceDoor[1])<.001));await loadCheckpoint();pause(true);core.step(160,64);paint();check('source door warp selects 3D house interior',observer(core).map?.name==='PalletTown_PlayersHouse_1F'&&interiors.group.visible&&!town.group.visible&&el('coverage').hidden,{map:observer(core).map?.name});await verifyPresentation(check);await verifyGameplayCamera(check);await loadCheckpoint();pause(true);const performanceSamples=[];const benchmarkStartFrame=core.frame,benchmarkStartTime=performance.now();paused=false;accum=0;let previousTime=performance.now();for(let i=0;i<250;i++){await new Promise(requestAnimationFrame);const now=performance.now();if(i>=10)performanceSamples.push(now-previousTime);previousTime=now;}pause(true);performanceSamples.sort((a,b)=>a-b);const performanceReport={cameraPosition:gameplayCamera.report.position,cameraTarget:gameplayCamera.report.target,mode:'live original simulation and town rendering',elapsedMs:performance.now()-benchmarkStartTime,simulationFrames:core.frame-benchmarkStartFrame,viewport:[renderer.domElement.width,renderer.domElement.height],pixelRatio:renderer.getPixelRatio(),samples:performanceSamples.length,medianFrameMs:performanceSamples[Math.floor(performanceSamples.length/2)],p95FrameMs:performanceSamples[Math.floor(performanceSamples.length*.95)],drawCalls:renderer.info.render.calls,triangles:renderer.info.render.triangles};return {performance:performanceReport,town:town?.report,passed:checks.every(c=>c.ok),checks,asset:assetReport,limitations:['Asset review stage; no photoreal acceptance yet','Pallet Town, Route 1, three interiors and first battle; NPCs, effects and remaining 3D game coverage are incomplete'],state:this.state}}};init();
