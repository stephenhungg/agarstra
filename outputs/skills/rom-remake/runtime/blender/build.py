"""Portable source-preserving NES tile reconstruction. Candidate relief, not inferred whole objects."""
import bpy, json, pathlib, argparse, sys, hashlib, math
args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--out',required=True);p.add_argument('--ids',required=True);opt=p.parse_args(args)
cat=pathlib.Path(opt.catalog).resolve();out=pathlib.Path(opt.out).resolve();out.mkdir(parents=True,exist_ok=True);(out/'models').mkdir(exist_ok=True)
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene['purpose']='Source-preserving prototype relief. Not whole-object artistic acceptance.'
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
assembled=collection('Source_Reconstruction');registry=[]
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

assets=json.loads(cat.read_text());data=json.loads((cat.parent/'source.json').read_text());selected=set(json.loads(pathlib.Path(opt.ids).read_text()))
for asset in assets:
 if asset['id'] not in selected:continue
 rgba=asset['rgba']
 if not any(rgba[3::4]):continue
 source={'sourceIdentity':asset['sourceAssetId'],'romSha256':data.get('romSha256'),'provenance':asset.get('provenance',asset.get('romSources',[]))}
 obj=mesh_asset(asset['id'],8,8,rgba,assembled,source,depth=.03)
 obj.select_set(True);bpy.context.view_layer.objects.active=obj
 file=out/'models'/(asset['id']+'.glb')
 bpy.ops.export_scene.gltf(filepath=str(file),export_format='GLB',use_selection=True,export_extras=True,export_materials='EXPORT')
 obj.select_set(False)
 registry.append({'id':asset['id'],'path':'models/'+file.name,'width':8,'height':8,'source':source,'sha256':hashlib.sha256(file.read_bytes()).hexdigest(),'quality':'source-relief-prototype'})
 i=len(registry)-1;obj.location=((i%12)*.6,0,-(i//12)*.6)
scene.world.color=tuple((v/255/12.92 if v/255<=.04045 else ((v/255+.055)/1.055)**2.4) for v in (30,35,30))
scene.view_settings.view_transform='Standard';scene.view_settings.look='None'
scene.view_settings.exposure=0;scene.view_settings.gamma=1
# Contact sheet rendered from the actual generated meshes, with editable geometry retained.
rows=max(1,math.ceil(len(registry)/12));width=7.2;height=rows*.6
bpy.ops.object.camera_add(location=(width/2,-12,-height/2))
camera=bpy.context.object;camera.rotation_euler=(math.pi/2,0,0);camera.data.type='ORTHO';camera.data.ortho_scale=max(width,height)*1.12;scene.camera=camera
scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.light='FLAT';scene.display.shading.color_type='MATERIAL';scene.display.shading.show_shadows=False;scene.display.shading.background_type='WORLD'
scene.render.resolution_x=1024;scene.render.resolution_y=1024;scene.render.resolution_percentage=100
scene.render.filepath=str(out/'render.png');bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
(out/'registry.json').write_text(json.dumps({'profile':'prototype','romSha256':data.get('romSha256'),'assets':registry},indent=2))
print('EXPORTED',len(registry),flush=True)
