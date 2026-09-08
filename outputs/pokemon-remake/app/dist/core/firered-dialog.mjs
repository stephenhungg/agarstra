// FireRed US 1.0, matching pret c75f3523. No writes or frame advancement.
const WINDOWS=0x020204b4, PRINTERS=0x02020034;
const BUFFERS=[{address:0x02021d18,size:1000,name:'gStringVar4'},{address:0x0202298c,size:300,name:'gDisplayedStringBattle'}];
const extra={0:' ',1:'À',2:'Á',3:'Â',4:'Ç',5:'È',6:'É',7:'Ê',8:'Ë',9:'Ì',11:'Î',12:'Ï',13:'Ò',14:'Ó',15:'Ô',16:'Œ',17:'Ù',18:'Ú',19:'Û',20:'Ñ',21:'ß',22:'à',23:'á',25:'ç',26:'è',27:'é',28:'ê',29:'ë',30:'ì',32:'î',33:'ï',34:'ò',35:'ó',36:'ô',37:'œ',38:'ù',39:'ú',40:'û',41:'ñ',42:'º',43:'ª',45:'&',46:'+',52:'Lv',53:'=',54:';',81:'¿',82:'¡',83:'PK',84:'MN',90:'Í',91:'%',92:'(',93:')',104:'â',111:'í',119:' ',121:'↑',122:'↓',123:'←',124:'→',133:'<',134:'>',171:'!',172:'?',173:'.',174:'-',175:'·',176:'…',177:'“',178:'”',179:'‘',180:'’',181:'♂',182:'♀',183:'₽',184:',',185:'×',186:'/',239:'▶',240:':',241:'Ä',242:'Ö',243:'Ü',244:'ä',245:'ö',246:'ü'};
export function decodeCharacter(byte){if(byte>=0xa1&&byte<=0xaa)return String(byte-0xa1);if(byte>=0xbb&&byte<=0xd4)return String.fromCharCode(65+byte-0xbb);if(byte>=0xd5&&byte<=0xee)return String.fromCharCode(97+byte-0xd5);return extra[byte]??null;}
const args={1:1,2:1,3:1,4:3,5:1,6:1,7:0,8:1,9:0,10:0,11:2,12:1,13:1,14:1,15:0,16:2,17:1,18:1,19:1,20:1,21:0,22:0,23:0,24:0};

export function decodePrintedPrefix(bytes,consumed,printerState=0){
  let text='',unsupported=null;let i=0;
  while(i<Math.min(consumed,bytes.length)){
    const b=bytes[i++];if(b===0xff)break;
    if(b===0xfe){text+='\n';continue;}
    if(b===0xfb||b===0xfa){
      // Pointer advances before waiting. Do not reveal the next page early.
      const waiting=i===consumed&&(printerState===2||printerState===3);
      if(!waiting){if(b===0xfb)text='';else{text=text.split('\n').slice(1).join('\n');text+='\n';}}
      continue;
    }
    if(b===0xfc){const code=bytes[i++],n=args[code];if(n===undefined){unsupported='unknown-control';break;}if([12,13,14,17,18,19,21].includes(code)){unsupported='layout-or-language-control';break;}if(code===15)text='';i+=n;continue;}
    if(b===0xfd||b===0xf8||b===0xf9){unsupported='dynamic-symbol';break;}
    const char=decodeCharacter(b);if(char===null){unsupported=`glyph-${b.toString(16)}`;break;}text+=char;
  }
  if(printerState===4)unsupported='source-scroll-animation';
  return{text,complete:bytes[Math.max(0,consumed-1)]===0xff,unsupported};
}

