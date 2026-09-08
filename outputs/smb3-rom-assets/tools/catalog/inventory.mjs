import fs from 'node:fs';import path from 'node:path';import crypto from 'node:crypto';import {fileURLToPath} from 'node:url';import {atlas} from './atlas.mjs';
const out=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../catalog');
const romPath=process.argv[2]||process.env.SMB3_ROM||(()=>{throw Error('Pass the source ROM path as the first argument or set SMB3_ROM')})();const rom=fs.readFileSync(romPath);
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
if(rom.toString('ascii',0,4)!=='NES\x1a')throw Error('Expected iNES image');
const trainerBytes=rom[6]&4?512:0,prgBytes=rom[4]*16384,chrStart=16+trainerBytes+prgBytes,chrBytes=rom[5]*8192;
const patterns=new Map(),tiles=[];
for(let offset=0;offset<chrBytes;offset+=16){const bytes=rom.subarray(chrStart+offset,chrStart+offset+16),sha=hash(bytes),indices=[];
 for(let y=0;y<8;y++)for(let x=0;x<8;x++)indices.push(((bytes[y]>>(7-x))&1)|(((bytes[y+8]>>(7-x))&1)<<1));
 const t={index:offset/16,chrByteOffset:offset,romByteOffset:chrStart+offset,bank4k:Math.floor(offset/4096),tileInBank:offset/16%256,sha256:sha,rawHex:bytes.toString('hex'),indices,width:8,height:8,rgba:indices.flatMap(c=>{let v=[22,92,166,244][c];return[v,v,v,255]})};
 if(!patterns.has(sha))patterns.set(sha,{sha256:sha,rawHex:t.rawHex,indices,physicalTileIndices:[],romByteOffsets:[],allZero:bytes.every(b=>b===0),uniformColor:new Set(indices).size===1});
 const p=patterns.get(sha);p.physicalTileIndices.push(t.index);p.romByteOffsets.push(t.romByteOffset);t.patternIndex=[...patterns.keys()].indexOf(sha);tiles.push(t);
}
const pages=atlas(tiles,out,'all-chr-patterns',{cols:32,perPage:1024,cell:10,scale:3});
const inventory={format:'smb3-complete-physical-chr-inventory-v2',romSHA256:hash(rom),romBytes:rom.length,headerHex:rom.subarray(0,16).toString('hex'),chrStart,chrBytes,physicalTileCount:tiles.length,uniquePatternCount:patterns.size,duplicatePhysicalTileCount:tiles.length-patterns.size,allZeroPhysicalTileCount:tiles.filter(t=>/^0+$/.test(t.rawHex)).length,coverage:'Every physical 16-byte CHR tile in the supplied iNES image. Not an exhaustive semantic object census. The gray atlas encodes 2-bit pixel indices, not inferred game colors.',pages,tiles:tiles.map(({rgba,width,height,...t})=>t),patterns:[...patterns.values()]};
fs.writeFileSync(path.join(out,'all-chr-inventory.json'),JSON.stringify(inventory,null,2));fs.writeFileSync(path.join(out,'chr.bin'),rom.subarray(chrStart,chrStart+chrBytes));
console.log(JSON.stringify({physicalTiles:tiles.length,uniquePatterns:patterns.size,duplicatePhysicalTiles:tiles.length-patterns.size,pages:pages.length}));
