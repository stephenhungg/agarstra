const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('auditROM',{load:()=>ipcRenderer.invoke('starter-audit:rom')});
