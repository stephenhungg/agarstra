const fs=require('node:fs');
const path=require('node:path');
const crypto=require('node:crypto');
const ROM='41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc';
function validate(bytes){const b=Buffer.from(bytes);if(b.length!==397312||b.readUInt32LE(0)!==0x0100000b)throw Error('Invalid FireRed snapshot');return b;}
function save(file,bytes){const b=validate(bytes),record={version:1,romSHA1:ROM,savedAt:new Date().toISOString(),sha256:crypto.createHash('sha256').update(b).digest('hex'),state:b.toString('base64')};fs.mkdirSync(path.dirname(file),{recursive:true});const temp=file+'.tmp';fs.writeFileSync(temp,JSON.stringify(record));fs.renameSync(temp,file);return {savedAt:record.savedAt};}
function load(file){if(!fs.existsSync(file))return null;const r=JSON.parse(fs.readFileSync(file,'utf8'));if(r.version!==1||r.romSHA1!==ROM)throw Error('Save is for a different ROM');const b=validate(Buffer.from(r.state,'base64'));if(crypto.createHash('sha256').update(b).digest('hex')!==r.sha256)throw Error('Save checksum mismatch');return{bytes:new Uint8Array(b),savedAt:r.savedAt};}
module.exports={save,load};
