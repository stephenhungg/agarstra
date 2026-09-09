import fs from 'node:fs';
import assert from 'node:assert/strict';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
import {GbaAdapter} from '../../runtime-core/gba-adapter.mjs';
import {readFireRedState} from '../../runtime-core/firered-state.mjs';
import {readBattlePresentation,createBattleEventTracker} from '../../app/battle.js';
const require=createRequire(import.meta.url),root=fileURLToPath(new URL('../../../../',import.meta.url)),vendor=fileURLToPath(new URL('../../runtime-core/vendor/',import.meta.url));
const core=new GbaAdapter(await require(vendor+'mgba.js')({locateFile:name=>vendor+name}),fs.readFileSync(root+'work/pokemon/rom/firered-user.gba'));
const checkpoint=fs.readFileSync(new URL('../../runtime-core/checkpoints/first-battle.state',import.meta.url)),replay=JSON.parse(fs.readFileSync(new URL('../../runtime-core/checkpoints/battle-verification.json',import.meta.url))).attackInputs;
const tracker=createBattleEventTracker(),checks=[];const check=(name,fn)=>{fn();checks.push({name,passed:true});};
function replayEvents(){
  core.loadState(checkpoint);tracker.update(readBattlePresentation(core,readFireRedState(core)));const events=[];
  for(const segment of replay)for(let i=0;i<segment.frames;i++){
    core.step(1,segment.keys);const data=readBattlePresentation(core,readFireRedState(core));events.push(...tracker.update(data));assert.deepEqual(tracker.update(data),[],'Repeated paint retriggered a source event');
  }
  return events;
}
try{
  const events=replayEvents(),observed=core.saveState();
  check('real first turn emits exactly Tackle, target hit, Scratch, target hit',()=>assert.deepEqual(events.map(e=>[e.frame,e.battlerId,e.action,e.moveId??null]),[[30610,0,'attack',33],[30652,1,'hit',null],[31290,1,'attack',10],[31323,0,'hit',null]]));
  check('original battle HP remains 11 and 14',()=>assert.deepEqual(readFireRedState(core).battle.battlers.map(b=>b.hp),[11,14]));
  check('checkpoint rewind and replay reproduce identical event ids and timing',()=>assert.deepEqual(replayEvents(),events));
  check('replayed original bytes remain identical',()=>assert.deepEqual(core.saveState(),observed));
  core.loadState(checkpoint);for(const segment of replay)for(let i=0;i<segment.frames;i++)core.step(1,segment.keys);
  check('reading animation events does not alter native simulation',()=>assert.deepEqual(core.saveState(),observed));
  const fixture=createBattleEventTracker(),battlers=[{id:0,species:7,hp:20,commandActive:false,command:0},{id:1,species:1,hp:20,commandActive:false,command:0}];
  const state={active:true,frame:1,battlers,animation:{active:true,moveId:39,power:0,attackerId:0,targetId:1}};
  check('fixture Squirtle Tail Whip requests status pose, never attack or hit',()=>assert.deepEqual(fixture.update(state).map(e=>e.action),['tailWhip']));
  check('persistent move script does not retrigger each frame',()=>assert.deepEqual(fixture.update({...state,frame:2}),[]));
  fixture.update({...state,frame:3,animation:{active:false}});
  check('Growl requests only native attacker status pose',()=>assert.deepEqual(fixture.update({...state,frame:4,animation:{...state.animation,moveId:45,attackerId:1}}).map(e=>[e.battlerId,e.action]),[[1,'growl']]));
  check('faint requires active native faint controller command',()=>assert.deepEqual(fixture.update({...state,frame:5,animation:{active:false},battlers:[{...battlers[0],hp:0,command:10,commandActive:true},battlers[1]]}).map(e=>e.action),['faint']));
  check('battle exit clears presentation events',()=>{fixture.update({active:false,frame:6});assert.equal(fixture.poseFor(0),null);});
  const report={passed:true,checkedAt:new Date().toISOString(),checks,events,romSHA1:'41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc',source:{commit:'c75f352304d529f6ba92d4f74b9cf8b5c3810788',move:'src/battle_anim.c DoMoveAnim / LaunchBattleAnimation',hitAndFaint:'src/battle_controller_player.c and battle_controller_opponent.c'},limitations:['Squirtle, status-pose, and faint cases here are isolated observer fixtures. Real ROM replay verifies Bulbasaur versus Charmander first turn.','Models and visible GLB animation require separate browser rendering verification.','Transitions are detected at observed source frames; an initial mid-animation snapshot has no earlier observation history.']};
  fs.writeFileSync(new URL('./event-checks.json',import.meta.url),JSON.stringify(report,null,2)+'\n');console.log(JSON.stringify({passed:true,checks:checks.length,events},null,2));
}finally{core.destroy();}
