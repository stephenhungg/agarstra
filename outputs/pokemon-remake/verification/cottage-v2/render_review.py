"""Import the existing candidate without remeshing, then save and render review views.

Run with Blender --background --threads 4 --python this-file.py.
The GLB is never overwritten; the editable scene preserves its imported transforms.
"""
import bpy
import bmesh
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from mathutils import Vector

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
GLB = BASE / "models/cottage-v2.glb"
BLEND = BASE / "models/cottage-v2.blend"
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.preferences.filepaths.save_version = 0
bpy.ops.import_scene.gltf(filepath=str(GLB))
meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in meshes for v in o.data.vertices]
minimum = Vector(tuple(min(p[a] for p in points) for a in range(3)))
maximum = Vector(tuple(max(p[a] for p in points) for a in range(3)))
center = (minimum + maximum) * .5
dimensions = maximum - minimum
span = max(dimensions)
source_objects = [{"name": o.name, "location": list(o.location), "rotationQuaternion": list(o.rotation_quaternion), "scale": list(o.scale), "matrixWorld": [list(row) for row in o.matrix_world], "vertices": len(o.data.vertices), "triangles": sum(len(p.vertices)-2 for p in o.data.polygons)} for o in meshes]

asset_collection = bpy.data.collections.new("Cottage V2 Imported Candidate")
bpy.context.scene.collection.children.link(asset_collection)
for o in meshes:
    for collection in list(o.users_collection):
        collection.objects.unlink(o)
    asset_collection.objects.link(o)
root = bpy.data.objects.new("CottageV2_SourceOrigin", None)
asset_collection.objects.link(root)
root.empty_display_type = 'PLAIN_AXES'
root.empty_display_size = span * .15
root["source_glb"] = str(GLB.relative_to(BASE))
root["source_sha256"] = hashlib.sha256(GLB.read_bytes()).hexdigest()
root["quality_status"] = "Candidate; visual review required"
for o in meshes:
    matrix = o.matrix_world.copy()
    o.parent = root
    o.matrix_world = matrix

topology = []
for o in meshes:
    bm = bmesh.new()
    bm.from_mesh(o.data)
    original_vertices = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=span*1e-6)
    topology.append({"object": o.name, "rawVertices": original_vertices, "weldedVerticesForDiagnosticOnly": len(bm.verts), "weldTolerance": span*1e-6, "boundaryEdgesAfterDiagnosticWeld": sum(e.is_boundary for e in bm.edges), "nonmanifoldEdgesAfterDiagnosticWeld": sum(not e.is_manifold for e in bm.edges), "degenerateFaces": sum(f.calc_area() < 1e-14 for f in bm.faces)})
    bm.free()

scene = bpy.context.scene
scene.render.engine = 'CYCLES'
scene.cycles.samples = 48
scene.cycles.use_denoising = True
scene.cycles.max_bounces = 6
scene.render.resolution_x = 1280
scene.render.resolution_y = 1280
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
scene.view_settings.view_transform = 'AgX'
scene.view_settings.look = 'AgX - Medium High Contrast'
scene.render.threads_mode = 'FIXED'
scene.render.threads = 4
scene.world = bpy.data.worlds.new("Review Neutral Daylight")
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs['Color'].default_value = (.78, .83, .9, 1)
scene.world.node_tree.nodes['Background'].inputs['Strength'].default_value = .32

stage = bpy.data.collections.new("Review Stage - Not Part of Asset")
scene.collection.children.link(stage)

def move_to_stage(o):
    for collection in list(o.users_collection):
        collection.objects.unlink(o)
    stage.objects.link(o)
    return o

bpy.ops.mesh.primitive_plane_add(size=span*200, location=(center.x, center.y, minimum.z-span*.002))
floor = move_to_stage(bpy.context.object)
floor.name = "Review Ground"
material = bpy.data.materials.new("Review Ground Neutral")
material.use_nodes = True
material.node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value = (.55,.57,.56,1)
material.node_tree.nodes.get('Principled BSDF').inputs['Roughness'].default_value = .85
floor.data.materials.append(material)

def area(name, direction, energy, size):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy = energy * span * span
    data.shape = 'DISK'
    data.size = size * span
    o = bpy.data.objects.new(name, data)
    stage.objects.link(o)
    o.location = center + Vector(direction) * span
    o.rotation_euler = (center - o.location).to_track_quat('-Z','Y').to_euler()

area("Review Key", (-3,-4,5), 550, 4)
area("Review Fill", (4,-1,2), 180, 3)
area("Review Back Fill", (1,4,3), 280, 3)

views = []
for name, direction in [('front',(3,-5,3.1)),('back',(-3,5,2.7)),('gameplay',(3,-4,6))]:
    data = bpy.data.cameras.new(f"Review {name.title()}")
    camera = bpy.data.objects.new(data.name, data)
    stage.objects.link(camera)
    camera.location = center + Vector(direction).normalized() * span * 6
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z','Y').to_euler()
    data.type = 'ORTHO'
    inverse = camera.rotation_euler.to_matrix().transposed()
    camera_points = [inverse @ (p-center) for p in points]
    width = max(p.x for p in camera_points)-min(p.x for p in camera_points)
    height = max(p.y for p in camera_points)-min(p.y for p in camera_points)
    data.ortho_scale = max(width,height) * 1.20
    data.clip_start = .001
    data.clip_end = span*300
    views.append({"name": name, "camera": camera.name, "location": list(camera.location), "lookAt": list(center), "orthographicScale": data.ortho_scale, "resolution": [1280,1280], "path": f"{name}.png"})

scene.camera = bpy.data.objects[views[0]['camera']]
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))

report = {"generatedAt": datetime.now(timezone.utc).isoformat(), "asset": "cottage-v2", "status": "candidate", "sourceGLB": str(GLB.relative_to(BASE)), "sourceSHA256": root['source_sha256'], "editableBlend": str(BLEND.relative_to(BASE)), "geometryUnchanged": True, "materialNodesUnchanged": True, "sourceObjects": source_objects, "boundsBlenderZUp": {"min": list(minimum), "max": list(maximum), "dimensions": list(dimensions)}, "originBlender": [0,0,0], "bottomCenter": [center.x,center.y,minimum.z], "originHorizontalOffsetFromBottomCenter": math.hypot(center.x,center.y), "physicalScale": "Unverified normalized source units, not established meters", "candidateUniformScaleForSixMeterHeight": 6/dimensions.z, "topology": topology, "textures": [{"name": i.name, "size": list(i.size), "colorSpace": i.colorspace_settings.name, "packed": bool(i.packed_file)} for i in bpy.data.images if i.type=='IMAGE'], "views": views, "lighting": {"engine": 'Cycles', "samples": 48, "worldStrength": .32, "viewTransform": 'AgX', "look": scene.view_settings.look}, "visualReview": "Pending actual rendered image inspection"}
(OUT/'mesh-inspection.json').write_text(json.dumps(report,indent=2)+'\n')
for view in views:
    scene.camera = bpy.data.objects[view['camera']]
    scene.render.filepath = str(OUT/view['path'])
    bpy.ops.render.render(write_still=True)
scene.camera = bpy.data.objects[views[0]['camera']]
bpy.ops.wm.save_as_mainfile(filepath=str(BLEND))
print("COTTAGE_REVIEW_COMPLETE", json.dumps({"blend":str(BLEND),"renders":[v['path']for v in views]}))
