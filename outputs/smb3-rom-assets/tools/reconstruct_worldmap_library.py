"""Build the additive world-map source-phase Blender library.
Run: Blender --background --python reconstruct_worldmap_library.py -- --catalog worldmap-assets.json --output worldmap-assets.blend
"""
import bpy, sys, argparse, json, hashlib, time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--catalog',required=True);parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);catalog=Path(args.catalog).resolve();output=Path(args.output).resolve()
assert output.name not in ('rom-source-assets.blend','binary-defined-assets.blend'),'Separate world-map output required'
bpy.ops.wm.read_factory_settings(use_empty=True);data=json.loads(catalog.read_text());assets=data['assets'];scene=bpy.context.scene
materials={}
def material(rgb):
 key=tuple(rgb)
 if key not in materials:
  m=bpy.data.materials.new('SourceRGB_'+''.join(f'{v:02X}' for v in key));m.use_nodes=True
  linear=tuple(v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4 for v in key)
  m.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value=(*linear,1);m.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value=.72;m.diffuse_color=(*linear,1);m['source_srgb_bytes']=list(key);materials[key]=m
 return materials[key]
def collection(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
metatiles=collection('World_Map__Source_Bank_Palette_Phases__State_Conditional')
counts={asset['kind']:0 for asset in assets};totalpolys=0;totalpixels=0;started=time.time();index=[]
for number,a in enumerate(assets):
 kind=a['kind'];assert kind in counts
 w,h=a['width'],a['height'];rgba=a['rgba'];assert len(rgba)==w*h*4
 pixels=[tuple(rgba[i:i+4]) for i in range(0,len(rgba),4)]
 # Merge only adjacent pixels of identical color. Every source silhouette and color boundary is preserved.
 used=set();rects=[]
 for y in range(h):
  for x in range(w):
   color=pixels[y*w+x]
   if not color[3] or (x,y) in used:continue
   width=1
   while x+width<w and (x+width,y) not in used and pixels[y*w+x+width]==color:width+=1
   height=1
   while y+height<h and all((xx,y+height) not in used and pixels[(y+height)*w+xx]==color for xx in range(x,x+width)):height+=1
   rects.append((x,y,width,height,color))
   for yy in range(y,y+height):
    for xx in range(x,x+width):used.add((xx,yy))
 # Exhaustive source-coverage verification before constructing each mesh.
 reconstructed=[(0,0,0,0)]*(w*h)
 for x,y,rw,rh,c in rects:
  for yy in range(y,y+rh):
   for xx in range(x,x+rw):assert reconstructed[yy*w+xx][3]==0;reconstructed[yy*w+xx]=c
 assert all((actual==expected if expected[3] else actual[3]==0) for actual,expected in zip(reconstructed,pixels)),a['id']
 totalpixels+=w*h
 verts=[];faces=[];mids=[];vertexMap={};colors=[];colorMap={}
 def face(points,color):
  ids=[]
  for p in points:
   if p not in vertexMap:vertexMap[p]=len(verts);verts.append(p)
   ids.append(vertexMap[p])
  if color[:3] not in colorMap:colorMap[color[:3]]=len(colors);colors.append(color[:3])
  faces.append(ids);mids.append(colorMap[color[:3]])
 depth=.075;front=-depth/2;back=depth/2
 for x,y,rw,rh,c in rects:
  x0=x/16;x1=(x+rw)/16;top=-y/16;bottom=-(y+rh)/16
  face([(x0,front,top),(x0,front,bottom),(x1,front,bottom),(x1,front,top)],c)
  face([(x0,back,top),(x1,back,top),(x1,back,bottom),(x0,back,bottom)],c)
 def opaque(x,y):return 0<=x<w and 0<=y<h and pixels[y*w+x][3]>0
 # Extrude exposed silhouette edges only; color boundaries stay flat and editable.
 for y in range(h):
  for x in range(w):
   c=pixels[y*w+x]
   if not c[3]:continue
   x0=x/16;x1=(x+1)/16;top=-y/16;bottom=-(y+1)/16
   if not opaque(x-1,y):face([(x0,back,top),(x0,back,bottom),(x0,front,bottom),(x0,front,top)],c)
   if not opaque(x+1,y):face([(x1,front,top),(x1,front,bottom),(x1,back,bottom),(x1,back,top)],c)
   if not opaque(x,y-1):face([(x0,back,top),(x0,front,top),(x1,front,top),(x1,back,top)],c)
   if not opaque(x,y+1):face([(x0,front,bottom),(x0,back,bottom),(x1,back,bottom),(x1,front,bottom)],c)
 mesh=bpy.data.meshes.new(a['id']);mesh.from_pydata(verts,[],faces);mesh.update()
 for color in colors:mesh.materials.append(material(color))
 for poly,mi in zip(mesh.polygons,mids):poly.material_index=mi
 obj=bpy.data.objects.new(a['id'],mesh);metatiles.objects.link(obj)
 n=counts[kind];counts[kind]+=1;cols=80;obj.location=((number%cols)*2.1,0,-(number//cols)*2.5)
 source={k:v for k,v in a.items() if k not in ('rgba','atlas')};obj['asset_id']=a['id'];obj['source_kind']=kind;obj['source_width_px']=w;obj['source_height_px']=h;obj['units_per_pixel']=1/16;obj['source_rgba_sha256']=hashlib.sha256(bytes(rgba)).hexdigest();obj['source_provenance']=json.dumps(source,separators=(',',':'));obj['reconstruction']='Exact source-color silhouette extrusion, not photoreal reconstruction';obj['reachability']='Source-defined world-map palette/bank phase. Phase use is state-conditional; this does not prove all animation states.';obj.asset_mark();obj.asset_data.description=obj['reconstruction']+'; '+obj['reachability'];obj.asset_data.author='ROM source reconstruction; Southbird disassembly';obj.asset_data.tags.new('source-backed');obj.asset_data.tags.new('worldmap-state-conditional')
 totalpolys+=len(faces);index.append({'assetId':a['id'],'kind':kind,'vertices':len(verts),'polygons':len(faces),'rgbaSHA256':obj['source_rgba_sha256']})
 if number%500==0:print('WORLDMAP_LIBRARY_PROGRESS',number,len(assets),round(time.time()-started,1),flush=True)
assert sum(counts.values())==len(assets)
scene['source_rom_sha256']=data['romSHA256'];scene['disassembly_commit']=data.get('sourceCommit','09b1bd81a788de8ceec664a34094e84ddb463117');scene['binary_library_counts']=json.dumps(counts);scene['source_pixels_verified']=totalpixels
text=bpy.data.texts.new('README__SOURCE_COVERAGE');text.write('World-map source-phase asset library\n\n'+json.dumps({'counts':counts,'sourcePixelsVerified':totalpixels,'coverage':data.get('coverage','World-map metatiles in explicitly resolved source bank and palette phases'),'limitations':['These are editable source-aligned silhouette extrusions, not photoreal models.','World-map bank phases are state-conditional; these assets do not claim exhaustive animation coverage.','Palette/bank contexts come from source-defined world-map phases; runtime reachability must be checked separately.'],'sourceCatalog':str(catalog),'romSHA256':data['romSHA256'],'sourceCommit':data.get('sourceCommit','09b1bd81a788de8ceec664a34094e84ddb463117'),'credit':'Southbird SMB3 disassembly https://github.com/captainsouthbird/smb3'},indent=2))
scene.view_settings.view_transform='Standard';scene.world=bpy.data.worlds.new('SourceNeutral');scene.world.color=(.2,.2,.2)
output.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
report={'passed':True,'counts':counts,'totalObjects':len(assets),'polygons':totalpolys,'sourcePixelsVerified':totalpixels,'blend':str(output),'blendBytes':output.stat().st_size,'seconds':round(time.time()-started,2),'sourceCatalogSHA256':hashlib.sha256(catalog.read_bytes()).hexdigest(),'romSHA256':data['romSHA256'],'objects':index}
output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2));print('WORLDMAP_LIBRARY_DONE',json.dumps({k:v for k,v in report.items()if k!='objects'}),flush=True)
