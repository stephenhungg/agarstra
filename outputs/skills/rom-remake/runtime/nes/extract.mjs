#!/usr/bin/env node
import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';
import { createHash } from 'node:crypto';
import { NES, Controller } from './vendor/jsnes/index.js';
import { RomAssetExtractor, recompose } from './rom-extractor.js';
import { decodeTile } from './ingest.mjs';
import { loadRom } from './load-rom.mjs';
export const hash=b=>createHash('sha256').update(b).digest('hex');
const serialize=v=>JSON.stringify(v,(_k,x)=>ArrayBuffer.isView(x)?Array.from(x):x);
export function normalizeInputs(input,frames) {
 const events=Array.isArray(input)?input:input.events;
 if(!Array.isArray(events))throw Error('Replay must be an event array or {events: [...]}');
 return events.map((e,i)=>{
  const frame=e.frame,button=String(e.button).toUpperCase(),player=e.player??1,down=e.down;
  if(!Number.isInteger(frame)||frame<0||frame>=frames||![1,2].includes(player)||typeof down!=='boolean'||!Number.isInteger(Controller[`BUTTON_${button}`]))throw Error(`Invalid replay event ${i}: use frame (zero-based), button, down:boolean, player:1|2.`);
  return {frame,button,down,player};
 }).sort((a,b)=>a.frame-b.frame);
}
export async function extract({rom,out,frames=300,inputs=[]}) {
 if(!Number.isInteger(frames)||frames<1||frames>36000)throw Error('frames must be an integer from 1 to 36000.');
 const {bytes,header,archiveMember}=await loadRom(rom),romSha256=hash(bytes),events=normalizeInputs(inputs,frames);
 let framebuffer;
 const nes=new NES({emulateSound:false,onFrame:p=>{framebuffer=new Uint32Array(p);}});
 nes.loadROM(bytes);const observer=new RomAssetExtractor(nes,bytes),trace=[];let ei=0;
 for(let frame=0;frame<frames;frame++){
  while(events[ei]?.frame===frame){const e=events[ei++];nes[e.down?'buttonDown':'buttonUp'](e.player,Controller[`BUTTON_${e.button}`]);}
  nes.frame();const captured=observer.getFrame(),rebuilt=recompose(captured);let mismatchedPixels=0;
  for(let i=0;i<rebuilt.length;i++)if(rebuilt[i]!==framebuffer[i])mismatchedPixels++;
  trace.push({frame,frameSha256:hash(Buffer.from(framebuffer.buffer)),ramSha256:hash(Buffer.from(nes.cpu.mem.slice(0,2048))),oamSha256:hash(Buffer.from(nes.ppu.spriteMem)),recomposedSha256:hash(Buffer.from(rebuilt.buffer)),mismatchedPixels});
 }
 const catalog=[...observer.assets.values()].map(a=>({...a,id:hash(a.id).slice(0,24),sourceAssetId:a.id,romSha256}));
 const rawTiles=[];for(let offset=0;offset<header.chrBytes;offset+=16){const tile=bytes.subarray(header.chrStart+offset,header.chrStart+offset+16);rawTiles.push({id:`chr-${offset/16}`,tileIndex:offset/16,chrOffset:offset,romOffset:header.chrStart+offset,byteLength:16,bank1k:Math.floor(offset/1024),romSha256,chrBytes:Array.from(tile),pixels:decodeTile(tile)});}
 const mismatchFrames=trace.filter(t=>t.mismatchedPixels>0).length;
 const source={schemaVersion:1,romSha256,archiveMember,header,emulator:'JSNES 2.1.0 + documented 8x16 sprite patch',coverage:{frames,allRawChrTiles:rawTiles.length,observedPaletteVariants:catalog.length,semanticObjects:false,binaryDecompilation:false,scope:'Complete immutable CHR-ROM tile inventory; palette variants and PPU draw state observed only during this replay.',recompositionMismatchFrames:mismatchFrames},limitations:['No semantic level/object/action inference.','Unvisited gameplay states have no observed palettes.','No source-code recovery or general binary decompilation.','NTSC iNES CHR-ROM mappers 0 and 4 only.']};
 await mkdir(out,{recursive:true});
 const artifacts={'source.json':source,'raw-tiles.json':rawTiles,'catalog.json':catalog,'capture.json':observer.getFrame(),'replay.json':{schemaVersion:1,romSha256,frames,events,trace},'state.json':nes.toJSON()};
 for(const [name,value] of Object.entries(artifacts))await writeFile(resolve(out,name),serialize(value)+'\n');
 return source;
}
if(process.argv[1]&&import.meta.url===pathToFileURL(resolve(process.argv[1])).href){
 try{const args={};for(let i=2;i<process.argv.length;i+=2){if(!['--rom','--out','--frames','--inputs'].includes(process.argv[i])||!process.argv[i+1])throw Error('Usage: node extract.mjs --rom game.nes --out directory [--frames 300] [--inputs replay.json]');args[process.argv[i].slice(2)]=process.argv[i+1];}if(!args.rom||!args.out)throw Error('--rom and --out are required');const result=await extract({rom:resolve(args.rom),out:resolve(args.out),frames:args.frames?Number(args.frames):300,inputs:args.inputs?JSON.parse(await readFile(args.inputs,'utf8')):[]});console.log(JSON.stringify(result,null,2));}catch(e){console.error(e.message);process.exitCode=1;}
}
