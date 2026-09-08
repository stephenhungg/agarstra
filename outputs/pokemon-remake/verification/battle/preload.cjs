const {contextBridge,ipcRenderer}=require('electron');contextBridge.exposeInMainWorld('testROM',{load:()=>ipcRenderer.invoke('battle-test:rom')});
