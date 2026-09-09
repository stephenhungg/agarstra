import * as THREE from 'three';
import {decodeCharacter,readVisibleWindows,cropSourcePixels} from '../runtime-core/firered-dialog.mjs';
import {createBattleModel} from './battle-model.js';
import './battle.css';

// FireRed US 1.0 / pret c75f3523. Read-only presentation; never advances the core.
const A={sprites:0x0202063c,matrices:0x02021bcc,coordX:0x02021bc8,coordY:0x02021bca,
  spriteIds:0x02023d44,positions:0x02023bd6,mons:0x02023be4,exec:0x02023bc8,
  buffer:0x02022bc4,actionCursor:0x02023ff8,moveCursor:0x02023ffc,controllers:0x03004fe0,
  speciesNames:0x08245ee0,moveNames:0x08247094,typeNames:0x0824f1a0,moves:0x08250c04,
  battleMenu:0x083fe725,safariMenu:0x083fe747,animActive:0x02037ee1,animMove:0x02037f18,animAttacker:0x02037f1a,animTarget:0x02037f1b};
const BATTLE_MAIN=0x08011100;
const CHARM_MODEL_SHA='ad78d6f71b421d5f3ce534806b2f816d160647be282276152dca03a25c6ce7e6';
const SOURCE_FPS=59.7275;
const sizes=[[[8,8],[16,16],[32,32],[64,64]],[[16,8],[32,8],[32,16],[64,32]],[[8,16],[8,32],[16,32],[32,64]]];
const signed16=n=>(n<<16)>>16;
const clamp=(n,a,b)=>Math.max(a,Math.min(b,n));
const controlArgs={1:1,2:1,3:1,4:3,5:1,6:1,7:0,8:1,9:0,10:0,11:2,12:1,13:1,14:1,15:0,16:2,17:1,18:1,19:1,20:1,21:0,22:0,23:0,24:0};

export function readRomText(core,address,length=32,menuSeparators=false){
  const bytes=core.readBytes(address,length);let text='';
  for(let i=0;i<bytes.length;i++){
    const b=bytes[i];if(b===0xff)break;
    if(b===0xfe){text+=menuSeparators?'|':'\n';continue;}
    if(b===0xfc){const op=bytes[++i],n=controlArgs[op];if(n===undefined)break;if(menuSeparators&&op===19)text+='|';i+=n;continue;}
    if(b===0xfd)break; // Do not invent unresolved substitutions.
    const ch=decodeCharacter(b);if(ch!==null)text+=ch;
  }
  return text.trim();
}
function nameOf(core,id,type){
  const move=type==='move',max=move?354:439;
  return id>0&&id<=max?readRomText(core,(move?A.moveNames:A.speciesNames)+id*(move?13:11),move?13:11):'';
}
function hashPixels(bytes){let h=2166136261;for(const n of bytes){h^=n;h=Math.imul(h,16777619);}return(h>>>0).toString(16).padStart(8,'0');}

