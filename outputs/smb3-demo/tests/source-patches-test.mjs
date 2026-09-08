import assert from 'node:assert/strict';
import { GameBridge } from '../src/bridge.js';
import { rasterizeSourcePatches } from '../src/source-patches.js';
import { readROM } from './read-rom.mjs';
const b=new GameBridge();b.load(readROM());b.bootToLevel();
const scene=b.getScene(),cloud=scene.semantic.objects.find(o=>o.type==='cloud');
assert(cloud);
const patch=rasterizeSourcePatches(scene.extraction,[cloud],scene.cameraX);
assert(patch.pixelCount>0&&patch.pixelCount<4096);
let count=0;
for(let i=0;i<256*192;i++)if(patch.pixels[i*4+3]){
 const x=i%256,y=Math.floor(i/256);
 assert(x>=cloud.x-scene.cameraX&&x<cloud.x-scene.cameraX+cloud.width&&y>=cloud.y&&y<cloud.y+cloud.height);
 for(let c=0;c<3;c++)assert.equal(patch.pixels[i*4+c],(b.pixels[i]>>>(c*8))&255);
 count++;
}
const goomba=scene.semantic.entities.find(e=>e.type==='goomba');
assert(goomba.source.spriteKeys.length>0);
const sprite=rasterizeSourcePatches(scene.extraction,[goomba],scene.cameraX);
assert(sprite.pixelCount>0);
assert.equal(rasterizeSourcePatches(scene.extraction,[{...goomba,source:{spriteKeys:['not-this-sprite']}}],scene.cameraX).pixelCount,0);
assert.equal(rasterizeSourcePatches(scene.extraction,[{...goomba,source:{spriteKeys:[]}}],scene.cameraX).pixelCount,0);
assert.equal(rasterizeSourcePatches(scene.extraction,[],scene.cameraX).pixelCount,0);
console.log(JSON.stringify({passed:true,cloudPixels:count,spritePixels:sprite.pixelCount,checks:['patch stays inside missing object','opaque patch pixels equal original PPU','sprite identities restrict fallback','empty patch is transparent']}));
