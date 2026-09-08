"""Deterministic Blender 4.5 block family; execute only through the build queue."""
import argparse
import json
import math
from pathlib import Path
import random
import sys
from array import array

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.dont_write_bytecode = True  # The shared helper directory is read-only.
sys.path.insert(0, str(SHARED / 'tools'))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

SOURCE = {
    'stone-block': {
        'definition': 'Tile_Layout_TS2-156', 'symbol': 'TILE2_SOLIDBRICK',
        'image': 'binary-metatile-4dfe1dcd42ca879b337e',
        'context': 'context-2-1-22',
        'interpretation': 'Castle solid brick framed square silhouette; granular grey stone is a material reinterpretation, not an exact palette match.'},
    'ice-block': {
        'definition': 'Tile_Layout_TS4_TS12-58', 'symbol': 'TILE12_ICEBLOCK',
        'image': 'binary-metatile-cacc009f82aaaa75b66f',
        'context': 'context-12-0-12',
        'interpretation': '16x16 rounded square, pale cyan border and diagonal white highlights; depth and fractures are authored.'},
}
WARNINGS = []


def fallback_material(name, color, roughness, cache):
    """Raster PBR fallback: periodic grain, albedo, roughness and tangent normals."""
    res = 512
    rng = random.Random(173)
    heights = [rng.random() * .12 for _ in range(res * res)]
    for y in range(res):
        for x in range(res):
            heights[y*res+x] += .10*math.sin(x*math.tau*9/res)*math.cos(y*math.tau*7/res)
    rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(res):
            for x in range(res):
                h = heights[y*res+x]
                if channel == 'basecolor':
                    c = [max(0, min(1, v*(.90+h))) for v in rgb]
                    c = [v/12.92 if v <= .04045 else ((v+.055)/1.055)**2.4 for v in c]
                elif channel == 'roughness':
                    c = [max(.04, min(1, roughness+(h-.06)*.6))]*3
                else:
                    dx = heights[y*res+(x+1)%res]-heights[y*res+(x-1)%res]
                    dy = heights[((y+1)%res)*res+x]-heights[((y-1)%res)*res+x]
                    n = Vector((-dx*2, -dy*2, 1)).normalized()
                    c = [(v+1)*.5 for v in n]
                pixels.extend((*c, 1))
        im = bpy.data.images.new(name+'_'+channel, width=res, height=res, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels)
        im.filepath_raw = str(cache/(name+'_'+channel+'.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = nodes.new('ShaderNodeTexImage'); tex.image = im
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic raster fallback'
    return mat


def material(name, color, roughness, cache, bump=.018, transmission=0):
    try:
        if pbr is None:
            raise RuntimeError('Shared helper unavailable')
        mat = pbr.material('stone', name=name, color=color, roughness=roughness,
                           bump=bump, scale=12, bake=True, resolution=512, cache_dir=cache)
    except Exception as exc:
        WARNINGS.append(f'{name}: shared bake unavailable ({exc}); using raster PBR fallback')
        mat = fallback_material(name, color, roughness, cache)
    bsdf = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    bsdf.inputs['IOR'].default_value = 1.31 if transmission else 1.5
    bsdf.inputs['Transmission Weight'].default_value = transmission
    if transmission:
        bsdf.inputs['Coat Weight'].default_value = .16
        bsdf.inputs['Coat Roughness'].default_value = .19
    return mat


# Right-handed local frames: U cross V points outwards.
FRAMES = [((1,0,0),(0,0,1),(0,-1,0)), ((-1,0,0),(0,0,1),(0,1,0)),
          ((0,1,0),(0,0,1),(1,0,0)), ((0,-1,0),(0,0,1),(-1,0,0)),
          ((1,0,0),(0,1,0),(0,0,1)), ((1,0,0),(0,-1,0),(0,0,-1))]


def smoothstep(a, b, x):
    t = max(0, min(1, (x-a)/(b-a)))
    return t*t*(3-2*t)


def sculpt_block(asset_id, materials, icy=False):
    """Welded six-sided gridded rounded box with actual inset relief and chipped faces."""
    steps = 20
    verts, faces, face_uvs, slots = [], [], [], []
    lookup = {}
    radius = .055 if icy else .035
    for side, frame in enumerate(FRAMES):
        uaxis, vaxis, normal = map(Vector, frame)
        grid = {}
        for j in range(steps+1):
            for i in range(steps+1):
                u, v = i/steps-.5, j/steps-.5
                raw = uaxis*u+vaxis*v+normal*.5
                inner = Vector([max(-.5+radius, min(.5-radius, c)) for c in raw])
                pos = inner+(raw-inner).normalized()*radius
                edge = max(abs(u), abs(v))
                fade = 1-smoothstep(.37, .46, edge)
                if icy:
                    relief = -.009*fade + .0013*math.sin(u*23+side)*math.cos(v*19)*fade
                else:
                    # A recessed dressed panel surrounded by a flat perimeter band.
                    inset = 1-smoothstep(.33, .405, edge)
                    relief = -.024*inset
                    relief += (.0028*math.sin(u*77+v*31+side*4)
                               + .0018*math.cos(u*39-v*87+side))*fade
                    # Uneven shallow carving across the dressed stone face.
                    line = v-(.19*u+.035*math.sin(u*19+side)+.08)
                    relief -= .008*math.exp(-(line/.015)**2)*fade
                pos += normal*relief
                pos.z += .5
                key = tuple(round(c, 7) for c in pos)
                if key not in lookup:
                    lookup[key] = len(verts); verts.append(tuple(pos))
                grid[i,j] = lookup[key]
        for j in range(steps):
            for i in range(steps):
                ids = [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]
                # Alternating diagonals retain modeled relief without non-planar quads.
                for tri in ((0,1,2),(0,2,3)) if (i+j)%2 else ((0,1,3),(1,2,3)):
                    faces.append(tuple(grid[ids[k]] for k in tri))
                    face_uvs.append(tuple((ids[k][0]/steps, ids[k][1]/steps) for k in tri))
                    edge = max(abs((i+.5)/steps-.5), abs((j+.5)/steps-.5))
                    slots.append(1 if edge > (.375 if icy else .405) else 0)
    mesh = bpy.data.meshes.new(asset_id+'_sculpted_mesh')
    mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new(asset_id+'_sculpted_body', mesh)
    bpy.context.collection.objects.link(obj)
    for mat in materials: mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly, coords, slot in zip(mesh.polygons, face_uvs, slots):
        poly.material_index = slot
        poly.use_smooth = icy
        for loop, coord in zip(poly.loop_indices, coords): uv.data[loop].uv = coord
    # The six patch borders must weld into a closed, consistently oriented shell.
    edge_counts = {}
    for face in faces:
        for a, b in zip(face, face[1:]+face[:1]):
            key = tuple(sorted((a, b)))
            edge_counts[key] = edge_counts.get(key, 0)+1
    assert all(count == 2 for count in edge_counts.values()), 'Open or non-manifold block shell'
    assert len(faces) <= 8000, 'Unexpected triangle budget'
    obj['mesh_features'] = 'Welded subdivided volume; rounded corners; recessed six-sided face panels; sculpted surface relief'
    return obj


def fractures(mat):
    """Closed tapered triangular prisms inside the ice, never decal planes."""
    verts, faces = [], []
    rng = random.Random(517)
    paths = [(-.31,.23,.20,.76), (-.24,.20,.29,.73), (.03,.15,.34,.48)]
    for idx,(x0,z0,x1,z1) in enumerate(paths):
        for segment in range(6):
            t0, t1 = segment/6, (segment+1)/6
            x = x0+(x1-x0)*t0; z = z0+(z1-z0)*t0
            xx = x0+(x1-x0)*t1; zz = z0+(z1-z0)*t1
            y = -.433+idx*.037+rng.uniform(-.003,.003)
            width = .007*(1-t0)+.002
            base = len(verts)
            verts.extend([(x-width,y,z),(x+width,y,z), (xx,y-.002,zz),
                          (x-width,y+.009,z),(x+width,y+.009,z),(xx,y+.007,zz)])
            faces.extend([tuple(base+i for i in reversed(f)) for f in
                          ((0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5))])
    mesh = bpy.data.meshes.new('ice_internal_fracture_prisms'); mesh.from_pydata(verts, [], faces); mesh.update()
    obj = bpy.data.objects.new('ice_internal_diagonal_fractures', mesh)
    bpy.context.collection.objects.link(obj); mesh.materials.append(mat)
    uv = mesh.uv_layers.new(name='UVMap')
    for poly in mesh.polygons:
        for loop in poly.loop_indices:
            co = mesh.vertices[mesh.loops[loop].vertex_index].co
            uv.data[loop].uv = (co.x+.5, co.z)
    return obj


def mesh_stats(objects):
    triangles = 0
    for obj in objects:
        if obj.type == 'MESH':
            obj.data.calc_loop_triangles(); triangles += len(obj.data.loop_triangles)
    return triangles


def export(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects: obj.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
                             export_apply=True, export_extras=True, export_materials='EXPORT',
                             export_image_format='AUTO', export_yup=True)
    # Structural validation runs in the queue, without relying on the shared helper.
    import struct
    raw = path.read_bytes()
    assert raw[:4] == b'glTF'
    length = struct.unpack_from('<I', raw, 12)[0]
    doc = json.loads(raw[20:20+length])
    images = doc.get('images', [])
    assert images and all('bufferView' in im for im in images), 'Textures must be embedded'
    for mat in doc.get('materials', []):
        p = mat.get('pbrMetallicRoughness', {})
        assert 'baseColorTexture' in p and 'metallicRoughnessTexture' in p and 'normalTexture' in mat, mat['name']
    return {'embedded_images': len(images), 'bytes': len(raw)}


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser = argparse.ArgumentParser(); parser.add_argument('--out', required=True)
    args = parser.parse_args(argv)
    out = Path(args.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out/'models').mkdir(exist_ok=True); cache = out/'materials'; cache.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    scene = bpy.context.scene; scene.unit_settings.system = 'METRIC'; scene.unit_settings.scale_length = 1
    stone = material('Fortress_granular_limestone', '92958E', .86, cache)
    rim = material('Fortress_dressed_edges', 'A2A59D', .77, cache, bump=.011)
    ice = material('Ice_cold_core', 'ACD6DF', .20, cache, bump=.002, transmission=.78)
    frost = material('Ice_frosted_perimeter', 'D4E8E9', .47, cache, bump=.009, transmission=.35)
    fissure = material('Ice_clouded_fractures', 'E0EFF0', .60, cache, bump=.004)
    families = [('stone-block', [sculpt_block('stone-block', [stone,rim])]),
                ('ice-block', [sculpt_block('ice-block', [ice,frost], icy=True), fractures(fissure)])]
    records = []
    for index, (asset_id, children) in enumerate(families):
        coll = bpy.data.collections.new(asset_id); scene.collection.children.link(coll)
        root = bpy.data.objects.new(asset_id, None); coll.objects.link(root)
        root['asset_id'] = asset_id; root['nominal_dimensions'] = [1.,1.,1.]
        root['front'] = '-Y'; root['origin_convention'] = 'bottom-center'
        for obj in children:
            for old in list(obj.users_collection): old.objects.unlink(obj)
            coll.objects.link(obj); obj.parent = root; obj['asset_id'] = asset_id
        path = out/'models'/f'{asset_id}.glb'
        verification = export(path, [root]+children)
        records.append({'asset_id': asset_id, 'path': f'models/{asset_id}.glb',
                        'nominal_dimensions': [1,1,1], 'dimension_axes': 'Blender XYZ',
                        'materials': sorted({m.name for obj in children for m in obj.data.materials}),
                        'mesh_features': [obj.get('mesh_features', 'Closed internal fracture prisms') for obj in children],
                        'triangles': mesh_stats(children), 'source_basis': SOURCE[asset_id],
                        'known_quality_limitations': [
                            'Authored reconstruction; render and visual acceptance pending central queue.',
                            'Image maps use repeated UV swatches; no unique large-scale weathering bake.',
                            'Ice refraction depends on viewer support for KHR_materials_transmission.'
                            if asset_id == 'ice-block' else 'Fine cracks are shallow modeled relief; this is one dressed stone, not brick courses.'],
                        'export_checks': verification})
        # Only the inspection library is spaced out. Standalone GLBs retain origin roots.
        root.location.x = index*1.6
    for image in bpy.data.images:
        if image.source == 'FILE' and image.has_data and not image.packed_file: image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets': records, 'warnings': WARNINGS,
        'units': '1 block = 1 Blender unit = 16 NES pixels',
        'style_contract': str(SHARED/'design/style.json')}, indent=2)+'\n')


if __name__ == '__main__':
    main()
