"""Reimport the exact runtime GLB, sample deformed skin, and render clip evidence."""
import bpy,json,hashlib,struct,sys,math
import numpy as np
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
QUICK='--quick' in args[2:]
GLB=Path(args[0]);OUT=Path(args[1]);OUT.mkdir(parents=True,exist_ok=True)
SOURCE_SHA=hashlib.sha256(GLB.read_bytes()).hexdigest()
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=30
bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
rigs=[o for o in scene.objects if o.type=='ARMATURE']
assert meshes and rigs,'No animated skin imported'
for o in list(scene.objects):
    if o.type=='MESH' and o not in meshes:bpy.data.objects.remove(o,do_unlink=True)
actions=list(bpy.data.actions)
for rig in rigs:
    for track in rig.animation_data.nla_tracks:track.mute=True
def pose(action,frame):
    for rig in rigs:
        rig.animation_data.action=action
        if action.slots:rig.animation_data.action_slot=action.slots[0]
    scene.frame_set(frame);bpy.context.view_layer.update()
def points():
    result=[];dg=bpy.context.evaluated_depsgraph_get()
    for obj in meshes:
        e=obj.evaluated_get(dg);m=e.to_mesh();vertices=np.empty(len(m.vertices)*3,dtype=np.float32);m.vertices.foreach_get('co',vertices);vertices=vertices.reshape(-1,3);matrix=np.array(e.matrix_world);result.append(vertices@matrix[:3,:3].T+matrix[:3,3]);e.to_mesh_clear()
    return np.concatenate(result)
def bounds(ps):return {'min':ps.min(axis=0).tolist(),'max':ps.max(axis=0).tolist()}
def travel_between(a,b):return float(np.linalg.norm(a-b,axis=1).max())
idle=next(a for a in actions if a.name=='idle');pose(idle,0)
base=points();bb=bounds(base);foot=np.flatnonzero(base[:,2]<bb['min'][2]+.025)
stats=[]
for a in actions:
    last=round(a.frame_range[1]);samples=[];first=None;foot_travel=0;travel=0
    for frame in (sorted({0,round(last*.25),round(last*.43),round(last*.75),last}) if QUICK else range(0,last+1)):
        pose(a,frame);ps=points()
        if first is None:first=ps
        foot_travel=max(foot_travel,travel_between(ps[foot],base[foot]))
        travel=max(travel,travel_between(ps,base))
        if frame in {0,round(last*.25),round(last*.5),round(last*.75),last}:samples.append({'frame':frame,'bounds':bounds(ps),'maxVertexDisplacement':travel_between(ps,base)})
    stats.append({'name':a.name,'durationSeconds':last/30,'sampledFrameCount':5 if QUICK else last+1,'samples':samples,'maxFootTravel':foot_travel,'loopError':travel_between(first,ps),'maxTravel':travel})
pose(idle,0)
center=Vector(((bb['min'][0]+bb['max'][0])/2,(bb['min'][1]+bb['max'][1])/2,(bb['min'][2]+bb['max'][2])/2))
span=max(bb['max'][i]-bb['min'][i] for i in range(3))
scene.render.engine='CYCLES';scene.cycles.samples=8 if QUICK else 16;scene.cycles.use_denoising=True
scene.render.resolution_x=640 if QUICK else 720;scene.render.resolution_y=640 if QUICK else 720;scene.render.resolution_percentage=100
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG'
scene.world=bpy.data.worlds.new('Neutral verification studio');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.55,.62,.68,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value=.4
bpy.ops.mesh.primitive_plane_add(size=span*200,location=(0,0,bb['min'][2]-.004))
floor=bpy.context.object;mat=bpy.data.materials.new('Matte review floor');mat.diffuse_color=(.17,.2,.2,1);floor.data.materials.append(mat)
for name,vec,power in [('Key',(2,-3,3),220),('Fill',(-2,-1,2),90),('Rim',(1,3,2),130)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power*span*span;d.size=span*2.5
    o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=center+Vector(vec)*span;o.rotation_euler=(center-o.location).to_track_quat('-Z','Y').to_euler()
d=bpy.data.cameras.new('Review');camera=bpy.data.objects.new('Review',d);scene.collection.objects.link(camera);scene.camera=camera;d.type='ORTHO';d.ortho_scale=span*1.55
evidence=[]
for a in actions:
    if QUICK and a.name not in ['attack','idle','faint']:continue
    fractions=[0,.25,.43,.7,1] if a.name=='attack' else [0,.5] if a.name=='idle' else [.4] if a.name in ['hit','growl','tailWhip'] else [1]
    if QUICK:fractions=[.43] if a.name=='attack' else [0] if a.name=='idle' else [1]
    for f in fractions:
        frame=round(a.frame_range[1]*f);pose(a,frame)
        camera.location=center+Vector((1.2,-3,1.1))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        path=OUT/f'{a.name}-{frame:03}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);evidence.append({'clip':a.name,'frame':frame,'file':path.name})
pose(idle,0);camera.location=center+Vector((-1.5,3,1.2))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'back.png');bpy.ops.render.render(write_still=True)
data=GLB.read_bytes();assert hashlib.sha256(data).hexdigest()==SOURCE_SHA,'GLB changed during verification';jlen=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+jlen])
report={'glb':str(GLB),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'skinBones':sum(len(r.data.bones) for r in rigs),'height':bb['max'][2]-bb['min'][2],'groundOffset':-bb['min'][2],'up':'+Y','front':'+Z, visual inspection required','rootPositions':[list(r.location) for r in rigs],'clips':stats,'evidence':evidence,'embeddedDependencies':not any(x.get('uri') and not x['uri'].startswith('data:') for x in gltf.get('images',[])+gltf.get('buffers',[])),'status':'candidate pending visual review','verificationScope':'five source-frame samples per clip and peak/rest/faint/back images' if QUICK else 'every source frame in every clip and full render sequence'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
html='<!doctype html><meta charset="utf-8"><title>Starter battle clip evidence</title><style>body{font:16px system-ui;background:#182020;color:white;margin:24px}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}img{width:100%}figure{margin:0}figcaption{padding:8px}</style><h1>'+GLB.stem+'</h1><p>Actual GLB reimport, original source-owned placement. Candidate review.</p><div class="grid">'
for item in evidence:html+=f'<figure><img src="{item["file"]}"><figcaption>{item["clip"]} frame {item["frame"]}</figcaption></figure>'
html+='</div>';(OUT/'motion-review.html').write_text(html)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'actual-export-review.blend'))
print(json.dumps({k:v for k,v in report.items() if k not in ['clips','evidence']}))
