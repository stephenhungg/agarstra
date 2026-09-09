const {app,BrowserWindow,ipcMain}=require('electron');
const fs=require('node:fs'),path=require('node:path');const {pathToFileURL}=require('node:url');
const out=__dirname,pokemon=path.resolve(out,'../..'),repo=path.resolve(pokemon,'../..');
const profile=path.join('/Volumes/Vault/agarstra-battle-arena-scratch','electron-runtime-profile');
fs.mkdirSync(profile,{recursive:true});app.setName('Starter Battle Verification');app.setPath('userData',profile);app.setPath('sessionData',profile);
app.commandLine.appendSwitch('disable-renderer-backgrounding');
app.commandLine.appendSwitch('disable-background-timer-throttling');
ipcMain.handle('starter-audit:rom',()=>new Uint8Array(fs.readFileSync(path.join(repo,'work/pokemon/rom/firered-user.gba'))));
app.whenReady().then(async()=>{
  let server;const messages=[];
  try{
    const {createServer}=await import(pathToFileURL(path.join(pokemon,'app/node_modules/vite/dist/node/index.js')).href);
    server=await createServer({root:out,configFile:false,publicDir:false,
      resolve:{alias:[{find:'three/addons',replacement:path.join(pokemon,'app/node_modules/three/examples/jsm')},{find:/^three$/,replacement:path.join(pokemon,'app/node_modules/three/build/three.module.js')}]},
      server:{host:'127.0.0.1',port:0,fs:{allow:[repo,'/Volumes/Vault']}},
      plugins:[{name:'current-local-assets',configureServer(s){s.middlewares.use((req,res,next)=>{
        const url=new URL(req.url,'http://local');let file;
        if(url.pathname==='/runtime-candidates.json')file=path.join(pokemon,'design/runtime-candidates.json');
        else if(url.pathname.startsWith('/models/'))file=path.join(pokemon,'models',path.basename(url.pathname));
        else if(url.pathname.startsWith('/core/'))file=path.resolve(pokemon,'runtime-core',url.pathname.slice(6));
        if(!file)return next();
        if(!fs.existsSync(file)){res.statusCode=404;res.end('Missing verification asset');return;}
        if(file.endsWith('.json'))res.setHeader('Content-Type','application/json');
        if(file.endsWith('.wasm'))res.setHeader('Content-Type','application/wasm');
        fs.createReadStream(file).pipe(res);
      });}}]});
    await server.listen();const port=server.httpServer.address().port;
    const win=new BrowserWindow({title:'Starter Battle Verification',width:1440,height:900,show:false,webPreferences:{preload:path.join(out,'preload.cjs'),contextIsolation:true,backgroundThrottling:false}});
    win.webContents.on('console-message',event=>messages.push({level:event.level,message:event.message}));
    win.webContents.on('render-process-gone',(_,details)=>messages.push({type:'renderer-gone',details}));
    await win.loadURL(`http://127.0.0.1:${port}`);console.log('STARTER_AUDIT_LOADED',port);
    let status;
    for(let n=0;n<360;n++){
      status=await win.webContents.executeJavaScript('({ready:window.starterAudit?.ready,error:window.starterAudit?.error})');
      if(status.error)throw Error(status.error);if(status.ready)break;
      await new Promise(r=>setTimeout(r,250));if(n===359)throw Error('Starter battle runtime verification timeout');
    }
    const result=await win.webContents.executeJavaScript('JSON.parse(JSON.stringify(window.starterAudit))');
    for(const [name,data] of Object.entries(result.captures??{}))fs.writeFileSync(path.join(out,`${name}.png`),Buffer.from(data.split(',')[1],'base64'));
    delete result.captures;
    for(const [name,width,height] of [['wide',1920,810],['portrait',720,1200]]){
      win.setContentSize(width,height);result[name]=await win.webContents.executeJavaScript(`window.starterAudit.resize(${width},${height})`);
      await new Promise(r=>setTimeout(r,100));fs.writeFileSync(path.join(out,`${name}-native-menu.png`),(await win.webContents.capturePage()).toPNG());
    }
    result.messages=messages;fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(result,null,2));
    console.log(JSON.stringify({passed:result.passed,checks:result.checks,events:result.events,render:result.render}));
    await server.close();app.exit(result.passed?0:1);
  }catch(error){fs.writeFileSync(path.join(out,'error.json'),JSON.stringify({error:error.stack,messages},null,2));console.error(error);if(server)await server.close();app.exit(1);}
});
