/** World 1-1 semantics from the decoded level grid and the byte-identical Southbird disassembly.
 * SRAM layout: PRG/prg030.asm Tile_Mem_Addr; definitions: smb3.asm TILE1_/TILEA_.
 * Source rebuilt SHA256 4377a7f5e6eb50bdd2ac6f249bf1a7085500aca8eb41f38545c3a2731c51a579.
 * No raw CHR-index guessing. x is world NES pixels; y is visible NES pixels, downward.
 */
export const SEMANTIC_SOURCE={tileset:1,tableRomOffset:0x1e010,gridAddress:0x6000,screenStride:0x1b0,columnsPerScreen:16,rowsPerScreen:27,layoutPointer:0xbb82,source:'Southbird SMB3 disassembly, byte-identical rebuild',sourceCommit:'09b1bd81a788de8ceec664a34094e84ddb463117'};
const groups=[[0,36,8424],[36,36,16616],[72,36,24808],[108,36,33000],[144,36,41192]];
const stateNames=['empty','initializing','normal','shelled','held','kicked','killed','squashed','poof'];
const signed=n=>n>127?n-256:n;
const ranges=(v,a,b)=>v>=a&&v<=b;
const definitionCache=new WeakMap();
const sceneCache=new WeakMap();
const groundTop=v=>[0x53,0x55,0x57].includes(v);
export function defineMetatile(value,rom){
 let type,materialVariant='default',solid=false,merge=false,ignored=false;
 if([0x80,0x02,0x41,0x44,0x45,0x46,0xf3].includes(value)||ranges(value,0xc0,0xc5))ignored=true;
 else if(ranges(value,0x53,0x58)){type='ground';merge=true;solid=true;}
 else if(ranges(value,0x60,0x65)){type='question';solid=true;materialVariant=['flower','leaf','star','coin','coin-star','coin'][value-0x60];}
 else if(value===0x5f){type='used-block';solid=true;}
 else if(ranges(value,0x67,0x70)){type='brick';solid=true;}
 else if(ranges(value,0xad,0xbb)){type='pipe';solid=true;merge=true;materialVariant=ranges(value,0xb5,0xb9)?'horizontal':'vertical';}
 else if(value===0x86){type='bush';merge=true;}
 else if(ranges(value,0x90,0x9f)){type='hill';merge=true;}
 else if(ranges(value,0x1f,0x24)||value===0x06||ranges(value,0x10,0x12)){type='cloud';merge=true;}
 else if(value===0x40){type='coin';}
 else {
  const palettes=[{ids:[0x26,0x25,0x27],range:[7,15],color:'white'},{ids:[0x51,0x50,0x52],range:[0x47,0x4f],color:'orange'},{ids:[0xa1,0xa0,0xa2],range:[0x87,0x8f],color:'green'},{ids:[0xe3,0xe2,0xe4],range:[0xc7,0xcf],color:'blue'}];
  const p=palettes.find(p=>p.ids.includes(value)||ranges(value,...p.range));
  if(p){type='platform';materialVariant=p.color;merge=true;solid=true;}
 }
 const base=SEMANTIC_SOURCE.tableRomOffset;
 return {id:`smb3-ts1-metatile-${value.toString(16).padStart(2,'0')}`,metatileId:value,type:type||'unknown',materialVariant,solid,merge,ignored,paletteIndex:value>>6,patterns:rom?[rom[base+value],rom[base+256+value],rom[base+512+value],rom[base+768+value]]:null,patternOrder:'upper-left,lower-left,upper-right,lower-right'};
}
function componentObject(cells,definition,viewY){
 const minCol=Math.min(...cells.map(c=>c.column)),maxCol=Math.max(...cells.map(c=>c.column)),minRow=Math.min(...cells.map(c=>c.row)),maxRow=Math.max(...cells.map(c=>c.row));
 const x=minCol*16,worldY=minRow*16,width=(maxCol-minCol+1)*16,height=(maxRow-minRow+1)*16;
 const topProfile=[];for(let col=minCol;col<=maxCol;col++){const rows=cells.filter(c=>c.column===col).map(c=>c.row);if(rows.length)topProfile.push({x:col*16,y:Math.min(...rows)*16-viewY+1});}
 return {id:definition.merge?`w1-1:${definition.type}:${definition.materialVariant}:${Math.min(...cells.map(c=>c.address)).toString(16)}`:`w1-1:cell:${cells[0].address.toString(16)}`,type:definition.type,x,y:worldY-viewY+1,worldY,width,height,solid:definition.solid,materialVariant:definition.materialVariant,topProfile,cells:cells.map(c=>({x:c.column*16,y:c.row*16-viewY+1,worldY:c.row*16,width:16,height:16,metatileId:c.value,sourceAddress:c.address,definitionId:c.definition.id})),source:{definition:'Tile_Layout_TS1',definitionRomOffset:SEMANTIC_SOURCE.tableRomOffset,metatileIds:[...new Set(cells.map(c=>c.value))],sramAddresses:cells.map(c=>c.address),grid:'16 columns x 27 rows per horizontal screen'}};
}
function semanticEntities(bridge,base,viewY){
 const ram=bridge.nes.cpu.mem,rom=bridge.rom,entities=[],unknown=[];
 const spriteHeight=bridge.nes.ppu.f_spriteSize?16:8,raw=bridge.nes.ppu.spriteMem;
 const spriteKey=at=>`${raw[at+3]},${raw[at]+1},${raw[at+1]},${raw[at+2]},${spriteHeight}`;
 const effectDraw=(x,y,patterns,palette)=>{
  // CPU effect coordinates can be one update ahead of the displayed OAM. Identify
  // the source-defined pattern pair near its RAM anchor, then use the actual draw
  // coordinates. The 8px search covers one scroll/bounce/coin update; no CHR guessing.
  const candidates=new Map();for(let at=0;at<256;at+=4){if((raw[at+2]&3)!==palette||raw[at]+1>=192)continue;for(const[dx,tile]of patterns){if(raw[at+1]!==tile)continue;const ax=raw[at+3]-dx,ay=raw[at]+1;if(Math.abs(ax-x)>8||Math.abs(ay-y)>8)continue;const key=`${ax},${ay}`;candidates.set(key,{x:ax,y:ay,distance:Math.abs(ax-x)+Math.abs(ay-y)});}}
  const sorted=[...candidates.values()].sort((a,b)=>a.distance-b.distance);if(!sorted.length||sorted[1]?.distance===sorted[0].distance)return {x,y,keys:[],matched:false};
  const best=sorted[0],keys=[];for(let at=0;at<256;at+=4)if(raw[at]+1===best.y&&(raw[at+2]&3)===palette&&patterns.some(([dx,tile])=>raw[at+3]===best.x+dx&&raw[at+1]===tile))keys.push(spriteKey(at));return {...best,keys,matched:true};
 };
 for(let slot=0;slot<8;slot++){
  const state=ram[0x661+slot];if(!state)continue;
  const objectId=ram[0x671+slot],spawnIndex=ram[0x659+slot],group=groups.find(([first,count])=>objectId>=first&&objectId<first+count),attr=group?rom[group[2]+objectId-group[0]]:0;
  const nominalWidth=(((attr>>4)&7)+1)*8,nominalHeight=(((attr>>2)&3)+1)*16;
  let width=nominalWidth,height=nominalHeight;
  // Sprite positions are the engine's rendered position, not the one-tick-newer world RAM.
  const worldX=ram[0x91+slot]+256*ram[0x76+slot],spriteX=ram[0xac+slot],worldY=ram[0xa3+slot]+256*ram[0x88+slot];
  let x=spriteX+base.cameraX;while(x-worldX>128)x-=256;while(worldX-x>128)x+=256;
  let y=ram[0xb5+slot]+1;
  const oamStart=ram[0x58f+slot],rendered=[];
  // Object_SprRAM may already be allocated for the next frame. Match current
  // OAM extents to the source object's rendered anchor and source palette instead.
  for(let at=0;at<256;at+=4){
   const sy=bridge.nes.ppu.spriteMem[at]+1,sx=bridge.nes.ppu.spriteMem[at+3],pal=bridge.nes.ppu.spriteMem[at+2]&3;
   if(sy>=y&&sy<y+nominalHeight&&sy<192&&sx>=spriteX&&sx<spriteX+nominalWidth&&pal===(attr&3))rendered.push({x:sx,y:sy,key:spriteKey(at)});
  }
  const isBouncer=[6,0x1b].includes(objectId),bounceKind=ram[0x689+slot]>>4;
  if(isBouncer&&bounceKind<8){
   // PRG001 BounceBlock_Update bypasses the general object's attribute palette.
   const palettes=[1,2,3,3,1,3,3,1],patterns=[[0x79,0x7b],[0x79,0x7b],[0x77,0x77],[0x75,0x75],[0x79,0x7b],[0x7f,0x7f],[0x75,0x75],[0x7b,0x7b]][bounceKind];
   const draw=effectDraw(spriteX,y,[[0,patterns[0]],[8,patterns[1]]],palettes[bounceKind]);rendered.length=0;
   for(const key of draw.keys){const [sx,sy]=key.split(',').map(Number);rendered.push({x:sx,y:sy,key});}
  }
  if(rendered.length){const left=Math.min(...rendered.map(p=>p.x));x+=left-spriteX;y=Math.min(...rendered.map(p=>p.y));width=Math.max(...rendered.map(p=>p.x+8))-left;height=Math.max(...rendered.map(p=>p.y+16))-y;}
  let type=objectId===0x72?'goomba':[0x6c,0x6d].includes(objectId)?'koopa':ranges(objectId,0xa0,0xa5)?'piranha':[0x0b,0x0d].includes(objectId)?'mushroom':objectId===0x19?'flower':objectId===0x1e?'leaf':objectId===0x0c?'star':[6,0x1b].includes(objectId)?'bouncing-block':'unknown';
  const e={id:`object:${spawnIndex===255?'dynamic':spawnIndex}:${slot}:${objectId}`,type,x,y,worldX,worldY,width,height,visible:x+width>=base.cameraX&&x<=base.cameraX+256&&y<192&&Math.abs(worldY-viewY-y)<64,state:stateNames[state]||`state-${state}`,frame:ram[0x669+slot],flipX:!!(ram[0x679+slot]&64),materialVariant:objectId===0x6d?'red':objectId===0x0b?'one-up':'default',velocity:{x:signed(ram[0xbe+slot])/16,y:signed(ram[0xd0+slot])/16},source:{slot,objectId,spawnIndex,idAddress:0x671+slot,stateAddress:0x661+slot,attributeRomOffset:group?group[2]+objectId-group[0]:null,oamOffsetAddress:0x58f+slot,oamStart,nominalWidth,nominalHeight,spriteKeys:rendered.map(p=>p.key)}};
  if(type==='goomba'&&state===7)e.squashed=true;
  if(isBouncer){e.source.drawDefinition='PRG001 BounceBlock_Update / BounceBlock_Pal / BounceBlock_Tile';e.visible=e.visible&&rendered.length>0;}
  if(e.visible){entities.push(e);if(type==='unknown')unknown.push({kind:'entity',...e});}
 }
 for(let slot=0;slot<4;slot++)if(ram[0x7fb2+slot]){
  const x=ram[0x7fba+slot],y=ram[0x7fb6+slot]+1,draw=effectDraw(x,y,[[0,0x49],[0,0x4f],[0,0x4d]],3);
  entities.push({id:`coin-popup:${slot}`,type:'coin',x:draw.x+base.cameraX,y:draw.y,width:8,height:16,visible:draw.matched,state:'emerging',frame:(ram[0x7fc2+slot]>>2)&3,source:{slot,stateAddress:0x7fb2+slot,xAddress:0x7fba+slot,yAddress:0x7fb6+slot,ramX:x,ramY:y,definition:'CoinPUp_State / CoinPUp_X / CoinPUp_Y',spriteKeys:draw.keys}});
 }
 // Scores_GiveAndDraw uses separate effect slots, not Object_ID or guessed CHR tiles.
 // A value of 1..13 selects Score_PatternLeft/Right; bit 7 only changes OAM allocation.
 const scoreLabels=['10','20','40','80','100','200','400','800','1000','2000','4000','8000','1-UP'];
 const scoreLeft=[0xff,0xff,0xff,0xff,0x5b,0x63,0x6b,0x6d,0x5b,0x63,0x6b,0x6d,0x61],scoreRight=[0x5b,0x63,0x6b,0x6d,0x69,0x69,0x69,0x69,0x59,0x59,0x59,0x59,0x6f];
 for(let slot=0;slot<5;slot++){
  const value=ram[0x79e+slot]&0x7f;if(!value)continue;
  const index=Math.min(13,value)-1,x=ram[0x7ad+slot]+base.cameraX,y=ram[0x7a8+slot]+1;
  const patterns=[[8,scoreRight[index]]];if(scoreLeft[index]!==0xff)patterns.push([0,scoreLeft[index]]);const draw=effectDraw(x-base.cameraX,y,patterns,1);
  entities.push({id:`score-popup:${slot}`,type:'score',x:draw.x+base.cameraX,y:draw.y,width:16,height:16,visible:draw.matched,state:'floating',label:scoreLabels[index],value:index===12?null:Number(scoreLabels[index]),source:{slot,valueAddress:0x79e+slot,counterAddress:0x7a3+slot,xAddress:0x7ad+slot,yAddress:0x7a8+slot,ramX:x-base.cameraX,ramY:y,value:ram[0x79e+slot],counter:ram[0x7a3+slot],definition:'Scores_GiveAndDraw / Score_PatternLeft / Score_PatternRight',spriteKeys:draw.keys}});
 }
 return {entities,unknown};
}
export function buildSemanticScene(bridge,baseScene){
 const base=baseScene||{cameraX:bridge.cameraX,player:null},ram=bridge.nes.cpu.mem,rom=bridge.rom;
 const cached=sceneCache.get(bridge);if(cached?.base===base&&cached.frame===bridge.frame&&cached.ppu===bridge.nes.ppu)return cached.scene;
 const viewY=ram[0x542]*256+ram[0x543],layoutPointer=ram[0x7eb9]+256*ram[0x7eba],sameLevel=ram[0x70a]===1&&layoutPointer===SEMANTIC_SOURCE.layoutPointer;
 const mode=!sameLevel?'unmapped':ram[0xf1]?'death':'level';
 const valid=sameLevel&&viewY===239;
 // Renderability means the source grid is understood. Coverage is deliberately stricter:
 // a missing object or Mario's death pose must not replace the entire scene with 8-bit.
 if(!valid)return {cameraX:base.cameraX,cameraY:viewY,mode,supported:false,renderable:false,objects:[],entities:[],player:base.player,unknown:[],coverage:{supported:false,renderable:false,fallbackScope:'scene',reasonCode:sameLevel?'unmapped-camera':'unmapped-region',reason:sameLevel?'The current vertical camera is outside the verified World 1-1 view':'The current map or level has no verified whole-object reconstruction',layoutPointer,tileset:ram[0x70a]}};
 const screenCount=Math.min(15,ram[0x372]+1),byKey=new Map(),cells=[];
 let definitions=definitionCache.get(rom);if(!definitions){definitions=Array.from({length:256},(_,v)=>defineMetatile(v,rom));definitionCache.set(rom,definitions);}
 for(let screen=0;screen<screenCount;screen++)for(let row=0;row<27;row++)for(let col=0;col<16;col++){
  const address=0x6000+screen*0x1b0+row*16+col,value=ram[address],definition=definitions[value],column=screen*16+col;
  if(definition.ignored)continue;
  const cell={address,value,definition,column,row};cells.push(cell);byKey.set(`${column},${row}`,cell);
 }
 const visited=new Set(),objects=[],unknown=[];
 for(const first of cells){if(visited.has(first.address))continue;const group=[first];visited.add(first.address);
  if(first.definition.merge)for(let q=0;q<group.length;q++){const c=group[q];for(const[dx,dy]of[[1,0],[-1,0],[0,1],[0,-1]]){const next=byKey.get(`${c.column+dx},${c.row+dy}`);if(next&&!visited.has(next.address)&&next.definition.type===first.definition.type&&next.definition.materialVariant===first.definition.materialVariant&&(first.definition.type!=='ground'||(dy===0&&groundTop(first.value)&&groundTop(next.value)))){visited.add(next.address);group.push(next);}}}
  if(first.definition.type==='ground'){
   if(!groundTop(first.value))continue;
   for(const top of [...group])for(let row=top.row+1;row<27;row++){const body=byKey.get(`${top.column},${row}`);if(!body||body.definition.type!=='ground'||groundTop(body.value))break;if(!visited.has(body.address)){visited.add(body.address);group.push(body);}}
  }
  const object=componentObject(group,first.definition,viewY);
  if(object.type==='pipe'){object.orientation=object.materialVariant;object.hasRim=group.some(c=>ranges(c.value,0xad,0xb7));}
  if(object.x+object.width<base.cameraX-64||object.x>base.cameraX+320||object.y+object.height<=0||object.y>=192)continue;
  objects.push(object);if(object.type==='unknown')unknown.push({kind:'terrain',...object});
 }
 const dynamic=semanticEntities(bridge,base,viewY);unknown.push(...dynamic.unknown);
 const raw=bridge.nes.ppu.spriteMem,spriteHeight=bridge.nes.ppu.f_spriteSize?16:8,playerSpriteKeys=[];for(let at=32;at<48;at+=4)if(raw[at]+1<192)playerSpriteKeys.push(`${raw[at+3]},${raw[at]+1},${raw[at+1]},${raw[at+2]},${spriteHeight}`);
 const player={...base.player,frame:ram[0xee],suit:ram[0xed],inAir:!!ram[0xd8],dying:!!ram[0xf1],velocity:{x:signed(ram[0xbd])/16,y:signed(ram[0xcf])/16},source:{frameAddress:0xee,suitAddress:0xed,xAddress:0x90,yAddress:0xa2,poseDefinition:'SPPF_Table',poseTableRomOffset:240737,spriteKeys:playerSpriteKeys}};
 const visibleUnknown=unknown.filter(o=>o.x+o.width>base.cameraX&&o.x<base.cameraX+256&&o.y+o.height>0&&o.y<192);
 const supported=mode==='level'&&visibleUnknown.length===0;
 const scene={cameraX:base.cameraX,cameraY:viewY,mode,supported,renderable:true,objects,player,entities:dynamic.entities,unknown,coverage:{supported,renderable:true,fallbackScope:visibleUnknown.length?'objects':'none',reasonCode:visibleUnknown.length?'unmapped-objects':mode==='death'?'player-death':'verified',region:'world-1-1-overworld',screenCount,layoutPointer,unknownVisible:visibleUnknown.length,reason:visibleUnknown.length?'Unmapped source definitions require fallback for those objects only':mode==='death'?'Verified World 1-1 remains renderable during the original death animation':'Verified source definitions for visible objects'},source:SEMANTIC_SOURCE};
 sceneCache.set(bridge,{base,frame:bridge.frame,ppu:bridge.nes.ppu,scene});return scene;
}
