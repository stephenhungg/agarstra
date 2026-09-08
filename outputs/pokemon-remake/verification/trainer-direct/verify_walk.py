import bpy,json,hashlib,math
from pathlib import Path
from mathutils import kdtree
root=Path('/Users/stephenhung/Documents/GitHub/agarstra');out=root/'outputs/pokemon-remake/verification/trainer-direct';v1=root/'outputs/pokemon-remake/models/trainer-direct-v1.glb';v2=root/'outputs/pokemon-remake/models/trainer-direct-v2.glb'
def load(path,clip):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(path));rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers));action=next(a for a in bpy.data.actions if a.name==clip)
 for t in rig.animation_data.nla_tracks:t.mute=True
 rig.animation_data.action=action;return rig,mesh

def coords(mesh,frame):
 bpy.context.scene.frame_set(frame);bpy.context.view_layer.update();o=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());m=o.to_mesh();p=[o.matrix_world@v.co for v in m.vertices];o.to_mesh_clear();return p
idleFrames=[1,31,61,91,121];r,m=load(v1,'idle');source={f:coords(m,f)for f in idleFrames};r,m=load(v2,'idle');dest={f:coords(m,f)for f in idleFrames};tree=kdtree.KDTree(len(source[1]));
for i,p in enumerate(source[1]):tree.insert(p,i)
tree.balance();mapping=[tree.find(p)[1]for p in dest[1]];idleErrors={f:max((p-source[f][mapping[i]]).length for i,p in enumerate(dest[f]))for f in idleFrames};assert max(idleErrors.values())<.001,idleErrors
r,m=load(v2,'walk');feet={};
for side in ['Left','Right']:
 groups={m.vertex_groups[n].index for n in [side+'Foot',side+'ToeBase']};feet[side]=[v.index for v in m.data.vertices if sum(g.weight for g in v.groups if g.group in groups)>.55]
frames=[];initial=None;roots=[];ankles={side:[]for side in feet};allSoles={side:[]for side in feet};maxtravel=0
for frame in range(31):
 p=coords(m,frame)
 if initial is None:initial=p
 maxtravel=max(maxtravel,max((a-b).length for a,b in zip(p,initial)))
 rootpos=(r.matrix_world@r.pose.bones['Hips'].matrix).translation.copy();roots.append(rootpos)
 soles={side:min(p[i].z for i in ids)for side,ids in feet.items()};ankle={side:list((r.matrix_world@r.pose.bones[side+'Foot'].matrix).translation) for side in feet}
 for side in feet:allSoles[side].append(soles[side]);ankles[side].append(ankle[side])
 frames.append({'frame':frame,'seconds':frame/30,'soles':soles,'ankles':ankle,'root':list(rootpos),'minZ':min(v.z for v in p)})
loop=max((a-b).length for a,b in zip(p,initial));rootXZ=max(math.hypot(p.x-roots[0].x,p.y-roots[0].y)for p in roots);assert loop<.0001,loop;assert rootXZ<.0001,rootXZ;assert maxtravel>.1,maxtravel
contact={}
for side,offset in [('Left',0),('Right',.5)]:
 planted=[abs(frames[f]['soles'][side]) for f in range(31) if ((f/30+offset)%1)<.5];contact[side]={'minSole':min(allSoles[side]),'maxSole':max(allSoles[side]),'maxPlantedError':max(planted),'ankleYTravel':max(p[1]for p in ankles[side])-min(p[1]for p in ankles[side])};assert contact[side]['maxPlantedError']<.025,contact;assert contact[side]['maxSole']>.06,contact;assert contact[side]['ankleYTravel']>.25,contact
report={'passed':True,'candidateSHA256':hashlib.sha256(v2.read_bytes()).hexdigest(),'idlePreservationMaxErrorByFrame':idleErrors,'walkMaxVertexTravel':maxtravel,'walkLoopMaxVertexError':loop,'walkRootHorizontalTravel':rootXZ,'contact':contact,'frames':frames,'bones':len(r.data.bones),'vertices':len(m.data.vertices),'clips':[a.name for a in bpy.data.actions]};(out/'walk-verification.json').write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k!='frames'}))
