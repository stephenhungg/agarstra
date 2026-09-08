import { fetchRegistry, parseVerifiedGLB } from "./production-gate.js";
import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {clone as cloneSkeleton} from 'three/addons/utils/SkeletonUtils.js';
import {Sky} from 'three/addons/objects/Sky.js';
import {mergeGeometries} from 'three/addons/utils/BufferGeometryUtils.js';

const PX=1/16, H=12, PITCH=Math.atan2(2.4,32);
const PRIORITY=['mario-hero','mario-body','question-block','used-block','brick-block','pipe-green','ground-grass','hill-green','bush','platform-coral','coin','goomba'];
const MAP={question:'question-block','used-block':'used-block',brick:'brick-block',pipe:'pipe-green',ground:'ground-grass',hill:'hill-green',bush:'bush',cloud:'cloud',coin:'coin',goomba:'goomba',koopa:'koopa-green',piranha:'piranha-plant',mushroom:'super-mushroom',flower:'fire-flower',leaf:'super-leaf',star:'star','bouncing-block':'question-block',platform:'platform-coral'};
const RUNTIME_IDS=new Set([...Object.values(MAP),...PRIORITY,'platform-blue','platform-cream','platform-green','koopa-red','one-up']);
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const SOURCE_FPS=60.0988;
const LOOPING_POSES=new Set(['idle','walk','run','bite']);

/** Animation is presentation of ROM state. No clip moves an actor in the level. */
export function sourceAnimationState(source){
 const state=source.state||'',speed=Math.abs(source.velocity?.x||0);
 if(source.dying||state==='killed'||state==='poof')return 'death';
 if(source.squashed||state==='squashed')return 'squash';
 if(['shelled','held','kicked'].includes(state))return 'shell';
 if(source.type==='player'&&source.inAir)return (source.velocity?.y||0)<0?'jump-rise':'jump-fall';
 if(source.type==='piranha')return speed>.05||Math.abs(source.velocity?.y||0)>.05||source.frame>0?'bite':'idle';
 if(speed>.08)return source.type==='player'&&speed>=2?'run':'walk';
 return 'idle';
}

export function createSourceAnimation(model,clips){
 const mixer=new THREE.AnimationMixer(model),actions=new Map();
 for(const clip of clips){const name=clip.name.toLowerCase().replace(/[_ ]+/g,'-');const action=mixer.clipAction(clip);action.setLoop(LOOPING_POSES.has(name)?THREE.LoopRepeat:THREE.LoopOnce,LOOPING_POSES.has(name)?Infinity:1);action.clampWhenFinished=!LOOPING_POSES.has(name);actions.set(name,action);}
 return {mixer,actions,current:null,requested:null,transitions:0,elapsed:0,initialized:false};
}

export function resetSourceAnimation(animation){
 animation.mixer.stopAllAction();animation.mixer.setTime(0);animation.current=null;animation.requested=null;animation.elapsed=0;animation.transitions=0;animation.initialized=false;
}

export function updateSourceAnimation(animation,source,dt){
 const requested=sourceAnimationState(source),fallbacks={run:['walk','idle'],walk:['run','idle'],'jump-rise':['jump','idle'],'jump-fall':['jump','idle'],death:['squash','idle'],squash:['death','idle'],shell:['idle'],bite:['idle'],idle:['walk']};
 const actual=[requested,...(fallbacks[requested]||[])].find(name=>animation.actions.has(name));
 if(!actual)return {state:requested,clip:null,time:0,available:[...animation.actions.keys()]};
 const action=animation.actions.get(actual),previous=animation.actions.get(animation.current);
 if(animation.current!==actual){
  action.reset().setEffectiveWeight(1).setEffectiveTimeScale(1).play();
  // Brief pose blends are measured in emulated time, so pausing freezes the blend too.
  if(previous&&animation.initialized&&dt>0)previous.crossFadeTo(action,['death','squash','shell'].includes(requested)?.05:.08,false);
  else {previous?.stop();action.fadeIn(0);}
  animation.current=actual;animation.transitions++;animation.initialized=true;
 }
 const speed=Math.abs(source.velocity?.x||0);action.setEffectiveTimeScale(actual==='walk'||actual==='run'?(speed>.08?clamp(speed/(actual==='run'?2.7:1.3),.35,2):0):1);
 const elapsed=Math.max(0,Number.isFinite(dt)?dt:0);animation.mixer.update(elapsed);animation.elapsed+=elapsed;animation.requested=requested;
 return {state:requested,clip:actual,time:action.time,duration:action.getClip().duration,transitions:animation.transitions,available:[...animation.actions.keys()]};
}

