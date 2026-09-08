const { contextBridge, ipcRenderer } = require("electron");
contextBridge.exposeInMainWorld("desktop", {
  defaultROM: () => ipcRenderer.invoke("rom:default"),
  chooseROM: () => ipcRenderer.invoke("rom:choose"),
  fullscreen: () => ipcRenderer.invoke("window:fullscreen"),
});
