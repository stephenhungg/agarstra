"""Editable pipe family. Run only through the central Blender queue."""
import argparse
import json
import math
import random
import sys
from array import array
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.path.insert(0, str(SHARED / 'tools'))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

TAU = math.tau
N = 64
LIMITATIONS = [
    'Authored code only; Blender execution and visual review belong to central queue.',
    'Elbow sweep, flange hardware and wear are physical interpretations, not pixel-exact ROM geometry.',
    'Wear textures repeat; no unique object-space dirt or baked ambient occlusion.',
    'Bores remain open at the floor; no artificial black cap or ground plane is included.',
]
SOURCE = {
    'catalog': '/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-rom-assets/catalog',
    'json': 'binary-asset-manifest.json',
    'symbols': ['TILE1_PIPETB1_L', 'TILE1_PIPETB1_R', 'TILE1_PIPEH1_B', 'TILE1_PIPEH_T'],
    'viewed_sheet': 'binary-metatiles-00.png',
    'basis': 'Paired pipe top/bottom tiles and horizontal barrel tiles: broad collar, narrower barrel, green enamel. Rounded elbow is an authored adaptation.',
}


def image_material(name, color, rough, metal, out):
    """Blender-only deterministic fallback, with real exported image textures."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bs = m.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Coat Weight'].default_value = .25
    rng = random.Random(248)
    for channel in ('basecolor', 'roughness', 'normal'):
        im = bpy.data.images.new(name + '_' + channel, width=512, height=512)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        pixels = array('f')
        for y in range(512):
            for x in range(512):
                noise = rng.uniform(-1, 1)
                wave = math.sin(x * .08) * math.sin(y * .063)
                if channel == 'basecolor':
                    rgb = [v * (1 + .06 * noise + .035 * wave) for v in color]
                elif channel == 'roughness':
                    rgb = [min(1, max(.05, rough + noise * .05))] * 3
                else:
                    rgb = [.5 + noise * .022, .5 + wave * .018, 1]
                pixels.extend((*rgb, 1))
        im.pixels.foreach_set(pixels)
        node = m.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = im
        node.label = channel
        if channel == 'normal':
            norm = m.node_tree.nodes.new('ShaderNodeNormalMap')
            m.node_tree.links.new(node.outputs['Color'], norm.inputs['Color'])
            m.node_tree.links.new(norm.outputs['Normal'], bs.inputs['Normal'])
        else:
            m.node_tree.links.new(node.outputs['Color'], bs.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    return m


def material(name, color, rough, metal, out):
    if pbr:
        mat = pbr.material('green_metal', name=name, color=color, roughness=rough,
                           metallic=metal, bake=True, resolution=512,
                           cache_dir=out / 'materials')
    else:
        rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
        mat = image_material(name, rgb, rough, metal, out)
    # Add sparse directional hairline scratches directly to portable texture maps.
    # Copy baked images so shared helper cache files stay untouched.
    for tex in [n for n in mat.node_tree.nodes if n.type == 'TEX_IMAGE']:
        im = tex.image.copy()
        tex.image = im
        channel = tex.label
        width, height = im.size
        pixels = array('f', [0]) * (width * height * 4)
        im.pixels.foreach_get(pixels)
        rng = random.Random(531)
        for _ in range(38):
            x, y = rng.randrange(width), rng.randrange(height)
            length = rng.randrange(3, 24)
            slope = rng.choice((-.2, .15, .4))
            for j in range(length):
                px, py = (x + j) % width, (y + int(j * slope)) % height
                idx = (py * width + px) * 4
                if channel == 'normal':
                    pixels[idx:idx+3] = array('f', [.46, .56, .994])
                elif channel == 'roughness':
                    pixels[idx:idx+3] = array('f', [.57, .57, .57])
                else:
                    for c in range(3):
                        pixels[idx+c] = pixels[idx+c] * .7 + .075
        im.pixels.foreach_set(pixels)
        im.update()
        im.filepath_raw = str(out / 'materials' / (name + '-' + channel + '.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
    return mat


def mesh_grid(name, rings, root, mats, indices=None, segments=N):
    verts = [tuple(v) for ring in rings for v in ring]
    faces, uvs = [], []
    for i in range(len(rings)-1):
        for j in range(segments):
            k = (j + 1) % segments
            faces.append((i*segments+j, i*segments+k, (i+1)*segments+k, (i+1)*segments+j))
            uvs.append(((j/segments, i/(len(rings)-1)), ((j+1)/segments, i/(len(rings)-1)),
                        ((j+1)/segments, (i+1)/(len(rings)-1)), (j/segments, (i+1)/(len(rings)-1))))
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    root.users_collection[0].objects.link(obj)
    obj.parent = root
    obj['asset_id'] = root['asset_id']
    for m in mats:
        data.materials.append(m)
    uv = data.uv_layers.new(name='UVMap')
    for poly, coords in zip(data.polygons, uvs):
        poly.use_smooth = True
        if indices:
            poly.material_index = indices[poly.index // segments]
        for loop, co in zip(poly.loop_indices, coords):
            uv.data[loop].uv = co
    return obj


def radial(center, angle, radius, theta):
    c = Vector(center)
    a = Vector((math.cos(angle), 0, -math.sin(angle)))
    b = Vector((0, 1, 0))
    return c + radius * (a * math.cos(theta) + b * math.sin(theta))


def lathe(name, profile, center, angle, root, mat, segments=N):
    tangent = Vector((math.sin(angle), 0, math.cos(angle)))
    rings = [[radial(Vector(center) + tangent*z, angle, r, j*TAU/segments)
              for j in range(segments)] for r, z in profile]
    return mesh_grid(name, rings, root, [mat], segments=segments)


def collar(name, center, angle, root, green, radius=1, half=.15):
    # Closed annular section with chamfered/rolled outer and inner lips.
    bevel = min(.045, half*.42)
    p = [(.73,-half), (radius-bevel,-half), (radius-.012,-half+bevel*.45),
         (radius,-half+bevel), (radius,half-bevel), (radius-.012,half-bevel*.45),
         (radius-bevel,half), (.77,half), (.738,half-bevel*.5), (.73,half-bevel), (.73,-half)]
    return lathe(name, p, center, angle, root, green)


def joint(center, angle, root, green, iron):
    collar('Flange lower casting', Vector(center)-Vector((math.sin(angle),0,math.cos(angle)))*.065,
           angle, root, green, radius=.945, half=.055)
    collar('Flange upper casting', Vector(center)+Vector((math.sin(angle),0,math.cos(angle)))*.065,
           angle, root, green, radius=.945, half=.055)
    lathe('Recessed graphite gasket', [(.835,-.012),(.923,-.012),(.923,.012),(.835,.012),(.835,-.012)],
          center, angle, root, iron)
    tangent = Vector((math.sin(angle),0,math.cos(angle)))
    for j in range(8):
        c = radial(center, angle, .889, TAU*(j+.5)/8) + tangent*.12
        lathe('Hex flange bolt %02d' % j, [(.0,0),(.041,0),(.049,.012),(.049,.043),(.039,.055),(0,.055)],
              c, angle, root, iron, segments=6)


def body(path, root, green, dark):
    rings, indices = [], []
    # Continuous outer skin, annular terminal edge, reversed inner bore, base annulus.
    for interior, samples in ((False,path),(True,list(reversed(path)))):
        for i,(center,angle) in enumerate(samples):
            radius = .735 if interior else .84
            ring = []
            for j in range(N):
                theta = j*TAU/N
                # Small bounded cast undulations, vanishing at terminal seams.
                wobble = 0 if interior else .0018*math.sin(theta*7+i*.7)*math.sin(math.pi*i/max(1,len(path)-1))
                ring.append(radial(center,angle,radius+wobble,theta))
            rings.append(ring)
    rings.append(rings[0])
    count = len(path)
    indices = [0 if i < count else 1 for i in range(len(rings)-1)]
    mesh_grid('Continuous cast shell and open bore', rings, root, [green,dark], indices)


def make_asset(asset_id, mats):
    green, dark, iron = mats
    collection = bpy.data.collections.new(asset_id)
    bpy.context.scene.collection.children.link(collection)
    root = bpy.data.objects.new(asset_id, None)
    collection.objects.link(root)
    root['asset_id'] = asset_id
    root['units'] = '1 unit = 16 NES pixels; Z up; front -Y'
    if asset_id == 'pipe-short':
        path = [((0,0,z),0) for z in (0,.12,.3,.55,.8,1.08,1.22,1.43)]
        body(path,root,green,dark)
        collar('Thick rolled mouth', (0,0,1.34),0,root,green,half=.16)
        joint((0,0,.28),0,root,green,iron)
    else:
        path = [((0,0,z),0) for z in (0,.2,.38,.55)]
        for i in range(1,21):
            t = math.pi*.5*i/20
            path.append(((1.1*(1-math.cos(t)),0,.55+1.1*math.sin(t)),t))
        path += [((x,0,1.65),math.pi/2) for x in (1.3,1.5,1.68)]
        body(path,root,green,dark)
        collar('Horizontal rolled mouth',(1.55,0,1.65),math.pi/2,root,green,half=.16)
        joint((0,0,.28),0,root,green,iron)
    objects = list(root.children)
    for ob in objects:
        bm = bmesh.new()
        bm.from_mesh(ob.data)
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-7)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-8)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(ob.data)
        bm.free()
        ob.data.update()
    points = [v.co.copy() for ob in objects for v in ob.data.vertices]
    low = Vector(tuple(min(p[k] for p in points) for k in range(3)))
    high = Vector(tuple(max(p[k] for p in points) for k in range(3)))
    offset = Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    for ob in objects:
        for v in ob.data.vertices:
            v.co -= offset
    dims = list(high-low)
    root['nominal_dimensions'] = dims
    return root, objects, dims


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out = Path(args.out).expanduser().resolve()
    (out/'models').mkdir(parents=True,exist_ok=True)
    (out/'materials').mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    mats = [material('Cast green enamel','287C4A',.32,.28,out),
            material('Dark unglazed bore','14231B',.86,.15,out),
            material('Oxidized flange hardware','424744',.57,.78,out)]
    entries, roots = [], []
    for asset_id in ('pipe-elbow','pipe-short'):
        root, objects, dims = make_asset(asset_id,mats)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in [root]+objects:
            ob.select_set(True)
        bpy.context.view_layer.objects.active = root
        target = out/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,
                                  export_extras=True,export_apply=True,export_materials='EXPORT',
                                  export_image_format='AUTO',export_yup=True)
        entry = {'asset_id':asset_id,'path':f'models/{asset_id}.glb',
                 'nominal_dimensions':dict(zip(('x','y','z'),dims)),
                 'materials':[m.name for m in mats],
                 'mesh_features':['64-sided hollow cast barrel','continuous inward-facing bore',
                                  'rolled annular mouth with beveled section','paired flange rings',
                                  'recessed gasket and eight hex bolts','UV mapped baked PBR scratches',
                                  'bounded geometric casting undulations'],
                 'triangles':sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in objects),
                 'source_basis':SOURCE,'known_quality_limitations':LIMITATIONS}
        if pbr:
            entry['glb_inspection'] = pbr.inspect_glb(target)
        entries.append(entry)
        roots.append(root)
    for i,root in enumerate(roots):
        root.location.x = i*4
    for im in bpy.data.images:
        if im.source == 'FILE' and not im.packed_file:
            im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    manifest = {'assets':entries,'coordinate_contract':'Z up; -Y front; bottom-center origin; glTF Y up',
                'material_backend':'pbr_common baked at 512' if pbr else 'deterministic 512px image fallback',
                'style_contract':json.loads((SHARED/'design/style.json').read_text()) if (SHARED/'design/style.json').exists() else {'material':'cast green enamel'},
                'scope':'Two variants using 2-unit rim diameter. pipe-green baseline is not authored by this job.'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__ == '__main__':
    main()
