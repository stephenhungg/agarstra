"""Author an Oak-lab battle presentation in Blender; original gameplay is external."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector
import numpy as np


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument('--root', required=True)
    parser.add_argument('--reference', required=True)
    return parser.parse_args(sys.argv[sys.argv.index('--') + 1:])


def point(x, y, z):
    # Author in runtime coordinates: runtime +Y up / +Z toward the viewer.
    return (x, -z, y)


def material(name, color, roughness=.65, metallic=0):
    result = bpy.data.materials.new(name)
    result.use_nodes = True
    bsdf = result.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    bsdf.inputs['Metallic'].default_value = metallic
    return result


def texture_material(name, color, kind, directory, roughness=.65):
    size = 512
    y, x = np.mgrid[0:size, 0:size].astype(np.float32)
    rng = np.random.default_rng(1845 + len(name))
    grain = rng.normal(0, .012, (size, size))
    broad = np.sin(x * .073 + np.sin(y * .018) * 2) * np.cos(y * .059) * .013
    values = grain + broad
    if kind == 'wood':
        values += np.sin(y * .52 + np.sin(x * .009) * 5) * .025
        values += np.sin(y * 1.27 + np.sin(x * .014) * 4) * .011
    elif kind == 'brushed':
        values = grain * .25 + rng.normal(0, .022, (size, 1))
    elif kind == 'tile':
        values += np.sin(x * .037 + y * .019) * .016
    image = bpy.data.images.new(name + ' color texture', width=size, height=size)
    pixels = np.ones((size, size, 4), dtype=np.float32)
    pixels[:, :, :3] = np.clip(np.asarray(color)[None, None, :] + values[:, :, None], .015, 1)
    image.pixels.foreach_set(pixels.ravel())
    image.filepath_raw = str(directory / (name.replace(' ', '-').lower() + '.png'))
    image.file_format = 'PNG'
    image.save()
    image.pack()
    mat = material(name, color, roughness)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    tex = nodes.new('ShaderNodeTexImage')
    tex.image = image
    links.new(tex.outputs['Color'], nodes.get('Principled BSDF').inputs['Base Color'])
    rough = bpy.data.images.new(name + ' roughness texture', width=size, height=size)
    rough.colorspace_settings.name = 'Non-Color'
    rough_pixels = np.ones((size, size, 4), dtype=np.float32)
    rough_pixels[:, :, :3] = np.clip(roughness + values[:, :, None] * 2, .1, 1)
    rough.pixels.foreach_set(rough_pixels.ravel())
    rough.filepath_raw = str(directory / (name.replace(' ', '-').lower() + '-roughness.png'))
    rough.file_format = 'PNG'
    rough.save()
    rough.pack()
    tex_rough = nodes.new('ShaderNodeTexImage')
    tex_rough.image = rough
    links.new(tex_rough.outputs['Color'], nodes.get('Principled BSDF').inputs['Roughness'])
    return mat


def ring(name, center, radius, thickness, mat):
    bpy.ops.mesh.primitive_torus_add(major_segments=96, minor_segments=6, location=point(*center), major_radius=radius, minor_radius=thickness)
    obj = bpy.context.object
    obj.name = name
    obj.scale.z = .2
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def box(name, center, size, mat, bevel=0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=point(*center))
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = (size[0], size[2], size[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if bevel:
        modifier = obj.modifiers.new('Soft manufactured edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 2
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)
    obj.data.materials.append(mat)
    return obj


def cylinder(name, center, radius, depth, mat, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=point(*center))
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = len(poly.vertices) == 4
    return obj


def sphere(name, center, scale, mat):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=8, location=point(*center))
    obj = bpy.context.object
    obj.name = name
    obj.scale = (scale[0], scale[2], scale[1])
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def camera(name, position, target, scale, resolution=(1440, 900)):
    data = bpy.data.cameras.new(name)
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = point(*position)
    obj.rotation_euler = (Vector(point(*target)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    data.type = 'ORTHO'
    data.sensor_fit = 'HORIZONTAL'
    data.ortho_scale = scale
    data.clip_end = 300
    bpy.context.scene.camera = obj
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = resolution
    return obj


def runtime_camera(resolution=(1440, 900)):
    aspect = resolution[0] / resolution[1]
    half_height = max(7.5, 12 / aspect)
    target = Vector((0, 1.8, 0))
    backward = Vector((0, 6.2, 18)).normalized()
    distance = max(Vector((0, 6.2, 18)).length, 4 + half_height * 3.2)
    position = target + backward * distance
    return camera('Original battle framing', position, target, half_height * aspect * 2, resolution)


def export_artifacts(root, reference, manifest):
    models = root / 'models'
    models.mkdir(parents=True, exist_ok=True)
    evidence = root / 'verification' / 'battle-arena'
    evidence.mkdir(parents=True, exist_ok=True)
    blend = models / 'battle-arena-v1.blend'
    glb = models / 'battle-arena-v1.glb'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    merge_runtime_meshes()
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', export_yup=True,
                             export_lights=False, export_cameras=False, export_animations=False,
                             export_apply=True)
    manifest.update({'reference': str(reference), 'referenceSha256': hash_file(reference),
                     'blend': str(blend), 'glb': str(glb), 'sha256': hash_file(glb),
                     'scale': 1, 'position': [0, 0, 0], 'up': '+Y', 'front': '+Z',
                     'origin': 'existing battle presentation world origin',
                     'stageSurfaceY': -.05, 'sourceSimulationChanged': False,
                     'artisticStatus': 'candidate, awaiting actual runtime review'})
    (evidence / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    return glb, evidence


def merge_runtime_meshes():
    # Keep the saved Blender authoring objects editable, batch the runtime copy.
    by_material = {}
    for obj in list(bpy.context.scene.objects):
        if obj.type == 'MESH':
            by_material.setdefault(tuple(mat.name for mat in obj.data.materials), []).append(obj)
    bpy.ops.object.select_all(action='DESELECT')
    for names, objects in by_material.items():
        if len(objects) < 2:
            continue
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = objects[0]
        bpy.ops.object.join()
        objects[0].name = 'Arena batch ' + (names[0] if names else 'default')
        objects[0].select_set(False)


def render_evidence(evidence):
    scene = bpy.context.scene
    for name, viewport in [('gameplay', (1440, 900)), ('wide', (1920, 810)), ('portrait', (720, 1200))]:
        runtime_camera(viewport)
        scene.render.filepath = str(evidence / (name + '.png'))
        bpy.ops.render.render(write_still=True)


def area(name, position, target, energy, size, color):
    data = bpy.data.lights.new(name, 'AREA')
    data.energy, data.shape, data.size, data.color = energy, 'DISK', size, color
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.location = point(*position)
    obj.rotation_euler = (Vector(point(*target)) - obj.location).to_track_quat('-Z', 'Y').to_euler()
    return obj


def hash_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def setup():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.world.color = (.18, .21, .24)
    scene.view_settings.view_transform = 'AgX'
    scene.view_settings.look = 'AgX - Medium High Contrast'


def build_arena(root):
    textures = root / 'environment' / 'battle-arena' / 'textures'
    textures.mkdir(parents=True, exist_ok=True)
    ivory = texture_material('Warm limestone', (.64, .59, .47), 'tile', textures, .39)
    sage = texture_material('Sage stone inlay', (.30, .33, .26), 'tile', textures, .49)
    plaster = texture_material('Limewashed plaster', (.67, .64, .55), 'tile', textures, .86)
    oak = texture_material('Aged oak cabinet', (.235, .135, .065), 'wood', textures, .53)
    walnut = texture_material('Dark oak rails', (.125, .074, .035), 'wood', textures, .57)
    counter = texture_material('Oiled wood worktop', (.285, .185, .095), 'wood', textures, .40)
    metal = texture_material('Brushed nickel', (.28, .29, .27), 'brushed', textures, .33)
    metal.node_tree.nodes.get('Principled BSDF').inputs['Metallic'].default_value = .8
    grout = material('Warm grey grout', (.31, .30, .26), .95)
    black = material('Soft black instrument casing', (.026, .033, .032), .43)
    ceramic = material('Ivory instrument enamel', (.62, .61, .51), .37)
    screen = material('Smoked CRT glass', (.018, .053, .043), .2)
    leaf = texture_material('Specimen leaf', (.105, .22, .058), 'tile', textures, .62)
    soil = material('Potting soil', (.045, .034, .022), .98)
    terracotta = material('Weathered terracotta', (.29, .15, .074), .87)
    paper = material('Aged book pages', (.54, .51, .39), .88)
    glass = material('Laboratory bottle glass', (.37, .50, .43), .16)
    glass.node_tree.nodes.get('Principled BSDF').inputs['Transmission Weight'].default_value = .28
    glass.node_tree.nodes.get('Principled BSDF').inputs['IOR'].default_value = 1.45
    window = material('Soft daylight glazing', (.70, .78, .65), .28)
    window_bsdf = window.node_tree.nodes.get('Principled BSDF')
    window_bsdf.inputs['Emission Color'].default_value = (.79, .82, .65, 1)
    window_bsdf.inputs['Emission Strength'].default_value = .5
    cover_colors = [(.09, .14, .12), (.14, .18, .17), (.24, .13, .085), (.24, .23, .13), (.12, .16, .22)]
    covers = [material('Cloth binding ' + str(i), color, .8) for i, color in enumerate(cover_colors)]
    rng = random.Random(1491)

    # Large continuous surfaces fill the view beyond the dressed room's perimeter.
    box('Continuous laboratory subfloor', (0, -.30, 15), (200, .30, 160), grout)
    box('Continuous limestone floor', (0, -.105, 15), (200, .04, 160), ivory)
    for ix in range(-16, 16):
        for iz in range(-8, 16):
            x, z = ix * 2 + 1, iz * 2 + 1
            mat = sage if abs(x) > 14 or z < -10 else ivory
            box('Limestone floor tile', (x, -.067, z), (1.98, .034, 1.98), mat)
    box('Tall rear plaster wall', (0, 30, -13.1), (200, 60, .4), plaster)
    for x in [-18, 18]:
        box('Side plaster wall', (x, 30, 10), (.4, 60, 46), plaster)
        box('Side sage wainscot', (x - math.copysign(.22, x), 1.2, 7), (.07, 2.4, 40), sage)
    box('Rear sage wainscot', (0, 1.25, -12.84), (200, 2.5, .08), sage)
    box('Rear picture rail', (0, 8.45, -12.8), (200, .16, .14), sage)
    box('Rear oak skirting', (0, .14, -12.75), (200, .26, .16), walnut)

    # Two quiet inlaid circles share the existing source combatant anchors.
    for x, z, radius in [(-4, 3, 2.65), (4, -3, 2.25)]:
        cylinder('Sage combat floor inlay', (x, -.044, z), radius, .009, sage, 96)
        cylinder('Limestone inlay center', (x, -.037, z), radius * .27, .01, ivory, 64)
        ring('Inlay outer fine joint', (x, -.035, z), radius, .014, grout)
        ring('Inlay center fine joint', (x, -.025, z), radius * .29, .012, grout)
        box('Inlay stone center seam', (x, -.025, z), (radius * 1.42, .007, .026), grout)

    def cabinet(x, z, width=3.25, drawers=False):
        box('Cabinet oak carcass', (x, .97, z), (width, 2, 1.65), walnut, .045)
        box('Thick oiled worktop', (x, 2.05, z), (width + .12, .16, 1.83), counter, .035)
        box('Cabinet recessed plinth', (x, .095, z + .10), (width - .2, .19, 1.46), black)
        columns = 2
        for col in range(columns):
            cx = x + (col - .5) * (width / columns)
            if drawers:
                for row in range(4):
                    y = .40 + row * .42
                    box('Framed oak drawer', (cx, y, z + .84), (width / 2 - .08, .36, .065), oak, .018)
                    box('Nickel drawer pull', (cx, y + .035, z + .91), (.40, .042, .047), metal, .012)
            else:
                box('Raised oak cabinet door', (cx, 1, z + .84), (width / 2 - .07, 1.69, .075), oak, .025)
                box('Inset door panel', (cx, 1, z + .89), (width / 2 - .26, 1.42, .025), counter, .014)
                box('Nickel cabinet handle', (cx + .40, 1.26, z + .965), (.045, .32, .045), metal, .012)

    for i, x in enumerate([-13.7, -10.35, -7, -3.65, 3.65, 7, 10.35, 13.7]):
        cabinet(x, -11.65, drawers=i % 3 == 0)
    # The central kneehole and stool make this a working research bench.
    box('Central desk worktop', (0, 2.05, -11.65), (4.05, .16, 1.83), counter, .03)
    for x in [-1.6, 1.6]:
        box('Desk leg', (x, .98, -11.65), (.11, 1.95, .11), walnut)
    cylinder('Stool seat', (.2, 1.15, -9.8), .45, .15, black)
    cylinder('Stool chrome post', (.2, .58, -9.8), .06, 1.07, metal)
    for angle in range(0, 360, 72):
        a = math.radians(angle)
        box('Stool foot', (.2 + math.cos(a) * .25, .14, -9.8 + math.sin(a) * .25), (.54, .07, .055), metal)

    for x in [-14, -7, 0, 7, 14]:
        box('Deep oak window frame', (x, 6.08, -12.65), (3.75, 3.05, .22), walnut, .025)
        box('Muted sage window reveal', (x, 6.08, -12.49), (3.44, 2.74, .08), sage)
        box('Daylight window glass', (x, 6.08, -12.425), (3.13, 2.43, .025), window)
        for y in [4.88, 6.08, 7.28]:
            box('Window horizontal muntin', (x, y, -12.38), (3.20, .075, .085), oak)
        for cx in [x - 1.55, x + 1.55]:
            box('Window vertical muntin', (cx, 6.08, -12.38), (.07, 2.44, .08), oak)
        box('Solid oak window sill', (x, 4.76, -12.39), (3.94, .12, .50), counter, .022)

    def books(x, y, z, count):
        for n in range(count):
            h = rng.uniform(.62, .89)
            w = rng.uniform(.13, .20)
            cx = x + n * .22
            box('Bound research volume', (cx, y + h / 2, z), (w, h, .46), covers[n % len(covers)], .01)
            box('Book spine gilt band', (cx, y + h * .82, z + .237), (w * .78, .017, .008), paper)
            box('Book spine lower band', (cx, y + h * .16, z + .237), (w * .78, .013, .008), paper)
    books(-3.3, 2.13, -11.29, 12)
    books(4.5, 2.13, -11.35, 16)
    books(10.5, 4.36, -12.04, 16)
    for x in [-10, 10.7]:
        box('Research shelf backing', (x, 3.4, -12.59), (5.4, 2.7, .15), walnut)
        for y in [2.2, 3.25, 4.3]:
            box('Research shelf', (x, y, -12.0), (5.55, .12, 1.1), counter, .02)
        for cx in [x - 2.65, x + 2.65]:
            box('Research shelf upright', (cx, 3.34, -12.04), (.12, 2.7, 1.05), oak)

    def bottle(x, y, z, h=.6, radius=.14):
        cylinder('Specimen bottle body', (x, y + h * .36, z), radius, h * .72, glass)
        sphere('Bottle shoulder', (x, y + h * .71, z), (radius, h * .12, radius), glass)
        cylinder('Bottle neck', (x, y + h * .86, z), radius * .38, h * .24, glass)
        cylinder('Bottle cork', (x, y + h * 1.005, z), radius * .44, .07, oak)
        box('Blank specimen label', (x, y + h * .36, z + radius * .95), (radius * 1.6, h * .23, .015), paper, .009)
    for x0 in [-12, -8.3, 8.5, 12.3]:
        for n in range(5):
            bottle(x0 + n * .35, 2.16 if x0 < 0 else 3.32, -11.8, .45 + rng.random() * .3)

    # Vintage research computer, keyboard and microscope use actual geometry.
    box('CRT computer base', (-.2, 2.30, -11.20), (1.42, .32, .95), ceramic, .05)
    box('CRT cabinet', (-.2, 2.98, -11.43), (1.46, 1.08, 1.08), ceramic, .10)
    box('CRT black bezel', (-.2, 3.03, -10.86), (1.17, .80, .10), black, .09)
    box('CRT convex screen', (-.2, 3.03, -10.79), (1.03, .66, .07), screen, .085)
    box('Computer keyboard', (-.2, 2.18, -10.52), (1.60, .07, .45), ceramic, .025)
    for row in range(3):
        for col in range(12):
            box('Keyboard key', (-.90 + col * .124, 2.23, -10.66 + row * .12), (.104, .035, .088), paper, .008)
    box('Microscope heavy base', (3.2, 2.19, -11.1), (.65, .13, .50), ceramic, .055)
    box('Microscope upright', (3.2, 2.67, -11.30), (.15, .90, .18), ceramic, .035)
    box('Microscope stage', (3.2, 2.60, -11.04), (.50, .075, .43), black)
    cylinder('Microscope optical tube', (3.2, 3.02, -11.0), .10, .63, metal)
    cylinder('Microscope eyepiece', (3.2, 3.35, -11.0), .13, .13, black)

    def plant(x, y, z, scale=1):
        cylinder('Specimen clay planter', (x, y + .21 * scale, z), .31 * scale, .42 * scale, terracotta)
        cylinder('Dark planter soil', (x, y + .435 * scale, z), .27 * scale, .025 * scale, soil)
        for n in range(7):
            a = n * 2.40
            h = (.55 + (n % 3) * .18) * scale
            cylinder('Plant stem', (x, y + .43 * scale + h / 2, z), .014 * scale, h, leaf, 8)
            obj = sphere('Broad specimen leaf', (x + math.cos(a) * .23 * scale, y + .43 * scale + h, z + math.sin(a) * .23 * scale), (.33 * scale, .08 * scale, .14 * scale), leaf)
            obj.rotation_euler[2] = -a
    for x in [-6, -4.8, 6.8]:
        plant(x, 2.14, -11.37, 1.05)
    for x in [-14, 14]:
        cabinet(x, -7.7, 3.6, False)
        box('Specimen tank base', (x, 2.22, -7.7), (3.3, .14, 1.55), black, .025)
        box('Specimen tank soil bed', (x, 2.34, -7.7), (3.12, .14, 1.35), soil)
        for cx in [x - 1.6, x + 1.6]:
            for z in [-8.40, -7.0]:
                box('Tank metal corner', (cx, 3.07, z), (.045, 1.80, .045), black)
        for y in [2.28, 3.99]:
            box('Tank front frame', (x, y, -7.0), (3.24, .055, .055), black)
            box('Tank back frame', (x, y, -8.40), (3.24, .055, .055), black)
        for n in range(4):
            plant(x - 1.05 + n * .70, 2.33, -7.7, .82 + n * .05)
    # Botanist's specimen illustrations are simple authored colored reliefs.
    for i, x in enumerate([-5.2, -3.5, 2.0, 3.7]):
        box('Framed botanical plate', (x, 3.80, -12.69), (1.20, 1.38, .08), sage, .015)
        box('Botanical plate paper', (x, 3.80, -12.62), (1.05, 1.22, .025), paper)
        box('Botanical plate stem', (x, 3.75, -12.59), (.02, .73, .015), oak)
        for n in range(4):
            sphere('Botanical plate leaf', (x + (-1 if n % 2 else 1) * .13, 3.50 + n * .14, -12.57), (.14, .07, .014), leaf)
    area('Warm window key', (-8, 10, -5), (0, 0, 1), 4500, 9, (1, .88, .69))
    area('Wide camera fill', (2, 11, 12), (0, 1, -4), 2500, 10, (.81, .87, 1))
    area('Rear soft sunlight', (10, 10, -9), (2, 0, 3), 3400, 6, (1, .89, .73))
    return {'referenceJob': '08e8185c-4820-4843-b681-9ec31be4b55a',
            'scene': 'Oak research laboratory, first FireRed starter battle',
            'sourceMap': 'PalletTown_ProfessorOaksLab',
            'combatAnchors': {'player': [-4, 0, 3], 'opponent': [4, -.04, -3]},
            'clearCombatZone': {'x': [-9, 9], 'z': [-7, 7]},
            'materials': len(bpy.data.materials), 'textureImages': len(bpy.data.images),
            'limitations': ['Authored interpretation of the generated target, not extracted hidden ROM geometry.',
                            'Lighting requires runtime lights/environment; Blender area lights are not embedded.',
                            'Specimen glass and small scientific apparatus remain simplified at gameplay distance.']}


if __name__ == '__main__':
    args = arguments()
    reference = Path(args.reference)
    if not reference.is_file():
        raise FileNotFoundError('A visible authored reference is required before arena production')
    setup()
    root = Path(args.root).resolve()
    manifest = build_arena(root)
    runtime_camera()
    glb, evidence = export_artifacts(root, reference, manifest)
    render_evidence(evidence)
    print('ARENA_COMPLETE ' + json.dumps({'glb': str(glb), 'sha256': hash_file(glb), 'evidence': str(evidence)}))
