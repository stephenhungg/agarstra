import bpy,json,hashlib,os
from pathlib import Path
OUT=Path(__file__).resolve().parent;BASE=OUT.parent.parent

def load(path,clip):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(path));r=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');m=next(o for o in bpy.context.scene.objects if o.type=='MESH');
 for t in r.animation_data.nla_tracks:t.mute=True
 r.animation_data.action=bpy.data.actions[clip];return r,m

def coords(m,f):
 bpy.context.scene.frame_set(f);bpy.context.view_layer.update();e=m.evaluated_get(bpy.context.evaluated_depsgraph_get());em=e.to_mesh();p=[e.matrix_world@v.co for v in em.vertices];e.to_mesh_clear();return p
results={}
for clip,frames in [('idle',[1,31,61,91,121]),('walk',list(range(31)))]:
 r,m=load(Path(os.environ.get('TRAINER_SOURCE_GLB',str(BASE/'models/trainer-direct-v2.glb'))),clip);lower={g.index for g in m.vertex_groups if any(s in g.name for s in ['Leg','Foot','Toe'])};ids=[v.index for v in m.data.vertices if sum(g.weight for g in v.groups if g.group in lower)>.99];base={f:coords(m,f)for f in frames}
 r,m=load(BASE/'models/trainer-direct-v3.glb',clip);dest={f:coords(m,f)for f in frames};err=max((base[f][i]-dest[f][i]).length for f in frames for i in ids);assert err<1e-6,err
 results[clip]={'samples':len(frames),'legFootVertices':len(ids),'maxDeformedLegFootError':err}
 if clip=='walk':
  loop=max((a-b).length for a,b in zip(dest[0],dest[30]));assert loop<.0001,loop;results[clip]['loopMaxVertexError']=loop
p=BASE/'models/trainer-direct-v3.glb';results['sha256']=hashlib.sha256(p.read_bytes()).hexdigest();results['passed']=True;(OUT/'deformation-verification.json').write_text(json.dumps(results,indent=2));print(json.dumps(results))
