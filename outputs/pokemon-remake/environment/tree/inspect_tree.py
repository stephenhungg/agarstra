import bpy, json, math
from pathlib import Path
from mathutils import Vector, Matrix

ROOT = Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT = ROOT / 'outputs/pokemon-remake/environment/tree'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(OUT/'tree-hunyuan-source.glb'))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
mn = Vector(tuple(min(p[i] for p in points) for i in range(3)))
mx = Vector(tuple(max(p[i] for p in points) for i in range(3)))
factor = 5.0/(mx.z-mn.z)
origin = Vector(((mn.x+mx.x)/2,(mn.y+mx.y)/2,mn.z))
normalization = Matrix.Scale(factor,4) @ Matrix.Translation(-origin)
for o in meshes:
    world = o.matrix_world.copy()
    o.parent = None
    o.matrix_world = normalization @ world
bpy.context.view_layer.update()
bpy.ops.object.select_all(action='DESELECT')
for o in meshes: o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
for i,o in enumerate(meshes): o.name = 'Pallet_Broadleaf_Tree' if i == 0 else f'Pallet_Broadleaf_Tree_{i}'
points = [o.matrix_world @ Vector(p) for o in meshes for p in o.bound_box]
new_min = [min(p[i] for p in points) for i in range(3)]
new_max = [max(p[i] for p in points) for i in range(3)]
materials=[]
for mat in bpy.data.materials:
    images=[]
    if mat.use_nodes:
        images=[{'name':n.image.name,'size':list(n.image.size)} for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image]
    materials.append({'name':mat.name,'textures':images})
stats={'height_m':5.0,'bbox_min_xyz_blender':new_min,'bbox_max_xyz_blender':new_max,
       'dimensions_m':[new_max[i]-new_min[i] for i in range(3)],
       'meshes':len(meshes),'vertices':sum(len(o.data.vertices) for o in meshes),
       'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in meshes),
       'normalization_scale':factor,'materials':materials,
       'origin':'bottom center','gltf_up_axis':'Y','blender_up_axis':'Z',
       'animation':'none; static tree','source':'Higgsfield Hunyuan3D v3 single-view reconstruction'}
(OUT/'mesh-inspection.json').write_text(json.dumps(stats,indent=2))
bpy.ops.export_scene.gltf(filepath=str(OUT/'tree.glb'),export_format='GLB',use_selection=True,export_animations=False)

# Inspection lighting and floor are excluded from the runtime export.
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.resolution_x=1024
scene.render.resolution_y=1024
scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral daylight')
scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(0.65,0.72,0.8,1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value=0.45
bpy.ops.object.light_add(type='AREA',location=(-4,-6,9))
bpy.context.object.data.energy=1800
bpy.context.object.data.shape='DISK'
bpy.context.object.data.size=6
bpy.context.object.rotation_euler=(Vector((0,0,2))-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.light_add(type='AREA',location=(4,3,7))
bpy.context.object.data.energy=900
bpy.context.object.data.size=5
bpy.context.object.rotation_euler=(Vector((0,0,2))-bpy.context.object.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-0.012))
floor=bpy.context.object
floor.name='Inspection_floor_excluded_from_GLB'
mat=bpy.data.materials.new('Neutral matte ground')
mat.diffuse_color=(0.31,0.34,0.29,1)
floor.data.materials.append(mat)
bpy.ops.object.camera_add()
cam=bpy.context.object
scene.camera=cam
cam.data.type='ORTHO'
cam.data.ortho_scale=7.2
for name,position,target in [('front',(8,-11,7),(0,0,2.5)),('back',(-8,11,7),(0,0,2.5)),('gameplay',(8,-11,13),(0,0,2.3))]:
    cam.location=position
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'tree-review-{name}.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree.blend'))
