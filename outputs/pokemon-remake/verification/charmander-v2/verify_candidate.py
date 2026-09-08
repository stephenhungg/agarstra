"""Validate/render only the actual v2 GLB, in a fresh Blender scene."""
import bpy, json, math, hashlib, numpy as np, struct
from pathlib import Path
from mathutils import Vector,kdtree
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/verification/charmander-v2'
GLB=ROOT/'outputs/pokemon-remake/models/charmander-existing-v2.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(GLB))
mesh=next(o for o in scene.objects if o.type=='MESH')
rig=next(o for o in scene.objects if o.type=='ARMATURE')
def positions():
    e=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=e.to_mesh()
    result=[e.matrix_world@v.co for v in m.vertices];e.to_mesh_clear();return result
samples={};root_matrices={}
for f in range(91):
    scene.frame_set(f);samples[f]=positions();root_matrices[f]=rig.matrix_world.copy()
source=np.load(OUT/'authored-samples.npz')
tree=kdtree.KDTree(len(source['0']))
for i,point in enumerate(source['0']):tree.insert(Vector(point),i)
tree.balance();mapping=[tree.find(p) for p in samples[0]]
comparison=[]
for key in source.files:
    frame=int(key);errors=[(co-Vector(source[key][mapping[i][1]])).length for i,co in enumerate(samples[frame])]
    comparison.append({'frame':frame,'maxError':max(errors),'meanError':sum(errors)/len(errors)})
feet=[i for i,p in enumerate(samples[0]) if p.z<.04]
maxfoot=max((sample[i]-samples[0][i]).length for sample in samples.values() for i in feet)
loop=max((a-b).length for a,b in zip(samples[0],samples[90]))
motion=max((a-b).length for sample in samples.values() for a,b in zip(sample,samples[0]))
all_coords=[p for sample in samples.values() for p in sample]
lo=Vector([min(c[i] for c in all_coords) for i in range(3)])
hi=Vector([max(c[i] for c in all_coords) for i in range(3)])
center=(lo+hi)/2;span=max(hi-lo)
data=GLB.read_bytes();length=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+length])
clip_info=[{'name':a['name'],'channels':len(a['channels']),'keyTimeMin':min(gltf['accessors'][s['input']]['min'][0] for s in a['samplers']),'keyTimeMax':max(gltf['accessors'][s['input']]['max'][0] for s in a['samplers'])} for a in gltf.get('animations',[])]
report={'status':'candidate pending visual review','glbSHA256':hashlib.sha256(data).hexdigest(),'clips':clip_info,'actualImportedActions':[{'name':a.name,'frames':list(a.frame_range)} for a in bpy.data.actions],'skinBones':len(rig.data.bones),'meshVertices':len(mesh.data.vertices),'triangles':sum(len(p.vertices)-2 for p in mesh.data.polygons),'materials':gltf['materials'],'sourceExportComparisons':comparison,'sampledFrames':91,'footVertices':len(feet),'maxFootVertexTravel':maxfoot,'loopClosureMaxVertexError':loop,'maxIdleVertexTravel':motion,'maxRootMatrixDelta':max(abs(root_matrices[f][r][c]-root_matrices[0][r][c]) for f in root_matrices for r in range(4) for c in range(4)),'allFrameBoundsBlender':{'min':list(lo),'max':list(hi)},'allFrameBoundsGLTF':{'min':[lo.x,lo.z,-hi.y],'max':[hi.x,hi.z,-lo.y]},'restFeetY':min(p.z for p in samples[0]),'rigRootMatrix':list(map(list,rig.matrix_world)),'sourceAttribution':['Charmander rig created by Milos Cerny and downloaded at http://www.miloscerny.com/','3D model created by Guilherme Lauck https://sketchfab.com/guilauck'],'license':'CC BY-NC 4.0'}
assert len(clip_info)==1 and clip_info[0]['name']=='idle'
assert abs(clip_info[0]['keyTimeMin'])<1e-8 and abs(clip_info[0]['keyTimeMax']-3)<1e-6
assert maxfoot<1e-5 and loop<1e-5 and 0<motion<.025
assert report['maxRootMatrixDelta']<1e-8
(OUT/'verification.json').write_text(json.dumps(report,indent=2))

scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1000;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral Review World');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.7,.76,.8,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.35
bpy.ops.mesh.primitive_plane_add(size=span*200,location=(0,0,lo.z-.002))
floor=bpy.context.object;floor.name='REVIEW_Floor';mat=bpy.data.materials.new('REVIEW_Neutral floor');mat.diffuse_color=(.2,.23,.24,1);floor.data.materials.append(mat)
for name,offset,energy in [('Key',(1.5,-2,2.5),180),('Fill',(-1,1,1.5),80)]:
    d=bpy.data.lights.new('REVIEW_'+name,'AREA');d.energy=energy;d.shape='DISK';d.size=2
    o=bpy.data.objects.new('REVIEW_'+name,d);scene.collection.objects.link(o);o.location=Vector(offset);o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('REVIEW_Camera');cam=bpy.data.objects.new('REVIEW_Camera',d);scene.collection.objects.link(cam);d.type='ORTHO';d.ortho_scale=span*1.45;scene.camera=cam;scene.view_settings.view_transform='AgX'
for f,name,direction in [(0,'front',(1.5,-3,1.3)),(22,'idle-inhale',(1.5,-3,1.3)),(67,'idle-exhale',(1.5,-3,1.3)),(0,'back',(-2,3,1.4))]:
    scene.frame_set(f);cam.location=center+Vector(direction)*span;cam.rotation_euler=(center-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
scene.frame_start=0;scene.frame_end=90;scene.frame_set(0)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'actual-export-review.blend'))
print('VERIFIED',json.dumps({k:v for k,v in report.items() if k not in ['materials','sourceExportComparisons','rigRootMatrix']}))
