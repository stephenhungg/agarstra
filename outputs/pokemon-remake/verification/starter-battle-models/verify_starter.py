"""Reimport the exact runtime GLB, sample deformed skin, and render clip evidence."""
import bpy,json,hashlib,struct,sys,math
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
GLB=Path(args[0]);OUT=Path(args[1]);OUT.mkdir(parents=True,exist_ok=True)
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
        e=obj.evaluated_get(dg);m=e.to_mesh();result.extend(e.matrix_world@v.co for v in m.vertices);e.to_mesh_clear()
    return result
def bounds(ps):return {'min':[min(p[i] for p in ps) for i in range(3)],'max':[max(p[i] for p in ps) for i in range(3)]}
idle=next(a for a in actions if a.name=='idle');pose(idle,0)
base=points();bb=bounds(base);foot=[i for i,p in enumerate(base) if p.z<bb['min'][2]+.025]
stats=[]
for a in actions:
    last=round(a.frame_range[1]);samples=[];first=None;last_pose=None;maxfoot=0;maxtravel=0
    for frame in range(0,last+1):
        pose(a,frame);ps=points()
        if first is None:first=ps
        last_pose=ps
        maxfoot=max(maxfoot,max((ps[i]-base[i]).length for i in foot))
        maxtravel=max(maxtravel,max((p-q).length for p,q in zip(ps,base)))
        if frame in {0,round(last*.25),round(last*.5),round(last*.75),last}:samples.append({'frame':frame,'bounds':bounds(ps),'maxVertexDisplacement':max((p-q).length for p,q in zip(ps,base))})
    stats.append({'name':a.name,'durationSeconds':last/30,'samples':samples,'maxFootTravel':maxfoot,'loopError':max((p-q).length for p,q in zip(first,last_pose)),'maxTravel':maxtravel})
pose(idle,0)
center=Vector(((bb['min'][0]+bb['max'][0])/2,(bb['min'][1]+bb['max'][1])/2,(bb['min'][2]+bb['max'][2])/2))
span=max(bb['max'][i]-bb['min'][i] for i in range(3))
scene.render.engine='CYCLES';scene.cycles.samples=20;scene.cycles.use_denoising=True
scene.render.resolution_x=720;scene.render.resolution_y=720;scene.render.resolution_percentage=100
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
    fractions=[0,.25,.43,.7,1] if a.name=='attack' else [0,.5] if a.name=='idle' else [.4] if a.name in ['hit','growl','tailWhip'] else [1]
    for f in fractions:
        frame=round(a.frame_range[1]*f);pose(a,frame)
        camera.location=center+Vector((1.2,-3,1.1))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
        path=OUT/f'{a.name}-{frame:03}.png';scene.render.filepath=str(path);bpy.ops.render.render(write_still=True);evidence.append({'clip':a.name,'frame':frame,'file':path.name})
pose(idle,0);camera.location=center+Vector((-1.5,3,1.2))*span;camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'back.png');bpy.ops.render.render(write_still=True)
data=GLB.read_bytes();jlen=struct.unpack_from('<I',data,12)[0];gltf=json.loads(data[20:20+jlen])
report={'glb':str(GLB),'sha256':hashlib.sha256(data).hexdigest(),'bytes':len(data),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),'skinBones':sum(len(r.data.bones) for r in rigs),'height':bb['max'][2]-bb['min'][2],'groundOffset':-bb['min'][2],'up':'+Y','front':'+Z, visual inspection required','rootPositions':[list(r.location) for r in rigs],'clips':stats,'evidence':evidence,'embeddedDependencies':not any(x.get('uri') and not x['uri'].startswith('data:') for x in gltf.get('images',[])+gltf.get('buffers',[])),'status':'candidate pending visual review'}
(OUT/'verification.json').write_text(json.dumps(report,indent=2))
html='<!doctype html><meta charset="utf-8"><title>Starter battle clip evidence</title><style>body{font:16px system-ui;background:#182020;color:white;margin:24px}.grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px}img{width:100%}figure{margin:0}figcaption{padding:8px}</style><h1>'+GLB.stem+'</h1><p>Actual GLB reimport, original source-owned placement. Candidate review.</p><div class="grid">'
for item in evidence:html+=f'<figure><img src="{item["file"]}"><figcaption>{item["clip"]} frame {item["frame"]}</figcaption></figure>'
html+='</div>';(OUT/'motion-review.html').write_text(html)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'actual-export-review.blend'))
print(json.dumps({k:v for k,v in report.items() if k not in ['clips','evidence']}))
