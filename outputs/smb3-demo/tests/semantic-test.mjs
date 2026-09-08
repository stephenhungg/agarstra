import assert from'node:assert/strict';import fs from'node:fs';
import{GameBridge}from'../src/bridge.js';import{buildSemanticScene,defineMetatile}from'../src/semantic-scene.js';import{readROM}from'./read-rom.mjs';
const b=new GameBridge();b.load(readROM());b.bootToLevel();const get=()=>buildSemanticScene(b,b.getScene());let s=get();
assert(s.supported);assert(s.renderable);assert.equal(s.coverage.fallbackScope,'none');assert.equal(s.entities[0].type,'goomba');assert.equal(s.entities[0].source.objectId,0x72);assert.equal(s.entities[0].height,16);
const firstBlock=s.objects.find(o=>o.x===176&&o.y===114&&o.type==='question'),secondBlock=s.objects.find(o=>o.x===192&&o.y===114&&o.type==='question');assert(firstBlock&&secondBlock);
assert(s.objects.some(o=>o.type==='ground'&&o.x===0&&o.y===178&&o.width===624));assert(s.objects.some(o=>o.type==='hill'&&o.x===16&&o.y===114&&o.width===128&&o.height===64));assert(s.objects.some(o=>o.type==='platform'&&o.x===240&&o.y===130&&o.width===48&&o.height===48&&o.materialVariant==='orange'));
let compared=0,spriteKeysCompared=0,scoreFrames=0;
function checkSpriteKeys(){
 const base=b.getScene(),scene=base.semantic,keys=new Set(base.extraction.sprites.map(o=>o.id));
 const playerKeys=new Set(scene.player.source.spriteKeys);
 for(const entity of [scene.player,...scene.entities]){
  if(!entity.visible)continue;
  assert(entity.source.spriteKeys.length>0,`visible ${entity.type} must identify its source sprites`);
  for(const key of entity.source.spriteKeys){assert(keys.has(key),`source sprite ${key} exists in the displayed frame`);spriteKeysCompared++;if(entity!==scene.player)assert(!playerKeys.has(key),'an object must not claim Mario sprites');}
  if(entity.type==='score'){scoreFrames++;assert.equal(entity.label,'100');assert.equal(entity.value,100);assert.equal(entity.y,Number(entity.source.spriteKeys[0].split(',')[1]));}
 }
}
function checkNametable(){const scene=get(),nt=b.nes.ppu.nameTable[1];for(const o of scene.objects)for(const c of o.cells){const sx=c.x-scene.cameraX;if(sx<8||sx+16>248||c.y<8||c.y+16>192)continue;const def=defineMetatile(c.metatileId,b.rom),col=(c.x/8)%32,row=(c.worldY/8)%30;for(const[part,dx,dy]of[[0,0,0],[1,0,1],[2,1,0],[3,1,1]]){assert.equal(nt.tile[(row+dy)*32+col+dx],def.patterns[part],`source SRAM cell ${c.sourceAddress.toString(16)} part${part}`);compared++;}}}
checkNametable();const actions={9:['RIGHT',true],39:['A',true],69:['A',false],95:['RIGHT',false],160:['LEFT',true],180:['LEFT',false],230:['A',true],260:['A',false],340:['RIGHT',true],353:['RIGHT',false],420:['A',true],450:['A',false]};
let coins=0,bumps=0,squashed=0,maxCamera=0;for(let i=0;i<550;i++){if(actions[i])b.button(...actions[i]);b.step();s=get();maxCamera=Math.max(maxCamera,s.cameraX);assert(s.supported,`unexpected fallback at${i}: ${JSON.stringify(s.unknown)}`);if(s.entities.some(e=>e.type==='coin'))coins++;if(s.entities.some(e=>e.type==='bouncing-block'))bumps++;if(s.entities.some(e=>e.type==='goomba'&&e.squashed))squashed++;
 assert(s.renderable);checkSpriteKeys();if([150,200,330,540].includes(i))checkNametable();if(i>=253)assert(s.objects.some(o=>o.id===firstBlock.id&&o.type==='used-block'));if(i>=443)assert(s.objects.some(o=>o.id===secondBlock.id&&o.type==='used-block'));
}
assert(coins>0&&bumps>0&&squashed>0&&scoreFrames>0);
b.reset();for(let i=0;i<220;i++){if(i===9)b.button('RIGHT',true);if(i===39)b.button('A',true);if(i===69)b.button('A',false);b.step();s=get();maxCamera=Math.max(maxCamera,s.cameraX);if([150,190,219].includes(i))checkNametable();}
assert(maxCamera>=190);assert(s.objects.some(o=>o.type==='pipe'&&o.x===352&&o.y===130&&o.width===32&&o.height===48&&o.hasRim));
b.reset();b.button('RIGHT',true);let death=false,unmapped=false,renderableDeathFrames=0,unmappedFrames=0;
for(let i=0;i<500;i++){b.step();s=get();if(s.mode==='death'){death=true;assert.equal(s.supported,false);if(s.cameraY===239){assert(s.renderable,'death pose must not discard the verified level');assert.equal(s.coverage.fallbackScope,'none');assert.equal(s.coverage.reasonCode,'player-death');renderableDeathFrames++;}else assert.equal(s.coverage.reasonCode,'unmapped-camera');}if(s.mode==='unmapped'){unmapped=true;unmappedFrames++;assert.equal(s.renderable,false);assert.equal(s.coverage.fallbackScope,'scene');assert.equal(s.coverage.reasonCode,'unmapped-region');}}
assert(death&&unmapped);assert.equal(renderableDeathFrames,200);assert.equal(unmappedFrames,221);
b.reset();const base=b.getScene(),address=firstBlock.source.sramAddresses[0],original=b.nes.cpu.mem[address];b.nes.cpu.mem[address]=0xfe;
const unknownScene=buildSemanticScene(b,{...base});assert(unknownScene.renderable);assert.equal(unknownScene.supported,false);assert.equal(unknownScene.coverage.fallbackScope,'objects');assert.equal(unknownScene.coverage.reasonCode,'unmapped-objects');assert(unknownScene.unknown.some(o=>o.source.sramAddresses.includes(address)));b.nes.cpu.mem[address]=original;
const memory=b.nes.cpu.mem.slice(),oam=b.nes.ppu.spriteMem.slice(),pixels=b.pixels.slice();buildSemanticScene(b,{...base});assert.deepEqual(b.nes.cpu.mem,memory);assert.deepEqual(b.nes.ppu.spriteMem,oam);assert.deepEqual(b.pixels,pixels);
const result={passed:true,sourcePatternComparisons:compared,spriteKeysCompared,coinFrames:coins,bounceFrames:bumps,scoreFrames,squashedFrames:squashed,maxCamera,renderableDeathFrames,unmappedFrames,checks:['SRAM coordinates match original nametable patterns','opening ground does not inherit a later raised ground height','whole connected hill and colored platform','RAM object identity and OAM extent','stable block ID from question to used','actual coin and score popup RAM with displayed OAM coordinates','source sprite identifiers match extracted frame without claiming Mario','death preserves renderable World 1-1','unknown definitions require object-only fallback','unmapped worldmap remains explicit','semantic observer leaves RAM, OAM and framebuffer unchanged']};console.log(JSON.stringify(result));fs.writeFileSync(new URL('./semantic-results.json',import.meta.url),JSON.stringify(result,null,2));
