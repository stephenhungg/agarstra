import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// Original simulation supplies every position, facing, jump offset and clock.
export async function createAvatar(renderer,{file,sha256,height=1.4}){
  const response=await fetch(new URL(`models/${file}`,document.baseURI));
  if(!response.ok)throw Error('Trainer model unavailable');
  const bytes=await response.arrayBuffer();
  const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(n=>n.toString(16).padStart(2,'0')).join('');
  if(hash!==sha256)throw Error('Trainer model hash mismatch');
  const gltf=await new GLTFLoader().parseAsync(bytes,'');
  const group=new THREE.Group();group.name='Original-game player';group.add(gltf.scene);
  const mixer=new THREE.AnimationMixer(gltf.scene),clips={};
  for(const name of ['idle','walk']){const matches=gltf.animations.filter(c=>c.name===name);if(matches.length>1)throw Error(`Ambiguous ${name} clip`);if(matches[0])clips[name]={clip:matches[0],action:mixer.clipAction(matches[0]).setLoop(THREE.LoopRepeat,Infinity).play()};}
  if(!clips.idle)throw Error('Trainer has no verified idle clip');
  clips.idle.action.setEffectiveWeight(1);clips.walk?.action.setEffectiveWeight(0);mixer.update(0);gltf.scene.updateMatrixWorld(true);
  const initial=new THREE.Box3().setFromObject(gltf.scene,true),size=initial.getSize(new THREE.Vector3());
  if(!Number.isFinite(size.y)||size.y<=0)throw Error('Invalid trainer dimensions');
  gltf.scene.scale.multiplyScalar(height/size.y);
  let skinned=0;group.traverse(o=>{if(o.isSkinnedMesh)skinned++;if(o.isMesh){o.castShadow=true;o.receiveShadow=true;for(const mat of Array.isArray(o.material)?o.material:[o.material])if(mat.map)mat.map.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());}});
  if(!skinned)throw Error('Trainer has no skin');
  const bounds=new THREE.Box3();let lastFrame=null,lastMap=null,lastPosition=null,walkWeight=0;
  const report={file,sha256:hash,height,skinnedMeshes:skinned,clips:Object.keys(clips),status:'candidate-not-photoreal-approved',frame:null,mode:'idle',groundY:0,sourcePosition:null,feet:null};
  function update(state,{visible=true,groundHeight=0}={}){
    const p=state.player;group.visible=Boolean(visible&&p&&!p.hidden);if(!group.visible)return;
    const map=state.map?.name,rewound=map!==lastMap||lastFrame===null||state.frame<lastFrame;
    const dt=rewound?0:Math.max(0,Math.min(.15,(state.frame-lastFrame)/59.7275));
    const displaced=!rewound&&dt>0&&lastPosition&&Math.hypot(p.worldX-lastPosition[0],p.worldY-lastPosition[1])>1e-5;
    const target=clips.walk&&(p.tileTransitionState===1||displaced)?1:0;walkWeight=rewound?target:THREE.MathUtils.damp(walkWeight,target,18,dt);
    clips.idle.action.time=(state.frame/59.7275)%clips.idle.clip.duration;clips.idle.action.setEffectiveWeight(1-walkWeight);
    if(clips.walk){const axis=p.facing==='left'?-p.worldX:p.facing==='right'?p.worldX:p.facing==='up'?-p.worldY:p.worldY;const stride=.64*(height/size.y);clips.walk.action.time=(((axis/stride)%1+1)%1)*clips.walk.clip.duration;clips.walk.action.setEffectiveWeight(walkWeight);}
    mixer.update(0);
    group.position.set(p.worldX+(p.visualOffsetX||0),0,p.worldY);group.rotation.y=({down:0,up:Math.PI,left:-Math.PI/2,right:Math.PI/2})[p.facing]??0;
    group.updateMatrixWorld(true);bounds.setFromObject(group,true);group.position.y=groundHeight-bounds.min.y-Math.min(0,p.visualOffsetY||0);group.updateMatrixWorld(true);
    lastFrame=state.frame;lastMap=map;lastPosition=[p.worldX,p.worldY];Object.assign(report,{frame:state.frame,mode:walkWeight>.1?'walk':'idle',walkWeight,groundY:group.position.y,sourcePosition:[p.worldX,p.worldY],feet:['LeftFoot','RightFoot'].map(name=>{const bone=group.getObjectByName(name);return bone?bone.getWorldPosition(new THREE.Vector3()).sub(group.position).toArray():null;})});
  }
  return{group,update,report,dispose(){mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);group.removeFromParent();}};
}
