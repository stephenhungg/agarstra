"""Terrain-family authoring for Blender 4.5. Run only through the central queue."""
import argparse
import json
import math
import random
import sys
from array import array
from pathlib import Path

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.path.insert(0, str(SHARED / 'tools'))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

ASSETS = ('ground-grass', 'ground-soil', 'ground-sand')
SOURCE = {
    'ground-grass': {'definition': 'Tile_Layout_TS1-83', 'symbol': 'TILE1_GROUNDTM', 'image': 'binary-clips/binary-metatile-a685531faf40b75b48d8.png', 'context': 'context-1-0-1'},
    'ground-soil': {'definition': 'Tile_Layout_TS1-84', 'symbol': 'TILE1_GROUNDMM', 'image': 'binary-clips/binary-metatile-7703daa188dd301288d1.png', 'context': 'context-1-0-1'},
    'ground-sand': {'definition': 'Tile_Layout_TS9-86', 'symbol': 'TILE9_BRICK_UM', 'image': 'binary-clips/binary-metatile-86d2d767fa6e41f5dc32.png', 'context': 'context-9-0-9'},
}
WARNINGS = []


def linear(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def fallback_material(name, color, roughness, out, seed):
    """Deterministic tileable image PBR; no shader-only procedural dependencies."""
    n = 512
    rng = random.Random(seed)
    phases = [rng.random() * math.tau for _ in range(5)]
    h = array('f')
    for y in range(n):
        v = y / n * math.tau
        for x in range(n):
            u = x / n * math.tau
            value = (.48 + .15 * math.sin(3*u + 2*v + phases[0])
                     + .10 * math.sin(9*u - 7*v + phases[1])
                     + .06 * math.sin(29*u + 31*v + phases[2])
                     + .10 * (rng.random() - .5))
            h.append(value)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    bsdf.inputs['Roughness'].default_value = roughness
    mat.diffuse_color = (*[linear(c) for c in rgb], 1)
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                i = y*n+x
                if channel == 'basecolor':
                    shade = .76 + h[i] * .48
                    values = tuple(linear(min(.99, c*shade)) for c in rgb)
                elif channel == 'roughness':
                    r = max(.05, min(1, roughness + (h[i]-.5)*.2))
                    values = (r, r, r)
                else:
                    dx = (h[y*n+(x+1)%n]-h[y*n+(x-1)%n]) * 1.4
                    dy = (h[((y+1)%n)*n+x]-h[((y-1)%n)*n+x]) * 1.4
                    normal = Vector((-dx, -dy, 1)).normalized()
                    values = tuple(a*.5+.5 for a in normal)
                pixels.extend((*values, 1))
        image = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(out / 'materials' / (name+'_'+channel+'.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = image
        tex.extension = 'REPEAT'
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic pixel synthesis fallback'
    return mat


def material(kind, name, color, roughness, out, seed):
    if pbr is not None:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                bake=True, resolution=512, cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared baker failed; used image fallback: {exc}')
    return fallback_material(name, color, roughness, out, seed)


def mesh_object(name, vertices, faces, materials, parent, indices=None, smooth=False, uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    parent.users_collection[0].objects.link(obj)
    obj.parent = parent
    for mat in materials:
        data.materials.append(mat)
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = smooth
        if indices is not None:
            poly.material_index = indices[poly.index]
        normal = poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        for li in poly.loop_indices:
            vi = data.loops[li].vertex_index
            co = data.vertices[vi].co
            # Object-space metric UVs, integer periods at repeat boundaries.
            uv.data[li].uv = uvs[vi] if uvs else ((co.x, co.y) if axis == 2 else ((co.x, co.z) if axis == 1 else (co.y, co.z)))
    obj['asset_id'] = parent['asset_id']
    return obj


def top_height(kind, x, y):
    # Periodic across both 4 m and 2 m tile boundaries, including first derivatives.
    u, v = math.tau*(x+2)/4, math.tau*(y+1)/2
    if kind == 'ground-sand':
        phase = 9*v + .45*math.sin(2*u)
        return .973 + .014*math.sin(phase) + .004*math.sin(2*phase+.6)
    return (.846 if kind == 'ground-grass' else .960) + .008*math.sin(3*u+2*v) + .005*math.cos(7*u-3*v)


def terrain_body(kind, parent, mats):
    nx, ny = (48, 48) if kind == 'ground-sand' else (40, 20)
    verts = []
    for j in range(ny+1):
        y = -1+2*j/ny
        for i in range(nx+1):
            x = -2+4*i/nx
            verts.append((x, y, top_height(kind, x, y)))
    faces, slots = [], []
    for j in range(ny):
        for i in range(nx):
            a = j*(nx+1)+i
            faces.append((a, a+1, a+nx+2, a+nx+1)); slots.append(2)
    # CCW perimeter seen from above, shared with the top grid.
    perimeter = list(range(nx+1))
    perimeter += [j*(nx+1)+nx for j in range(1,ny+1)]
    perimeter += [ny*(nx+1)+i for i in range(nx-1,-1,-1)]
    perimeter += [j*(nx+1) for j in range(ny-1,0,-1)]
    prev = perimeter
    for level, z in enumerate((.78 if kind == 'ground-grass' else .84, .59, .29, .018, 0)):
        ring = []
        for vi in perimeter:
            x,y,_ = verts[vi]
            # Carved stratification undulates without changing X/Y mating planes.
            wave = (.014*math.sin(math.tau*(x+2)/4*3) + .009*math.cos(math.tau*(y+1)/2*2)) if z > .1 else 0
            ring.append(len(verts)); verts.append((x,y,z+wave))
        for k in range(len(ring)):
            b = (k+1)%len(ring)
            faces.append((prev[k],ring[k],ring[b],prev[b])); slots.append(1 if level in (0,2) else 0)
        prev = ring
    faces.append(tuple(reversed(prev))); slots.append(0)
    obj = mesh_object(kind+'_stratified_body',verts,faces,mats,parent,slots)
    for poly in obj.data.polygons[:nx*ny]:
        poly.use_smooth = True
    obj['feature'] = 'Continuous periodic heightfield, five exposed sediment courses, closed bottom'
    return obj


class Batch:
    def __init__(self):
        self.v, self.f, self.m, self.uv = [], [], [], []

    def clod(self, center, radii, rng, slot=0):
        """Low-poly weathered angular pebble, with chamfer-like shoulder rings."""
        start = len(self.v)
        angle = rng.random()*math.tau
        sides = 7
        jitter = [rng.uniform(.83, 1.12) for _ in range(sides)]
        for z, width in ((-.80,.52),(-.40,.96),(.38,1),(.82,.50)):
            for k in range(sides):
                a = angle+k*math.tau/sides
                self.v.append((center[0]+math.cos(a)*radii[0]*width*jitter[k],
                               center[1]+math.sin(a)*radii[1]*width*jitter[k],
                               center[2]+z*radii[2]))
        self.f.append(tuple(start+k for k in reversed(range(sides)))); self.m.append(slot)
        for j in range(3):
            for k in range(sides):
                a=start+j*sides+k; b=start+j*sides+(k+1)%sides
                self.f.append((a,b,b+sides,a+sides)); self.m.append(slot)
        self.f.append(tuple(start+3*sides+k for k in range(sides))); self.m.append(slot)

    def blade(self, x, y, z, h, width, angle, lean, slot):
        # Closed triangular-section blade with a tapered middle and pointed tip.
        start=len(self.v)
        dx,dy=math.cos(angle),math.sin(angle)
        for t,w in ((0,1),(.58,.64)):
            cx,cy=x+dx*lean*t*t,y+dy*lean*t*t
            for side,fold in ((-1,0),(0,.003),(1,0)):
                self.v.append((cx-dy*width*w*side+dx*fold*w,cy+dx*width*w*side+dy*fold*w,z+h*t))
                self.uv.append(((side+1)*.5,t))
        self.v.append((x+dx*lean,y+dy*lean,z+h));self.uv.append((.5,1))
        self.f.append((start+2,start+1,start)); self.m.append(slot)
        for k in range(3):
            b=(k+1)%3
            self.f.append((start+k,start+b,start+b+3,start+k+3));self.m.append(slot)
            self.f.append((start+k+3,start+b+3,start+6));self.m.append(slot)


def details(kind, root, soil, rock, leaf, dry):
    rng=random.Random({'ground-grass':2301,'ground-soil':2302,'ground-sand':2303}[kind])
    stones=Batch()
    # Angular embedded clods on top, with individual mesh islands for editing.
    count=14 if kind=='ground-sand' else 32
    for i in range(count):
        x,y=rng.uniform(-1.88,1.88),rng.uniform(-.88,.88)
        size=rng.uniform(.023,.060) if kind=='ground-sand' else rng.uniform(.032,.08)
        stones.clod((x,y,top_height(kind,x,y)-.012), (size,size*.68,.018 if kind=='ground-sand' else .03),rng,1 if i%3==0 else 0)
    if kind!='ground-sand':
        for i in range(28):
            x=rng.uniform(-1.84,1.84); z=rng.uniform(.12,.77)
            stones.clod((x,-.980,z),(rng.uniform(.025,.075),.024,rng.uniform(.024,.052)),rng,1 if i%4==0 else 0)
    mesh_object(kind+'_embedded_aggregate',stones.v,stones.f,[soil,rock],root,stones.m)
    if kind=='ground-grass':
        blades=Batch()
        # Stratified jitter gives broad coverage; no cards, alpha cutouts or particles.
        for j in range(15):
            for i in range(32):
                x=-1.94+(i+rng.uniform(.15,.85))*3.88/32
                y=-.94+(j+rng.uniform(.15,.85))*1.88/15
                h=rng.uniform(.070,.137)
                z=top_height(kind,x,y)-.008
                blades.blade(x,y,z,h,rng.uniform(.008,.017),rng.random()*math.tau,rng.uniform(.01,.034),1 if rng.random()<.18 else 0)
        obj=mesh_object(kind+'_480_folded_blades',blades.v,blades.f,[leaf,dry],root,blades.m,uvs=blades.uv)
        obj['feature']='480 closed, curved, triangular-section blades; editable mesh islands'


def validate_export(path):
    import struct
    raw=path.read_bytes()
    magic,version,total=struct.unpack_from('<III',raw,0)
    assert magic==0x46546C67 and version==2 and total==len(raw)
    length,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4E4F534A
    doc=json.loads(raw[20:20+length])
    assert not doc.get('cameras'), 'GLB must not contain cameras'
    assert not doc.get('extensions',{}).get('KHR_lights_punctual'), 'GLB must not contain lights'
    assert doc.get('images') and all('bufferView' in i for i in doc['images'])
    for mat in doc.get('materials',[]):
        assert 'baseColorTexture' in mat.get('pbrMetallicRoughness',{})
        assert 'metallicRoughnessTexture' in mat.get('pbrMetallicRoughness',{})
        assert 'normalTexture' in mat
    return {'bytes':len(raw),'embedded_images':len(doc['images']),'mesh_count':len(doc.get('meshes',[]))}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=args.out.resolve()
    (out/'models').mkdir(parents=True,exist_ok=True)
    (out/'materials').mkdir(parents=True,exist_ok=True)
    # Only the queue invokes this script in an isolated background Blender session.
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj,do_unlink=True)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    scene.unit_settings.scale_length=1
    earth=material('soil','Earth_ochre','68513B',.95,out,1)
    humus=material('soil','Humus_dark','3C3023',.98,out,2)
    turf=material('soil','Turf_moss','4A5630',.93,out,3)
    stone=material('stone','Weathered_grit','918370',.85,out,4)
    leaf=material('leaf','Grass_olive','526C31',.73,out,5)
    dry=material('leaf','Grass_dry_tips','8B834A',.82,out,6)
    sand=material('soil','Sand_quartz','C3A06A',.88,out,7)
    compact=material('soil','Sand_compacted','A68655',.94,out,8)
    roots=[];records=[]
    for asset_id in ASSETS:
        coll=bpy.data.collections.new(asset_id)
        scene.collection.children.link(coll)
        root=bpy.data.objects.new(asset_id,None)
        coll.objects.link(root)
        root['asset_id']=asset_id
        root['nominal_dimensions']= [4.,2.,1.]
        root['coordinate_contract']='Z up, front -Y, X right; bottom-center origin'
        root['source_basis']=json.dumps(SOURCE[asset_id])
        roots.append(root)
        mats=([compact,sand,sand] if asset_id=='ground-sand' else [earth,humus,turf if asset_id=='ground-grass' else earth])
        terrain_body(asset_id,root,mats)
        details(asset_id,root,sand if asset_id=='ground-sand' else earth,stone,leaf,dry)
        bpy.context.view_layer.update()
        objects=[root]+list(root.children)
        verts=[ob.matrix_world@v.co for ob in root.children for v in ob.data.vertices]
        lo=[min(v[k] for v in verts) for k in range(3)]
        hi=[max(v[k] for v in verts) for k in range(3)]
        assert lo[2]>=-1e-6
        assert lo[0]>=-2.001 and hi[0]<=2.001 and lo[1]>=-1.01 and hi[1]<=1.001
        triangles=0
        for ob in root.children:
            ob.data.calc_loop_triangles();triangles+=len(ob.data.loop_triangles)
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects:ob.select_set(True)
        bpy.context.view_layer.objects.active=root
        path=out/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_extras=True,export_apply=True,export_yup=True,
                                  export_materials='EXPORT',export_image_format='AUTO',export_texcoords=True)
        audit=validate_export(path)
        records.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb',
                        'nominal_dimensions':{'width':4,'height':1,'depth':2},
                        'actual_bounds_xyz':{'min':lo,'max':hi},'triangles':triangles,
                        'materials':sorted({m.name for ob in root.children for m in ob.data.materials}),
                        'mesh_features':['Closed layered substrate with metric UVs','Angular chamfered aggregate islands',
                                         '480 solid tapered grass blades' if asset_id=='ground-grass' else ('Periodic modeled sand ripples' if asset_id=='ground-sand' else 'Undulating compact soil surface and exposed embedded clods')],
                        'source_basis':{**SOURCE[asset_id],'catalog':'smb3-rom-assets/catalog/binary-assets.json',
                                        'interpretation':'Source tile silhouette and repeating ground role; material microstructure and depth are authored interpretation.'},
                        'known_quality_limitations':['Not visually reviewed until the central queue renders it.',
                                                    'Nominal 1 m envelope; surface height varies and grass blades end below 1 m.',
                                                    'Same-asset substrate joins tile in X/Y; scattered details are kept inside tile bounds. Cross-family upper edges differ.',
                                                    'Material swatches are 512 px. No scanned material source.',
                                                    'Interior cut faces retained for independent tile use.'],
                        'export_validation':audit})
    for i,root in enumerate(roots):root.location=(i*5,0,0)
    bpy.ops.object.select_all(action='DESELECT')
    for root in roots:root.select_set(True)
    bpy.context.view_layer.objects.active=roots[0]
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file:
            image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'schema':'terrain-family-v1','assets':records,
        'coordinates':'Blender XYZ width/depth/height; GLB Y-up; each export root at origin',
        'style_contract':str(SHARED/'design/style.json'),'warnings':WARNINGS},indent=2)+'\n')


if __name__=='__main__':
    main()
