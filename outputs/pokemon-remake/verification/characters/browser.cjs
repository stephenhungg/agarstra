// Invoke with the canonical Electron binary. All output stays beside this script.
const {app,BrowserWindow}=require('electron');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),assert=require('node:assert/strict'),crypto=require('node:crypto');
const out=__dirname,base=path.resolve(out,'../..'),canonical=process.env.CHARACTER_REFERENCE_ROOT||'/Users/stephenhung/Documents/GitHub/agarstra';
const types={'.html':'text/html','.js':'text/javascript','.mjs':'text/javascript','.wasm':'application/wasm','.json':'application/json'};
const server=http.createServer((req,res)=>{const pathname=new URL(req.url,'http://localhost').pathname;let file;
 if(pathname==='/rom')file=canonical+'/work/pokemon/rom/firered-user.gba';
 else if(pathname.startsWith('/fixture/'))file=canonical+'/work/pokemon/bridge-probe/'+path.basename(pathname);
 else if(pathname.startsWith('/deps/'))file=canonical+'/outputs/pokemon-remake/app/node_modules/'+pathname.slice(6);
 else file=path.join(base,pathname);
 try{let data=fs.readFileSync(file);if(data.subarray(0,42).toString().startsWith('version https://git-lfs.github.com/spec/v1'))data=fs.readFileSync(path.join(canonical,'outputs/pokemon-remake',path.relative(base,file)));res.setHeader('Content-Type',types[path.extname(file)]||'application/octet-stream');res.end(data);}catch(e){res.writeHead(404);res.end(e.message);}
});
app.setPath('userData',fs.mkdtempSync(path.join(require('node:os').tmpdir(),'firered-characters-')));
server.listen(0,'127.0.0.1',async()=>{await app.whenReady();const win=new BrowserWindow({show:false,width:1100,height:780,useContentSize:true,webPreferences:{nodeIntegration:false,contextIsolation:true}});const errors=[];win.webContents.on('console-message',(_e,level,message)=>{if(level>=2)errors.push(message);});
 try{
 await win.loadURL(`http://127.0.0.1:${server.address().port}/verification/characters/harness.html`);
 let ready=false;for(let i=0;i<300;i++){if(await win.webContents.executeJavaScript('window.ready===true')){ready=true;break;}await new Promise(r=>setTimeout(r,50));}assert.ok(ready,errors.join('\n'));
 if(process.env.CHARACTER_LIFECYCLE_ONLY){
 await win.webContents.executeJavaScript("window.showFixture('/fixture/house1f.state')");const lifecycle=await win.webContents.executeJavaScript('window.lifecycle()');assert.ok(lifecycle.passed,JSON.stringify(lifecycle));
 const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');const file=path.join(out,'browser-results.json'),existing=JSON.parse(fs.readFileSync(file));assert.equal(existing.moduleSHA256,sha(path.join(base,'app/characters.js')));existing.decoderSHA256=sha(path.join(base,'app/character-source.mjs'));existing.lifecycle=lifecycle;fs.writeFileSync(file,JSON.stringify(existing,null,2));console.log(JSON.stringify(lifecycle));win.destroy();server.close();app.quit();return;
 }
 const reports=[];
 function verifyActors(r){assert.ok(r.readOnly);assert.equal(r.report.unsupported.length,0);for(const o of r.state.objectEvents){const a=r.report.actors.find(a=>a.id===o.id);if(o.hidden){assert.equal(a,undefined);continue;}assert.ok(a,`missing actor ${o.id}`);assert.equal(a.graphicsId,o.graphicsId);assert.equal(a.facing,o.facing);assert.equal(a.position[0],o.worldX+(o.visualOffsetX||0));assert.equal(a.position[2],o.worldY);assert.equal(a.position[1],.025-(o.visualOffsetY||0));}}
 for(const [name,file]of [['town','/fixture/pallet-town.state'],['bedroom','/fixture/bedroom.state'],['house','/fixture/house1f.state'],['lab','/fixture/choose-starter.state'],['dialog','/verification/dialog/sign-complete.state']]){
 const r=await win.webContents.executeJavaScript(`window.showFixture(${JSON.stringify(file)})`);verifyActors(r);assert.ok(r.state.objectEvents.length);assert.ok(r.drawCalls>1);
 if(name==='dialog')assert.ok(r.dialog.dialog);
 await new Promise(r=>setTimeout(r,60));fs.writeFileSync(path.join(out,name+'.png'),(await win.capturePage()).toPNG());reports.push({name,...r});
 }
 await win.webContents.executeJavaScript("window.showFixture('/fixture/house1f.state')");
 const motion=await win.webContents.executeJavaScript('window.move(128,24)');assert.ok(motion.samples.some(s=>s.state.player.worldY!==motion.before.state.player.worldY));motion.samples.forEach(verifyActors);assert.ok(new Set(motion.samples.map(s=>s.report.actors.find(a=>a.isPlayer)?.pixelHash)).size>1);
 fs.writeFileSync(path.join(out,'movement.png'),(await win.capturePage()).toPNG());
 const transitions=await win.webContents.executeJavaScript('window.transitions()');for(const t of transitions){assert.ok(t.readOnly);assert.ok(t.gameplayMemoryExact);verifyActors(t.final);for(const v of t.visited)if(!v.key.startsWith('overworld:'))assert.equal(v.report.actors.length,0);}
 const sha=f=>crypto.createHash('sha256').update(fs.readFileSync(f)).digest('hex');
 fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checkedAt:new Date().toISOString(),moduleSHA256:sha(path.join(base,'app/characters.js')),decoderSHA256:sha(path.join(base,'app/character-source.mjs')),reports,motion,transitions,errors,limitations:['Isolated coordinate-grid renderer: scene lighting, occlusion and main app camera integration are not tested here.','All state changes come from original ROM frames/controller inputs or existing checkpoints; no RAM writes.','Transition replay equality covers memory from serialized offset 0x800, not all emulator header/IO bytes.']},null,2));
 console.log(JSON.stringify({passed:true,fixtures:reports.length,motionFrames:motion.samples.length,transitions:transitions.length,errors}));win.destroy();server.close();app.quit();
 }catch(e){console.error(e);console.error(errors);server.close();app.exit(1);}
});
