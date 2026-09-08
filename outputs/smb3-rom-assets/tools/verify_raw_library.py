"""Read-only verification of the saved original CHR/observed Blender library."""
import bpy,json,sys,argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--aliases',required=True);p.add_argument('--registry',required=True);p.add_argument('--report',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);cat=Path(a.catalog);inventory=json.loads((cat/'all-chr-inventory.json').read_text());observed=json.loads((cat/'observed-assets.json').read_text());aliases=json.loads(Path(a.aliases).read_text());registry=json.loads(Path(a.registry).read_text());expected={v['id']:v for v in observed['assets']+observed['sourceAssets']};materialColors={}
def color(material):
 if material.name not in materialColors:
  linear=material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value[:3]
  materialColors[material.name]=tuple(max(0,min(255,round((12.92*v if v<=.0031308 else 1.055*v**(1/2.4)-.055)*255))) for v in linear)
 return materialColors[material.name]
def raster(obj,w,h):
 out=bytearray(w*h*4)
 if not len(obj.data.vertices):return out
 front=min(v.co.y for v in obj.data.vertices)
 for poly in obj.data.polygons:
  vs=[obj.data.vertices[i].co for i in poly.vertices]
  if not all(abs(v.y-front)<.000001 for v in vs):continue
  x0=round(min(v.x for v in vs)*16);x1=round(max(v.x for v in vs)*16);y0=round(-max(v.z for v in vs)*16);y1=round(-min(v.z for v in vs)*16)
  # A degenerate projection belongs to an edge rather than the front.
  if x0==x1 or y0==y1:continue
  assert 0<=x0<x1<=w and 0<=y0<y1<=h,(obj.name,x0,x1,y0,y1)
  c=color(obj.data.materials[poly.material_index])
  for y in range(y0,y1):
   for x in range(x0,x1):i=(y*w+x)*4;assert out[i+3]==0,(obj.name,'overlapping front faces');out[i:i+4]=bytes((*c,255))
 return out
raw={};gray={20:0,90:1,170:2,245:3};raw_pixels=0
for entry in aliases:
 name=entry['assetId']
 if name not in raw:
  obj=bpy.data.objects.get(name);assert obj and obj.type=='MESH',name;rgba=raster(obj,8,8);indices=[]
  for i in range(64):r,g,b,alpha=rgba[i*4:i*4+4];assert r==g==b and alpha==255 and r in gray,(name,r,g,b,alpha);indices.append(gray[r])
  data=bytearray(16)
  for y in range(8):
   for x in range(8):v=indices[y*8+x];data[y]|=(v&1)<<(7-x);data[y+8]|=((v>>1)&1)<<(7-x)
  sha=hashlib.sha256(data).hexdigest();assert name=='chr_'+sha[:20];raw[name]={'indices':indices,'sha':sha};raw_pixels+=64
 actual=raw[name];tile=inventory['tiles'][entry['physicalIndex']];assert actual['indices']==tile['indices'];assert actual['sha']==entry['sha256']==tile['sha256'];assert tile['romByteOffset']==entry['romOffset']
assert len(aliases)==8192 and len(raw)==5531
colored_pixels=0;colored=[]
for entry in registry['entries']:
 ident=entry['assetId'];obj=bpy.data.objects.get(ident);assert obj and obj.type=='MESH',ident;source=expected[ident];assert source['width']==entry['width'] and source['height']==entry['height'];assert hashlib.sha256(bytes(source['rgba'])).hexdigest()==entry['sourceRgbaSHA256'];assert json.loads(obj['source_provenance']).get('id')==ident
 rgba=raster(obj,entry['width'],entry['height'])
 for i in range(entry['width']*entry['height']):
  e=source['rgba'][i*4:i*4+4];v=list(rgba[i*4:i*4+4]);assert (e==v if e[3] else v[3]==0),(ident,i,e,v)
 colored_pixels+=entry['width']*entry['height'];colored.append(ident)
assert len(colored)==320
report={'passed':True,'method':'Read-only reopen of .blend; rasterize actual local front-face mesh polygons and convert stored linear material colors to source sRGB','blend':bpy.data.filepath,'totalMeshObjects':sum(o.type=='MESH' for o in bpy.data.objects),'rawUniqueMeshesVerified':len(raw),'physicalChrIndicesCovered':len(aliases),'uniqueRawPixelsVerified':raw_pixels,'physicalRawPixelsVerified':len(aliases)*64,'observedColoredMeshesVerified':len(colored),'coloredSourcePixelsVerified':colored_pixels,'pixelMismatches':0,'sourceROM_SHA256':inventory['romSHA256'],'notes':['Grayscale raw palette20/90/170/245 was inverted to exact2-bit source indices, re-encoded to16-byteCHR, and SHA-verified for every physical alias.','Colored sourceRGBA hashes match registry; opaque pixels and transparency match actual mesh geometry. Invisible RGB of alpha0pixels is represented in source catalog, not mesh faces.','Viewport orientation does not affect verification; file was not saved or modified.']};Path(a.report).write_text(json.dumps(report,indent=2));print('RAW_LIBRARY_REOPEN_VERIFICATION',json.dumps(report))
