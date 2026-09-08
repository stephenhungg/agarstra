import assert from 'node:assert/strict';
import fs from 'node:fs';
import {readROM} from './read-rom.mjs';
import {NES} from '../../../smb3-demo/src/vendor/jsnes/index.js';
import {GameBridge} from '../../../smb3-demo/src/bridge.js';
import {RomAssetExtractor} from '../../../smb3-demo/src/rom-extractor.js';
const rom=readROM(),nes=new NES({emulateSound:false,onFrame:()=>{}});nes.loadROM(rom);const ex=new RomAssetExtractor(nes,rom);
const aliasSet=[...ex.romTiles.values()].find(sources=>sources.length>1&&sources[0].bank1k!==sources[1].bank1k&&rom.subarray(sources[0].romOffset,sources[0].romOffset+16).some(b=>b));
assert(aliasSet,'ROM has a populated duplicate pattern in different banks');
const [a,b]=aliasSet,lookup=source=>nes.rom.vromTile[Math.floor(source.tileIndex/256)][source.tileIndex%256],palette=[0,0x112233,0x445566,0x778899];
const synthetic=[];
for(const sources of[[a],[b],[a,b]]){
 nes.ppu.startFrame();const ids=sources.map(source=>ex.asset(lookup(source),palette,'sprite').id);nes.ppu.endFrame();const frame=ex.getFrame();
 assert.equal(new Set(ids).size,1,'byte-identical patterns keep their stable shared identity');
 assert.deepEqual(frame.assets[0].mappedSources.map(s=>s.tileIndex),sources.map(s=>s.tileIndex));
 assert(frame.assets[0].romSources.length>=2,'all aliases remain available separately');
 synthetic.push({id:ids[0],mapped:frame.assets[0].mappedSources.map(s=>s.tileIndex)});
}
assert.equal(new Set(synthetic.map(s=>s.id)).size,1,'runtime ID unchanged across banks and frames');
const game=new GameBridge();game.load(rom);game.bootToLevel();let verified=0,nonFirstAlias=0;const banks=new Set();
for(let f=0;f<220;f++){
 if(f===9)game.button('RIGHT',true);if(f===39)game.button('A',true);if(f===69)game.button('A',false);
 game.step();for(const asset of game.getScene().extraction.assets){
  assert(asset.mappedSources.length>0,'every rendered asset has exact object-identity provenance');
  for(const source of asset.mappedSources){assert.deepEqual(Array.from(rom.subarray(source.romOffset,source.romOffset+16)),Array.from(asset.chrBytes));assert(asset.romSources.some(s=>s.tileIndex===source.tileIndex));banks.add(source.bank1k);verified++;if(source.tileIndex!==asset.romSources[0].tileIndex)nonFirstAlias++;}
 }
}
assert(nonFirstAlias>0,'live mapping demonstrates why choosing the first alias is incorrect');
const result={passed:true,frames:220,verifiedAssetUses:verified,nonFirstAliasUses:nonFirstAlias,mappedBanks1k:[...banks].sort((a,b)=>a-b),aliasTest:synthetic,checks:['stable identity across bank aliases','per-frame provenance does not leak prior banks','multiple actual sources retained when used in one frame','all active sources match original ROM bytes','live mapping differs from first matching alias']};
fs.writeFileSync(new URL('./provenance.json',import.meta.url),JSON.stringify(result,null,2));console.log(JSON.stringify(result));
