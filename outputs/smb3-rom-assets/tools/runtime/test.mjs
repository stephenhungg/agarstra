import {readROM} from './read-rom.mjs';
import fs from 'node:fs';import assert from'node:assert/strict';import{NES}from'../../../smb3-demo/src/vendor/jsnes/index.js';import{RomAssetExtractor,recompose}from'../../../smb3-demo/src/rom-extractor.js';
const rom=readROM();let source;const nes=new NES({emulateSound:false,onFrame:p=>source=Uint32Array.from(p)});nes.loadROM(rom);
const actions={300:[3,true],302:[3,false],600:[3,true],602:[3,false],900:[0,true],902:[0,false],1000:[7,true],1002:[7,false],1100:[4,true],1102:[4,false],1200:[0,true],1202:[0,false],1400:[7,true],1430:[0,true],1460:[0,false]};let extractor;
const results=[];
for(let i=0;i<1650;i++){
 if(i===1380)extractor=new RomAssetExtractor(nes,rom);
 if(actions[i])nes[actions[i][1]?'buttonDown':'buttonUp'](1,actions[i][0]);nes.frame();
 if([1390,1420,1450,1500,1550,1600,1649].includes(i)){
 const frame=extractor.getFrame(),reconstructed=recompose(frame);let mismatch=0,playfield=0;const first=[];for(let j=0;j<source.length;j++)if(source[j]!==reconstructed[j]){mismatch++;if(j<192*256)playfield++;if(first.length<10)first.push({x:j%256,y:Math.floor(j/256),expected:source[j],actual:reconstructed[j]});}
 results.push({frame:i,mismatch,playfield,assets:frame.assets.length,tiles:frame.backgroundTiles.length,sprites:frame.sprites.length,unresolved:frame.assets.filter(a=>!a.romSources.length).length,first});
 }
}
console.log(JSON.stringify(results,null,2));fs.writeFileSync(new URL('./results.json',import.meta.url),JSON.stringify(results,null,2));assert(results.every(r=>r.mismatch===0));
