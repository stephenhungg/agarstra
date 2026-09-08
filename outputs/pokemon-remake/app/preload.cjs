const {contextBridge,ipcRenderer}=require('electron');
contextBridge.exposeInMainWorld('nativeROM',{load:()=>ipcRenderer.invoke('rom:load'),saveProgress:bytes=>ipcRenderer.invoke('progress:save',bytes),loadProgress:()=>ipcRenderer.invoke('progress:load')});