export function readBattleSprite(core,spriteId,memory){
  if(!Number.isInteger(spriteId)||spriteId<0||spriteId>=64)return null;
  const bytes=memory?.sprites??core.readBytes(A.sprites,64*0x44),v=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),o=spriteId*0x44;
  const a0=v.getUint16(o,true),a1=v.getUint16(o+2,true),a2=v.getUint16(o+4,true),flags=bytes[o+0x3e];
  const shape=a0>>>14,size=a1>>>14,dimensions=sizes[shape]?.[size];
  if(!(flags&1)||!dimensions)return null;
  const [width,height]=dimensions,affine=(a0>>>8)&3,bpp8=!!(a0&0x2000),tileNumber=a2&1023,paletteNumber=a2>>>12;
  const visible=!(flags&4)&&affine!==2&&((a0>>>10)&3)!==2;
  const dw=width*(affine===3?2:1),dh=height*(affine===3?2:1),rgba=new Uint8ClampedArray(dw*dh*4);
  const vram=memory?.vram??core.readBytes(0x06010000,0x8000),palette=memory?.palette??core.readBytes(0x05000200,512);
  const oneD=!!((memory?.display??core.read16(0x04000000))&64),tileUnits=bpp8?2:1;
  let matrix=[256,0,0,256];
  if(affine&1){const index=(a1>>>9)&31,mat=memory?.matrices??core.readBytes(A.matrices,256),mv=new DataView(mat.buffer,mat.byteOffset,mat.byteLength);matrix=[0,2,4,6].map(n=>mv.getInt16(index*8+n,true));}
  let opaquePixels=0;
  for(let y=0;y<dh;y++)for(let x=0;x<dw;x++){
    let sx=x,sy=y;
    if(affine&1){sx=Math.floor((matrix[0]*(x-dw/2)+matrix[1]*(y-dh/2))/256+width/2);sy=Math.floor((matrix[2]*(x-dw/2)+matrix[3]*(y-dh/2))/256+height/2);}
    else{if(a1&0x1000)sx=width-1-sx;if(a1&0x2000)sy=height-1-sy;}
    if(sx<0||sy<0||sx>=width||sy>=height)continue;
    const tile=tileNumber+Math.floor(sy/8)*(oneD?(width/8)*tileUnits:32)+Math.floor(sx/8)*tileUnits;
    const addr=tile*32+(sy%8)*(bpp8?8:4)+(bpp8?sx%8:Math.floor((sx%8)/2));
    if(addr>=vram.length)continue;
    const idx=bpp8?vram[addr]:(vram[addr]>>>((sx&1)*4))&15;if(!idx)continue;
    const pi=(bpp8?idx:paletteNumber*16+idx)*2,color=palette[pi]|palette[pi+1]<<8,d=(y*dw+x)*4;
    rgba[d]=Math.round((color&31)*255/31);rgba[d+1]=Math.round(((color>>>5)&31)*255/31);rgba[d+2]=Math.round(((color>>>10)&31)*255/31);rgba[d+3]=255;opaquePixels++;
  }
  const coord=!!(flags&2),x=v.getInt16(o+0x20,true)+v.getInt16(o+0x24,true)+(coord?signed16(core.read16(A.coordX)):0),y=v.getInt16(o+0x22,true)+v.getInt16(o+0x26,true)+(coord?signed16(core.read16(A.coordY)):0);
  return{spriteId,visible,width:dw,height:dh,nativeWidth:width,nativeHeight:height,x,y,
    offsetX:v.getInt16(o+0x24,true),offsetY:v.getInt16(o+0x26,true),animation:bytes[o+0x2a],animationCommand:bytes[o+0x2b],
    tileNumber,paletteNumber,affine,matrix,rgba,opaquePixels,pixelHash:hashPixels(rgba),
    limitations:[...(a0&0x1000?['source OBJ mosaic not reconstructed']:[]),...(((a0>>>10)&3)===1?['OBJ blend equation not reconstructed']:[])],sourceAddress:A.sprites+o};
}

