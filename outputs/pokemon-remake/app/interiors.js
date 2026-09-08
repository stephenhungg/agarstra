import * as THREE from 'three';
import {RoundedBoxGeometry} from 'three/addons/geometries/RoundedBoxGeometry.js';

// Source-aligned presentation only. GBA owns movement, interaction and collision.
export async function createInteriors(renderer){
  const manifest=await(await fetch(new URL('../source/interiors.json',import.meta.url))).json();
  const group=new THREE.Group();group.name='FireRed source interiors';
  const camera=new THREE.PerspectiveCamera(38,1,.05,100);let aspect=1,last=null,current=null,enabled=true,playerModelVisible=false,sourceCharactersVisible=false;
  const material=(color,roughness=.75,metalness=0)=>new THREE.MeshStandardMaterial({color,roughness,metalness});
  const M={wood:material('#755339'),edge:material('#3e3028'),oak:material('#ad8a59'),cream:material('#e6dfc7'),wall:material('#d9d6bc'),metal:material('#879c9c',.3,.7),dark:material('#263534'),white:material('#eef1df'),green:material('#739a60'),rug:material('#719557'),blue:material('#69949c'),red:material('#b75741'),glass:new THREE.MeshStandardMaterial({color:'#a9dcd4',roughness:.12,metalness:.1,transparent:true,opacity:.72}),screen:new THREE.MeshStandardMaterial({color:'#afc6b1',roughness:.4,emissive:'#486658',emissiveIntensity:.3})};
  const mesh=(parent,geometry,mat,x,y,z)=>{const o=new THREE.Mesh(geometry,mat);o.position.set(x,y,z);o.castShadow=true;o.receiveShadow=true;parent.add(o);return o;};
  const box=(p,w,h,d,m,x,y,z,r=.025)=>mesh(p,new RoundedBoxGeometry(w,h,d,2,Math.min(r,w/5,h/5,d/5)),m,x,y,z);
  function legs(p,x,z,w,d,height,mat=M.wood){for(const dx of [-1,1])for(const dz of [-1,1])box(p,.09,height,.09,mat,x+dx*(w/2-.1),height/2,z+dz*(d/2-.1));}
  function desk(p,x,z,w=1.7,d=.8){legs(p,x,z,w,d,.7);box(p,w,.1,d,M.oak,x,.75,z);box(p,w,.05,.08,M.edge,x,.69,z+d/2-.04);}
  function books(p,x,z,width,height=1.7){
    box(p,width,height,.48,M.oak,x,height/2,z);box(p,width-.12,height-.1,.045,M.edge,x,height/2,z+.249);
    for(const y of [.12,.62,1.12,1.64])box(p,width,.065,.52,M.wood,x,y,z+.02);
    const count=Math.max(6,Math.floor(width*10)),book=new THREE.InstancedMesh(new THREE.BoxGeometry(.085,.36,.25),M.white,count*2),matrix=new THREE.Matrix4(),colors=['#8d4e37','#627c78','#c2b26b','#61728d','#c7c4a8'];
    for(let row=0;row<2;row++)for(let i=0;i<count;i++){matrix.makeTranslation(x-width/2+.1+i*(width-.15)/count,.35+row*.5,z+.29);book.setMatrixAt(row*count+i,matrix);book.setColorAt(row*count+i,new THREE.Color(colors[(i+row*3)%colors.length]));}book.castShadow=true;p.add(book);
  }
  function tv(p,x,z){box(p,.77,.65,.46,M.cream,x,.8,z);box(p,.59,.4,.025,M.screen,x-.045,.85,z+.24);box(p,.04,.07,.025,M.dark,x+.31,.78,z+.24);box(p,.65,.42,.52,M.oak,x,.23,z);}
  function pc(p,x,z){box(p,.57,.5,.4,M.cream,x,1.05,z);box(p,.43,.31,.035,M.screen,x,1.08,z+.21);box(p,.66,.045,.24,M.cream,x,.785,z+.4);for(let i=0;i<6;i++)box(p,.065,.012,.035,M.dark,x-.22+i*.085,.816,z+.4);}
  function plant(p,x,z){mesh(p,new THREE.CylinderGeometry(.2,.14,.38,16),M.cream,x,.19,z);mesh(p,new THREE.CylinderGeometry(.19,.19,.025,16),M.edge,x,.39,z);for(let i=0;i<7;i++){const leaf=mesh(p,new THREE.SphereGeometry(.19,10,8),M.green,x+Math.sin(i*2.4)*.15,.75+(i%3)*.13,z+Math.cos(i*2.4)*.15);leaf.scale.set(.6,1.6,.38);leaf.rotation.z=Math.sin(i)*.7;}}
  function chair(p,x,z,side){const c=new THREE.Group();c.position.set(x,0,z);c.rotation.y=side;legs(c,0,0,.55,.55,.4);box(c,.61,.09,.61,M.blue,0,.43,0);box(c,.59,.53,.08,M.blue,0,.7,-.27);p.add(c);}
  function floor(room,map,lab){
    const cells=[];for(let z=1;z<map.height;z++)for(let x=0;x<map.width;x++)if(map.metatileIds[z*map.width+x]!==8)cells.push([x,z]);
    const geom=lab?new THREE.BoxGeometry(.975,.08,.975):new THREE.BoxGeometry(.97,.08,.23);
    const pieces=lab?1:4,inst=new THREE.InstancedMesh(geom,M.white,cells.length*pieces),matrix=new THREE.Matrix4(),color=new THREE.Color();let i=0;
    for(const [x,z]of cells)for(let n=0;n<pieces;n++){
      matrix.makeRotationY(!lab&&(x+z)%2?Math.PI/2:0);const off=lab?0:(n-1.5)*.245;
      matrix.setPosition(x+(!lab&&(x+z)%2?off:0),-.045,z+(!lab&&(x+z)%2?0:off));inst.setMatrixAt(i,matrix);
      color.set(lab?'#c9d2cd':'#a48851');color.multiplyScalar(.92+((x*19+z*13+n*7)%11)/75);inst.setColorAt(i++,color);
    }inst.receiveShadow=true;room.add(inst);
    box(room,map.width+.25,.2,map.height+.1,M.edge,(map.width-1)/2,-.2,(map.height-1)/2);
  }
  const rooms=new Map();
  for(const [name,map]of Object.entries(manifest.maps)){
    const room=new THREE.Group();room.name=name;room.visible=false;group.add(room);const lab=name.includes('Lab');floor(room,map,lab);
    const left=lab?-.5:.5,right=map.width-.5;
    box(room,right-left,2.5,.17,M.wall,(left+right)/2,1.25,.38);box(room,right-left,.11,.2,M.cream,(left+right)/2,2.47,.4);box(room,right-left,.15,.22,M.blue,(left+right)/2,.25,.49);
    // Cutaway side walls keep source-positioned interactions readable.
    for(const x of [left,right])box(room,.12,.38,map.height-1,M.wall,x,.19,(map.height-1)/2+.5);
    for(const feature of map.features){const [x0,z0,x1,z1]=feature.bounds,x=(x0+x1)/2,z=(z0+z1)/2,w=x1-x0+1,d=z1-z0+1;
      const item=new THREE.Group();item.name=feature.id;item.userData.sourceCells=feature.sourceCells;room.add(item);
      switch(feature.kind){
        case 'rug':box(item,w-.1,.025,d-.1,M.cream,x,.012,z);box(item,w-.3,.03,d-.3,M.rug,x,.029,z);break;
        case 'table':{const width=w-.15,depth=d-.4;desk(item,x,z,width,depth);box(item,width-.08,.018,depth-.08,lab?M.green:M.blue,x,.815,z);if(!lab)for(let n=0;n<5;n++)box(item,.08,.005,depth-.08,M.white,x-width/2+.18+n*.3,.827,z);break;}
        case 'desk':desk(item,x,z+.25,w-.15,1.55);break;
        case 'chair':chair(item,x,z,feature.id.endsWith('ne')||feature.id.endsWith('se')?-Math.PI/2:feature.id==='desk-chair'?0:Math.PI/2);break;
        case 'bookshelf':books(item,x,z+.35,w-.1,lab?1.7:1.9);break;
        case 'tv':tv(item,x,z+.3);break;
        case 'pc':pc(item,x,z+.7);break;
        case 'plant':plant(item,x,z+.25);break;
        case 'window':box(item,w-.1,1.4,.08,M.cream,x,1.65,.5);box(item,w-.28,1.18,.05,M.glass,x,1.65,.55);box(item,.045,1.2,.04,M.white,x,1.65,.59);box(item,w-.25,.04,.04,M.white,x,1.65,.59);break;
        case 'poster':box(item,.76,.95,.055,M.wood,x,1.67,.52);box(item,.65,.84,.04,M.white,x,1.67,.56);for(let k=0;k<4;k++)box(item,.45,.025,.008,k===0?M.blue:M.metal,x,1.88-k*.14,.59);break;
        case 'sink':box(item,w-.1,.7,.82,M.blue,x,.35,z+.2);box(item,w,.1,.95,M.cream,x,.75,z+.2);box(item,.65,.045,.6,M.metal,x-.3,.815,z+.23);box(item,.52,.045,.45,M.dark,x-.3,.834,z+.23);mesh(item,new THREE.CylinderGeometry(.035,.035,.38,8),M.metal,x-.3,.96,z-.12);break;
        case 'cupboard':box(item,w-.1,1.1,.57,M.oak,x,.55,z+.25);for(const dx of [-.35,.35])box(item,.05,.09,.04,M.metal,x+dx,.65,z+.56);box(item,w,.08,.65,M.cream,x,1.14,z+.25);break;
        case 'bed':{const width=1.42,depth=2.3;box(item,width,.3,depth,M.wood,x,.25,z);box(item,width-.1,.24,depth-.08,M.white,x,.51,z);box(item,width-.1,.12,1.42,M.green,x,.67,z+.35);box(item,1.06,.17,.46,M.cream,x,.68,z-.78,.08);box(item,width,.73,.12,M.edge,x,.48,z-depth/2);break;}
        case 'console':box(item,.55,.15,.42,M.cream,x,.14,z-.2);box(item,.26,.025,.22,M.dark,x,.23,z-.23);box(item,.32,.07,.14,M.dark,x-.2,.06,z+.17);break;
        case 'stairsUp':for(let i=0;i<7;i++)box(item,.26,.17*(i+1),1.05,M.oak,10.6+i*.25,.085*(i+1),2);box(item,.8,.025,.85,M.red,10,.04,2);break;
        case 'stairsDown':box(item,1.9,.028,1.5,M.dark,8.75,.025,2.55);for(let i=0;i<6;i++)box(item,.24,.05,1.18,M.oak,8.05+i*.28,.035+i*.013,2.55);box(item,.8,.025,.85,M.red,10,.04,2);box(item,1.9,.25,.1,M.cream,8.75,.15,3.3);break;
        case 'machine':box(item,.85,1.6,.8,M.metal,x,.8,z+.2);box(item,.7,.6,.06,M.screen,x,1.03,z+.63);for(let k=0;k<3;k++)box(item,.42,.08,.08,M.red,x,.25+k*.17,z+.65);break;
        case 'healer':mesh(item,new THREE.CylinderGeometry(.65,.8,.9,24),M.metal,x,.45,z);mesh(item,new THREE.CylinderGeometry(.77,.65,.25,24),M.cream,x,1.02,z);mesh(item,new THREE.SphereGeometry(.55,24,12,0,Math.PI*2,0,Math.PI/2),M.red,x,1.12,z);box(item,.52,.43,.2,M.cream,x,.37,z+.75);box(item,.34,.22,.025,M.screen,x,.4,z+.86);break;
        case 'rack':box(item,.5,1.2,.3,M.oak,x,.6,z);for(let k=0;k<3;k++)box(item,.44,.22,.18,k%2?M.blue:M.green,x,.35+k*.32,z+.18);break;
      }
    }
    for(const warp of map.warps){if(warp.y>=map.height-2)box(room,.85,.025,.75,M.red,warp.x,.04,Math.min(warp.y,map.height-1));}
    const actors=new Map();rooms.set(name,{room,map,actors});
  }
  const ambient=new THREE.HemisphereLight('#e5f0e5','#544330',1.7);group.add(ambient);
  const sun=new THREE.DirectionalLight('#ffecd0',3.1);sun.position.set(3,13,3);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);sun.shadow.camera.left=-14;sun.shadow.camera.right=14;sun.shadow.camera.top=16;sun.shadow.camera.bottom=-16;sun.shadow.bias=-.0003;group.add(sun);
  function aim(map){const x=(map.width-1)/2,z=(map.height-1)/2,span=Math.max(map.height,map.width/Math.max(.6,aspect));camera.position.set(x+span*.12,span*1.35,z+span*1.27);camera.lookAt(x,0,z+.1);camera.aspect=aspect;camera.updateProjectionMatrix();}
  function update(core,state){last=state;const found=rooms.get(state?.map?.name);current=found?state.map.name:null;for(const [name,data]of rooms)data.room.visible=enabled&&name===current;if(!found)return;
    group.visible=enabled;aim(found.map);const ids=new Set();
    for(const obj of state.objectEvents||[]){if(obj.hidden)continue;ids.add(obj.id);let a=found.actors.get(obj.id);if(!a){a=new THREE.Group();if(obj.graphicsId===92){mesh(a,new THREE.SphereGeometry(.18,16,12,0,Math.PI*2,0,Math.PI/2),M.red,0,.2,0);mesh(a,new THREE.SphereGeometry(.18,16,12,0,Math.PI*2,Math.PI/2,Math.PI/2),M.white,0,.2,0);mesh(a,new THREE.CylinderGeometry(.183,.183,.035,16),M.dark,0,.2,0);}else if(obj.graphicsId===94){box(a,.3,.09,.4,M.red,0,.1,0);}else{const marker=mesh(a,new THREE.TorusGeometry(.24,.045,8,24),obj.isPlayer?M.red:M.cream,0,.07,0);marker.rotation.x=Math.PI/2;const pointer=mesh(a,new THREE.ConeGeometry(.1,.22,8),marker.material,0,.1,.28);pointer.rotation.x=Math.PI/2;}a.userData.graphicsId=obj.graphicsId;found.room.add(a);found.actors.set(obj.id,a);}a.visible=(!sourceCharactersVisible||[92,94].includes(obj.graphicsId))&&!(obj.isPlayer&&playerModelVisible);a.position.set(obj.worldX,obj.graphicsId===92?.82:obj.graphicsId===94?.78:.025,obj.worldY);a.rotation.y=({down:0,up:Math.PI,left:-Math.PI/2,right:Math.PI/2})[obj.facing]??0;}
    for(const [id,a]of found.actors)if(!ids.has(id))a.visible=false;
  }
  const report={status:manifest.status,photorealApproved:false,maps:Object.fromEntries([...rooms].map(([name,v])=>[name,{width:v.map.width,height:v.map.height,features:v.map.features.length,warps:v.map.warps,sourceMapSHA256:v.map.mapDataSHA256}])),get activeMap(){return current;},get actorPositions(){return current?[...rooms.get(current).actors].map(([id,a])=>({id,x:a.position.x,z:a.position.z,visible:a.visible})):[];},limitations:['source-linked candidate geometry; not photoreal approved','source actors are supplied by the scene-level character renderer','source 2D furniture footprints are mapped; vertical forms and lighting are interpreted','cutaway walls preserve gameplay visibility']};
  return{group,camera,update,setSourceCharactersVisible(value){sourceCharactersVisible=value;for(const r of rooms.values())for(const a of r.actors.values())if(![92,94].includes(a.userData.graphicsId))a.visible=false;},setPlayerModelVisible(value){playerModelVisible=value;},resize(w,h){aspect=w/Math.max(1,h);if(current)aim(rooms.get(current).map);},supports(name){return rooms.has(name);},report,setVisible(value){enabled=value;group.visible=value;if(last)update(null,last);}};
}
