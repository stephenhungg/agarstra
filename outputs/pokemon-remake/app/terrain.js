import * as THREE from 'three';

const pathIDs=new Set([0x28e,0x28f,0x295,0x296,0x297,0x29e,0x29f,0x2ae,0x2af,0x285,0x286,0x2bf,0x2be,0x2c6,0x2c7]);
export async function createTerrain(renderer,layout){
  const group=new THREE.Group();group.name='scanned-terrain-candidate';
  const loader=new THREE.TextureLoader();
  const maps={};
  await Promise.all(['lawn','dirt'].flatMap(slug=>['Diffuse','nor_gl','Rough'].map(async role=>{
    const texture=await loader.loadAsync(new URL(`terrain/${slug}-${role}.jpg`,document.baseURI).href);
    texture.wrapS=texture.wrapT=THREE.RepeatWrapping;texture.anisotropy=Math.min(8,renderer.capabilities.getMaxAnisotropy());
    if(role==='Diffuse')texture.colorSpace=THREE.SRGBColorSpace;maps[`${slug}-${role}`]=texture;
  })));
  const isPath=(x,z)=>{const ix=Math.round(x),iz=Math.round(z);return ix>=0&&ix<24&&iz>=0&&iz<20&&pathIDs.has(layout.metatileIds[iz*24+ix]);};
  // A small transition band follows the original path cells; collisions remain
  // entirely in the ROM. This affects only surface appearance and grass density.
  function pathWeight(x,z){let sum=0;for(const dx of [-.16,0,.16])for(const dz of [-.16,0,.16])sum+=isPath(x+dx,z+dz)?1:0;return sum/9;}
  const geometry=new THREE.PlaneGeometry(26,22,208,176);geometry.rotateX(-Math.PI/2);geometry.translate(11.5,0,9.5);
  const position=geometry.attributes.position,uv=geometry.attributes.uv,weights=new Float32Array(position.count);
  for(let i=0;i<position.count;i++){const x=position.getX(i),z=position.getZ(i);uv.setXY(i,x/1.4,z/1.4);weights[i]=pathWeight(x,z);position.setY(i,-.01+.006*Math.sin(x*2.4)*Math.cos(z*2.7)*(1-weights[i]));}
  geometry.setAttribute('pathWeight',new THREE.BufferAttribute(weights,1));geometry.computeVertexNormals();
  const material=new THREE.MeshStandardMaterial({map:maps['lawn-Diffuse'],normalMap:maps['lawn-nor_gl'],roughnessMap:maps['lawn-Rough'],roughness:1,normalScale:new THREE.Vector2(.65,.65)});
  material.onBeforeCompile=shader=>{
    shader.uniforms.dirtMap={value:maps['dirt-Diffuse']};shader.uniforms.dirtNormal={value:maps['dirt-nor_gl']};shader.uniforms.dirtRough={value:maps['dirt-Rough']};
    shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nattribute float pathWeight; varying float vPathWeight;').replace('#include <begin_vertex>','#include <begin_vertex>\nvPathWeight=pathWeight;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <common>','#include <common>\nuniform sampler2D dirtMap; uniform sampler2D dirtNormal; uniform sampler2D dirtRough; varying float vPathWeight;');
    shader.fragmentShader=shader.fragmentShader.replace('#include <map_fragment>','diffuseColor *= mix(texture2D(map,vMapUv),texture2D(dirtMap,vMapUv),smoothstep(0.0,1.0,vPathWeight));');
    shader.fragmentShader=shader.fragmentShader.replace('#include <roughnessmap_fragment>','float roughnessFactor=roughness*mix(texture2D(roughnessMap,vRoughnessMapUv).g,texture2D(dirtRough,vRoughnessMapUv).g,vPathWeight);');
    shader.fragmentShader=shader.fragmentShader.replace('#include <normal_fragment_maps>','vec3 mapN=mix(texture2D(normalMap,vNormalMapUv).xyz,texture2D(dirtNormal,vNormalMapUv).xyz,vPathWeight)*2.0-1.0;mapN.xy*=normalScale;normal=normalize(tbn*mapN);');
  };
  const ground=new THREE.Mesh(geometry,material);ground.receiveShadow=true;group.add(ground);
  const bank=new THREE.Mesh(new THREE.BoxGeometry(26,.38,22),new THREE.MeshStandardMaterial({color:'#56513f',roughness:1}));bank.position.set(11.5,-.23,9.5);bank.receiveShadow=true;group.add(bank);
  let seed=7163;const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  const blade=new THREE.BufferGeometry();blade.setAttribute('position',new THREE.Float32BufferAttribute([-.012,0,0,.012,0,0,-.007,.09,.012,.007,.09,.012,0,.18,.035],3));blade.setIndex([0,1,2,1,3,2,2,3,4]);blade.computeVertexNormals();
  const grassMaterial=new THREE.MeshStandardMaterial({color:'#ffffff',roughness:.95,side:THREE.DoubleSide});
  const wind={value:0};grassMaterial.onBeforeCompile=shader=>{shader.uniforms.sourceTime=wind;shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nuniform float sourceTime;').replace('#include <begin_vertex>','#include <begin_vertex>\ntransformed.x+=sin(sourceTime*1.5+instanceMatrix[3].x*1.7+instanceMatrix[3].z)*pow(position.y/.18,2.0)*.025;');};
  const grass=new THREE.InstancedMesh(blade,grassMaterial,100000),dummy=new THREE.Object3D(),color=new THREE.Color();let count=0;
  for(let attempt=0;attempt<280000&&count<100000;attempt++){
    const x=-1+random()*25,z=-1+random()*21;
    if(pathWeight(x,z)>.15||x>6.6&&x<10.4&&z>16.7)continue;
    if(layout.buildings.some(b=>x>b.bounds[0]-.5&&x<b.bounds[2]+.5&&z>b.bounds[1]-.5&&z<b.bounds[3]+.5))continue;
    dummy.position.set(x,-.012,z);dummy.rotation.set(0,random()*Math.PI*2,0);dummy.scale.setScalar(.5+random()*.7);dummy.updateMatrix();grass.setMatrixAt(count,dummy.matrix);color.setHSL(.21+random()*.07,.38+random()*.2,.12+random()*.13);grass.setColorAt(count++,color);
  }
  grass.count=count;grass.receiveShadow=true;group.add(grass);
  const waterGeometry=new THREE.PlaneGeometry(3,3.3,36,36);waterGeometry.rotateX(-Math.PI/2);waterGeometry.translate(8.5,.028,18.45);
  const waterMaterial=new THREE.MeshPhysicalMaterial({color:'#326764',roughness:.15,metalness:0,clearcoat:1,clearcoatRoughness:.1,transparent:true,opacity:.86});
  const water=new THREE.Mesh(waterGeometry,waterMaterial);group.add(water);
  const waterTime={value:0};waterMaterial.onBeforeCompile=shader=>{shader.uniforms.sourceTime=waterTime;shader.vertexShader=shader.vertexShader.replace('#include <common>','#include <common>\nuniform float sourceTime;').replace('#include <begin_vertex>','#include <begin_vertex>\ntransformed.y+=.012*sin(position.x*7.0+sourceTime*1.2)*cos(position.z*5.0+sourceTime*.7);');};
  return {group,update(frame,fps=59.7275){wind.value=waterTime.value=frame/fps;},report:{status:'candidate',textures:6,grassBlades:count,materialSource:'ambientCG CC0 Grass004 lawn; Poly Haven CC0 dirt',pathMask:'PalletTown metatile IDs, .16 tile visual transition; no collision changes',limitations:['terrain height remains mostly flat','water shading lacks refracted depth','garden flowers not yet reconstructed']}};
}