/** Use emulated frames, not display refresh rate; redraws and pause cannot animate. */
export function advanceSourceClock(clock,frame,dt=0){
 if(!Number.isFinite(frame)){const delta=clamp(Number.isFinite(dt)?dt:0,0,.05);clock.time+=delta;return {dt:delta,reset:false};}
 const reset=clock.frame!==null&&frame<clock.frame;
 const delta=clock.frame===null||reset?0:Math.max(0,frame-clock.frame)/SOURCE_FPS;
 if(reset)clock.time=0;clock.frame=frame;clock.time+=delta;
 return {dt:delta,reset};
}

export function unresolvedSourceObject(source,modelId,cameraX,reason='missing-model'){
 const x=Number(source.x)||0,y=Number(source.y)||0,width=Math.max(0,Number(source.width)||0),height=Math.max(0,Number(source.height)||0);
 const left=clamp(x-cameraX,0,256),top=clamp(y,0,192),right=clamp(x-cameraX+width,0,256),bottom=clamp(y+height,0,192);
 if(right<=left||bottom<=top)return null;
 return {id:source.id,type:source.type,modelId:modelId||null,reason,x,y,width,height,screenRect:{x:left,y:top,width:right-left,height:bottom-top},source:source.source||null,cells:source.cells||[]};
}

/** Derive a rigid-part rig only for the documented, unskinned mario-body kit.
 * The kit bakes anatomical coordinates into each mesh; attach() preserves those
 * world transforms while sleeves/gloves and trousers/boots acquire true joints.
 */
export function buildMarioBodyRig(model) {
 const buckets={left_arm:[],right_arm:[],left_leg:[],right_leg:[]};
 const localBounds=object=>{model.updateWorldMatrix(true,true);const box=new THREE.Box3().setFromObject(object);const inverse=model.matrixWorld.clone().invert();return box.applyMatrix4(inverse);};
 const candidates=[];model.traverse(o=>{if(o.isMesh&&!o.isSkinnedMesh)candidates.push(o);});
 for(const object of candidates){let limb;if(/^(Shirt_relaxed_sleeve|Glove_)/i.test(object.name))limb='arm';else if(/^(Denim_trouser_leg|Trouser_|Worn_boot_)/i.test(object.name))limb='leg';else continue;const bounds=localBounds(object),side=bounds.getCenter(new THREE.Vector3()).x<0?'left':'right';buckets[`${side}_${limb}`].push(object);}
 if(Object.values(buckets).some(parts=>parts.length===0))return null;
 const rig={limbs:{},model,phase:0,pose:'idle',partCount:0,localBounds};
 for(const [name,parts]of Object.entries(buckets)){
  const arm=name.endsWith('arm'),primary=parts.find(o=>(arm?/^Shirt_relaxed_sleeve/:/^Denim_trouser_leg/).test(o.name));if(!primary)return null;
  const bounds=localBounds(primary),center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3());const left=name.startsWith('left');
  // Sleeve root is the inner upper fifth; trouser root lies inside the waist overlap.
  const anchor=new THREE.Vector3(arm?(left?bounds.max.x-size.x*.25:bounds.min.x+size.x*.25):center.x,bounds.max.y-size.y*(arm?.20:.06),center.z);
  const joint=new THREE.Group();joint.name=`Runtime_${name}`;joint.position.copy(anchor);model.add(joint);model.updateWorldMatrix(true,true);
  for(const part of parts)joint.attach(part);
  model.updateWorldMatrix(true,true);rig.limbs[name]={joint,restPosition:joint.position.clone(),restRotation:joint.rotation.clone(),restMinY:localBounds(joint).min.y,angle:0,parts:parts.map(o=>o.name)};rig.partCount+=parts.length;
 }
 // Preserve articulation while batching identical materials inside each rigid part.
 rig.ownedGeometries=[];rig.drawMeshesBefore=candidates.length;
 const jointSet=new Set(Object.values(rig.limbs).map(l=>l.joint));
 function mergePart(target,meshes){
  target.updateWorldMatrix(true,true);const inverse=target.matrixWorld.clone().invert(),buckets=new Map();
  for(const object of meshes){if(Array.isArray(object.material))continue;const material=object.material;if(!material)continue;const bucket=buckets.get(material.uuid)||{material,objects:[],geometries:[]};bucket.objects.push(object);bucket.geometries.push(object.geometry.clone().applyMatrix4(inverse.clone().multiply(object.matrixWorld)));buckets.set(material.uuid,bucket);}
  for(const bucket of buckets.values()){
   if(bucket.objects.length<2){for(const g of bucket.geometries)g.dispose();continue;}
   const geometry=mergeGeometries(bucket.geometries,false);for(const g of bucket.geometries)g.dispose();if(!geometry)continue;
   const combined=new THREE.Mesh(geometry,bucket.material);combined.name=`Batched_${target.name||'body'}_${bucket.material.name||bucket.material.uuid}`;combined.castShadow=bucket.objects.some(o=>o.castShadow);combined.receiveShadow=bucket.objects.some(o=>o.receiveShadow);combined.userData.sourceParts=bucket.objects.map(o=>o.name);target.add(combined);rig.ownedGeometries.push(geometry);
   for(const object of bucket.objects)object.removeFromParent();
  }
 }
 for(const limb of Object.values(rig.limbs)){const meshes=[];limb.joint.traverse(o=>{if(o.isMesh)meshes.push(o);});mergePart(limb.joint,meshes);}
 const staticMeshes=[];model.traverse(o=>{if(!o.isMesh)return;let p=o.parent;while(p&&p!==model){if(jointSet.has(p))return;p=p.parent;}staticMeshes.push(o);});mergePart(model,staticMeshes);
 model.updateWorldMatrix(true,true);rig.drawMeshesAfter=0;model.traverse(o=>{if(o.isMesh)rig.drawMeshesAfter++;});
 return rig;
}

