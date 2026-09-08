import fs from 'node:fs';
import path from 'node:path';
import {createRequire} from 'node:module';
const require=createRequire(import.meta.url);
const {PNG}=require('./vendor/pngjs');
export function writePNG(file,width,height,rgba){const p=new PNG({width,height});p.data=Buffer.from(rgba);fs.writeFileSync(file,PNG.sync.write(p));}
export function atlas(records,out,prefix,{cols=16,perPage=256,cell=24,scale=3}={}){
 const pages=[];
 for(let start=0;start<records.length;start+=perPage){
  const entries=records.slice(start,start+perPage), rows=Math.ceil(entries.length/cols),w=cols*cell*scale,h=rows*cell*scale,rgba=new Uint8Array(w*h*4);
  for(let y=0;y<h;y++)for(let x=0;x<w;x++){let i=(y*w+x)*4, v=((Math.floor(x/(4*scale))+Math.floor(y/(4*scale)))%2)?38:47;rgba.set([v,v+3,v+6,255],i);}
  const file=prefix+'-'+String(pages.length).padStart(2,'0')+'.png';
  entries.forEach((r,j)=>{let sx=(j%cols)*cell*scale+Math.floor((cell-r.width)*scale/2),sy=Math.floor(j/cols)*cell*scale+Math.floor((cell-r.height)*scale/2);
   for(let y=0;y<r.height*scale;y++)for(let x=0;x<r.width*scale;x++){let si=(Math.floor(y/scale)*r.width+Math.floor(x/scale))*4,di=((sy+y)*w+sx+x)*4;if(r.rgba[si+3])rgba.set(r.rgba.slice(si,si+4),di);}
   r.atlas={file,x:sx,y:sy,width:r.width*scale,height:r.height*scale,scale,index:start+j};
  });
  writePNG(path.join(out,file),w,h,rgba);pages.push(file);
 }
 return pages;
}
