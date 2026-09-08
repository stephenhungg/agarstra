import json,hashlib,struct
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[4];B=ROOT/'outputs/pokemon-remake';S=ROOT/'work/pokemon/source/pokefirered'
r=json.loads((B/'source/source-maps.json').read_text())['maps']['Route1'];w=r['layout']['width'];h=r['layout']['height'];a=r['metatileIds'];sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def attrs(p):
 b=p.read_bytes();return struct.unpack('<'+'I'*(len(b)//4),b)
pa=S/'data/tilesets/primary/general/metatile_attributes.bin';sa=S/'data/tilesets/secondary/pallet_town/metatile_attributes.bin';primary,secondary=attrs(pa),attrs(sa)
behavior=[(primary[t] if t<640 else secondary[t-640])&0x1ff for t in a]
pathids={0xd3,0xd4,0xd5,0xdb,0xdc,0xdd,0xe3,0xe4,0xe5,0x102,0x103,0x104,0x105,0x97,0xc0,0xc1,0xc8,0xc9}
im=Image.open(B/'source/Route1-source.png').convert('RGB');mask=[]
for y in range(h*4):
 for x in range(w*4):
  count=sum(1 for yy in range(y*4,y*4+4) for xx in range(x*4,x*4+4) if (lambda c:c[0]>190 and c[1]>170 and c[2]<170)(im.getpixel((xx,yy))))
  mask.append(round(count/16,4) if a[(y//4)*w+x//4]in pathids else 0)
layout={'map':'Route1','width':w,'height':h,'coordinates':'x=source tile x,z=source tile y; centers at integer coordinates; original core owns collision, jump and transitions','source':{'commit':'c75f352304d529f6ba92d4f74b9cf8b5c3810788','mapDataSHA256':r['mapDataSHA256'],'sourceCompositeSHA256':sha(B/'source/Route1-source.png'),'attributeFiles':{str(pa.relative_to(S)):sha(pa),str(sa.relative_to(S)):sha(sa)}},'metatileIds':a,'collision':r['collision'],'elevation':r['elevation'],'behavior':behavior,'connections':r['events']['connections'],'objects':r['events']['object_events'],'signs':r['events']['bg_events'],'trees':[{'x':i%w+.5,'z':i//w+.75,'sourceTile':[i%w,i//w],'metatile':t}for i,t in enumerate(a)if t in [0x1c,0x1e]],'ledges':[{'x':i%w,'z':i//w,'direction':'south','behavior':b,'metatile':a[i]}for i,b in enumerate(behavior)if b==0x3b],'tallGrass':[{'x':i%w,'z':i//w}for i,b in enumerate(behavior)if b==2],'flowers':[{'x':i%w,'z':i//w}for i,t in enumerate(a)if t==4],'fences':[{'x':i%w,'z':i//w,'metatile':t}for i,t in enumerate(a)if t in [0xe7,0xec,0xed]],'pathMask':{'width':w*4,'height':h*4,'samplesPerTile':4,'weights':mask,'method':'4x4-pixel coverage from exact source composite, restricted to observed path/ledge metatiles; yellow palette RGB thresholds r>190,g>170,b<170'},'heightPolicy':'Source elevation 0/3 denotes collision layers, not metric terrain height. Walkable floor remains y=0. Low .28-tile-high south-facing ledge berms occupy actual MB_JUMP_SOUTH cells; no invented continuous terraces or independent collision.'}
(B/'source/route1-layout.json').write_text(json.dumps(layout,separators=(',',':'))+'\n')
print({k:len(layout[k])for k in ['trees','ledges','tallGrass','flowers','fences']})
