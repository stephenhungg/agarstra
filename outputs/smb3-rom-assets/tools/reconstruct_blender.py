"""Build source-aligned Blender meshes from verified ROM pixels.
Run: Blender --background --python reconstruct_blender.py -- --catalog DIR --output DIR
These are literal asset blockouts, not invented photoreal geometry.
"""
import bpy, json, pathlib, argparse, sys, hashlib
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--output',required=True);p.add_argument('--skip-raw',action='store_true');p.add_argument('--include-binary',action='store_true',help='Also export all larger binary catalog entries; default reproduces the compact runtime library');opt=p.parse_args(args)
cat=pathlib.Path(opt.catalog).resolve();out=pathlib.Path(opt.output).resolve();out.mkdir(parents=True,exist_ok=True);(out/'glb').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene['purpose']='ROM-derived source asset reconstruction. Preserve source silhouette and palette; photoreal reauthoring remains separate.'
scene['pixel_scale']=1/16
materials={}
def material(c):
 key=tuple(c[:3]);name='NES_'+'_'.join(f'{v:02x}' for v in key)
 if key not in materials:
  m=bpy.data.materials.new(name);m.use_nodes=True
  # Convert sRGB source palette to linear scene RGB, matching glTF renderer color management.
  rgb=[(v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4) for v in key]
  bsdf=m.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(*rgb,1);bsdf.inputs['Roughness'].default_value=.66;m.diffuse_color=(*rgb,1)
  materials[key]=m
 return materials[key]
def collection(name):
 c=bpy.data.collections.new(name);scene.collection.children.link(c);return c
rawcoll=collection('01_Raw_CHR_Patterns__all_unique');assembled=collection('02_Assembled_Source_Assets');registry=[]
def mesh_asset(assetid,w,h,rgba,target,source,depth=.12):
 verts=[];faces=[];mids=[];colors=[];cmap={};zfront=-depth/2;zback=depth/2
 def pixel(x,y):
  if not(0<=x<w and 0<=y<h):return None
  c=rgba[(y*w+x)*4:(y*w+x)*4+4]
  return c if c[3]>0 else None
 def quad(points,col):
  k=tuple(col[:3])
  if k not in cmap:cmap[k]=len(colors);colors.append(k)
  start=len(verts);verts.extend(points);faces.append(tuple(range(start,start+4)));mids.append(cmap[k])
 for y in range(h):
  for x in range(w):
   col=pixel(x,y)
   if col is None:continue
   x0=x/16;x1=(x+1)/16;top=-y/16;bottom=-(y+1)/16
   quad([(x0,zfront,top),(x0,zfront,bottom),(x1,zfront,bottom),(x1,zfront,top)],col)
   quad([(x0,zback,top),(x1,zback,top),(x1,zback,bottom),(x0,zback,bottom)],col)
   if pixel(x-1,y) is None:quad([(x0,zback,top),(x0,zback,bottom),(x0,zfront,bottom),(x0,zfront,top)],col)
   if pixel(x+1,y) is None:quad([(x1,zfront,top),(x1,zfront,bottom),(x1,zback,bottom),(x1,zback,top)],col)
   if pixel(x,y-1) is None:quad([(x0,zback,top),(x0,zfront,top),(x1,zfront,top),(x1,zback,top)],col)
   if pixel(x,y+1) is None:quad([(x0,zfront,bottom),(x0,zback,bottom),(x1,zback,bottom),(x1,zfront,bottom)],col)
 mesh=bpy.data.meshes.new(assetid);mesh.from_pydata(verts,[],faces);mesh.update()
 for c in colors:mesh.materials.append(material(c))
 for poly,idx in zip(mesh.polygons,mids):poly.material_index=idx
 obj=bpy.data.objects.new(assetid,mesh);target.objects.link(obj)
 obj['asset_id']=assetid;obj['source_width_px']=w;obj['source_height_px']=h;obj['source_provenance']=json.dumps(source,separators=(',',':'));obj['reconstruction']='source-pixel silhouette extrusion; editable blockout'
 return obj
physical=json.loads((cat/'all-chr-inventory.json').read_text())
scene['source_rom_sha256']=physical['romSHA256']
if not opt.skip_raw:
 seen={};alias=[]
 for t in physical['tiles']:
  key=t['sha256']
  if key not in seen:
   i=len(seen);rgba=[]
   for value in t['indices']:
    v=[20,90,170,245][value];rgba.extend([v,v,v,255])
   obj=mesh_asset('chr_'+key[:20],8,8,rgba,rawcoll,{'pattern_sha256':key,'first_rom_offset':t['romByteOffset'],'indices_are_not_palettes':True},.035)
   obj.location=((i%64)*.65,0,-(i//64)*.65);seen[key]=obj
  alias.append({'physicalIndex':t['index'],'romOffset':t['romByteOffset'],'assetId':seen[key].name,'sha256':key})
 (out/'raw-tile-aliases.json').write_text(json.dumps(alias,indent=2))
 print('RECONSTRUCTED_RAW',len(seen),'unique meshes /',len(alias),'physical tiles',flush=True)
asset_files=[cat/'observed-assets.json']
if opt.include_binary:asset_files.append(cat/'binary-assets.json')
merged=[]
for file in asset_files:
 if file.exists():
  data=json.loads(file.read_text());merged.extend(data.get('assets',[]));merged.extend(data.get('sourceAssets',[]))
seen=set()
palettes={p['id']:p for p in json.loads((cat/'observed-assets.json').read_text()).get('palettes',[])}
for i,a in enumerate(merged):
 key=a.get('id') or a.get('assetId')
 if not key or key in seen:continue
 seen.add(key);rgba=a.get('rgba')
 if rgba is None:continue
 if a.get('paletteId') in palettes:
  a['sourceIdentity']=a['rawHex']+':'+''.join(f'{c:06x}' for c in palettes[a['paletteId']]['packedBBGGRR'])+':'+a['kind']
 w=a['width'];h=a['height'];source={k:v for k,v in a.items() if k not in ['rgba','occurrences']};obj=mesh_asset(key,w,h,rgba,assembled,source)
 obj.select_set(True);bpy.context.view_layer.objects.active=obj
 glb=out/'glb'/f'{key}.glb'
 bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_extras=True,export_materials='EXPORT')
 obj.select_set(False);obj.location=((i%16)*3,0,4+(i//16)*3)
 registry.append({'assetId':key,'path':'glb/'+glb.name,'width':w,'height':h,'origin':'top-left','unitsPerPixel':1/16,'source':source,'sourceRgbaSHA256':hashlib.sha256(bytes(rgba)).hexdigest(),'status':'source-aligned-blockout'})
 if i%25==0:print('ASSEMBLED',i,len(merged),flush=True)
rawcoll.hide_render=True
scene['assembled_asset_count']=len(registry);scene['physical_tile_count']=physical['physicalTileCount'];scene['unique_pattern_count']=physical['uniquePatternCount']
scene.world.color=(.04,.04,.04)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'rom-source-assets.blend'))
(out/'replacement-registry.json').write_text(json.dumps({'romSHA256':physical['romSHA256'],'schemaVersion':1,'entries':registry,'rawGeometryCoverage':'all unique physical CHR patterns, grayscale index values','assembledCoverage':'see catalog manifests: observed entries do not imply exhaustive semantic coverage'},indent=2))
print('DONE',len(registry),'assembled assets',flush=True)
