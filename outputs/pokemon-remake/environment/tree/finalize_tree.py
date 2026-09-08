import bpy,json,hashlib
from pathlib import Path
from mathutils import Vector
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/environment/tree'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'tree.blend'))
leaves=bpy.data.objects['Pallet_Broadleaf_Foliage']
mesh=leaves.data
colors=[tuple(m.diffuse_color) for m in mesh.materials]
attr=mesh.color_attributes.new(name='FoliageTint',type='FLOAT_COLOR',domain='CORNER')
for p in mesh.polygons:
    for idx in p.loop_indices: attr.data[idx].color=colors[p.material_index]
mesh.color_attributes.active_color=attr
mat=bpy.data.materials.new('Foliage_vertex_color_PBR')
mat.use_nodes=True
mat.use_backface_culling=False
shader=mat.node_tree.nodes.get('Principled BSDF')
shader.inputs['Roughness'].default_value=.72
node=mat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='FoliageTint'
mat.node_tree.links.new(node.outputs['Color'],shader.inputs['Base Color'])
mesh.materials.clear();mesh.materials.append(mat)
for p in mesh.polygons:p.material_index=0
bpy.ops.object.select_all(action='DESELECT')
for name in ['Pallet_Broadleaf_Tree','Pallet_Broadleaf_Foliage']:bpy.data.objects[name].select_set(True)
bpy.context.view_layer.objects.active=leaves
assets=[bpy.data.objects[n] for n in ['Pallet_Broadleaf_Tree','Pallet_Broadleaf_Foliage']]
pts=[v.co.copy() for o in assets for v in o.data.vertices]
mn=Vector(tuple(min(p[i] for p in pts) for i in range(3)))
mx=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
offset=Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z))
scale=5/(mx.z-mn.z)
for o in assets:
    for v in o.data.vertices:v.co=(v.co-offset)*scale
pts=[v.co.copy() for o in assets for v in o.data.vertices]
bounds_min=[min(p[i] for p in pts) for i in range(3)]
bounds_max=[max(p[i] for p in pts) for i in range(3)]
bpy.ops.export_scene.gltf(filepath=str(OUT/'tree.glb'),export_format='GLB',use_selection=True,export_animations=False)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree.blend'))
# Reimport exported artifact to render evidence of the actual GLB/materials.
for name in ['Pallet_Broadleaf_Tree','Pallet_Broadleaf_Foliage']:
    bpy.data.objects.remove(bpy.data.objects[name],do_unlink=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/'tree.glb'))
scene=bpy.context.scene;cam=scene.camera
for name,position,target in [('front',(8,-11,7),(0,0,2.5)),('back',(-8,11,7),(0,0,2.5)),('gameplay',(8,-11,13),(0,0,2.3))]:
    cam.location=position
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'tree-review-{name}.png')
    bpy.ops.render.render(write_still=True)
stats=json.loads((OUT/'mesh-inspection.json').read_text())
stats['export_material_count']=2
stats['bbox_min_xyz_blender']=bounds_min
stats['bbox_max_xyz_blender']=bounds_max
stats['dimensions_m']=[bounds_max[i]-bounds_min[i] for i in range(3)]
stats['foliage_material']='Vertex-colored PBR leaf geometry, double sided, roughness 0.72; no alpha textures or transparency sorting'
stats['export_verification']='GLB reimported into Blender and rendered in three views'
(OUT/'mesh-inspection.json').write_text(json.dumps(stats,indent=2))
