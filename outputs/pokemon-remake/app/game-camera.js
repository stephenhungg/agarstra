import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';

// Source state owns the focus; pointer input temporarily offsets the view.
// Releasing the pointer returns to a consistent north-up gameplay angle.
export function createGameCamera(element){
  const camera=new THREE.OrthographicCamera(-8,8,5.5,-5.5,.1,120);
  const target=new THREE.Vector3(),offset=new THREE.Vector3(0,24,24*Math.sqrt(3)),home=new THREE.Vector3();
  const controls=new OrbitControls(camera,element);
  controls.enableDamping=false;controls.enablePan=false;
  controls.minPolarAngle=Math.PI/12;controls.maxPolarAngle=Math.PI*.46;
  controls.minAzimuthAngle=-Math.PI*.45;controls.maxAzimuthAngle=Math.PI*.45;
  controls.minZoom=.75;controls.maxZoom=1.6;controls.rotateSpeed=.65;
  controls.enabled=false;
  let aspect=1,lastState=null,lastInterior=false,mapName=null,dragging=false,returning=false;
  function reset(){dragging=false;returning=false;home.copy(target).add(offset);camera.position.copy(home);camera.zoom=1;controls.target.copy(target);camera.up.set(0,1,0);camera.lookAt(target);camera.updateProjectionMatrix();controls.update();camera.updateMatrixWorld(true);}
  controls.addEventListener('start',()=>{dragging=true;returning=false;});
  controls.addEventListener('end',()=>{dragging=false;returning=true;});
  function update(state,{interior=false}={}){
    lastState=state;lastInterior=interior;
    const {map,player}=state||{};if(!map||!player)return;
    const half=interior?Math.max(5.5,(map.height*.5+3)/2,(map.width+1.5)/(2*aspect)):5.5;
    camera.left=-half*aspect;camera.right=half*aspect;camera.top=half;camera.bottom=-half;
    const fit=(value,size,margin)=>size<=margin*2?(size-1)/2:THREE.MathUtils.clamp(value,margin-.5,size-margin-.5);
    const next=new THREE.Vector3(interior?(map.width-1)/2:fit(player.worldX,map.width,half*aspect),0,interior?(map.height-1)/2:fit(player.worldY,map.height,half/.5));
    camera.position.add(next.clone().sub(target));target.copy(next);home.copy(target).add(offset);controls.target.copy(target);
    if(mapName!==map.name){mapName=map.name;reset();}
    else if(!dragging&&!returning)reset();
    camera.updateProjectionMatrix();camera.updateMatrixWorld(true);
  }
  function tick(dt){
    if(!controls.enabled||dragging||!returning)return;
    const alpha=1-Math.exp(-10*Math.min(dt,.1));
    camera.position.lerp(home,alpha);camera.zoom=THREE.MathUtils.lerp(camera.zoom,1,alpha);
    camera.lookAt(target);camera.updateProjectionMatrix();controls.update();camera.updateMatrixWorld(true);
    if(camera.position.distanceTo(home)<.001&&Math.abs(camera.zoom-1)<.0001)reset();
  }
  return{camera,update,tick,reset,setEnabled(value){if(controls.enabled&&!value)reset();controls.enabled=value;},resize(width,height){aspect=width/Math.max(1,height);if(lastState)update(lastState,{interior:lastInterior});},get report(){const relative=camera.position.clone().sub(target);return{projection:'orthographic',behavior:'return-on-release',defaultPitchDegrees:30,pitchDegrees:THREE.MathUtils.radToDeg(Math.atan2(relative.y,Math.hypot(relative.x,relative.z))),yawDegrees:THREE.MathUtils.radToDeg(Math.atan2(relative.x,relative.z)),interactive:controls.enabled,dragging,returning,position:camera.position.toArray(),target:target.toArray(),quaternion:camera.quaternion.toArray(),zoom:camera.zoom,frustum:[camera.left,camera.right,camera.top,camera.bottom]};}};
}