function tileAddress(base,width,x,y){return base+((Math.floor(y/32)*(width/256)+Math.floor(x/32))*1024+(y%32)*32+(x%32))*2;}
export function readVisibleWindows(core){
  const display=core.read16(0x04000000),out=[];
  for(let id=0;id<32;id++){
    const a=WINDOWS+id*12,b=core.readBytes(a,12),bg=b[0],left=b[1],top=b[2],width=b[3],height=b[4];
    if(bg>3||!(display&(1<<(8+bg)))||!width||!height||width>32||height>32)continue;
    const ptr=new DataView(b.buffer).getUint32(8,true);if(ptr<0x02000000||ptr>=0x02040000)continue;
    const control=core.read16(0x04000008+bg*2),size=control>>14,bgWidth=(size===1||size===3)?512:256,bgHeight=size>=2?512:256;
    const scrollX=core.read16(0x04000010+bg*4)&511,scrollY=core.read16(0x04000012+bg*4)&511;
    let x=((left*8-scrollX)%bgWidth+bgWidth)%bgWidth,y=((top*8-scrollY)%bgHeight+bgHeight)%bgHeight;
    if(x>=240)x-=bgWidth;if(y>=160)y-=bgHeight;
    if(x+width*8<=0||y+height*8<=0||x>=240||y>=160)continue;
    const baseBlock=b[6]|b[7]<<8,screenBase=0x06000000+((control>>8)&31)*0x800;
    let matches=0;
    for(const [cx,cy]of [[0,0],[Math.floor(width/2),Math.floor(height/2)],[width-1,height-1]]){
      const tx=(left+cx)%(bgWidth/8),ty=(top+cy)%(bgHeight/8),entry=core.read16(tileAddress(screenBase,bgWidth,tx,ty));
      if((entry&1023)===((baseBlock+cy*width+cx)&1023))matches++;
    }
    if(!matches)continue; // allocated window ≠ visible window
    const px=Math.max(0,x-8),py=Math.max(0,y-8),right=Math.min(240,x+width*8+8),bottom=Math.min(160,y+height*8+8);
    out.push({id,bg,x,y,width:width*8,height:height*8,palette:b[5],baseBlock,tileData:ptr,rect:{x:px,y:py,width:right-px,height:bottom-py},sourceAddress:a});
  }
  return out;
}

export function readFireRedDialog(core,state){
  const windows=readVisibleWindows(core),window=windows.find(w=>w.width>=160&&w.height<=64&&w.y>=80),battle=state?.battle?.active;
  let dialog=null;
  if(window&&window.width>=160&&window.height<=64&&window.y>=80){
    const b=core.readBytes(PRINTERS+window.id*36,36),cursor=new DataView(b.buffer).getUint32(0,true),active=!!b[27],printerState=b[28];
    const buffer=BUFFERS.find(v=>cursor>=v.address&&cursor<=v.address+v.size);
    let decoded=null;
    if(buffer&&b[4]===window.id){const consumed=cursor-buffer.address,bytes=core.readBytes(buffer.address,buffer.size);decoded=decodePrintedPrefix(bytes,consumed,printerState);}
    dialog={windowId:window.id,rect:window.rect,mode:decoded&&!decoded.unsupported?'text':'pixels',text:decoded?.text??'',active,printerState,waiting:[1,2,3].includes(printerState),complete:decoded?.complete??false,reason:decoded?.unsupported??(buffer?null:'unrecognized-string-source'),source:{printerAddress:PRINTERS+window.id*36,cursor,buffer:buffer?.name??null},battle:!!battle};
  }
  // Battle menus have a dedicated owner. Overworld ancillary windows preserve
  // exact options/cursor as bounded source pixels until a semantic decoder exists.
  const auxiliary=battle?[]:windows.filter(w=>w.id!==window?.id&&w.rect.width*w.rect.height<240*120);
  return{frame:core.frame,dialog,windows,auxiliary};
}

export function cropSourcePixels(core,rect){
  const source=core.pixels(),out=new Uint8ClampedArray(rect.width*rect.height*4);
  for(let y=0;y<rect.height;y++){const start=((rect.y+y)*240+rect.x)*4;out.set(source.subarray(start,start+rect.width*4),y*rect.width*4);}
  return out;
}
