#!/usr/bin/env python3
"""Render two static metatile layers; NPCs and tileset animation are not included."""
from PIL import Image,ImageDraw
from pathlib import Path
import json,struct
root=Path('/Users/stephenhung/Documents/GitHub/agarstra'); repo=root/'work/pokemon/source/pokefirered'
out=root/'outputs/pokemon-remake/verification/interiors'
import sys
p=repo/'data/tilesets/primary/building'; s=repo/('data/tilesets/secondary/'+sys.argv[1])
images=[Image.open(x/'tiles.png') for x in [p,s]]
pals=[]
for i in range(13):
    lines=((p if i<7 else s)/f'palettes/{i:02d}.pal').read_text().splitlines()[3:19]
    pals.append([tuple(map(int,line.split())) for line in lines])
metatiles=[]
for ts in [p,s]:
    raw=(ts/'metatiles.bin').read_bytes()
    metatiles.extend(struct.unpack('<8H',raw[i:i+16]) for i in range(0,len(raw),16))
def render(meta):
    result=Image.new('RGBA',(16,16),(0,0,0,255))
    for layer in range(2):
        for k in range(4):
            word=meta[layer*4+k]; tid=word&1023; palette=word>>12
            sheet=images[0 if tid<640 else 1]; tid=tid if tid<640 else tid-640
            tile=sheet.crop(((tid%16)*8,(tid//16)*8,(tid%16)*8+8,(tid//16)*8+8))
            if word&1024: tile=tile.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
            if word&2048: tile=tile.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
            pix=Image.new('RGBA',(8,8)); pix.putdata([pals[palette][x]+(255 if x else 0,) for x in tile.getdata()]); result.alpha_composite(pix,((k%2)*8,(k//2)*8))
    return result
cache=[render(m) for m in metatiles]
manifest=json.loads((root/'outputs/pokemon-remake/source/source-maps.json').read_text())
for name in sys.argv[2:]:
    m=manifest['maps'][name]; w=m['layout']['width']; h=m['layout']['height']; im=Image.new('RGBA',(w*16,h*16))
    for i,t in enumerate(m['metatileIds']): im.paste(cache[t],((i%w)*16,(i//w)*16))
    im.resize((w*48,h*48),Image.Resampling.NEAREST).save(out/f'{name}-source.png')
    dr=ImageDraw.Draw(im)
    for y in range(h):
        for x in range(w): dr.text((x*16,y*16),str(x)+','+str(y),fill='white')
    im.resize((w*64,h*64),Image.Resampling.NEAREST).save(out/f'{name}-grid.png')
print('Rendered exact source interior previews static source maps')
