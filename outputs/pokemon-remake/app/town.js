import * as THREE from 'three';
import {createTerrain} from './terrain.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// Presentation only. Positions and motion come from the unmodified GBA core.
export async function createTown(renderer,cottage,candidates) {
  const layout=await (await fetch(new URL('scene-layout.json',document.baseURI))).json();
  const group=new THREE.Group();group.name='PalletTown';
  const terrain=await createTerrain(renderer,layout);group.add(terrain.group);
  const rockMaterial=new THREE.MeshStandardMaterial({color:'#767771',roughness:.95});
  const woodMaterial=new THREE.MeshStandardMaterial({color:'#877257',roughness:.9});
  const houses=[];
  const labResponse=await fetch(new URL(`models/${candidates.laboratory.file}`,document.baseURI));
  if(!labResponse.ok)throw Error('Laboratory candidate unavailable');
  const labBytes=await labResponse.arrayBuffer();
  const labHash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',labBytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
  if(labHash!==candidates.laboratory.sha256)throw Error('Laboratory candidate hash mismatch');
  const laboratory=(await new GLTFLoader().parseAsync(labBytes,'')).scene;
  laboratory.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true;}});
  for(const building of layout.buildings){
    const [x0,z0,x1,z1]=building.bounds;
    if(building.kind==='cottage'||building.kind==='unbuilt-laboratory'){
      const candidate=building.kind==='cottage'?candidates.cottage:candidates.laboratory;
      const model=(building.kind==='cottage'?cottage:laboratory).clone(true);model.position.set(0,0,0);model.scale.setScalar(1);model.updateMatrixWorld(true);
      const bounds=new THREE.Box3().setFromObject(model),size=bounds.getSize(new THREE.Vector3()),center=bounds.getCenter(new THREE.Vector3());
      const scale=Math.min((x1-x0+.5)/size.x,(z1-z0+.1)/size.z);model.scale.setScalar(scale);
      const door=candidate.doorAnchor;if(door){model.position.set(building.door[0]-door[0]*scale,-bounds.min.y*scale,building.door[1]-door[2]*scale);}else{model.position.set((x0+x1)/2-center.x*scale,-bounds.min.y*scale,(z0+z1)/2-center.z*scale);}
      group.add(model);houses.push({id:building.id,scale,sourceBounds:building.bounds,doorAnchor:candidate.doorAnchor,runtimeDoor:door?new THREE.Vector3(...door).multiplyScalar(scale).add(model.position).toArray():null,sourceDoor:building.door});
    }else{
      const footprint=new THREE.Mesh(new THREE.BoxGeometry(x1-x0+.8,.08,z1-z0+.8),rockMaterial);footprint.position.set((x0+x1)/2,.025,(z0+z1)/2);footprint.receiveShadow=true;group.add(footprint);
      addLabel('OAK’S LAB · MODEL PENDING',(x0+x1)/2,.4,(z0+z1)/2,4.5);
    }
  }
  function addLabel(text,x,y,z,width=2.5){const c=document.createElement('canvas');c.width=768;c.height=128;const ctx=c.getContext('2d');ctx.fillStyle='rgba(24,38,31,.82)';ctx.fillRect(0,0,768,128);ctx.fillStyle='#f3f0de';ctx.font='bold 28px Arial';ctx.textAlign='center';ctx.textBaseline='middle';ctx.fillText(text,384,64);const texture=new THREE.CanvasTexture(c);texture.colorSpace=THREE.SRGBColorSpace;const s=new THREE.Sprite(new THREE.SpriteMaterial({map:texture,depthTest:false}));s.scale.set(width,width/6,1);s.position.set(x,y,z);group.add(s);return s;}
  for(const fence of layout.fences){const [x0,z]=fence.from,[x1]=fence.to;for(let x=x0-.4;x<=x1+.4;x+=.32){const post=new THREE.Mesh(new THREE.BoxGeometry(.075,.65,.08),woodMaterial);post.position.set(x,.325,z);post.castShadow=true;group.add(post)}for(const y of [.2,.48]){const rail=new THREE.Mesh(new THREE.BoxGeometry(x1-x0+.85,.055,.065),woodMaterial);rail.position.set((x0+x1)/2,y,z);rail.castShadow=true;group.add(rail)}}
  for(const sign of layout.signs){const post=new THREE.Mesh(new THREE.BoxGeometry(.1,.7,.1),woodMaterial);post.position.set(sign.x,.35,sign.y);post.castShadow=true;group.add(post);const board=new THREE.Mesh(new THREE.BoxGeometry(.5,.28,.08),woodMaterial);board.position.set(sign.x,.7,sign.y);board.castShadow=true;group.add(board)}
  let treeReport={loaded:false};
  try{const tree=(await new GLTFLoader().loadAsync(new URL('models/tree.glb',document.baseURI).href)).scene;tree.updateMatrixWorld(true);const b=new THREE.Box3().setFromObject(tree),s=b.getSize(new THREE.Vector3()),c=b.getCenter(new THREE.Vector3()),scale=3.8/s.y;
    for(const pos of layout.trees){const t=tree.clone(true);t.scale.setScalar(scale);t.position.set(pos.x-c.x*scale,-b.min.y*scale,pos.z-c.z*scale);t.rotation.y=((pos.x*17+pos.z*29)%360)*Math.PI/180;t.traverse(o=>{if(o.isMesh){o.castShadow=true;o.receiveShadow=true}});group.add(t)}treeReport={loaded:true,count:layout.trees.length};
  }catch(e){treeReport.error=e.message;}
  const actors=new Map();let lastState=null;
  function update(state){terrain.update(state.frame);lastState=state;const inTown=state?.map?.name==='PalletTown';group.visible=true;
    const visible=new Set();if(!inTown)return;
    for(const obj of state.objectEvents||[]){if(obj.hidden)continue;visible.add(obj.id);let actor=actors.get(obj.id);if(!actor){actor=new THREE.Group();const ring=new THREE.Mesh(new THREE.TorusGeometry(.23,.045,8,24),new THREE.MeshStandardMaterial({color:obj.isPlayer?'#c9653e':'#d6cfab',roughness:.65}));ring.rotation.x=Math.PI/2;actor.add(ring);const pointer=new THREE.Mesh(new THREE.ConeGeometry(.09,.25,8),ring.material);pointer.rotation.x=Math.PI/2;pointer.position.z=.29;actor.add(pointer);group.add(actor);actors.set(obj.id,actor)}actor.visible=true;actor.position.set(obj.worldX,.12,obj.worldY);actor.rotation.y=({down:0,up:Math.PI,left:-Math.PI/2,right:Math.PI/2})[obj.facing]||0;}
    for(const [id,actor] of actors)if(!visible.has(id))actor.visible=false;
  }
  return {group,update,report:{map:layout.map,houses,trees:treeReport,terrain:terrain.report,limitations:['trainer and NPCs use temporary markers','laboratory candidate requires vent/roof/material revision','terrain materials are candidates; flowers absent']},get actorPositions(){return [...actors].map(([id,a])=>({id,visible:a.visible,x:a.position.x,z:a.position.z}))},get playerPosition(){const p=lastState?.player;return p?actors.get(p.id)?.position.clone():null;}};
}