export function readBattlePresentation(core,state){
  if(!state?.battle?.active)return{active:false,frame:core.frame,battlers:[],menu:null};
  const windows=readVisibleWindows(core),exec=core.read32(A.exec),battleScreen=(state.callback2&~1)===BATTLE_MAIN;
  const memory={sprites:core.readBytes(A.sprites,64*0x44),vram:core.readBytes(0x06010000,0x8000),palette:core.readBytes(0x05000200,512),matrices:core.readBytes(A.matrices,256),display:core.read16(0x04000000)};
  const battlers=(state.battle.battlers||[]).map(mon=>{
    const position=core.read8(A.positions+mon.id),address=A.mons+mon.id*0x58;
    return{...mon,position,side:position&1?'opponent':'player',nickname:readRomText(core,address+0x30,11)||nameOf(core,mon.species,'species'),speciesName:nameOf(core,mon.species,'species'),
      pp:[0,1,2,3].map(i=>core.read8(address+0x24+i)),status:core.read32(address+0x4c),
      controller:core.read32(A.controllers+mon.id*4),command:core.read8(A.buffer+mon.id*512),commandActive:!!(exec&(1<<mon.id)),
      sprite:readBattleSprite(core,core.read8(A.spriteIds+mon.id),memory)};
  });
  const chooser=battlers.find(b=>b.side==='player'&&(exec&(1<<b.id))&&[18,20].includes(b.command));
  let menu=null;
  if(battleScreen&&chooser){
    const id=chooser.id,mode=chooser.command===18?'actions':'moves';
    // Controller bytes can precede DMA/display; require the native menu window.
    const nativeWindow=windows.find(w=>w.id===(mode==='actions'?2:3));
    if(nativeWindow){
      const cursor=core.read8((mode==='actions'?A.actionCursor:A.moveCursor)+id);
      if(mode==='actions'){
        const safari=!!(state.battle.flags&0x80),labels=readRomText(core,safari?A.safariMenu:A.battleMenu,safari?31:34,true).split('|').map(x=>x.trim()).filter(Boolean);
        menu={mode,battlerId:id,cursor,items:labels.map((label,index)=>({index,label})),nativeWindowId:nativeWindow.id};
      }else{
        const start=A.buffer+id*512+4,items=[0,1,2,3].map(index=>{
          const move=core.read16(start+index*2),type=move>0&&move<=354?core.read8(A.moves+move*12+2):null;
          return{index,move,label:nameOf(core,move,'move')||'—',pp:core.read8(start+8+index),maxPP:core.read8(start+12+index),type:type!==null&&type<18?readRomText(core,A.typeNames+type*7,7):null};
        });menu={mode,battlerId:id,cursor,items,nativeWindowId:nativeWindow.id};
      }
    }
  }
  const animation=readBattleAnimationSource(core),moveId=animation.moveId;
  return{active:true,frame:core.frame,battleScreen,battlers,menu,windows,
    animation,activeMove:animation.active?{id:moveId,name:nameOf(core,moveId,'move'),sourceAddress:A.animMove}:null,
    nativeMenuFallback:!battleScreen,source:'BPRE-0 / matching pret c75f3523'};
}

// DoMoveAnim / LaunchBattleAnimation in matching pret source set these exact
// globals. gDoingBattleAnim is a hit-blink/ball-throw flag, not a move signal.
export function readBattleAnimationSource(core){
  const moveId=core.read16(A.animMove),active=!!core.read8(A.animActive)&&moveId>0&&moveId<=354;
  return {active,moveId,attackerId:core.read8(A.animAttacker),targetId:core.read8(A.animTarget),power:active?core.read8(A.moves+moveId*12+1):0,sourceAddress:A.animActive};
}

// Edge detection uses only observed original frames and controller commands.
// Repeated paints never retrigger an action; rewinding a checkpoint clears it.
export function createBattleEventTracker(){
  let lastFrame=null,moveKey=null,commands=new Map();const poses=new Map();
  function update(data){
    if(!data.active||lastFrame!==null&&data.frame<lastFrame){moveKey=null;commands.clear();poses.clear();}
    lastFrame=data.frame;if(!data.active)return [];
    const events=[],animation=data.animation;
    function emit(battlerId,action,detail={}){
      const mon=data.battlers.find(b=>b.id===battlerId);if(!mon)return;
      const event={id:`${data.frame}:${battlerId}:${action}`,frame:data.frame,battlerId,species:mon.species,action,...detail};poses.set(battlerId,event);events.push(event);
    }
    const key=animation?.active?`${animation.moveId}:${animation.attackerId}:${animation.targetId}`:null;
    if(key&&key!==moveKey){
      const action=animation.power>0?'attack':animation.moveId===45?'growl':animation.moveId===39?'tailWhip':null;
      if(action)emit(animation.attackerId,action,{moveId:animation.moveId,targetId:animation.targetId,signal:'native-move-script'});
    }
    moveKey=key;
    const nextCommands=new Map();
    for(const mon of data.battlers){
      const command=mon.commandActive?mon.command:null;nextCommands.set(mon.id,command);
      if(command!==commands.get(mon.id)){
        if(command===41)emit(mon.id,'hit',{signal:'CONTROLLER_HITANIMATION'});
        if(command===10)emit(mon.id,'faint',{signal:'CONTROLLER_FAINTANIMATION'});
      }
      if(poses.get(mon.id)?.species!==mon.species)poses.delete(mon.id);
    }
    commands=nextCommands;return events;
  }
  return {update,poseFor:id=>poses.get(id)??null};
}

