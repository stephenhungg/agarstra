import bpy,json
from pathlib import Path
from mathutils import Vector
root=Path('/Users/stephenhung/Documents/GitHub/agarstra');out=root/'outputs/pokemon-remake/verification/charmander-v2'
bpy.ops.wm.open_mainfile(filepath=str(root/'outputs/pokemon-remake/models/charmander-existing-v1.blend'))
bpy.context.scene.frame_set(1)
rig=next(o for o in bpy.context.scene.objects if o.type=='ARMATURE');mesh=next(o for o in bpy.context.scene.objects if o.type=='MESH')
names=['LArmCollarbone','LArm1','LArm2','LArmPalm','RArmCollarbone','RArm1','RArm2','RArmPalm','Pelvis','Spine1','Spine2','Chest','Neck','Head','Tail1','Tail2','Tail3','Tail4','Tail5','LLegAnkle','RLegAnkle']
r=[]
for n in names:
 p=rig.pose.bones['Charmander_'+n];w=rig.matrix_world@p.matrix;r.append({'name':p.name,'parent':p.parent.name if p.parent else None,'head':list(rig.matrix_world@p.head),'tail':list(rig.matrix_world@p.tail),'worldAxes':[list(w.to_3x3().col[i].normalized()) for i in range(3)],'basis':list(map(list,p.matrix_basis))})
coords=[mesh.matrix_world@v.co for v in mesh.data.vertices]
adj=[set() for _ in coords]
for edge in mesh.data.edges:
 a,b=edge.vertices;adj[a].add(b);adj[b].add(a)
components=[];pending=set(range(len(coords)))
while pending:
 component=set();queue=[pending.pop()]
 while queue:
  i=queue.pop();component.add(i)
  for j in adj[i]:
   if j in pending:pending.remove(j);queue.append(j)
 components.append({'vertices':len(component),'indices':sorted(component),'min':[min(coords[i][a] for i in component) for a in range(3)],'max':[max(coords[i][a] for i in component) for a in range(3)]})
report={'bones':r,'connectedComponents':components}
(out/'rig-inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps({'bones':[{k:v for k,v in x.items() if k!='basis'} for x in r],'components':[{k:v for k,v in x.items() if k!='indices'} for x in components]},indent=2))
