"""Headless Blender contact sheet of actual exported GLBs, not source screenshots."""
import bpy,sys,argparse,math,json
from pathlib import Path
from mathutils import Vector
p=argparse.ArgumentParser();p.add_argument('--family',type=Path,required=True);p.add_argument('--samples',type=int,default=24);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);files=sorted((a.family/'models').glob('*.glb'))
if not files:raise RuntimeError('No exported GLBs to render')
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
cols=min(3,len(files));rows=math.ceil(len(files)/cols);items=[];staged=[]
for i,file in enumerate(files):
 before=set(bpy.data.objects);bpy.ops.import_scene.gltf(filepath=str(file));objects=list(set(bpy.data.objects)-before);mesh=[o for o in objects if o.type=='MESH'];bpy.context.view_layer.update()
 points=[o.matrix_world@Vector(v) for o in mesh for v in o.bound_box]
 if not points:raise RuntimeError('Imported asset has no bounds: '+file.name)
 lo=Vector(tuple(min(v[k]for v in points)for k in range(3)));hi=Vector(tuple(max(v[k]for v in points)for k in range(3)));size=hi-lo
 root=bpy.data.objects.new(file.stem+'_preview_root',None);bpy.context.collection.objects.link(root)
 for o in objects:
  if o.parent not in objects:world=o.matrix_world.copy();o.parent=root;o.matrix_world=world
 factor=2.15/max(size.x,size.y,size.z,.001);root.scale=(factor,)*3;x=(i%cols-(cols-1)/2)*3.2;y=(i//cols-(rows-1)/2)*3.6;root.location=(x-(lo.x+hi.x)/2*factor,y-(lo.y+hi.y)/2*factor,-lo.z*factor+.04)
 # Labels are part of this verification stage only; exports are untouched.
 curve=bpy.data.curves.new(file.stem+'_label','FONT');curve.body=file.stem;curve.align_x='CENTER';curve.size=.19;curve.extrude=.0005;text=bpy.data.objects.new(curve.name,curve);bpy.context.collection.objects.link(text);text.location=(x,y-1.42,.08);text.rotation_euler=(math.pi/2,0,0)
 labelmat=bpy.data.materials.get('Label ink') or bpy.data.materials.new('Label ink');labelmat.diffuse_color=(.10,.14,.13,1);text.data.materials.append(labelmat)
 staged.extend(mesh);staged.append(text)
 items.append({'asset':file.name,'originalBounds':{'min':list(lo),'max':list(hi)},'previewScale':factor})
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.01));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral studio floor');mat.use_nodes=True;b=mat.node_tree.nodes.get('Principled BSDF');b.inputs['Base Color'].default_value=(.35,.40,.36,1);b.inputs['Roughness'].default_value=.82;floor.data.materials.append(mat)
center=Vector((0,0,.65));bpy.ops.object.camera_add(location=(3.2,-10.5,7.7));cam=bpy.context.object;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='ORTHO';cam.data.ortho_scale=max(6.6,cols*3.45,rows*4.9);bpy.context.scene.camera=cam
for pos,power,size,col in [((-5,-4,8),1600,5,(1,.85,.68)),((5,-1,5),1000,5,(.70,.85,1)),((1,5,7),1800,4,(1,1,.88))]:
 bpy.ops.object.light_add(type='AREA',location=pos);l=bpy.context.object;l.data.energy=power;l.data.shape='DISK';l.data.size=size;l.data.color=col;l.rotation_euler=(center-l.location).to_track_quat('-Z','Y').to_euler()
bpy.context.view_layer.update()
# Fit the actual imported bounds and labels in camera space; no family gets cropped.
inv=cam.matrix_world.inverted();projected=[inv@(o.matrix_world@Vector(v))for o in staged for v in o.bound_box]
minx=min(v.x for v in projected);maxx=max(v.x for v in projected);miny=min(v.y for v in projected);maxy=max(v.y for v in projected)
cam.location+=cam.rotation_euler.to_matrix()@Vector(((minx+maxx)/2,(miny+maxy)/2,0))
cam.data.ortho_scale=max(maxx-minx,(maxy-miny)*1280/720)*1.14
s=bpy.context.scene;s.render.engine='CYCLES';s.cycles.samples=a.samples;s.cycles.use_denoising=True;s.render.threads_mode='FIXED';s.render.threads=4;s.world.use_nodes=True;s.world.node_tree.nodes['Background'].inputs[0].default_value=(.25,.30,.28,1);s.world.node_tree.nodes['Background'].inputs[1].default_value=.35;s.render.resolution_x=1280;s.render.resolution_y=720;s.render.resolution_percentage=100;s.render.filepath=str(a.family/'preview.png');bpy.ops.render.render(write_still=True)
(a.family/'render-report.json').write_text(json.dumps({'rendered':True,'source':'actual exported GLB imports','engine':'Cycles','samples':a.samples,'resolution':[1280,720],'stageOnly':True,'assets':items},indent=2))
