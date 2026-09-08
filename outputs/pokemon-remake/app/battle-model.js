import * as THREE from 'three';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';

// Presentation-only candidate loader. The caller supplies source-frame time.
export async function createBattleModel(renderer,{url,sha256}={}) {
  if(!url || !/^[a-f\d]{64}$/i.test(sha256??''))throw new Error('Battle model requires a URL and SHA256');
  const response=await fetch(url);
  if(!response.ok)throw new Error(`Battle model fetch failed: ${response.status}`);
  const bytes=await response.arrayBuffer();
  const actualHash=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
  if(actualHash!==sha256.toLowerCase())throw new Error(`Battle model SHA256 mismatch: ${actualHash}`);
  const view=new DataView(bytes);
  if(bytes.byteLength<20 || view.getUint32(0,true)!==0x46546c67 || view.getUint32(4,true)!==2 || view.getUint32(8,true)!==bytes.byteLength || view.getUint32(16,true)!==0x4e4f534a)throw new Error('Battle model must be a valid GLB v2');
  const jsonLength=view.getUint32(12,true);
  if(jsonLength>bytes.byteLength-20)throw new Error('Battle model has a truncated JSON chunk');
  const definition=JSON.parse(new TextDecoder().decode(new Uint8Array(bytes,20,jsonLength)));
  // The verified GLB must carry its dependencies; an external texture would escape its hash.
  if([...(definition.buffers??[]),...(definition.images??[])].some(item=>item.uri&&!item.uri.startsWith('data:')))throw new Error('Battle model requires embedded buffers and textures');
  const gltf=await new GLTFLoader().parseAsync(bytes,'');
  const group=new THREE.Group();group.name='Source-timed battle model candidate';
  group.add(gltf.scene); // Keep every armature ancestor, scale, rotation, and skin binding.
  const geometries=new Set(),materials=new Set(),textures=new Set(),skeletons=new Set(),skinnedMeshes=[];
  let meshCount=0,boneCount=0,nodeCount=0,disposed=false,mixer=null,sourceSeconds=null;
  group.traverse(node=>{
    nodeCount++;if(node.isBone)boneCount++;
    if(node.isMesh){meshCount++;node.castShadow=true;node.receiveShadow=true;geometries.add(node.geometry);for(const mat of Array.isArray(node.material)?node.material:[node.material])if(mat){materials.add(mat);for(const value of Object.values(mat))if(value?.isTexture)textures.add(value);}}
    if(node.isSkinnedMesh){skeletons.add(node.skeleton);skinnedMeshes.push({name:node.name,bones:node.skeleton.bones.length,vertices:node.geometry.attributes.position.count,bindMode:node.bindMode});}
  });
  function dispose(){if(disposed)return;disposed=true;if(mixer){mixer.stopAllAction();mixer.uncacheRoot(gltf.scene);}for(const skeleton of skeletons)skeleton.dispose();for(const geometry of geometries)geometry.dispose();for(const material of materials)material.dispose();for(const texture of textures){texture.dispose();texture.source?.data?.close?.();}group.removeFromParent();group.clear();}
  const idleClips=gltf.animations.filter(clip=>clip.name==='idle');
  if(idleClips.length>1 || idleClips.some(clip=>!Number.isFinite(clip.duration)||clip.duration<=0)){dispose();throw new Error('Battle model has an ambiguous or invalid idle clip');}
  const idle=idleClips[0]??null;
  if(idle){mixer=new THREE.AnimationMixer(gltf.scene);mixer.clipAction(idle).setLoop(THREE.LoopRepeat,Infinity).play();mixer.setTime(0);}
  group.updateMatrixWorld(true);
  const bounds=new THREE.Box3().setFromObject(gltf.scene,true),size=bounds.getSize(new THREE.Vector3());
  if(bounds.isEmpty() || ![...bounds.min.toArray(),...bounds.max.toArray()].every(Number.isFinite) || size.y<=0){dispose();throw new Error('Battle model has invalid bounds');}
  const report={status:'candidate-loader-only-not-visual-acceptance',url:String(url),sha256:actualHash,bytes:bytes.byteLength,hierarchyPreserved:true,up:'+Y',front:'+Z (asset convention; visually verify)',bounds:{min:bounds.min.toArray(),max:bounds.max.toArray(),size:size.toArray()},height:size.y,groundOffset:-bounds.min.y,meshCount,nodeCount,boneCount,skinnedMeshes,clips:gltf.animations.map(clip=>({name:clip.name,duration:clip.duration,tracks:clip.tracks.length})),selectedClip:idle?.name??null,animationReady:!!idle,staticOnly:!idle,get sourceSeconds(){return sourceSeconds;},get disposed(){return disposed;}};
  function setTime(seconds){if(disposed)throw new Error('Battle model is disposed');if(!Number.isFinite(seconds)||seconds<0)throw new RangeError('Battle model time must be finite and non-negative');sourceSeconds=seconds;if(mixer){mixer.setTime(seconds%idle.duration);group.updateMatrixWorld(true);}return !!mixer;}
  return {group,setTime,report,dispose};
}
