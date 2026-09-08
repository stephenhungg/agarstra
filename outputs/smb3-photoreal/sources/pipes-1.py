"""Editable enamel pipe family; run with Blender 4.5, never plain Python."""
import argparse
import json
import math
import random
import sys
from array import array
from pathlib import Path

import bpy

HELPER = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools')
sys.path.insert(0, str(HELPER))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

IDS = ('pipe-green', 'pipe-red', 'pipe-gold')
COLORS = ('287C4A', 'A7352C', 'BB913C')
LIMITATIONS = [
    'Authored code only: Blender execution, export and visual inspection pending central queue.',
    'All variants share 2 x 2 x 3 dimensions; red and gold heights were unspecified.',
    'Industrial joints, fasteners and wear are interpretive additions, not literal ROM details.',
    'Bore is open through the base; scene ground or receiving pipe supplies its termination.',
]
FALLBACKS = []


def fallback_material(name, color, roughness, metallic, cache):
    """Deterministic bitmap PBR; no unexportable procedural nodes."""
    size = 512
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    rng = random.Random(37)
    height = [rng.random() * .13 for _ in range(size * size)]
    # Periodic fine scoring; most of the finish remains intact.
    for _ in range(100):
        x, y = rng.randrange(size), rng.randrange(size)
        for step in range(rng.randrange(4, 35)):
            height[((y + step) % size) * size + (x + step // 5) % size] -= .24
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    bsdf.inputs['Coat Weight'].default_value = .25
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(size):
            for x in range(size):
                h = height[y * size + x]
                if channel == 'basecolor':
                    factor = .94 + .11 * math.sin(x * math.tau / size) * math.sin(y * math.tau / size) + h * .15
                    # Generated image pixels are scene-linear, saved to sRGB PNG.
                    values = [((v / 12.92) if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * factor for v in rgb]
                elif channel == 'roughness':
                    values = [max(.05, min(.98, roughness + h * .35))] * 3
                else:
                    dx = (height[y * size + (x + 1) % size] - height[y * size + (x - 1) % size]) * .45
                    dy = (height[((y + 1) % size) * size + x] - height[((y - 1) % size) * size + x]) * .45
                    norm = math.sqrt(dx * dx + dy * dy + 1)
                    values = [.5 - dx / norm * .5, .5 - dy / norm * .5, .5 + .5 / norm]
                pixels.extend((*values, 1))
        image = bpy.data.images.new(name + '_' + channel, width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(cache / (name + '_' + channel + '.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        texture = nodes.new('ShaderNodeTexImage')
        texture.image = image
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(texture.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(texture.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    return mat


def material(name, color, roughness, metallic, cache):
    if pbr:
        try:
            return pbr.material('green_metal', name=name, color=color, roughness=roughness,
                                metallic=metallic, bump=.004, coat=.28,
                                bake=True, resolution=512, cache_dir=cache)
        except Exception as exc:
            FALLBACKS.append(name + ': ' + str(exc))
    return fallback_material(name, color, roughness, metallic, cache)


def mesh_object(name, verts, faces, mats, root, smooth=True):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.parent = root
    obj['asset_id'] = root['asset_id']
    for mat in mats:
        mesh.materials.append(mat)
    for poly in mesh.polygons:
        poly.use_smooth = smooth
    return obj


def lathe(name, profile, mats, root, segments=64, inner_rows=(), wobble=False, offset=(0, 0, 0)):
    """Explicit quad rings, circumference UV seam and arc-length profile V."""
    verts, faces = [], []
    distances = [0.0]
    for a, b in zip(profile, profile[1:]):
        distances.append(distances[-1] + math.hypot(b[0] - a[0], b[1] - a[1]))
    for r, z in profile:
        for j in range(segments):
            theta = j * math.tau / segments
            delta = .0014 * math.sin(theta * 7 + z * 4) * math.sin(z * math.pi / 3) if wobble else 0
            verts.append(((r + delta) * math.cos(theta) + offset[0],
                          (r + delta) * math.sin(theta) + offset[1], z + offset[2]))
    for row in range(len(profile) - 1):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append((row * segments + j, row * segments + k,
                          (row + 1) * segments + k, (row + 1) * segments + j))
    obj = mesh_object(name, verts, faces, mats, root)
    uv = obj.data.uv_layers.new(name='UVMap')
    for poly in obj.data.polygons:
        row, j = divmod(poly.index, segments)
        coordinates = ((j / segments, distances[row]), ((j + 1) / segments, distances[row]),
                       ((j + 1) / segments, distances[row + 1]), (j / segments, distances[row + 1]))
        for loop, coordinate in zip(poly.loop_indices, coordinates):
            uv.data[loop].uv = coordinate
        if row in inner_rows:
            poly.material_index = 1
    return obj


def build_asset(asset_id, paint, dark, metal):
    root = bpy.data.objects.new(asset_id, None)
    bpy.context.collection.objects.link(root)
    root['asset_id'] = asset_id
    root['nominal_dimensions'] = [2.0, 2.0, 3.0]
    root.empty_display_type = 'PLAIN_AXES'
    # Closed wall cross-section; actual open bore, including downward-facing bottom annulus.
    body = [(.80, 0), (.845, .025), (.85, .065), (.85, .3), (.85, .8),
            (.85, 1.4), (.85, 1.9), (.85, 2.4), (.85, 2.64),
            (.75, 2.64), (.75, 2.3), (.75, 1.8), (.75, 1.2), (.75, .5), (.75, 0), (.80, 0)]
    lathe(asset_id + '_cast_barrel', body, [paint, dark], root, inner_rows=range(9, 15), wobble=True)
    collar = [(.84, 2.53), (.94, 2.53), (.985, 2.56), (1, 2.60),
              (1, 2.86), (.985, 2.90), (.94, 2.92), (.77, 2.92),
              (.735, 2.88), (.735, 2.61), (.77, 2.56), (.84, 2.53)]
    lathe(asset_id + '_mouth_collar', collar, [paint, dark], root, 96, inner_rows=(8, 9))
    # True torus ring: major .865, minor .135; exact outside diameter 2 and top Z 3.
    rim = [(.865 + .135 * math.cos(i * math.tau / 12),
            2.865 + .135 * math.sin(i * math.tau / 12)) for i in range(13)]
    lathe(asset_id + '_rolled_torus_rim', rim, [paint], root, 96)
    for z in (1.34, 1.455):
        flange = [(.846, z), (.92, z), (.94, z + .018), (.94, z + .063),
                  (.92, z + .083), (.846, z + .083), (.846, z)]
        lathe(asset_id + '_segment_flange_' + str(z), flange, [paint], root)
    gasket = [(.848, 1.423), (.915, 1.423), (.915, 1.455), (.848, 1.455), (.848, 1.423)]
    lathe(asset_id + '_recessed_joint_gasket', gasket, [dark], root)
    for j in range(10):
        angle = j * math.tau / 10
        offset = (.889 * math.cos(angle), .889 * math.sin(angle), 0)
        # Beveled hex heads recessed slightly into upper flange, and lower hex nuts.
        for z in (1.32, 1.533):
            profile = [(.024, z), (.033, z + .006), (.033, z + .031),
                       (.025, z + .037), (.001, z + .037), (.001, z), (.024, z)]
            obj = lathe(asset_id + '_hex_' + str(j) + '_' + str(z), profile, [metal], root, 6, offset=offset)
            for poly in obj.data.polygons:
                poly.use_smooth = False
    # Narrow irregular exposed-metal scores following the curved barrel, not billboard planes.
    rng = random.Random(1908)
    for j in range(18):
        a, z = rng.uniform(0, math.tau), rng.uniform(.18, 2.38)
        length = rng.uniform(.025, .105)
        verts = []
        for k in range(5):
            t = k / 4
            theta = a + .015 * t
            zz = z + length * t
            width = .0005 + .0010 * math.sin(math.pi * t)
            rr = .8504 + .0014 * math.sin(theta * 7 + zz * 4) * math.sin(zz * math.pi / 3)
            for side in (-1, 1):
                aa = theta + side * width
                verts.append((rr * math.cos(aa), rr * math.sin(aa), zz))
        faces = [(k * 2, k * 2 + 1, k * 2 + 3, k * 2 + 2) for k in range(4)]
        obj = mesh_object(asset_id + '_enamel_score_' + str(j), verts, faces, [metal], root)
        uv = obj.data.uv_layers.new(name='UVMap')
        for poly in obj.data.polygons:
            for li in poly.loop_indices:
                vi = obj.data.loops[li].vertex_index
                uv.data[li].uv = (vi % 2, vi // 2 / 4)
    return root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    out = args.out.resolve()
    (out / 'models').mkdir(parents=True, exist_ok=True)
    cache = out / 'materials'
    cache.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    dark = material('dark_oxidized_bore', '1C2420', .82, .32, cache)
    metal = material('exposed_cast_iron', '555957', .54, .75, cache)
    roots, manifest = [], []
    for asset_id, color in zip(IDS, COLORS):
        paint = material(asset_id + '_enamel', color, .31, .22, cache)
        root = build_asset(asset_id, paint, dark, metal)
        roots.append(root)
        objects = [root, *root.children]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = out / 'models' / (asset_id + '.glb')
        bpy.ops.export_scene.gltf(filepath=str(target), export_format='GLB', use_selection=True,
                                  export_extras=True, export_apply=True, export_materials='EXPORT',
                                  export_image_format='AUTO', export_yup=True)
        triangles = sum(sum(len(p.vertices) - 2 for p in obj.data.polygons)
                        for obj in root.children if obj.type == 'MESH')
        manifest.append({'asset_id': asset_id, 'path': 'models/' + target.name,
                         'nominal_dimensions': {'x': 2, 'y': 2, 'z': 3},
                         'materials': [paint.name, dark.name, metal.name], 'triangles': triangles,
                         'mesh_features': ['64-sided hollow cast barrel', '96-sided mouth collar',
                                           '96 x 12 torus rolled lip', 'paired beveled annular flanges',
                                           '20 beveled hex fasteners', 'dark inner wall',
                                           'recessed gasket', 'casting waviness', '18 surface wear scores',
                                           'UV-mapped packed basecolor, roughness and tangent normal textures'],
                         'source_basis': {'catalog': 'smb3-rom-assets/catalog/binary-assets.json',
                                          'definitions': ['Tile_Layout_TS1-173', 'Tile_Layout_TS1-174'],
                                          'symbols': ['TILE1_PIPETB1_L', 'TILE1_PIPETB1_R'],
                                          'visual_catalog': 'binary-metatiles-00.png',
                                          'interpretation': 'Wide mouth over narrower vertical barrel; colors from requested family.'},
                         'known_quality_limitations': LIMITATIONS})
    for i, root in enumerate(roots):
        root.location.x = (i - 1) * 3.2
    for image in bpy.data.images:
        if image.source == 'FILE' or image.has_data:
            if not image.packed_file:
                image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'library.blend'))
    (out / 'manifest.json').write_text(json.dumps({'assets': manifest, 'material_fallbacks': FALLBACKS,
                                                 'coordinates': 'Z up; front -Y; GLB Y up',
                                                 'library_layout': 'Roots at X=-3.2,0,3.2 for inspection; individual GLBs at origin.'}, indent=2))


if __name__ == '__main__':
    main()