export function animateMarioBodyRig(rig, source, dt) {
 dt=clamp(Number.isFinite(dt)?dt:0,0,.05);const speed=Math.abs(source.velocity?.x||0),air=!!source.inAir,dead=!!source.dying;
 if(dt===0)return;
 // Velocity is NES pixels/frame; a 34-pixel stride ties cadence to actual travel.
 if(!air&&!dead&&speed>.08)rig.phase=(rig.phase+speed*60*dt*Math.PI*2/34)%(Math.PI*2);
 const amplitude=clamp(speed/2.8,0,1);const step=Math.sin(rig.phase);let targets;
 if(dead){rig.pose='death';targets={left_leg:.16,right_leg:-.12,left_arm:-.28,right_arm:-.28};}
 else if(air){const rising=(source.velocity?.y||0)<0;rig.pose=rising?'jump-rise':'jump-fall';targets=rising?{left_leg:-.42,right_leg:.20,left_arm:-.64,right_arm:-.38}:{left_leg:-.17,right_leg:.12,left_arm:-.27,right_arm:-.18};}
 else{rig.pose=speed>.08?'run':'idle';targets={left_leg:step*.36*amplitude,right_leg:-step*.36*amplitude,left_arm:-step*.42*amplitude,right_arm:step*.42*amplitude};}
 const blend=dt===0?1:1-Math.exp(-dt*(air?22:16));
 for(const [name,limb]of Object.entries(rig.limbs)){limb.angle+=((targets[name]||0)-limb.angle)*blend;limb.joint.position.copy(limb.restPosition);limb.joint.rotation.copy(limb.restRotation);limb.joint.rotation.x+=limb.angle;}
 rig.model.updateWorldMatrix(true,true);
 if(!air&&!dead)for(const name of ['left_leg','right_leg']){const limb=rig.limbs[name];const penetration=limb.restMinY-rig.localBounds(limb.joint).min.y;if(penetration>0)limb.joint.position.y+=penetration;}
 rig.model.updateWorldMatrix(true,true);
}

