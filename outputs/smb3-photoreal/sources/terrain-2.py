"""Deterministic editable terrain family. Execute only in the central Blender queue."""
import argparse
import json
import math
import random
import struct
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

IDS = ['ground-snow', 'ground-stone', 'ground-wood']
SOURCE = {
    'ground-snow': ('Tile_Layout_TS4_TS12-35', 'TILE12_SNOWBLOCK_UM', 'binary-metatile-aff0fcc9032781b3e828'),
    'ground-stone': ('Tile_Layout_TS18-80', 'TILE18_BRICKFLOOR', 'binary-metatile-74301bee8cfabbd00713'),
    'ground-wood': ('Tile_Layout_TS4_TS12-75', 'TILE4_LONGWOOD_M', 'binary-metatile-c2afb31ee45bc5564ce2'),
}
WARNINGS = []
ROOT = None
COLLECTION = None
TAU = 2 * math.pi


def texture_material(name, color, roughness, out, wood=False, metallic=0):
    """Periodic image PBR fallback; no procedural runtime shader dependencies."""
    n = 512
    base = tuple(int(color[i:i+2], 16) / 255 for i in (0, 2, 4))
    heights = []
    for y in range(n):
        v = y / n
        for x in range(n):
            u = x / n
            fine = math.sin(TAU * (67*u + 31*v)) * math.sin(TAU * (43*v - 19*u))
            if wood:
                bend = .20 * math.sin(TAU*u) + .09 * math.sin(TAU*(2*u+v))
                grain = math.sin(TAU*(39*v + bend))
                h = .5 + .20*grain + .12*math.sin(TAU*(83*v + bend*2)) + .04*fine
            else:
                h = .5 + .15*math.sin(TAU*(7*u+3*v))*math.cos(TAU*(5*v-2*u)) + .12*fine
            heights.append(h)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bs = nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = metallic
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                h = heights[y*n+x]
                if channel == 'basecolor':
                    rgb = [min(1, c*(.72+.40*h)) for c in base]
                elif channel == 'roughness':
                    rgb = [max(.1, min(1, roughness + (h-.5)*.25))]*3
                else:
                    dx = (heights[y*n+(x+1)%n]-heights[y*n+(x-1)%n]) * (1.7 if wood else .7)
                    dy = (heights[((y+1)%n)*n+x]-heights[((y-1)%n)*n+x]) * (1.7 if wood else .7)
                    v = Vector((-dx, -dy, 1)).normalized()
                    rgb = [v[i]*.5+.5 for i in range(3)]
                pixels.extend((*rgb, 1))
        im = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels)
        im.filepath_raw = str(out / 'materials' / (name+'_'+channel+'.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = nodes.new('ShaderNodeTexImage'); tex.image = im; tex.extension = 'REPEAT'
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bs.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], bs.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'Deterministic periodic raster maps'
    return mat


def material(name, kind, color, rough, out, wood=False, metallic=0):
    if pbr and not wood:
        try:
            return pbr.material(kind, name=name, color=color, roughness=rough,
                                metallic=metallic, bake=True, resolution=512,
                                cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(name+': shared bake failed; raster fallback: '+str(exc))
    return texture_material(name, color, rough, out, wood, metallic)


def mesh(name, verts, faces, mat, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces); data.update()
    obj = bpy.data.objects.new(name, data); COLLECTION.objects.link(obj)
    obj.parent = ROOT; obj['asset_id'] = ROOT['asset_id']
    data.materials.append(mat)
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = smooth
        normal = poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        for li in poly.loop_indices:
            co = data.vertices[data.loops[li].vertex_index].co
            # Grain U follows X on the top and front; physical texture scale in units.
            if axis == 2: pair = (co.x, co.y)
            elif axis == 1: pair = (co.x, co.z)
            else: pair = (co.y, co.z)
            uv.data[li].uv = pair
    return obj


def box(name, lo, hi, mat, bevel=.015):
    x,y,z=lo; X,Y,Z=hi
    obj=mesh(name,[(x,y,z),(X,y,z),(X,Y,z),(x,Y,z),(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],
             [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)],mat)
    if bevel:
        mod=obj.modifiers.new('Worn edge bevel', 'BEVEL'); mod.width=bevel; mod.segments=2
    return obj


def slab(name, x0,x1,y0,y1,bottom,top,mat,nx=32,ny=12,smooth=False):
    """Closed regular-grid slab with independently sculpted top and bottom."""
    verts=[]
    for fn in (bottom,top):
        for j in range(ny+1):
            y=y0+(y1-y0)*j/ny
            for i in range(nx+1):
                x=x0+(x1-x0)*i/nx; verts.append((x,y,fn(x,y)))
    count=(nx+1)*(ny+1); faces=[]
    for j in range(ny):
        for i in range(nx):
            a=j*(nx+1)+i; b=a+1; c=b+nx+1; d=a+nx+1
            faces.extend([(d,c,b,a),(a+count,b+count,c+count,d+count)])
    boundary=list(range(nx+1))+[j*(nx+1)+nx for j in range(1,ny+1)]+[ny*(nx+1)+i for i in range(nx-1,-1,-1)]+[j*(nx+1) for j in range(ny-1,0,-1)]
    for a,b in zip(boundary,boundary[1:]+boundary[:1]): faces.append((a,b,b+count,a+count))
    return mesh(name,verts,faces,mat,smooth)


def pebble(name, center, size, mat, seed):
    rng=random.Random(seed); verts=[]; sides=7
    for z,r in [(-.5,.5),(-.20,1),(.22,.85),(.5,.32)]:
        for i in range(sides):
            a=TAU*i/sides; jitter=rng.uniform(.84,1.12)
            verts.append((center[0]+size[0]*r*math.cos(a)*jitter,
                          center[1]+size[1]*r*math.sin(a)*jitter,center[2]+size[2]*z))
    faces=[tuple(reversed(range(sides))),tuple(range(3*sides,4*sides))]
    for row in range(3):
        for i in range(sides):
            a=row*sides+i; b=row*sides+(i+1)%sides
            faces.append((a,b,b+sides,a+sides))
    return mesh(name,verts,faces,mat)


def snow(m):
    def wave(x,y): return .012*math.cos(TAU*x/4)+.006*math.sin(TAU*y)
    def seam(x,y): return .70+wave(x,y)+.011*math.sin(TAU*(x*2+y))
    slab('Dense basal snow',-2,2,-1,1,lambda x,y:0,lambda x,y:.46+wave(x,y),m['ice'],24,10)
    slab('Compressed middle strata',-2,2,-1,1,lambda x,y:.46+wave(x,y),seam,m['snow'],32,12)
    slab('Wind crust band',-2,2,-1,1,seam,lambda x,y:seam(x,y)+.026,m['ice'],32,12)
    slab('Soft compacted snow cap',-2,2,-1,1,lambda x,y:seam(x,y)+.026,
         lambda x,y:.978+.012*math.cos(TAU*x/4)+.006*math.sin(TAU*y)+.004*math.cos(TAU*(2*x+y)),m['snow'],40,16,True)
    rng=random.Random(64)
    for i in range(22):
        x=rng.uniform(-1.86,1.86); z=rng.uniform(.06,.38)
        pebble('Entrained grit %02d'%i,(x,-.981,z),(.022,.017,.03),m['stone'],i)
    return ['Four closed sculpted snow strata', 'Periodic cap and compression seams', '22 embedded angular grit grains']


def stone(m):
    box('Recessed continuous mortar bed',(-2,-.95,0),(2,.95,.96),m['mortar'],.006)
    rng=random.Random(103)
    for row in range(3):
        # Clipped half blocks close the staggered course at modular boundaries.
        edges=[-2,-1,0,1,2] if row%2==0 else [-2,-1.5,-.5,.5,1.5,2]
        for col,(a,b) in enumerate(zip(edges,edges[1:])):
            for side in (-1,1):
                y0,y1=(-1,-.49) if side<0 else (.49,1)
                z0=row*.32+.012; z1=(row+1)*.32-.012
                obj=box('Course %d block %d side %d'%(row,col,side),(a+.009,y0,z0),(b-.009,y1,z1),m['stone' if (row+col)%3 else 'stone2'],.025)
                # Deterministic corner erosion, retained bevel modifier; never beyond envelope.
                for v in obj.data.vertices:
                    v.co.x += rng.uniform(-.007,.007)
                    if abs(v.co.y)==1: v.co.y -= side*rng.uniform(0,.014)
                obj.data.update()
    for j in range(2):
        for i in range(4):
            slab('Worn coping %d %d'%(i,j),-2+i+.008,-1+i-.008,-1+j+.008,j-.008,
                 lambda x,y:.943,lambda x,y:.989+.006*math.sin(TAU*x)*math.sin(TAU*y),m['stone2'],8,5)
    # Inset angular spalls along the mortar give exposed aggregate at genuine depth.
    for i in range(30):
        x=rng.uniform(-1.93,1.93); z=rng.choice([.32,.64])+rng.uniform(-.008,.008)
        pebble('Mortar aggregate %02d'%i,(x,-.958,z),(.023,.021,.021),m['stone2'],400+i)
    return ['Three staggered courses with individual beveled masonry blocks', 'Eight relief-sculpted coping slabs', 'Recessed mortar and 30 angular aggregate pieces']


def wood(m):
    # Structural timber body fills the nominal segment; planks remain separate editable meshes.
    for j in range(4):
        y0=-1+j*.5+.006; y1=y0+.488
        def top(x,y,j=j):
            v=(y-(-1+j*.5))/.5
            crown=.008*math.sin(math.pi*v)
            grooves=sum(.009*math.exp(-((v-c-.014*math.sin(TAU*x/4))/.022)**2) for c in (.23,.68))
            return .986+crown-grooves
        obj=slab('Aged deck plank %d'%j,-2,2,y0,y1,lambda x,y:.78,top,m['wood' if j%2 else 'wood2'],40,10)
        mod=obj.modifiers.new('Soft plank edges','BEVEL'); mod.width=.004; mod.segments=2; mod.angle_limit=.7
    for side in (-1,1):
        for row in range(2):
            y0,y1=(-1,-.70) if side<0 else (.70,1)
            box('Long grain fascia %d %d'%(side,row),(-2,y0,.02+row*.375),(2,y1,.375+row*.375),m['wood'],.018)
    for x in (-1.65,0,1.65):
        box('Under deck cross bearer', (x-.13,-.71,0),(x+.13,.71,.79),m['wood2'],.014)
    # Pegs are low polygon ring meshes; flush heads and actual circular end grain geometry.
    for j in range(4):
        for x in (-1.65,0,1.65):
            y=-.75+j*.5
            verts=[]
            for z in (.975,.995):
                for k in range(10):
                    a=TAU*k/10; verts.append((x+.028*math.cos(a),y+.028*math.sin(a),z))
            faces=[tuple(reversed(range(10))),tuple(range(10,20))]
            faces.extend((k,(k+1)%10,(k+1)%10+10,k+10) for k in range(10))
            mesh('Flush oak dowel',verts,faces,m['wood2'])
    return ['Four subdivided planks with modeled longitudinal grain grooves', 'Four rounded fascia timbers and three structural bearers', 'Twelve flush timber dowels', 'Periodic grain image maps and open board joins']


def inspect_export(path):
    raw=path.read_bytes(); magic,version,total=struct.unpack_from('<III',raw)
    assert magic==0x46546C67 and version==2 and total==len(raw)
    size,kind=struct.unpack_from('<II',raw,12); assert kind==0x4E4F534A
    d=json.loads(raw[20:20+size])
    assert all('bufferView' in image for image in d.get('images',[])), 'External texture reference'
    for mat in d.get('materials',[]):
        assert 'baseColorTexture' in mat['pbrMetallicRoughness'], mat['name']
        assert 'metallicRoughnessTexture' in mat['pbrMetallicRoughness'], mat['name']
        assert 'normalTexture' in mat, mat['name']
    return {'embedded_images':len(d.get('images',[])), 'texture_checks':'passed'}


def main():
    global ROOT,COLLECTION
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(); parser.add_argument('--out',required=True)
    out=Path(parser.parse_args(args).out).resolve()
    (out/'models').mkdir(parents=True,exist_ok=True); (out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    style=json.loads((SHARED/'design/style.json').read_text()) if (SHARED/'design/style.json').exists() else {'units':'Z up, front -Y; root at floor'}
    mats={}
    specs=[('snow','stone','E6ECEA',.83),('ice','stone','AEBEC4',.61),('stone','stone','77796E',.88),('stone2','stone','959486',.83),('mortar','soil','646157',.97),('wood','soil','796047',.84),('wood2','soil','9A7E5D',.86)]
    for name,kind,color,rough in specs:
        mats[name]=material(name,kind,color,rough,out,wood=name.startswith('wood'))
    records=[]; roots=[]
    for asset_id,builder in zip(IDS,(snow,stone,wood)):
        COLLECTION=bpy.data.collections.new(asset_id); bpy.context.scene.collection.children.link(COLLECTION)
        ROOT=bpy.data.objects.new(asset_id,None); COLLECTION.objects.link(ROOT)
        ROOT['asset_id']=asset_id; ROOT['nominal_dimensions']=[4,2,1]; ROOT['root_convention']='bottom-center, Blender Z up, front -Y'
        features=builder(mats); objects=[ROOT]+list(ROOT.children)
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get(); triangles=0; points=[]
        for obj in ROOT.children:
            evaluated=obj.evaluated_get(deps); me=evaluated.to_mesh(); me.calc_loop_triangles(); triangles+=len(me.loop_triangles)
            points.extend(obj.matrix_world@v.co for v in me.vertices); evaluated.to_mesh_clear()
        bounds=[[min(v[i] for v in points) for i in range(3)],[max(v[i] for v in points) for i in range(3)]]
        assert abs(bounds[0][2])<.0001, (asset_id,'root floor',bounds)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects: obj.select_set(True)
        bpy.context.view_layer.objects.active=ROOT
        path=out/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_extras=True,export_apply=True,export_yup=True,
                                  export_materials='EXPORT',export_image_format='AUTO')
        check=inspect_export(path)
        definition,symbol,clip=SOURCE[asset_id]
        records.append({'asset_id':asset_id,'path':str(Path('models')/path.name),
                        'nominaldimensions':{'width':4,'depth':2,'height':1},'bounds_blender':bounds,
                        'materials':sorted({slot.material.name for ob in ROOT.children for slot in ob.material_slots}),
                        'meshfeatures':features,'triangles':triangles,'export_validation':check,
                        'sourcebasis':{'catalog':'smb3-rom-assets/catalog/binary-assets.json','definition':definition,'symbol':symbol,'clip':clip,
                                       'interpretation':'Source modular silhouette; realistic material and structural details are authored interpretation.'},
                        'knownqualitylimitations':['Not rendered or visually inspected during authoring.', 'Tile pitch is 4 along X; end faces retained. Masonry bevel seams remain visible.', 'Snow uses opaque compacted crust, without volumetric scattering.' if asset_id=='ground-snow' else 'Surface wear is deterministic and repeats per segment.']})
        roots.append(ROOT)
    for i,root in enumerate(roots): root.location.x=i*5
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file: im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':records,'style_contract':style,'warnings':WARNINGS,'library':'library.blend'},indent=2)+'\n')

if __name__=='__main__':
    main()
