import assert from'node:assert/strict';import fs from'node:fs';import{NES}from'../../../smb3-demo/src/vendor/jsnes/index.js';
// Known synthetic pattern data tests address selection independently of frame parity.
let cases=0,pixels=0;
for(const number of[0,1,6,7,254,255])for(const flip of[0,64,128,192])for(const behind of[0,32]){
 const n=new NES({emulateSound:false,onFrame:()=>{}});n.mmap={latchAccess(){}};const p=n.ppu;p.f_spVisibility=1;p.f_spriteSize=1;p.sprPalette=[0,0x112233,0x445566,0x778899];
 const hardwareTop=(number&0xfe)+((number&1)?256:0);
 for(let index=0;index<512;index++)for(let y=0;y<8;y++)for(let x=0;x<8;x++)p.ptTile[index].pix[y*8+x]=(index*2+y+x)%3+1;
 p.buffer.fill(0);p.pixrendered.fill(65);
 for(let sy=0;sy<16;sy++){const scan=20+sy;p.scanlineSpriteCount[scan]=1;const base=scan*32;p.scanlineSecondaryOAM.set([19,number,flip|behind,40],base);}
 p.renderSpritesPartially(20,16,behind?1:0);
 for(let y=0;y<16;y++)for(let x=0;x<8;x++){
  const sourceY=(flip&128)?15-y:y,sourceX=(flip&64)?7-x:x;
  const expectedIndex=hardwareTop+Math.floor(sourceY/8),expectedColor=p.sprPalette[(expectedIndex*2+(sourceY%8)+sourceX)%3+1];
  assert.equal(p.buffer[(20+y)*256+40+x],expectedColor,`tile${number} flip${flip} priority${behind} pixel${x},${y}`);pixels++;
 }cases++;
}
const report={passed:true,cases,pixels,checks:['even and odd tile bank selection','top tile clears low bit without subtracting twice','horizontal flip','vertical flip swaps both halves and rows','sprite background priority variants'],scope:'direct synthetic 8x16 renderer conformance; separate from recomposition parity'};fs.writeFileSync(new URL('./conformance.json',import.meta.url),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