export async function createBattle(renderer){
  let registry={species:{4:{file:'charmander-existing-v2.glb',sha256:CHARM_MODEL_SHA,height:3.5,clips:{idle:'idle'},status:'existing-candidate'}}},registryError=null;
  try{
    const response=await fetch(new URL('runtime-candidates.json',document.baseURI));
    if(!response.ok)throw Error(`Battle registry unavailable: ${response.status}`);
    const manifest=await response.json();if(manifest.battle)registry=manifest.battle;
  }catch(error){registryError=error.message;}
  const group=new THREE.Group();group.name='BattleSourcePresentation';group.visible=false;
  const camera=new THREE.OrthographicCamera(-12,12,8,-8,.1,100);camera.position.set(0,8,18);camera.lookAt(0,1.8,0);camera.updateMatrixWorld(true);
  const forward=new THREE.Vector3();camera.getWorldDirection(forward);
  const right=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,0),up=new THREE.Vector3().setFromMatrixColumn(camera.matrixWorld,1),center=new THREE.Vector3(0,2.7,0);
  const ground=new THREE.Mesh(new THREE.CylinderGeometry(16,16,.5,80),new THREE.MeshStandardMaterial({color:'#86947d',roughness:.97}));ground.position.y=-.4;ground.receiveShadow=true;group.add(ground);
  const patches=[];
  for(const [x,z,r] of [[-4,3,3.1],[4,-3,2.7]]){
    const patch=new THREE.Mesh(new THREE.CylinderGeometry(r,r+.18,.08,64),new THREE.MeshStandardMaterial({color:'#b0b99b',roughness:1}));patch.position.set(x,-.08,z);patch.receiveShadow=true;group.add(patch);patches.push(patch);
  }
  const hemisphere=new THREE.HemisphereLight('#edf2e4','#4f604c',1.6);group.add(hemisphere);
  const sun=new THREE.DirectionalLight('#fff0d8',2);sun.position.set(-6,10,7);group.add(sun);
  const root=document.createElement('section');root.className='rom-battle-hud';root.hidden=true;root.setAttribute('aria-label','Original battle presentation');
  root.innerHTML='<div class="rom-battle-quality">SOURCE SPRITE CANDIDATES · RIGGED 3D CREATURES PENDING</div><div class="rom-battle-health"></div><div class="rom-battle-move" hidden></div><div class="rom-battle-menu" hidden><div class="rom-battle-menu-heading"></div><div class="rom-battle-options" role="list"></div><div class="rom-battle-menu-note"></div></div><div class="rom-battle-native" hidden><div>ORIGINAL GAME MENU</div><canvas width="240" height="160"></canvas></div><canvas class="rom-battle-menu-fallback" hidden></canvas>';
  (renderer.domElement.parentElement??document.body).appendChild(root);
  const quality=root.querySelector('.rom-battle-quality'),health=root.querySelector('.rom-battle-health'),menuEl=root.querySelector('.rom-battle-menu'),heading=root.querySelector('.rom-battle-menu-heading'),options=root.querySelector('.rom-battle-options'),note=root.querySelector('.rom-battle-menu-note'),moveEl=root.querySelector('.rom-battle-move'),native=root.querySelector('.rom-battle-native'),nativeCanvas=native.querySelector('canvas'),fallback=root.querySelector('.rom-battle-menu-fallback');
  const actors=new Map(),cards=new Map();let last=null,enabled=true,lastHealth='',lastMenu='',disposed=false,lastCore=null,lastSourceState=null;
  const slots=new Map(),eventTracker=createBattleEventTracker();let arenaModel=null;
  const report={status:'candidate',source:'Live FireRed OBJ VRAM, palette, sprite transforms and battle RAM',updates:0,sourceFrames:0,
    registryError,registeredSpecies:Object.keys(registry.species??{}).map(Number),models:{},arena:{status:registry.arena?'loading':'unconfigured'},events:[],
    modelLoadStatus:'unrequested',modelError:null,creatureModel:null,modelBattlerId:null,
    limitations:['Only registered species use candidate 3D assets; missing or rejected assets keep live source sprites.','Authored clips respond to observed native move-script and hit/faint controller edges; clip motion is presentation only.','An update starting midway through an animation cannot recover unobserved earlier event time.','Source affine deformation, palette flashes and separate attack-effect sprites/background effects are not rebuilt for models.','Native party/bag menus use exact source pixels.'],
    modelCredit:['Charmander original rig by Milos Cerny http://www.miloscerny.com/','Charmander original model by Guilherme Lauck https://sketchfab.com/guilauck'],modelLicense:'See individual registry asset licenses; existing Charmander CC BY-NC 4.0'};
  const modelURL=config=>new URL(`models/${config.file}`,document.baseURI).href;
  if(registry.arena){
    const config=registry.arena;
    createBattleModel(renderer,{url:modelURL(config),sha256:config.sha256,clips:{}}).then(model=>{
      if(disposed){model.dispose();return;}
      model.group.scale.setScalar(config.scale??1);model.group.position.fromArray(config.position??[0,0,0]);group.add(model.group);arenaModel=model;
      ground.visible=false;for(const patch of patches)patch.visible=false;report.arena={status:'ready',model:model.report};
    }).catch(error=>{report.arena={status:'failed',error:error.message};});
  }
  function requestCreatureModel(mon){
    const config=registry.species?.[mon.species];if(!config)return null;
    const previous=slots.get(mon.id);if(previous?.species===mon.species)return previous;
    if(previous){previous.model?.dispose();previous.group.removeFromParent();}
    const slot={species:mon.species,config,group:new THREE.Group(),model:null,status:'loading'};
    slot.group.name=`Battler ${mon.id} species ${mon.species} candidate`;slot.group.visible=false;group.add(slot.group);slots.set(mon.id,slot);
    report.models[mon.id]={species:mon.species,file:config.file,status:'loading'};
    createBattleModel(renderer,{url:modelURL(config),sha256:config.sha256,clips:config.clips??{idle:'idle',attack:'attack',hit:'hit',faint:'faint',growl:'growl',tailWhip:'tailWhip'}}).then(model=>{
      if(disposed||slots.get(mon.id)!==slot){model.dispose();return;}
      const scale=(config.height??({1:2.5,4:3.5,7:2.7}[mon.species]??3))/model.report.height;
      model.group.scale.setScalar(scale);model.group.position.y=model.report.groundOffset*scale;
      model.group.rotation.y=config.facingOffset??0;slot.group.add(model.group);slot.model=model;slot.status='ready';
      report.models[mon.id]={species:mon.species,file:config.file,status:'ready',model:model.report};
      // A GLB may finish loading while the source is paused. Repaint its latest
      // observed frame without stepping the ROM or replaying a stale snapshot.
      if(lastCore&&lastSourceState&&lastCore.frame===lastSourceState.frame)update(lastCore,lastSourceState);
    }).catch(error=>{if(slots.get(mon.id)!==slot)return;slot.status='failed';slot.error=error.message;report.models[mon.id]={species:mon.species,file:config.file,status:'failed',error:error.message};});
    return slot;
  }
  function animateModel(slot,mon,frame){
    const event=eventTracker.poseFor(mon.id),duration=slot.model.report.availableActions[event?.action]?.duration;
    const elapsed=event?Math.max(0,frame-event.frame)/SOURCE_FPS:0;
    if(event&&duration&&(event.action==='faint'||elapsed<duration))slot.model.setPose(event.action,elapsed,{loop:false});
    else slot.model.setTime(Math.max(0,frame)/SOURCE_FPS);
    slot.model.report.event=event;slot.model.report.nativeFrame=frame;
  }
  function actorFor(id){
    if(actors.has(id))return actors.get(id);
    const canvas=document.createElement('canvas'),texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.magFilter=THREE.NearestFilter;texture.minFilter=THREE.NearestFilter;texture.generateMipmaps=false;
    // The source cutout is already a screen-space sprite; draft terrain must
    // not slice it in half where its billboard intersects the ground plane.
    const material=new THREE.SpriteMaterial({map:texture,transparent:true,alphaTest:.01,depthTest:false,depthWrite:false,toneMapped:false});const sprite=new THREE.Sprite(material);sprite.renderOrder=10+id;group.add(sprite);
    const actor={canvas,texture,sprite,hash:null};actors.set(id,actor);return actor;
  }
  function update(core,state){
    if(disposed)return null;
    lastCore=core;lastSourceState=state;
    const data=readBattlePresentation(core,state);last=data;root.hidden=!enabled||!data.active;group.visible=enabled&&data.active;
    const events=eventTracker.update(data);report.events.push(...events);if(report.events.length>128)report.events.splice(0,report.events.length-128);
    for(const slot of slots.values())slot.group.visible=false;
    if(!data.active)return data;
    report.updates++;report.sourceFrames=data.frame;
    for(const mon of data.battlers)requestCreatureModel(mon);
    const present=new Set();
    for(const mon of data.battlers){const src=mon.sprite;if(!src)continue;present.add(mon.id);const actor=actorFor(mon.id);actor.sprite.visible=data.battleScreen&&src.visible&&src.opaquePixels>0;
      if(actor.hash!==src.pixelHash){actor.canvas.width=src.width;actor.canvas.height=src.height;actor.canvas.getContext('2d').putImageData(new ImageData(src.rgba,src.width,src.height),0,0);actor.texture.needsUpdate=true;actor.hash=src.pixelHash;}
      actor.sprite.scale.set(src.width*.082,src.height*.082,1);
      actor.sprite.position.copy(center).addScaledVector(right,(src.x-120)*.082).addScaledVector(up,(58-src.y)*.082).addScaledVector(forward,mon.side==='player'?-1:1);
      const slot=slots.get(mon.id);
      if(slot?.model&&slot.species===mon.species){
        slot.group.visible=actor.sprite.visible;actor.sprite.visible=false;animateModel(slot,mon,data.frame);
        // Keep original offsets and hide flags. Neither clip nor arena owns travel.
        slot.group.position.set(mon.side==='player'?-4:4,-.04,mon.side==='player'?3:-3).addScaledVector(right,src.offsetX*.082).addScaledVector(up,-src.offsetY*.082);
        slot.group.rotation.y=mon.side==='player'?Math.atan2(8,-6):Math.atan2(-8,6);
      }
    }
    for(const [id,a]of actors)if(!present.has(id))a.sprite.visible=false;
    const modeled=data.battlers.filter(mon=>slots.get(mon.id)?.model&&slots.get(mon.id).species===mon.species);
    const loading=[...slots.values()].some(slot=>slot.status==='loading'),failed=[...slots.values()].find(slot=>slot.status==='failed');
    report.modelBattlerId=modeled[0]?.id??null;report.creatureModel=modeled.length?slots.get(modeled[0].id).model.report:null;
    report.modelLoadStatus=modeled.length?'ready':loading?'loading':failed?'failed':'unrequested';report.modelError=failed?.error??null;
    quality.textContent=modeled.length?`3D CANDIDATES: ${modeled.map(mon=>mon.speciesName).join(' · ')}${modeled.length<data.battlers.length?' · REMAINING SOURCE SPRITES':''}`:loading?'SOURCE SPRITES · 3D CANDIDATES LOADING':'SOURCE SPRITE CANDIDATES';
    const healthKey=JSON.stringify(data.battlers.map(b=>[b.id,b.nickname,b.hp,b.maxHP,b.level,b.status,b.side]));
    if(healthKey!==lastHealth){lastHealth=healthKey;health.replaceChildren();cards.clear();for(const mon of data.battlers){if(!mon.maxHP||!mon.species)continue;const card=document.createElement('div');card.className=`rom-battle-card ${mon.side}`;card.dataset.battler=mon.id;card.style.setProperty('--slot',Math.floor(mon.position/2));const title=document.createElement('div');title.className='rom-battle-card-title';const name=document.createElement('strong');name.textContent=mon.nickname;const level=document.createElement('span');level.textContent=`Lv ${mon.level}`;title.append(name,level);const meter=document.createElement('div');meter.className='rom-battle-hp-track';const bar=document.createElement('div');const fraction=mon.maxHP?clamp(mon.hp/mon.maxHP,0,1):0;bar.style.width=`${fraction*100}%`;bar.style.background=fraction>.5?'#729d57':fraction>.2?'#c3a35b':'#b66151';meter.append(bar);const amount=document.createElement('div');amount.className='rom-battle-hp-value';amount.textContent=`HP ${mon.hp} / ${mon.maxHP}`;card.append(title,meter,amount);health.append(card);cards.set(mon.id,card);}}
    health.hidden=!data.battleScreen;
    const menuKey=JSON.stringify(data.menu);if(menuKey!==lastMenu){lastMenu=menuKey;menuEl.hidden=!data.menu;options.replaceChildren();if(data.menu){const m=data.menu;heading.textContent=m.mode==='moves'?'Choose a move':'Choose a command';for(const item of m.items){const option=document.createElement('div');option.className='rom-battle-option';option.setAttribute('role','listitem');option.dataset.selected=String(item.index===m.cursor);option.dataset.index=item.index;const label=document.createElement('span');label.textContent=item.label;option.append(label);if(m.mode==='moves'&&item.move){const pp=document.createElement('small');pp.textContent=`PP ${item.pp}/${item.maxPP}`;option.append(pp);}options.append(option);}const chosen=m.items[m.cursor];note.textContent=m.mode==='moves'?(chosen?.type?`${chosen.type} · `:'')+'Arrows select · X / Space confirm · Z back':'Arrows select · X / Space confirm';}}
    root.dataset.nativeBattleMenu=data.menu?.mode??'';
    moveEl.hidden=!data.activeMove?.name;moveEl.textContent=data.activeMove?.name??'';
    native.hidden=!data.nativeMenuFallback;
    if(data.nativeMenuFallback)nativeCanvas.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(core.pixels()),240,160),0,0);
    // Preserve nonstandard controller menus (e.g. targeting) without invented UI.
    const unknownMenu=!data.menu&&data.battleScreen&&data.windows.some(w=>[2,3,4,5,6,7].includes(w.id)&&w.y>=100);
    fallback.hidden=!unknownMenu;if(unknownMenu){const rect={x:0,y:112,width:240,height:48};fallback.width=240;fallback.height=48;fallback.getContext('2d').putImageData(new ImageData(cropSourcePixels(core,rect),240,48),0,0);}
    return data;
  }
  function resize(width,height){const aspect=Math.max(width,1)/Math.max(height,1),halfHeight=Math.max(6.8,9/aspect);camera.left=-halfHeight*aspect;camera.right=halfHeight*aspect;camera.top=halfHeight;camera.bottom=-halfHeight;camera.position.set(0,1.8,0).addScaledVector(forward,-Math.max(19.1,4+halfHeight*3.2));camera.far=Math.max(300,halfHeight*12);camera.updateProjectionMatrix();camera.updateMatrixWorld(true);}
  function setVisible(value){enabled=!!value;group.visible=enabled&&!!last?.active;root.hidden=!group.visible;}
  function dispose(){disposed=true;arenaModel?.dispose();for(const slot of slots.values())slot.model?.dispose();for(const a of actors.values()){a.texture.dispose();a.sprite.material.dispose();}group.traverse(o=>{if(o.isMesh){o.geometry.dispose();o.material.dispose();}});root.remove();group.removeFromParent();}
  return{group,camera,update,resize,setVisible,dispose,report,get snapshot(){return last;},get actorSnapshots(){return[...actors].map(([id,a])=>{const mon=last?.battlers.find(b=>b.id===id),slot=slots.get(id),modeled=!!slot?.model&&slot.species===mon?.species;return {id,species:mon?.species,visible:modeled?slot.group.visible:a.sprite.visible,position:(modeled?slot.group:a.sprite).position.toArray(),presentation:modeled?(slot.model.report.boneCount?'rigged-3d-candidate':'static-3d-candidate'):'source-sprite',clip:modeled?slot.model.report.selectedClip:null,sourceOffsets:mon?.sprite?{x:mon.sprite.offsetX,y:mon.sprite.offsetY}:null,pixelHash:a.hash};});}};
}
