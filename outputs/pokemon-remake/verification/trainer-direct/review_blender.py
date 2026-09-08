"""Inspect the returned GLB without changing its skin or guessing an action mapping."""
import bpy,json,hashlib,math,sys
from pathlib import Path
from mathutils import Vector
root=Path('/Users/stephenhung/Documents/GitHub/agarstra');out=root/'outputs/pokemon-remake/verification/trainer-direct';glb=Path(sys.argv[sys.argv.index('--')+1]) if '--' in sys.argv else root/'outputs/pokemon-remake/models/trainer-direct-v1.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(glb));scene=bpy.context.scene
meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)];rigs=[o for o in scene.objects if o.type=='ARMATURE'];actions=[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions]
def vertices():
 points=[];dg=bpy.context.evaluated_depsgraph_get()
 for obj in meshes:
  evaluated=obj.evaluated_get(dg);mesh=evaluated.to_mesh();points.extend(evaluated.matrix_world@v.co for v in mesh.vertices);evaluated.to_mesh_clear()
 return points
def bounds(points):return {'min':[min(p[i] for p in points) for i in range(3)],'max':[max(p[i] for p in points) for i in range(3)]}
active=[{'rig':r.name,'action':r.animation_data.action.name if r.animation_data and r.animation_data.action else None,'nlaTracks':len(r.animation_data.nla_tracks) if r.animation_data else 0} for r in rigs]
frame0=min((a['frames'][0] for a in actions),default=0);frame1=max((a['frames'][1] for a in actions),default=0);frames=sorted(set(round(frame0+(frame1-frame0)*t) for t in [0,.25,.5,.75,1]))
scene.frame_set(round(frame0));initial=vertices();b=bounds(initial);height=b['max'][2]-b['min'][2];center=Vector([(lo+hi)/2 for lo,hi in zip(b['min'],b['max'])]);samples=[]
for frame in frames:
 scene.frame_set(frame);points=vertices();samples.append({'frame':frame,'seconds':frame/30,'bounds':bounds(points),'maxVertexTravelFromFirst':max((a-b).length for a,b in zip(points,initial))})
report={'glb':str(glb),'glbSHA256':hashlib.sha256(glb.read_bytes()).hexdigest(),'status':'candidate-requires-visual-review','meshCount':len(meshes),'armatureCount':len(rigs),'bones':sum(len(r.data.bones) for r in rigs),'vertices':sum(len(o.data.vertices) for o in meshes),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'actions':actions,'activeAnimation':active,'boundsBlenderZUp':b,'height':height,'samples':samples,'materials':[{'name':m.name,'surfaceRenderMethod':m.surface_render_method} for m in bpy.data.materials],'skeleton':[{'rig':r.name,'bones':[{'name':b.name,'parent':b.parent.name if b.parent else None,'headLocal':list(b.head_local),'tailLocal':list(b.tail_local),'restMatrixLocal':[list(row) for row in b.matrix_local]} for b in r.data.bones]} for r in rigs]}
(out/'blender-review.json').write_text(json.dumps(report,indent=2))
world=bpy.data.worlds.new('Neutral inspection');scene.world=world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs['Color'].default_value=(.13,.16,.17,1);world.node_tree.nodes['Background'].inputs['Strength'].default_value=.65
bpy.ops.mesh.primitive_plane_add(size=max(height*5,5),location=(center.x,center.y,b['min'][2]-.008));floor=bpy.context.object;mat=bpy.data.materials.new('Neutral floor');mat.diffuse_color=(.18,.22,.22,1);floor.data.materials.append(mat)
def light(name,loc,power,size):
 data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size;obj=bpy.data.objects.new(name,data);scene.collection.objects.link(obj);obj.location=loc;obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
light('Key',center+Vector((height*1.7,-height*2, height*2)),700,height*2);light('Fill',center+Vector((-height*2,-height*.5,height)),350,height*2);light('Rim',center+Vector((0,height*2,height*1.5)),500,height)
cameraData=bpy.data.cameras.new('Review camera');camera=bpy.data.objects.new('Review camera',cameraData);scene.collection.objects.link(camera);scene.camera=camera;cameraData.type='ORTHO';cameraData.ortho_scale=height*1.4
scene.render.engine='CYCLES';scene.cycles.samples=24;scene.render.resolution_x=900;scene.render.resolution_y=1000;scene.render.resolution_percentage=100;scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
for name,offset in [('front',(height*.3,-height*3,height*.25)),('back',(-height*.3,height*3,height*.25))]:
 camera.location=center+Vector(offset);camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
 for frame in frames if name=='front' else [frames[0]]:
  scene.frame_set(frame);scene.render.filepath=str(out/f'{name}-frame-{frame}.png');bpy.ops.render.render(write_still=True)
scene.frame_set(frames[0]);bpy.ops.wm.save_as_mainfile(filepath=str(root/'outputs/pokemon-remake/models/trainer-direct-v1.blend'));print(json.dumps(report))
