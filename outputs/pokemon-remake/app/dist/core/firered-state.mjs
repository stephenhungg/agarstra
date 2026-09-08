// Exact FireRed US 1.0 symbols from matching pret ELF, c75f3523.
// Read-only observer. It does not advance frames, write RAM, or infer game rules.
const S={main:0x030030f0,save1:0x03005008,objects:0x02036e38,avatar:0x02037078,sprites:0x0202063c,battleFlags:0x02022b4c,battleMons:0x02023be4,battleOutcome:0x02023e8a,battlersCount:0x02023bcc,totalCameraX:0x0300506c,totalCameraY:0x03005068};
const maps={"3:0":{"name":"PalletTown","width":24,"height":20},"3:19":{"name":"Route1","width":24,"height":40},"4:0":{"name":"PalletTown_PlayersHouse_1F","width":13,"height":10},"4:1":{"name":"PalletTown_PlayersHouse_2F","width":12,"height":9},"4:3":{"name":"PalletTown_ProfessorOaksLab","width":13,"height":14}};
const signed16=x=>(x<<16)>>16,signed8=x=>(x<<24)>>24;
const facing={1:'down',2:'up',3:'left',4:'right'};
export function readFireRedState(gba){
  const r8=a=>gba.read8(a),r16=a=>gba.read16(a),r32=a=>gba.read32(a),s16=a=>signed16(r16(a));
  const save=r32(S.save1),validSave=save>=0x02000000&&save+0x3d68<=0x02040000;
  const inBattle=!!(r8(S.main+0x439)&2),callback2=r32(S.main+4)>>>0;
  const overworld=(callback2&~1)===0x080565b4;
  const group=validSave?r8(save+4):null,number=validSave?r8(save+5):null;
  const meta=maps[`${group}:${number}`];
  const map=validSave?{group,number,name:meta?.name??`Map_${group}_${number}`,width:meta?.width??null,height:meta?.height??null}:null;
  const cameraX=(r32(0x03005060)|0),cameraY=(r32(0x03005064)|0);
  const cameraFractionX=cameraX/16-Math.sign(cameraX),cameraFractionY=cameraY/16-Math.sign(cameraY);
  const objects=[];
  if(validSave&&overworld&&!inBattle){
    for(let id=0;id<16;id++){
      const a=S.objects+id*0x24,flags=r32(a);if(!(flags&1))continue;
      const spriteId=r8(a+4);if(spriteId>=64)continue;
      const sprite=S.sprites+spriteId*0x44;
      const x=s16(sprite+0x20),y=s16(sprite+0x22),x2=s16(sprite+0x24),y2=s16(sprite+0x26),cornerY=signed8(r8(sprite+0x29));
      // Inverse of GetMapCoordsFromSpritePos plus SpawnObjectEvent sprite anchor.
      // Engine map grid has a 7-tile border. Coordinates below match map JSON.
      const worldX=(x-8+s16(S.totalCameraX))/16+s16(save)-7+cameraFractionX;
      const worldY=(y-16-cornerY+s16(S.totalCameraY))/16+s16(save+2)-7+cameraFractionY;
      objects.push({id,spriteId,graphicsId:r8(a+5),localId:r8(a+8),mapGroup:r8(a+10),mapNumber:r8(a+9),isPlayer:!!(flags&0x10000),hidden:!!(flags&0x2000),spriteInvisible:!!(r8(sprite+0x3e)&4),visible:!(flags&0x2000)&&!(r8(sprite+0x3e)&4),offScreen:!!(flags&0x4000),tileX:s16(a+0x10)-7,tileY:s16(a+0x12)-7,previousTileX:s16(a+0x14)-7,previousTileY:s16(a+0x16)-7,worldX,worldY,x:worldX,y:worldY,visualOffsetX:x2/16,visualOffsetY:y2/16,facing:facing[r8(a+0x18)&15]??'unknown',direction:r8(a+0x18)&15,movementDirection:r8(a+0x18)>>4,moving:!!(flags&2),elevation:r8(a+0xb)&15,animation:r8(sprite+0x2a),animationFrame:r8(sprite+0x2b),source:{objectAddress:a,spriteAddress:sprite}});
    }
  }
  const player=objects.find(o=>o.id===r8(S.avatar+5))??objects.find(o=>o.isPlayer)??null;
  if(player){player.runningState=r8(S.avatar+2);player.tileTransitionState=r8(S.avatar+3);player.avatarFlags=r8(S.avatar);}
  const battlers=[];
  if(inBattle){for(let id=0;id<Math.min(r8(S.battlersCount),4);id++){const a=S.battleMons+id*0x58;battlers.push({id,species:r16(a),hp:r16(a+0x28),maxHP:r16(a+0x2c),level:r8(a+0x2a),moves:[0,1,2,3].map(i=>r16(a+0xc+i*2)),sourceAddress:a});}}
  return{frame:gba.frame,callback2,phase:inBattle?'battle':overworld?'overworld':'transition-or-menu',map,player,objectEvents:objects,battle:{active:inBattle,flags:r32(S.battleFlags),outcome:r8(S.battleOutcome),battlers},source:{rom:'BPRE-0',verifiedSHA1:'41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc',saveBlock1:validSave?save:null}};
}
