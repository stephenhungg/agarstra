const {app,BrowserWindow,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path');
const out=__dirname,root=path.resolve(out,'../../../..');
ipcMain.handle('battle-test:rom',()=>new Uint8Array(fs.readFileSync(path.join(root,'work/pokemon/rom/firered-user.gba'))));
app.whenReady().then(async()=>{const win=new BrowserWindow({width:1280,height:900,show:false,webPreferences:{preload:path.join(out,'preload.cjs'),contextIsolation:true}});const messages=[];win.webContents.on('console-message',(_,level,message)=>messages.push({level,message}));try{
 await win.loadURL('http://127.0.0.1:4187');
 for(let n=0;n<160;n++){const status=await win.webContents.executeJavaScript('({ready:window.battleTest?.ready,error:window.battleTest?.error})');if(status.error)throw Error(status.error);if(status.ready)break;await new Promise(r=>setTimeout(r,100));if(n===159)throw Error('Battle test startup timeout');}
 const samples={};
 for(const name of ['first-battle','first-attack']){samples[name]=await win.webContents.executeJavaScript(`window.battleTest.load(${JSON.stringify(name)})`);await new Promise(r=>setTimeout(r,100));fs.writeFileSync(path.join(out,name+'-3d.png'),(await win.webContents.capturePage()).toPNG());const src=await win.webContents.executeJavaScript('window.battleTest.sourceImage()');fs.writeFileSync(path.join(out,name+'-source.png'),Buffer.from(src.split(',')[1],'base64'));}
 await win.webContents.executeJavaScript('window.battleTest.load("first-battle")');await win.webContents.executeJavaScript('window.battleTest.advance(12,1)');samples.moves=await win.webContents.executeJavaScript('window.battleTest.advance(40,0)');await new Promise(r=>setTimeout(r,100));fs.writeFileSync(path.join(out,'move-selection-3d.png'),(await win.webContents.capturePage()).toPNG());
 const passed=samples['first-battle'].drawCalls>0&&samples['first-battle'].actors.filter(a=>a.visible).length===2&&samples['first-battle'].hp.join(',')==='20,18'&&samples['first-attack'].hp.join(',')==='11,14'&&samples.moves.menu?.mode==='moves';
 fs.writeFileSync(path.join(out,'webgl-checks.json'),JSON.stringify({passed,samples,messages},null,2));console.log(JSON.stringify({passed,samples:Object.keys(samples)}));app.exit(passed?0:1);
 }catch(e){fs.writeFileSync(path.join(out,'webgl-error.json'),JSON.stringify({error:e.stack,messages},null,2));console.error(e);app.exit(1);}});
