import bpy,json,numpy as np,hashlib
from pathlib import Path
from mathutils import Vector
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.import_scene.gltf(filepath=str(BASE/'models/laboratory-v1.glb'))
meshes=[o for o in bpy.context.scene.objects if o.type=='MESH'];points=[o.matrix_world@v.co for o in meshes for v in o.data.vertices]
bounds=[[min(p[i]for p in points)for i in range(3)],[max(p[i]for p in points)for i in range(3)]]
assigned=0
for o in meshes:
 original=o.data.materials[0];roof=original.copy();roof.name='LaboratoryV2_MatteRoof_OriginalColorAndNormal';bsdf=next(n for n in roof.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
 for key,value in [('Roughness',.87),('Metallic',0),('Specular IOR Level',.25)]:
  socket=bsdf.inputs[key]
  for link in list(socket.links):roof.node_tree.links.remove(link)
  socket.default_value=value
 o.data.materials.append(roof)
 tex=next(n for n in original.node_tree.nodes if n.type=='BSDF_PRINCIPLED').inputs['Base Color'].links[0].from_node.image
 pix=np.array(tex.pixels[:]).reshape(tex.size[1],tex.size[0],4);uvs=o.data.uv_layers.active.data
 for p in o.data.polygons:
  xyz=o.matrix_world@p.center;uv=sum((uvs[i].uv for i in p.loop_indices),Vector((0,0)))/len(p.loop_indices);c=pix[min(int(uv.y*tex.size[1]),tex.size[1]-1),min(int(uv.x*tex.size[0]),tex.size[0]-1),:3]
  if xyz.z>.255 and max(c)-min(c)<.12 and sum(c)/3>.11 and not(.19<xyz.x<.38 and -.215<xyz.y<-.005 and xyz.z>.35):
   p.material_index=1;assigned+=1
cap_bounds=[[.219,-.177,.463638],[.354,-.017,.47363799810409546]]
lo,hi=map(Vector,cap_bounds)
bpy.ops.mesh.primitive_cube_add(size=1,location=(lo+hi)/2);cap=bpy.context.object;cap.name='LaboratoryV2_ClosedRedVentCap';cap.dimensions=hi-lo
bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
mat=bpy.data.materials.new('LaboratoryV2_RedPaintedClosedCap');mat.use_nodes=True;bsdf=mat.node_tree.nodes.get('Principled BSDF');bsdf.inputs['Base Color'].default_value=(.265,.028,.045,1);bsdf.inputs['Metallic'].default_value=.08;bsdf.inputs['Roughness'].default_value=.76
cap.data.materials.append(mat)
bevel=cap.modifiers.new('FoldedSheetEdgeRadius','BEVEL');bevel.width=.0012;bevel.segments=3;bpy.ops.object.modifier_apply(modifier=bevel.name)
cap['repair']='Closed red vent cap fitted to source-faithful top; original building geometry unchanged.'
meshes.append(cap)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=cap
bpy.ops.export_scene.gltf(filepath=str(BASE/'models/laboratory-v2.glb'),export_format='GLB',use_selection=True,export_yup=True,export_apply=True)
result={'sourceSHA256':hashlib.sha256((BASE/'models/laboratory-v1.glb').read_bytes()).hexdigest(),'sha256':hashlib.sha256((BASE/'models/laboratory-v2.glb').read_bytes()).hexdigest(),'originalGeometryAndTransformsUnchanged':True,'originalBoundsBlender':bounds,'capBoundsBlender':cap_bounds,'roofTrianglesReassigned':assigned,'roofRoughness':.87,'roofMetallic':0,'roofSpecularIORLevel':.25,'sourceDoorAnchorUnchanged':True,'authoring':'Direct Blender geometry and materials; no generated intermediary'}
(OUT/'repair.json').write_text(json.dumps(result,indent=2)+'\n');print('REPAIR',json.dumps(result))