/** Whole-object PBR replacements driven exclusively by decoded ROM semantics. */
export class PhotorealRenderer {
 constructor(canvas){
  this.canvas=canvas;this.renderer=new THREE.WebGLRenderer({canvas,antialias:true,alpha:false,powerPreference:'high-performance'});this.renderer.setPixelRatio(Math.min(devicePixelRatio||1,1.75));this.renderer.outputColorSpace=THREE.SRGBColorSpace;this.renderer.toneMapping=THREE.ACESFilmicToneMapping;this.renderer.toneMappingExposure=.93;this.renderer.shadowMap.enabled=true;this.renderer.shadowMap.type=THREE.PCFSoftShadowMap;
  this.scene=new THREE.Scene();this.scene.fog=new THREE.Fog('#b6c9bb',44,90);this.camera=new THREE.OrthographicCamera(-8,8,6*Math.cos(PITCH),-6*Math.cos(PITCH),.1,150);this.camera.position.set(8,8.4,32);this.camera.lookAt(8,6,0);
  this.models=new Map();this.entries=new Map();this.instances=new Map();this.time=0;this.sourceClock={frame:null,time:0};this.frame=0;this.last=null;this.mode='day';this.stats={supported:false,loadedModels:0,loadFailures:0,visibleObjects:0,replacedObjects:0,missingModels:[],sourceCoverage:null,heroModel:null};
  this.actorRoot=new THREE.Group();this.scene.add(this.actorRoot);this.makeLighting();this.makeAtmosphere();this.resize(canvas.clientWidth||1024,canvas.clientHeight||768);
 }
 makeLighting(){
  this.sun=new THREE.DirectionalLight('#fff0d2',2.8);this.sun.position.set(-7,18,15);this.sun.target.position.set(8,3,0);this.sun.castShadow=true;this.sun.shadow.mapSize.set(2048,2048);Object.assign(this.sun.shadow.camera,{left:-12,right:12,top:14,bottom:-10,near:1,far:65});this.sun.shadow.bias=-.0002;this.sun.shadow.normalBias=.018;this.sun.shadow.radius=3;this.scene.add(this.sun,this.sun.target);
  this.hemi=new THREE.HemisphereLight('#d7e8f0','#655943',.5);this.scene.add(this.hemi);this.fill=new THREE.DirectionalLight('#c3dcf4',.22);this.fill.position.set(18,8,12);this.scene.add(this.fill);
  this.sky=new Sky();this.sky.scale.setScalar(1000);const u=this.sky.material.uniforms;u.turbidity.value=2.1;u.rayleigh.value=1.4;u.mieCoefficient.value=.003;u.mieDirectionalG.value=.82;u.sunPosition.value.set(-.5,.55,.85).normalize();
  const pmrem=new THREE.PMREMGenerator(this.renderer);const envScene=new THREE.Scene();const envSky=this.sky.clone();envScene.add(envSky);this.environmentTarget=pmrem.fromScene(envScene,.025);this.scene.environment=this.environmentTarget.texture;this.scene.environmentIntensity=.38;pmrem.dispose();
 }
 makeAtmosphere(){
  this.backdrops=[];
  this.skyGradient=new THREE.Mesh(new THREE.PlaneGeometry(200,100),new THREE.ShaderMaterial({
   uniforms:{topColor:{value:new THREE.Color('#619dbb')},bottomColor:{value:new THREE.Color('#d4dfda')}},
   vertexShader:'varying vec2 vUv; void main(){vUv=uv;gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.0);}',
   fragmentShader:'uniform vec3 topColor;uniform vec3 bottomColor;varying vec2 vUv;void main(){float t=smoothstep(0.36,0.63,vUv.y);gl_FragColor=vec4(mix(bottomColor,topColor,t),1.0); #include <colorspace_fragment> }',
   depthWrite:false,toneMapped:false
  }));
  // The physical Sky provides reflections. A height gradient keeps an orthographic sky from becoming one flat horizon sample.
  this.skyGradient.material.fragmentShader=this.skyGradient.material.fragmentShader.replace(' #include','\n#include').replace('> }','>\n}');
  this.skyGradient.position.set(8,6,-58);this.skyGradient.renderOrder=-100;this.scene.add(this.skyGradient);
  // Non-colliding distant countryside, kept below the active platform region.
  for(let layer=0;layer<3;layer++){
   const vertices=[],indices=[];const width=180,steps=200,z=-15-layer*8;
   for(let i=0;i<=steps;i++){const x=-width/2+i/steps*width;const top=.45+Math.sin(x*.17+layer)*.7+Math.sin(x*.37+layer*4)*.3+(2-layer)*.18;vertices.push(x,top,z,x,-7,z);if(i<steps){const n=i*2;indices.push(n,n+1,n+2,n+1,n+3,n+2);}}
   const geometry=new THREE.BufferGeometry();geometry.setAttribute('position',new THREE.Float32BufferAttribute(vertices,3));geometry.setIndex(indices);geometry.computeVertexNormals();const material=new THREE.MeshStandardMaterial({color:['#688653','#819a70','#9aaf94'][layer],roughness:1,side:THREE.DoubleSide});const mesh=new THREE.Mesh(geometry,material);mesh.userData.parallax=.16-layer*.04;this.scene.add(mesh);this.backdrops.push(mesh);
  }
 }
 async prepareAssets(){
  const generation=this.assetGeneration=(this.assetGeneration||0)+1;
  const verified=await fetchRegistry('assets/photoreal-registry.json');
  const staged=Object.create(this);
  staged.entries=new Map([...verified].map(([id,asset])=>[id,asset.entry]));
  staged.models=new Map();staged.instances=new Map();staged.stats={...this.stats,loadFailures:0};staged.verified=verified;
  try { for(const id of staged.entries.keys()) if(RUNTIME_IDS.has(id)) await staged.loadModel(id); }
  catch(error){for(const model of staged.models.values())this.disposeModel(model);throw error;}
  const validate=()=>{if(generation!==this.assetGeneration)throw new Error('Superseded photoreal release');};
  const commit=()=>{
   validate();
   for(const instance of this.instances.values()){this.actorRoot.remove(instance.group);instance.mixer?.stopAllAction();instance.marioRig?.ownedGeometries.forEach(g=>g.dispose());}
   this.instances.clear();for(const model of this.models.values())this.disposeModel(model);
   this.entries=staged.entries;this.models=staged.models;this.stats.loadedModels=this.models.size;this.stats.loadFailures=0;delete this.stats.registryError;
   if(this.last)this.update(this.last,0);return this.getStats();
  };
  commit.validate=validate;commit.dispose=()=>{for(const model of staged.models.values())this.disposeModel(model);};return commit;
 }
 disposeModel(model){model.root.traverse(o=>{if(o.isMesh){o.geometry.dispose();for(const m of Array.isArray(o.material)?o.material:[o.material])m.dispose();}});}
 async init(){return this.reloadAssets();}
 async loadModel(id,force=false){if((this.models.has(id)&&!force)||!this.entries.has(id))return;const entry=this.entries.get(id);try{const loader=new GLTFLoader();const verified=this.verified?.get(id);if(!verified)throw new Error('Model was not verified');const gltf=await parseVerifiedGLB(loader,verified.bytes);let root=gltf.scene;root.updateMatrixWorld(true);if(/^(ground-|hill-|bush|platform-|pipe-|question-|used-|brick-|stone-|ice-|cloud)/.test(id)&&!gltf.animations?.length){const buckets=new Map();let compatible=true;root.traverse(o=>{if(o.isSkinnedMesh||o.isMesh&&Array.isArray(o.material))compatible=false;if(o.isMesh&&!Array.isArray(o.material)){const key=o.material.uuid;const b=buckets.get(key)||{material:o.material,geometries:[]};b.geometries.push(o.geometry.clone().applyMatrix4(o.matrixWorld));buckets.set(key,b);}});if(compatible&&buckets.size){const merged=new THREE.Group();let success=true;for(const b of buckets.values()){const geometry=mergeGeometries(b.geometries,false);if(!geometry){success=false;break;}merged.add(new THREE.Mesh(geometry,b.material));}for(const b of buckets.values())for(const geometry of b.geometries)geometry.dispose();if(success)root=merged;}}root.updateMatrixWorld(true);const bounds=new THREE.Box3().setFromObject(root),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());if(!Number.isFinite(size.y)||size.y<=0)throw new Error('Empty model bounds');root.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;if(o.material){for(const m of Array.isArray(o.material)?o.material:[o.material]){if(m.map)m.map.anisotropy=Math.min(8,this.renderer.capabilities.getMaxAnisotropy());m.envMapIntensity=.7;}}}});if(force)for(const [key,instance] of this.instances){if(instance.modelId===id){this.actorRoot.remove(instance.group);instance.mixer?.stopAllAction();instance.marioRig?.ownedGeometries.forEach(g=>g.dispose());this.instances.delete(key);}}this.models.set(id,{root,size,center,bottom:bounds.min.y,clips:gltf.animations||[]});this.stats.loadedModels=this.models.size;if(id==='mario-hero'){const current=this.instances.get('player');if(current){this.actorRoot.remove(current.group);this.instances.delete('player');}}
  }catch(error){this.stats.loadFailures++;throw error;}}
 async reloadAssets(){
  if(this.assetReload)return this.assetReload;
  this.assetReload=(async()=>{try{const commit=await this.prepareAssets();return commit();}catch(error){this.stats.registryError=error.message;throw error;}finally{this.assetReload=null;}})();
  return this.assetReload;
 }
 async refreshRegistry(){return this.reloadAssets();}
 getStats(){return {...this.stats,drawCalls:this.renderer.info.render.calls,triangles:this.renderer.info.render.triangles};}
 modelFor(source){
  if(source.type==='player')return this.models.has('mario-hero')?'mario-hero':'mario-body';
  if(source.type==='platform'){const desired={white:'platform-cream',orange:'platform-coral',green:'platform-green',blue:'platform-blue'}[source.materialVariant];if(!this.models.has(desired)&&desired!=='platform-coral')this.variantFallbacks?.add(`${source.id}:${desired}->platform-coral`);return this.models.has(desired)?desired:'platform-coral';}
  if(source.type==='koopa'){const id=source.materialVariant==='red'?'koopa-red':'koopa-green';return this.models.has(id)?id:(this.models.has('koopa')?'koopa':'koopa-green');}
  if(source.type==='mushroom'&&source.materialVariant==='one-up'&&this.models.has('one-up'))return 'one-up';
  const id=MAP[source.type];const alternates={piranha:['piranha-plant'],flower:['flower'],leaf:['leaf'],cloud:['cloud-white'],mushroom:['mushroom-red']};if(this.models.has(id))return id;return (alternates[source.type]||[]).find(x=>this.models.has(x))||id;
 }
 resetAnimation(){
  this.sourceClock={frame:null,time:0};this.time=0;
  for(const instance of this.instances.values()){
   if(instance.animation)resetSourceAnimation(instance.animation);
   if(instance.marioRig){instance.marioRig.phase=0;instance.marioRig.pose='idle';for(const limb of Object.values(instance.marioRig.limbs)){limb.angle=0;limb.joint.position.copy(limb.restPosition);limb.joint.rotation.copy(limb.restRotation);}}
   for(const limb of instance.limbs)limb.rotation.copy(instance.baseRotations.get(limb));
  }
 }
 releaseInstance(instance){instance.animation?.mixer.stopAllAction();instance.animation?.mixer.uncacheRoot(instance.model);instance.marioRig?.ownedGeometries.forEach(g=>g.dispose());this.actorRoot.remove(instance.group);}
 instance(key,modelId){
  let instance=this.instances.get(key);
  if(instance&&instance.modelId===modelId){if(instance.seen<this.frame-1){if(instance.animation)resetSourceAnimation(instance.animation);if(instance.marioRig)instance.marioRig.phase=0;}instance.seen=this.frame;instance.group.visible=true;return instance;}
  if(instance){this.releaseInstance(instance);this.instances.delete(key);}
  const prototype=this.models.get(modelId);if(!prototype)return null;
  const group=new THREE.Group(),pivot=new THREE.Group(),model=cloneSkeleton(prototype.root);
  model.position.sub(new THREE.Vector3(prototype.center.x,prototype.bottom,prototype.center.z));pivot.add(model);group.add(pivot);this.actorRoot.add(group);
  instance={group,pivot,model,modelId,prototype,seen:this.frame,limbs:[],baseRotations:new Map()};
  if(modelId==='mario-body'&&!prototype.clips.length)instance.marioRig=buildMarioBodyRig(model);
  model.traverse(o=>{if(/(left|right|[lr])[_ .-]?(arm|leg)|(arm|leg)[_ .-]?(left|right)/i.test(o.name)&&!o.isMesh){instance.limbs.push(o);instance.baseRotations.set(o,o.rotation.clone());}});
  if(prototype.clips.length){instance.animation=createSourceAnimation(model,prototype.clips);instance.mixer=instance.animation.mixer;}
  this.instances.set(key,instance);return instance;
 }
 markUnresolved(source,modelId,reason='missing-model'){
  const unresolved=unresolvedSourceObject(source,modelId,this.cameraX,reason);
  if(unresolved){this.unresolved.push(unresolved);this.missing.add(modelId||`${source.type}:${source.id}`);}
 }
 placeScore(source){
  const label=String(source.label??source.value??'');if(!label||typeof document==='undefined'){this.markUnresolved(source,null,'score-label-unavailable');return false;}
  this.scoreMaterials??=new Map();this.scoreGeometry??=new THREE.PlaneGeometry(1,1);
  let material=this.scoreMaterials.get(label);
  if(!material){
   const canvas=document.createElement('canvas');canvas.width=canvas.height=256;const context=canvas.getContext('2d');
   context.textAlign='center';context.textBaseline='middle';context.lineJoin='round';context.font='900 144px Arial, sans-serif';
   const measured=context.measureText(label).width;if(measured>222)context.font=`900 ${Math.floor(144*222/measured)}px Arial, sans-serif`;
   context.lineWidth=13;context.strokeStyle='#263127';context.strokeText(label,128,136);context.fillStyle='#fff9d9';context.fillText(label,128,136);
   const texture=new THREE.CanvasTexture(canvas);texture.colorSpace=THREE.SRGBColorSpace;texture.minFilter=THREE.LinearFilter;texture.magFilter=THREE.LinearFilter;texture.generateMipmaps=false;
   material=new THREE.MeshBasicMaterial({map:texture,transparent:true,depthTest:false,depthWrite:false,toneMapped:false});this.scoreMaterials.set(label,material);
  }
  const key=source.id,modelId=`score:${label}`;let instance=this.instances.get(key);
  if(instance&&instance.modelId!==modelId){this.releaseInstance(instance);this.instances.delete(key);instance=null;}
  if(!instance){const group=new THREE.Group(),mesh=new THREE.Mesh(this.scoreGeometry,material);mesh.renderOrder=20;group.add(mesh);this.actorRoot.add(group);instance={group,model:mesh,modelId,seen:this.frame,limbs:[],baseRotations:new Map()};this.instances.set(key,instance);}
  instance.seen=this.frame;instance.group.visible=true;instance.group.position.set((source.x+source.width/2)*PX,H-(source.y+source.height/2)*PX,.65);instance.group.scale.set(source.width*PX,source.height*PX,1);instance.group.quaternion.copy(this.camera.quaternion);instance.group.userData.source=source.source;this.placedSources.add(source.id);this.scoreLabels++;
  return true;
 }
 place(key,source,modelId,options={}){
  const instance=this.instance(key,modelId);if(!instance){this.markUnresolved(source,modelId);return false;}
  const {group,pivot,prototype}=instance,w=source.width*PX,h=source.height*PX,uniform=options.character;
  const sx=uniform?Math.min(w/prototype.size.x,h/prototype.size.y):w/prototype.size.x,sy=uniform?sx:h/prototype.size.y;let sz=uniform?sx:Math.min(sx,sy);
  if(source.type==='ground')sz=Math.min(1.1,w/prototype.size.x);
  pivot.scale.set(sx,sy,Math.max(.08,sz));group.position.set((source.x+source.width/2)*PX,H-(source.y+source.height)*PX,options.depth??0);pivot.rotation.set(0,0,0);
  const actor=['player','goomba','koopa','piranha'].includes(source.type);
  if(actor){
   const facing=source.flipX?-1:1;pivot.rotation.y=source.type==='player'?facing*.88:source.type==='piranha'?0:facing*.22;
   // Clip geometry handles squash/shell poses; the old kit has no such authored pose.
   if(source.squashed&&!instance.animation?.actions.has('squash'))pivot.scale.y*=.3;
   if((source.dying||source.state==='killed')&&!instance.animation?.actions.has('death'))pivot.rotation.z=source.velocity?.y>0?.3:-.3;
   if(instance.animation){
    const state=updateSourceAnimation(instance.animation,source,this.dt);instance.animationState=state;this.animationStates.push({id:key,modelId,...state});
    if(source.type==='player')this.stats.playerAnimation={mode:state.state,clip:state.clip,time:state.time,kind:'glTF-clips',joints:instance.limbs.length,available:state.available};
   }else if(instance.marioRig){
    animateMarioBodyRig(instance.marioRig,source,this.dt);this.stats.playerAnimation={mode:instance.marioRig.pose,kind:'derived-rigid-joints',joints:4,attachedMeshes:instance.marioRig.partCount,drawMeshes:instance.marioRig.drawMeshesAfter,originalDrawMeshes:instance.marioRig.drawMeshesBefore,stridePixels:34};this.derivedAnimations++;
   }else if(instance.limbs.length){
    const speed=Math.abs(source.velocity?.x||0);for(const limb of instance.limbs){const base=instance.baseRotations.get(limb);limb.rotation.copy(base);if(speed>.15&&!source.inAir){const side=/left|_l|\.l/i.test(limb.name)?1:-1;limb.rotation.x+=Math.sin(this.time*17)*.45*side;}}
    this.derivedAnimations++;
   }else this.staticActors.push({id:key,modelId,state:sourceAnimationState(source)});
  }else if(source.type==='coin')pivot.rotation.y=this.time*1.4;
  group.userData.source=source.source;this.placedSources.add(source.id||key);return true;
 }
 drawObject(object){const modelId=this.modelFor(object);if(object.type==='ground'){
   const start=Math.max(object.x,Math.floor((this.cameraX-32)/64)*64),end=Math.min(object.x+object.width,this.cameraX+288);for(let x=start;x<end;x+=64){const width=Math.min(64,end-x);this.place(`${object.id}:ground:${x}`,{...object,x,width},modelId,{depth:-.3});}return;
  }
  if(object.type==='hill'&&object.topProfile?.length>2){
   // Source-connected decorative hills contain several peaks. Preserve their heights and span.
   const profile=object.topProfile,runs=[];for(const p of profile){let run=runs[runs.length-1];if(!run||run.y!==p.y){run={x:p.x,y:p.y,width:16};runs.push(run);}else run.width+=16;}
   const peaks=runs.filter((r,i)=>r.y<=(runs[i-1]?.y??Infinity)&&r.y<=(runs[i+1]?.y??Infinity));if(peaks.length){for(let i=0;i<peaks.length;i++){const peak=peaks[i],left=i===0?object.x:(peaks[i-1].x+peaks[i-1].width+peak.x)/2,right=i===peaks.length-1?object.x+object.width:(peak.x+peak.width+peaks[i+1].x)/2;this.place(`${object.id}:peak:${i}`,{...object,x:left,y:peak.y,width:right-left,height:object.y+object.height-peak.y},modelId,{depth:-1.5});}return;}
  }
  this.place(object.id,object,modelId,{depth:object.type==='hill'||object.type==='bush'?-1.3:object.type==='cloud'?-5:object.type==='platform'?-.35:0});
 }
 update(scene,dt=1/60){
  const semantic=scene?.semantic||scene;if(!semantic?.objects)return;
  this.last=scene;const clock=advanceSourceClock(this.sourceClock,scene?.frame??semantic.frame,dt);if(clock.reset){this.resetAnimation();this.sourceClock.frame=scene?.frame??semantic.frame;}
  this.dt=clock.dt;this.time=this.sourceClock.time;this.frame++;this.cameraX=Number.isFinite(semantic.cameraX)?semantic.cameraX:0;
  const x=this.cameraX*PX;this.camera.position.x=x+8;this.sun.position.x=x-7;this.sun.target.position.x=x+8;this.fill.position.x=x+18;this.sky.position.x=x+8;this.skyGradient.position.x=x+8;for(const back of this.backdrops)back.position.x=x*(1-back.userData.parallax);
  this.missing=new Set();this.unresolved=[];this.variantFallbacks=new Set();this.placedSources=new Set();this.animationStates=[];this.staticActors=[];this.derivedAnimations=0;this.scoreLabels=0;this.stats.playerAnimation=null;let count=0;
  for(const object of semantic.objects){
   if(object.x+object.width<this.cameraX-32||object.x>this.cameraX+288||object.y>192||object.y+object.height<0)continue;
   count++;if(object.type==='unknown'){this.markUnresolved(object,null,'unknown-terrain');continue;}this.drawObject(object);
  }
  for(const entity of semantic.entities||[]){
   if(entity.visible===false)continue;count++;
   if(entity.type==='unknown'){this.markUnresolved(entity,null,'unknown-entity');continue;}
   if(entity.type==='score'){this.placeScore(entity);continue;}
   this.place(entity.id,entity,this.modelFor(entity),{character:!['coin','bouncing-block','score'].includes(entity.type),depth:.38});
  }
  if(semantic.player&&semantic.player.visible!==false){const p={...semantic.player,type:'player'};count++;this.place('player',p,this.modelFor(p),{character:true,depth:.48});this.stats.heroModel=this.modelFor(p);}
  for(const [key,instance]of this.instances){if(instance.seen!==this.frame)instance.group.visible=false;if(this.frame-instance.seen>900&&this.instances.size>250){this.releaseInstance(instance);this.instances.delete(key);}}
  const renderable=semantic.renderable??semantic.supported;
  Object.assign(this.stats,{supported:!!semantic.supported,renderable:!!renderable,sourceCoverage:semantic.coverage,visibleObjects:count,replacedObjects:this.placedSources.size,scoreLabels:this.scoreLabels,missingModels:[...this.missing],unresolvedObjects:this.unresolved,variantFallbacks:[...this.variantFallbacks],needsOriginal:!renderable,mode:semantic.mode,animation:{sourceFrame:this.sourceClock.frame,sourceTime:this.time,clipInstances:this.animationStates.length,derivedInstances:this.derivedAnimations,staticActors:this.staticActors,states:this.animationStates,loadedAnimatedModels:[...this.models].filter(([,m])=>m.clips.length).map(([id,m])=>({id,clips:m.clips.map(c=>c.name)}))}});
  this.render();
 }
 render(){this.renderer.setScissorTest(false);this.renderer.setClearColor('#9ec6d1');this.renderer.render(this.scene,this.camera);}
 setLighting(mode){this.mode=mode;const dusk=mode==='dusk';this.sun.color.set(dusk?'#ffc78a':'#fff0d2');this.sun.intensity=dusk?1.8:2.8;this.hemi.intensity=dusk?.35:.5;this.fill.intensity=dusk?.2:.22;this.scene.environmentIntensity=dusk?.3:.38;this.renderer.toneMappingExposure=dusk?.86:.93;this.skyGradient?.material.uniforms.topColor.value.set(dusk?'#456486':'#619dbb');this.skyGradient?.material.uniforms.bottomColor.value.set(dusk?'#c5aca0':'#d4dfda');this.sky.material.uniforms.sunPosition.value.set(-.5,dusk?.15:.55,.85).normalize();if(this.last)this.render();}
 resize(width,height){this.renderer.setSize(Math.max(1,width),Math.max(1,height),false);if(this.last)this.render();}
 dispose(){this.scoreGeometry?.dispose();for(const material of this.scoreMaterials?.values()||[]){material.map?.dispose();material.dispose();}for(const instance of this.instances.values()){instance.mixer?.stopAllAction();instance.marioRig?.ownedGeometries.forEach(g=>g.dispose());}const geometries=new Set(),materials=new Set(),textures=new Set();for(const model of this.models.values())model.root.traverse(o=>{if(o.geometry)geometries.add(o.geometry);for(const m of o.material?(Array.isArray(o.material)?o.material:[o.material]):[]){materials.add(m);for(const v of Object.values(m))if(v?.isTexture)textures.add(v);}});for(const x of geometries)x.dispose();for(const x of materials)x.dispose();for(const x of textures)x.dispose();for(const mesh of this.backdrops){mesh.geometry.dispose();mesh.material.dispose();}this.skyGradient.geometry.dispose();this.skyGradient.material.dispose();this.sky.geometry.dispose();this.sky.material.dispose();this.environmentTarget.dispose();this.renderer.dispose();}
}
export {PhotorealRenderer as WorldRenderer};
