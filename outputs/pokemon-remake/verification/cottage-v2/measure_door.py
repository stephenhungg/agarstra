"""Measure the generated brown door against the blue/white facade.

This is a texture-and-geometry-derived candidate anchor, requiring visual review.
No geometry or material changes. Reads the packed cottage-v2.blend scene.
"""
import bpy
import array
import hashlib
import json
from pathlib import Path
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

BASE = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
BLEND = BASE / 'models/cottage-v2.blend'
GLB = BASE / 'models/cottage-v2.glb'
bpy.ops.wm.open_mainfile(filepath=str(BLEND))
collection = bpy.data.collections['Cottage V2 Imported Candidate']
objects = [o for o in collection.objects if o.type == 'MESH']
points = [o.matrix_world @ v.co for o in objects for v in o.data.vertices]
minimum = Vector(tuple(min(p[a] for p in points) for a in range(3)))
maximum = Vector(tuple(max(p[a] for p in points) for a in range(3)))
dimensions = maximum - minimum
selected = []
images = {}

for obj in objects:
    mesh = obj.data
    mesh.calc_loop_triangles()
    uv = mesh.uv_layers.active.data
    material = obj.data.materials[0]
    image = next(n.image for n in material.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image and n.image.colorspace_settings.name == 'sRGB')
    if image.name not in images:
        pixels = array.array('f', [0]) * (image.size[0] * image.size[1] * 4)
        image.pixels.foreach_get(pixels)
        images[image.name] = (image.size[0],image.size[1],pixels)
    width,height,pixels = images[image.name]
    for tri in mesh.loop_triangles:
        coordinates = [obj.matrix_world @ mesh.vertices[index].co for index in tri.vertices]
        center = sum(coordinates, Vector()) / 3
        normal = (coordinates[1]-coordinates[0]).cross(coordinates[2]-coordinates[0]).normalized()
        if not (minimum.z+dimensions.z*.015 < center.z < minimum.z+dimensions.z*.58):
            continue
        # Expected front comes from inspecting the provider convention and reference.
        # A missing cluster is a failed measurement, not permission to invent an anchor.
        if center.y > minimum.y+dimensions.y*.28 or normal.y > -.65:
            continue
        texcoord = sum((uv[index].uv for index in tri.loops), Vector((0,0))) / 3
        x = min(width-1,max(0,int(texcoord.x*width)))
        y = min(height-1,max(0,int(texcoord.y*height)))
        index = (y*width+x)*4
        red,green,blue = pixels[index:index+3]
        if red > .12 and red > green*1.24 and red > blue*1.40 and .03 < green < .58:
            selected.append({'center':list(center),'rgb':[red,green,blue],'vertices':[list(p)for p in coordinates],'triangle':tri.index,'object':obj.name})

if len(selected) < 8:
    raise RuntimeError(f'Insufficient brown facade triangles for a reliable candidate door: {len(selected)}')

def quantile(values, fraction):
    values=sorted(values)
    return values[round((len(values)-1)*fraction)]

centers=[Vector(p['center'])for p in selected]
door_min = Vector(tuple(quantile([p[a]for p in centers],.02)for a in range(3)))
door_max = Vector(tuple(quantile([p[a]for p in centers],.98)for a in range(3)))
center_x=(door_min.x+door_max.x)*.5
facade_y=quantile([p.y for p in centers],.5)
threshold=Vector((center_x,facade_y,door_min.z))
ground=Vector((center_x,facade_y,minimum.z))
to_gltf=lambda p:[p.x,p.z,-p.y]
report={
    'asset':'cottage-v2','status':'candidate-anchor-needs-visual-confirmation',
    'assetSHA256':hashlib.sha256(GLB.read_bytes()).hexdigest(),
    'coordinateFrame':'glTF scene/root coordinates after node transforms, before runtime scale/centering. Not raw mesh accessor coordinates.',
    'frontDirectionGLTF':[0,0,1], 'upDirectionGLTF':[0,1,0],
    'frontDirectionBlender':[0,-1,0], 'upDirectionBlender':[0,0,1],
    'thresholdAnchorGLTF':to_gltf(threshold),'groundEntryAnchorGLTF':to_gltf(ground),
    'thresholdAnchorBlender':list(threshold),'groundEntryAnchorBlender':list(ground),
    'doorColorClusterBoundsBlender':{'min':list(door_min),'max':list(door_max)},
    'doorWidthEstimate':door_max.x-door_min.x,'doorHeightEstimate':door_max.z-door_min.z,
    'doorAcrossWholeAssetFraction':(center_x-minimum.x)/dimensions.x,
    'method':'Brown base-color triangle-centroid samples on lower front facade, robust 2nd/98th percentile bounds. Window reflections and roof excluded by color, height, normal, and depth. Anchor uses facade median depth and lower detected door height.',
    'selectedTriangles':len(selected),'limitations':['Texture-based selection approximates the visible wooden leaf; trim and threshold may extend farther.','Anchor is not collision geometry and does not establish metric physical scale.','Verify the reported front direction and left-of-center location against actual rendered views before integration.'],
    'assetBoundsBlender':{'min':list(minimum),'max':list(maximum)},
}
bottom_center=Vector(((minimum.x+maximum.x)*.5,(minimum.y+maximum.y)*.5,minimum.z))
report['runtimeBottomCenterToSubtractGLTF']=to_gltf(bottom_center)
report['bottomCenteredGroundEntryAnchorGLTF']=to_gltf(ground-bottom_center)
report['bottomCenteredThresholdAnchorGLTF']=to_gltf(threshold-bottom_center)
report['projectedAnchorPixels']={}
for name in ['Front','Back','Gameplay']:
    camera=bpy.data.objects[f'Review {name}']
    projected={}
    for label,point in [('threshold',threshold),('groundEntry',ground)]:
        screen=world_to_camera_view(bpy.context.scene,camera,point)
        projected[label]=[screen.x*bpy.context.scene.render.resolution_x,(1-screen.y)*bpy.context.scene.render.resolution_y]
    report['projectedAnchorPixels'][name.lower()]=projected
(OUT/'door-anchor.json').write_text(json.dumps(report,indent=2)+'\n')
(OUT/'door-samples.json').write_text(json.dumps(selected,indent=2)+'\n')
print('DOOR_ANCHOR',json.dumps(report))
