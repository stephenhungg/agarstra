"""Build a separate, source-backed Blender library; never replaces rom-source-assets.blend.
Run: Blender --background --python reconstruct_binary_library.py -- --catalog binary-assets.json --output binary-defined-assets.blend
"""
import bpy, sys, argparse, json, hashlib, time
from pathlib import Path
parser=argparse.ArgumentParser();parser.add_argument('--catalog',required=True);parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);catalog=Path(args.catalog).resolve();output=Path(args.output).resolve()
assert output.name!='rom-source-assets.blend','Separate output required'
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
metatiles=collection('01_Binary_Metatiles__5747_Source_Context_Compositions')
players=collection('02_DIAGNOSTIC_Player_Previews__Reachability_UNVERIFIED')
counts={'binary-metatile':0,'binary-player-template-preview':0};totalpolys=0;totalpixels=0;started=time.time();index=[]
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
 obj=bpy.data.objects.new(a['id'],mesh);target=metatiles if kind=='binary-metatile' else players;target.objects.link(obj)
 n=counts[kind];counts[kind]+=1;cols=80 if kind=='binary-metatile' else 32;obj.location=((n%cols)*2.1+(0 if kind=='binary-metatile' else 175),0,-(n//cols)*2.5)
 source={k:v for k,v in a.items() if k not in ('rgba','atlas')};obj['asset_id']=a['id'];obj['source_kind']=kind;obj['source_width_px']=w;obj['source_height_px']=h;obj['units_per_pixel']=1/16;obj['source_rgba_sha256']=hashlib.sha256(bytes(rgba)).hexdigest();obj['source_provenance']=json.dumps(source,separators=(',',':'));obj['reconstruction']='Exact source-color silhouette extrusion, not photoreal reconstruction';obj['reachability']='UNVERIFIED diagnostic suit/shared-template combination' if kind!='binary-metatile' else 'Source-defined initial palette/bank context; later animation banks not inferred';obj.asset_mark();obj.asset_data.description=obj['reconstruction']+'; '+obj['reachability'];obj.asset_data.author='ROM source reconstruction; Southbird disassembly';obj.asset_data.tags.new('source-backed');obj.asset_data.tags.new('metatile' if kind=='binary-metatile' else 'diagnostic-unverified')
 totalpolys+=len(faces);index.append({'assetId':a['id'],'kind':kind,'vertices':len(verts),'polygons':len(faces),'rgbaSHA256':obj['source_rgba_sha256']})
 if number%500==0:print('BINARY_LIBRARY_PROGRESS',number,len(assets),round(time.time()-started,1),flush=True)
assert counts['binary-metatile']==data['counts']['metatileRGBAAssets'];assert counts['binary-player-template-preview']==data['counts']['playerUniquePreviewImages']
scene['source_rom_sha256']=data['romSHA256'];scene['disassembly_commit']=data['sourceCommit'];scene['binary_library_counts']=json.dumps(counts);scene['source_pixels_verified']=totalpixels
text=bpy.data.texts.new('README__SOURCE_COVERAGE');text.write('Binary-defined source asset library\n\n'+json.dumps({'counts':counts,'sourcePixelsVerified':totalpixels,'coverage':data['coverage'],'limitations':['These are editable source-aligned silhouette extrusions, not photoreal models.','Player previews are diagnostic; reachable gameplay states are unverified.','Palette/bank contexts are initial source-defined contexts; animated banks require runtime extraction.'],'sourceCatalog':str(catalog),'romSHA256':data['romSHA256'],'sourceCommit':data['sourceCommit'],'credit':'Southbird SMB3 disassembly https://github.com/captainsouthbird/smb3'},indent=2))
scene.view_settings.view_transform='Standard';scene.world=bpy.data.worlds.new('SourceNeutral');scene.world.color=(.2,.2,.2)
output.parent.mkdir(parents=True,exist_ok=True);bpy.ops.wm.save_as_mainfile(filepath=str(output),compress=True)
report={'passed':True,'counts':counts,'totalObjects':len(assets),'polygons':totalpolys,'sourcePixelsVerified':totalpixels,'blend':str(output),'blendBytes':output.stat().st_size,'seconds':round(time.time()-started,2),'sourceCatalogSHA256':hashlib.sha256(catalog.read_bytes()).hexdigest(),'romSHA256':data['romSHA256'],'objects':index}
output.with_suffix('.verification.json').write_text(json.dumps(report,indent=2));print('BINARY_LIBRARY_DONE',json.dumps({k:v for k,v in report.items()if k!='objects'}),flush=True)
