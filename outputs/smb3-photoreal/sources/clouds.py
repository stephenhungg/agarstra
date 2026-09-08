"""Opening cloud + green architectural platform. Authored only; central queue runs Blender."""
import argparse
import json
import math
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[4]
SHARED = ROOT / 'outputs' / 'smb3-photoreal'
sys.path.insert(0, str(SHARED / 'tools'))
import pbr_common as pbr


def active(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def attach(asset_id, objects):
    root = bpy.data.objects.new(asset_id, None)
    bpy.context.collection.objects.link(root)
    root['asset_id'] = asset_id
    root['origin'] = 'bottom-center'
    root['front_axis'] = '-Y'
    for obj in objects:
        obj.parent = root
        obj['asset_id'] = asset_id
    return root, [root, *objects]


def cloud(materials):
    white, recess = materials['cloud'], materials['cloud_recess']
    # Overlapping, asymmetric closed lobes form one smooth physical cloud volume.
    # Front is -Y. Broad lower shelf + unequally sized upper towers preserve source silhouette.
    lobes = [
        ((0, .08, .47), (1.45, .48, .39)),
        ((-1.40, .04, .53), (.59, .44, .45)),
        ((1.42, .08, .51), (.57, .42, .42)),
        ((-.87, .08, .91), (.71, .51, .65)),
        ((.05, .13, .96), (.69, .53, .69)),
        ((.92, .11, .88), (.64, .48, .61)),
        ((-1.07, -.20, .42), (.51, .31, .32)),
        ((-.37, -.29, .45), (.48, .29, .34)),
        ((.41, -.28, .43), (.48, .30, .33)),
        ((1.12, -.20, .39), (.42, .29, .28)),
        ((-.66, .39, .76), (.50, .34, .48)),
        ((.55, .39, .67), (.61, .32, .45)),
    ]
    parts = [pbr.sphere('Cloud billow %02d' % i, scale, center, white, segments=24, rings=16)
             for i, (center, scale) in enumerate(lobes)]
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = 'Sculpted continuous asymmetric cloud'
    remesh = body.modifiers.new('Fuse overlapping vapor billows', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = .045
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth = body.modifiers.new('Soften billow joins', 'SMOOTH')
    smooth.factor = .65
    smooth.iterations = 3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    # Real shallow silhouette breakup; fine surface detail remains in the baked normal map.
    texture = bpy.data.textures.new('Cloud fine turbulent shape', type='CLOUDS')
    texture.noise_scale = .19
    texture.noise_depth = 2
    displacement = body.modifiers.new('Subtle volumetric turbulence', 'DISPLACE')
    displacement.texture = texture
    displacement.strength = .021
    displacement.mid_level = .5
    bpy.ops.object.modifier_apply(modifier=displacement.name)
    body.data.calc_loop_triangles()
    triangles = len(body.data.loop_triangles)
    if triangles > 6400:
        decimate = body.modifiers.new('Cloud runtime triangle budget', 'DECIMATE')
        decimate.ratio = 6400 / triangles
        bpy.ops.object.modifier_apply(modifier=decimate.name)
    # Normalize local geometry without moving its editable bottom-center origin.
    coords = [v.co.copy() for v in body.data.vertices]
    low = Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    high = Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    span = high - low
    for vertex in body.data.vertices:
        v = vertex.co
        vertex.co = ((v.x - low.x) / span.x * 4 - 2,
                     (v.y - low.y) / span.y * 1.15 - .575,
                     (v.z - low.z) / span.z * 1.6)
    body.location = (0, 0, 0)
    for face in body.data.polygons:
        face.use_smooth = True
    pbr.uv_smart(body)
    parts = [body]
    # Restrained recessed shadow marks acknowledge the tiny source eyes. They are geometry,
    # neither painted sprite decals nor high-contrast cartoon face replacements.
    for x in (-.31, .31):
        parts.append(pbr.sphere('Soft cloud eye recess', (.019, .013, .041), (x, -.573, .69), recess, segments=12, rings=8))
        parts.append(pbr.sphere('Cloud brow billow', (.085, .027, .032), (x, -.562, .75), white, segments=16, rings=10))
    return attach('cloud', parts)


def cylinder(name, radius, depth, center, material, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=center, rotation=(math.pi / 2, 0, 0))
    obj = bpy.context.object
    obj.name = name
    if material:
        obj.data.materials.append(material)
    pbr.uv_smart(obj)
    return obj


def green_platform(materials):
    paint, substrate, iron = materials['green'], materials['substrate'], materials['iron']
    core = pbr.bevel_cube('Green platform structural core', (2.96, .39, 1.96), (0, .025, .98), substrate, bevel=.09, segments=5)
    face = pbr.bevel_cube('Green cast panel with recessed fasteners', (3, .15, 2), (0, -.19, 1), paint, bevel=.095, segments=6)
    objects = [core, face]
    for x in (-1.27, 1.27):
        for z in (.23, 1.77):
            cutter = cylinder('Temporary mounting recess cutter', .108, .23, (x, -.20, z), None, 32)
            active(face)
            mod = face.modifiers.new('Actual recessed corner socket', 'BOOLEAN')
            mod.operation = 'DIFFERENCE'
            mod.solver = 'EXACT'
            mod.object = cutter
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(cutter, do_unlink=True)
            objects.append(cylinder('Dark recessed mounting socket', .103, .022, (x, -.162, z), iron, 24))
            bolt = cylinder('Inset six-sided iron bolt', .059, .035, (x, -.187, z), iron, 6)
            bevel = bolt.modifiers.new('Soft forged bolt edges', 'BEVEL')
            bevel.width = .008
            bevel.segments = 3
            objects.append(bolt)
    pbr.uv_smart(face)
    for x in (-1.425, 1.425):
        objects.append(pbr.bevel_cube('Rounded green panel side return', (.065, .18, 1.68), (x, -.12, 1), paint, bevel=.02))
    for z in (.065, 1.935):
        objects.append(pbr.bevel_cube('Rounded green panel horizontal return', (2.65, .18, .065), (0, -.12, z), paint, bevel=.02))
    for x in (-1.02, 1.02):
        objects.append(pbr.bevel_cube('Rear structural rib', (.17, .12, 1.72), (x, .245, .96), substrate, bevel=.025))
    return attach('platform-green', objects)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    out = Path(args.out).resolve()
    (out / 'models').mkdir(parents=True, exist_ok=True)
    style = json.loads((SHARED / 'design' / 'style.json').read_text())
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    cache = SHARED / 'textures'
    materials = {
        'cloud': pbr.material('stone', name='Soft warm cloud microstructure', color='F4F3ED', roughness=.98, metallic=0, bump=.003, scale=3, resolution=512, cache_dir=cache),
        'cloud_recess': pbr.material('stone', name='Faint cloud fold occlusion', color='C8C7C0', roughness=1, metallic=0, bump=.002, scale=3, resolution=256, cache_dir=cache),
        'green': pbr.material('green_metal', name='Sage green painted architectural panel', color='64836B', roughness=.74, metallic=.025, coat=.06, bump=.014, scale=8, resolution=512, cache_dir=cache),
        'substrate': pbr.material('stone', name='Warm mineral platform core', color='A09176', roughness=.86, metallic=0, bump=.018, scale=7, resolution=512, cache_dir=cache),
        'iron': pbr.material('worn_brass', name='Blackened platform fasteners', color='3C403B', roughness=.55, metallic=.75, bump=.006, resolution=512, cache_dir=cache),
    }
    entries, roots = [], []
    for asset_id, builder, dimensions in [('cloud', cloud, {'width': 4, 'height': 1.6, 'depth': 1.15}), ('platform-green', green_platform, {'width': 3, 'height': 2, 'depth': .55})]:
        root, objects = builder(materials)
        roots.append(root)
        path = out / 'models' / (asset_id + '.glb')
        inspection = pbr.export_glb(path, objects, extras={'asset_id': asset_id, 'origin': 'bottom-center', 'front_axis': '-Y'})
        deps = bpy.context.evaluated_depsgraph_get()
        triangles = 0
        for obj in objects:
            if obj.type == 'MESH':
                evaluated = obj.evaluated_get(deps)
                mesh = evaluated.to_mesh()
                mesh.calc_loop_triangles()
                triangles += len(mesh.loop_triangles)
                evaluated.to_mesh_clear()
        entries.append({'asset_id': asset_id, 'path': 'models/' + path.name, 'nominaldimensions': dimensions, 'triangles': triangles, 'export_inspection': inspection,
                        'sourcebasis': 'World 1-1 source semantic cloud or green large-platform definitions; new volumetric PBR interpretation, not recovered hidden geometry.',
                        'meshfeatures': ['continuous voxel-fused asymmetric sculpt with twelve physical billows', 'shallow displaced turbulence', 'baked fine normal and roughness maps', 'subtle geometric eye-recess folds'] if asset_id == 'cloud' else ['layered rounded structural panel', 'actual boolean recessed sockets and inset hex fasteners', 'side returns and rear ribs', 'baked weathered green paint'],
                        'knownqualitylimitations': ['Visual quality requires central rendered review.', 'Cloud is opaque authored geometry with diffuse PBR, not a participating atmospheric volume.', 'Exact source silhouette is adapted by runtime normalization.']})
    # Save an editable catalog only after exporting assets at their zero origins.
    roots[1].location = (5, 0, 0)
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'library.blend'))
    (out / 'manifest.json').write_text(json.dumps({'schemaVersion': 1, 'job': 'clouds', 'style': style, 'assets': entries}, indent=2))
    print('CLOUDS_JOB_COMPLETE', json.dumps({'assets': [e['asset_id'] for e in entries], 'triangles': [e['triangles'] for e in entries]}), flush=True)


if __name__ == '__main__':
    main()
