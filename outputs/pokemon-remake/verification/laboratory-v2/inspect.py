import bpy,json,numpy as np
from pathlib import Path
base=Path('/Users/stephenhung/Documents/GitHub/agarstra/outputs/pokemon-remake')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(base/'models/laboratory-v1.glb'))
out={}
for o in [o for o in bpy.context.scene.objects if o.type=='MESH']:
 mat=o.data.materials[0];bsdf=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED');out['nodes']=[{'name':n.name,'type':n.type,'image':n.image.name if n.type=='TEX_IMAGE' else None} for n in mat.node_tree.nodes]
 tex=bsdf.inputs['Base Color'].links[0].from_node.image;pix=np.array(tex.pixels[:]).reshape(tex.size[1],tex.size[0],4);uvs=o.data.uv_layers.active.data
 samples=[]
 for p in o.data.polygons:
  xyz=o.matrix_world@p.center;uv=sum((uvs[i].uv for i in p.loop_indices),__import__('mathutils').Vector((0,0)))/len(p.loop_indices);c=pix[min(int(uv.y*tex.size[1]),tex.size[1]-1),min(int(uv.x*tex.size[0]),tex.size[0]-1),:3]
  if xyz.z>.25 and c[0]>c[1]*1.45 and c[0]>c[2]*1.4:samples.append([*xyz,*c,p.index])
 out['redSamples']=samples;out['redBounds']=[[min(s[i] for s in samples) for i in range(3)],[max(s[i] for s in samples) for i in range(3)]]
 out['object']={'name':o.name,'matrix':[list(r) for r in o.matrix_world]}
(base/'verification/laboratory-v2/inspection.json').write_text(json.dumps(out,indent=2))
print('INSPECTION',out['redBounds'],out['nodes'])
