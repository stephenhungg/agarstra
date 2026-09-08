import fs from 'node:fs';
import {execFileSync} from 'node:child_process';
export function readROM(){
 const file=process.argv[2]||process.env.NES_ROM;
 if(!file)throw new Error('Provide the SMB3 ROM path as the first argument or NES_ROM environment variable.');
 if(!file.toLowerCase().endsWith('.zip'))return fs.readFileSync(file);
 const entry=execFileSync('unzip',['-Z1',file],{encoding:'utf8',maxBuffer:1024*1024}).split('\n').find(name=>/\.nes$/i.test(name));
 if(!entry)throw new Error('No .nes file in ZIP archive.');
 return execFileSync('unzip',['-p',file,entry],{maxBuffer:8*1024*1024});
}
