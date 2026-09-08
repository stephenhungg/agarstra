import { readFile } from 'node:fs/promises';
import { inflateRawSync } from 'node:zlib';
import { inspectRom } from './ingest.mjs';
const LIMIT=32*1024*1024;
function crc32(b){let c=0xffffffff;for(const n of b){c^=n;for(let k=0;k<8;k++)c=(c>>>1)^((c&1)?0xedb88320:0);}return (c^0xffffffff)>>>0;}
export async function loadRom(path) {
 const input=await readFile(path); if(input.length>LIMIT)throw Error('ROM/archive exceeds 32 MiB limit.');
 let bytes=input,archiveMember=null;
 if(input.length>=4 && input.readUInt32LE(0)===0x04034b50){
  let end=-1;for(let p=input.length-22;p>=Math.max(0,input.length-65557);p--)if(input.readUInt32LE(p)===0x06054b50){end=p;break;}
  if(end<0)throw Error('ZIP end directory missing.');
  if(input.readUInt16LE(end+4)||input.readUInt16LE(end+6))throw Error('Multi-disk ZIP unsupported.');
  let pos=input.readUInt32LE(end+16);const candidates=[];
  for(let i=0;i<input.readUInt16LE(end+10);i++){
   if(pos+46>input.length||input.readUInt32LE(pos)!==0x02014b50)throw Error('Invalid ZIP directory.');
   const flags=input.readUInt16LE(pos+8),method=input.readUInt16LE(pos+10),crc=input.readUInt32LE(pos+16),size=input.readUInt32LE(pos+20),rawSize=input.readUInt32LE(pos+24),n=input.readUInt16LE(pos+28),extra=input.readUInt16LE(pos+30),comment=input.readUInt16LE(pos+32),offset=input.readUInt32LE(pos+42),name=input.subarray(pos+46,pos+46+n).toString('utf8');
   if(/\.nes$/i.test(name))candidates.push({flags,method,crc,size,rawSize,offset,name});pos+=46+n+extra+comment;
  }
  if(candidates.length!==1)throw Error(`ZIP must contain exactly one .nes ROM; found ${candidates.length}.`);
  const a=candidates[0];if(a.flags&1)throw Error('Encrypted ZIP unsupported.');if(a.rawSize>LIMIT)throw Error('Expanded ROM exceeds 32 MiB.');
  if(a.offset+30>input.length||input.readUInt32LE(a.offset)!==0x04034b50)throw Error('Invalid ZIP local entry.');
  const start=a.offset+30+input.readUInt16LE(a.offset+26)+input.readUInt16LE(a.offset+28);
  if(start+a.size>input.length)throw Error('Truncated ZIP payload.');
  const compressed=input.subarray(start,start+a.size);bytes=a.method===0?compressed:a.method===8?inflateRawSync(compressed,{maxOutputLength:LIMIT}):null;
  if(!bytes)throw Error(`ZIP method ${a.method} unsupported.`);if(bytes.length!==a.rawSize||crc32(bytes)!==a.crc)throw Error('ZIP ROM integrity check failed.');archiveMember=a.name;
 }
 return {bytes,header:inspectRom(bytes),archiveMember};
}
