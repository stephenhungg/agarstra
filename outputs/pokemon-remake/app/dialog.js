import {readFireRedDialog,cropSourcePixels} from '../runtime-core/firered-dialog.mjs';

export function createDialogOverlay(container){
  const root=document.createElement('div');root.className='rom-dialog-layer';root.innerHTML='<div class="rom-dialog-card" hidden><div class="rom-dialog-text"></div><canvas class="rom-dialog-pixels" hidden></canvas><span class="rom-dialog-continue" hidden>▾</span></div><div class="rom-dialog-choices"></div>';
  const style=document.createElement('style');style.textContent=`.rom-dialog-layer{position:absolute;inset:0;pointer-events:none;z-index:30}.rom-dialog-card{position:absolute;left:50%;bottom:5%;transform:translateX(-50%);width:min(760px,85%);box-sizing:border-box;padding:24px 32px;background:rgba(14,23,24,.96);border:1px solid rgba(208,228,203,.45);border-radius:16px;box-shadow:0 14px 45px #0008;color:#f3f4e9;font:500 clamp(18px,2.2vw,26px)/1.45 system-ui,sans-serif;min-height:110px}.rom-dialog-card[hidden],.rom-dialog-pixels[hidden],.rom-dialog-continue[hidden]{display:none}.rom-dialog-text{white-space:pre-wrap;min-height:2.9em}.rom-dialog-pixels{display:block;width:100%;height:auto;image-rendering:pixelated}.rom-dialog-continue{position:absolute;right:18px;bottom:9px;color:#dfe4ac}.rom-dialog-choices{position:absolute;right:7.5%;bottom:calc(5% + 155px);display:flex;gap:12px;align-items:flex-end}.rom-dialog-choices canvas{image-rendering:pixelated;max-height:240px;max-width:45vw;border-radius:5px;box-shadow:0 8px 25px #0008}`;
  root.appendChild(style);container.appendChild(root);
  const card=root.querySelector('.rom-dialog-card'),text=root.querySelector('.rom-dialog-text'),canvas=root.querySelector('.rom-dialog-pixels'),arrow=root.querySelector('.rom-dialog-continue'),choices=root.querySelector('.rom-dialog-choices');let last=null;
  function paint(canvas,core,rect){canvas.width=rect.width;canvas.height=rect.height;canvas.getContext('2d').putImageData(new ImageData(cropSourcePixels(core,rect),rect.width,rect.height),0,0);}
  return{
    update(core,state){last=readFireRedDialog(core,state);const d=last.dialog;card.hidden=!d;
      if(d){const pixels=d.mode==='pixels';canvas.hidden=!pixels;text.hidden=pixels;text.textContent=pixels?'':d.text;arrow.hidden=pixels||!d.waiting;if(pixels)paint(canvas,core,d.rect);card.dataset.mode=d.mode;}
      while(choices.children.length>last.auxiliary.length)choices.lastChild.remove();
      last.auxiliary.forEach((w,i)=>{let c=choices.children[i];if(!c){c=document.createElement('canvas');choices.appendChild(c);}paint(c,core,w.rect);c.style.width=`${w.rect.width*2}px`;});return last;
    },
    report(){return last;},
    setVisible(visible){root.hidden=!visible;},
    destroy(){root.remove();}
  };
}
