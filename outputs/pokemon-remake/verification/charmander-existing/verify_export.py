"""Reimport the shipped GLB and compare its sampled skin to the creator rig."""
import bpy, json, math, hashlib
from pathlib import Path
from mathutils import Vector, kdtree

ROOT = Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT = ROOT / 'outputs/pokemon-remake/verification/charmander-existing'
GLB = ROOT / 'outputs/pokemon-remake/models/charmander-existing-v1.glb'
FRAMES = [1, 26, 51, 76, 101, 126, 151, 176, 201]

def coords(obj):
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    values = [evaluated.matrix_world @ v.co for v in mesh.vertices]
    evaluated.to_mesh_clear()
    return values

def sample(obj, rig):
    positions, bones = {}, {}
    for frame in FRAMES:
        bpy.context.scene.frame_set(frame)
        positions[frame] = coords(obj)
        bones[frame] = {p.name: rig.matrix_world @ p.matrix for p in rig.pose.bones}
    return positions, bones

bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'outputs/pokemon-remake/models/charmander-existing-v1.blend'))
source = next(o for o in bpy.data.objects if o.type == 'MESH')
source_rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
source_positions, source_bones = sample(source, source_rig)
source_weights = []
for vertex in source.data.vertices:
    weights = sorted((g.weight for g in vertex.groups if g.weight > 1e-7), reverse=True)
    source_weights.append({'count': len(weights), 'discardedWeight': sum(weights[4:])})

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.fps = 30
bpy.ops.import_scene.gltf(filepath=str(GLB))
scene = bpy.context.scene
mesh = next(o for o in bpy.data.objects if o.type == 'MESH')
rig = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
positions, bones = sample(mesh, rig)
tree = kdtree.KDTree(len(source_positions[1]))
for i, co in enumerate(source_positions[1]): tree.insert(co, i)
tree.balance()
mapping = [tree.find(co) for co in positions[1]]
frame_results = []
for frame in FRAMES:
    differences = [(co - source_positions[frame][mapping[i][1]]).length for i, co in enumerate(positions[frame])]
    motion = [(co - positions[1][i]).length for i, co in enumerate(positions[frame])]
    joint_changes = []
    for name, matrix in bones[frame].items():
        initial = bones[1][name]
        angle = initial.to_quaternion().rotation_difference(matrix.to_quaternion()).angle
        angle = min(angle, 2 * math.pi - angle)
        travel = (matrix.translation - initial.translation).length
        if angle > .001 or travel > .0001:
            joint_changes.append({'bone':name, 'degrees':math.degrees(angle), 'travel':travel})
    frame_results.append({'frame':frame, 'seconds':frame/30, 'maxExportSkinError':max(differences), 'meanExportSkinError':sum(differences)/len(differences), 'maxVertexTravel':max(motion), 'meanVertexTravel':sum(motion)/len(motion), 'changedJoints':sorted(joint_changes,key=lambda q:q['travel'], reverse=True)})

report = {
 'glbSHA256':hashlib.sha256(GLB.read_bytes()).hexdigest(),
 'actualImportedActions':[{'name':a.name,'frameRange':list(a.frame_range)} for a in bpy.data.actions],
 'fps':30, 'sourceVertexCount':len(source_positions[1]), 'exportVertexCount':len(positions[1]),
 'sourceVerticesOverFourWeights':sum(w['count']>4 for w in source_weights),
 'maxDiscardedWeight':max(w['discardedWeight'] for w in source_weights),
 'maxFrame1NearestSourceDistance':max(m[2] for m in mapping),
 'comparisonMethod':'Match exported vertices to nearest source world-space vertex at frame 1, then compare that fixed correspondence at all samples. UV seams may duplicate exported vertices.',
 'frames':frame_results,
 'importedRootTransform':{'meshMatrix':list(map(list,mesh.matrix_world)), 'rigMatrix':list(map(list,rig.matrix_world))},
 'boundsBlenderZUp':{'min':[min(co[i] for co in positions[1]) for i in range(3)],'max':[max(co[i] for co in positions[1]) for i in range(3)]}
}
(OUT/'skin-verification.json').write_text(json.dumps(report,indent=2))

# Same camera and stage across all samples; the camera bounds include every pose.
all_co = [co for values in positions.values() for co in values]
lo = Vector([min(c[i] for c in all_co) for i in range(3)])
hi = Vector([max(c[i] for c in all_co) for i in range(3)])
center = (lo+hi)/2
span = max(hi-lo)
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = scene.render.resolution_y = 1000
scene.render.resolution_percentage = 100
scene.world = bpy.data.worlds.new('Neutral Review World')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.7,.76,.8,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .35
bpy.ops.mesh.primitive_plane_add(size=span*200, location=(0,0,lo.z-.003))
floor = bpy.context.object
floor.name = 'REVIEW_Floor'
mat = bpy.data.materials.new('REVIEW_Neutral floor')
mat.diffuse_color=(.2,.23,.24,1)
floor.data.materials.append(mat)
for name, offset, energy in [('Key',(1.5,-2,2.5),180),('Fill',(-1,1,1.5),80)]:
    data=bpy.data.lights.new('REVIEW_'+name,'AREA')
    data.energy=energy
    data.shape='DISK';data.size=2
    obj=bpy.data.objects.new('REVIEW_'+name,data);scene.collection.objects.link(obj)
    obj.location=Vector(offset)
    obj.rotation_euler=(center-obj.location).to_track_quat('-Z','Y').to_euler()
data=bpy.data.cameras.new('REVIEW_Camera')
camera=bpy.data.objects.new('REVIEW_Camera',data);scene.collection.objects.link(camera)
data.type='ORTHO';data.ortho_scale=span*1.45
scene.camera=camera
scene.view_settings.view_transform='AgX'
for frame, suffix, direction in [(1,'front',(2,-3,1.6)),(51,'front',(2,-3,1.6)),(151,'front',(2,-3,1.6)),(1,'back',(-2,3,1.6))]:
    scene.frame_set(frame)
    camera.location=center+Vector(direction)*span
    camera.rotation_euler=(center-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'glb-frame-{frame}-{suffix}.png')
    bpy.ops.render.render(write_still=True)
scene.frame_set(1)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'reimport-review.blend'))
print('VERIFICATION_DONE',json.dumps({k:v for k,v in report.items() if k not in ['frames','importedRootTransform']}))
