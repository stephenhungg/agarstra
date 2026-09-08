"""Blender 4.5 asset authoring; executed only by the central build queue."""
import argparse
import json
import math
import sys
from pathlib import Path
from array import array
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
ASSETS = {}
CURRENT = None
OUT = None
WARNINGS = []


def material(name, color, roughness, bump=.01, kind='stone'):
    if pbr is not None:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                bump=bump, metallic=0, bake=True, resolution=512,
                                cache_dir=OUT / 'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed; image fallback: {exc}')
    # Fully image-backed deterministic fallback, including tangent-space normals.
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    size = 512
    paths = {}
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(size):
            for x in range(size):
                u, v = TAU*x/size, TAU*y/size
                grain = math.sin(43*u + 2*math.sin(7*v))*math.cos(37*v)
                broad = math.sin(5*u)*math.sin(4*v)
                if channel == 'basecolor':
                    values = [max(0, min(1, c*(.94+.04*broad+.02*grain))) for c in rgb]
                elif channel == 'roughness':
                    values = [max(.04, min(1, roughness+.04*grain))]*3
                else:
                    nx = bump*4*math.cos(43*u+2*math.sin(7*v))*math.cos(37*v)
                    ny = -bump*4*math.sin(43*u+2*math.sin(7*v))*math.sin(37*v)
                    normal = Vector((nx, ny, 1)).normalized()
                    values = [n*.5+.5 for n in normal]
                pixels.extend((*values, 1))
        im = bpy.data.images.new(name+'_'+channel, width=size, height=size)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels)
        im.filepath_raw = str(OUT/'materials'/f'{name}_{channel}.png')
        im.file_format = 'PNG'
        im.save(); im.pack()
        paths[channel] = im.filepath_raw
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage'); tex.image = im
        if channel == 'normal':
            normal_node = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            mat.node_tree.links.new(tex.outputs['Color'], normal_node.inputs['Color'])
            mat.node_tree.links.new(normal_node.outputs['Normal'], bs.inputs['Normal'])
        else:
            mat.node_tree.links.new(tex.outputs['Color'], bs.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_files'] = json.dumps(paths)
    return mat


def mesh(name, vertices, faces, mat, uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces); data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = CURRENT
    obj['asset_id'] = CURRENT['asset_id']
    data.materials.append(mat)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        for j, li in enumerate(poly.loop_indices):
            vi = data.loops[li].vertex_index
            layer.data[li].uv = uv[vi] if uv else ((j == 1 or j == 2), (j >= 2))
    # Weld geometric seams/poles while retaining independent per-loop UVs.
    bm = bmesh.new(); bm.from_mesh(data)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=1e-7)
    bm.to_mesh(data); bm.free(); data.update()
    ASSETS[CURRENT['asset_id']].append(obj)
    return obj


def grid(name, rows, mat, closed=True):
    n = len(rows[0]); verts = [v for row in rows for v in row]
    # Duplicated seam gives continuous UVs without wrap interpolation.
    if closed:
        rows = [r+[r[0]] for r in rows]; n += 1
        verts = [v for row in rows for v in row]
    faces = [(i*n+j, i*n+j+1, (i+1)*n+j+1, (i+1)*n+j)
             for i in range(len(rows)-1) for j in range(n-1)]
    uv = [(j/(n-1), i/(len(rows)-1)) for i in range(len(rows)) for j in range(n)]
    return mesh(name, verts, faces, mat, uv)


def ellipsoid(name, center, scale, mat, n=28, rings=16):
    rows = []
    for i in range(rings+1):
        a = math.pi*i/rings
        rows.append([(center[0]+scale[0]*math.sin(a)*math.cos(TAU*j/n),
                      center[1]+scale[1]*math.sin(a)*math.sin(TAU*j/n),
                      center[2]+scale[2]*math.cos(a)) for j in range(n)])
    # Reverse latitude direction for outward normals.
    return grid(name, rows[::-1], mat)


def sweep(name, points, radii, mat, n=12, flatten=1):
    rows = []
    for i, p in enumerate(points):
        p = Vector(p)
        tangent = Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize()
        ref = Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
        a = tangent.cross(ref).normalized(); b = tangent.cross(a).normalized()
        rows.append([tuple(p+radii[i]*(math.cos(TAU*j/n)*a + flatten*math.sin(TAU*j/n)*b)) for j in range(n)])
    rows.insert(0, [tuple(points[0])]*n); rows.append([tuple(points[-1])]*n)
    return grid(name, rows, mat)


def bone(name, start, end, radius, mat):
    a, b = Vector(start), Vector(end)
    ts = [0,.08,.2,.35,.65,.8,.92,1]
    return sweep(name, [tuple(a.lerp(b,t)) for t in ts],
                 [radius*r for r in (.55,1.12,1.05,.62,.62,1.05,1.12,.55)], mat)


def loop(name, points, radius, mat, n=10):
    return sweep(name, points+[points[0],points[1]], [radius]*(len(points)+2), mat, n)


def root(asset):
    global CURRENT
    CURRENT = bpy.data.objects.new(asset, None)
    bpy.context.collection.objects.link(CURRENT)
    CURRENT['asset_id'] = asset
    CURRENT['front'] = '-Y'
    CURRENT['units'] = '1 unit = 16 NES pixels'
    ASSETS[asset] = []
    return CURRENT


def carve(target, center, scale, name):
    cutter = ellipsoid('temporary_cutter', center, scale, M['dark'], n=24, rings=16)
    mod = target.modifiers.new(name, 'BOOLEAN'); mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
    bpy.context.view_layer.objects.active=target
    bpy.ops.object.modifier_apply(modifier=mod.name)
    ASSETS[CURRENT['asset_id']].remove(cutter)
    bpy.data.objects.remove(cutter, do_unlink=True)


def dry_bones():
    root('dry-bones')
    # Compact shell, open skeletal torso, broad muzzle and large shoes.
    ellipsoid('Shell continuous domed carapace', (0,.22,1.02), (.48,.31,.59), M['shell'])
    rim = [( .47*math.cos(TAU*i/48), .035, 1.02+.58*math.sin(TAU*i/48)) for i in range(48)]
    loop('Ivory shell rolled rim', rim, .052, M['bone'])
    # Raised scutes on back, each with a bevel-like second ring and recessed seams.
    for row, z in enumerate((.69,1.0,1.31)):
        for col, x in enumerate((-.235,.235) if row!=1 else (-.29,0,.29)):
            r = .18 if row!=1 else .155
            rings=[]
            for size, lift in ((1,0),(.90,.023),(.16,.037)):
                ring=[]
                for j in range(6):
                    xx=x+r*size*math.cos(TAU*j/6); zz=z+r*size*math.sin(TAU*j/6)
                    yy=.22+.31*math.sqrt(max(.02,1-(xx/.49)**2-((zz-1.02)/.61)**2))+lift
                    ring.append((xx,yy,zz))
                rings.append(ring)
            rings.append([(x,.22+.31*math.sqrt(max(.02,1-(x/.49)**2-((z-1.02)/.61)**2))+.037,z)]*6)
            grid(f'Shell scute {row}-{col}',rings[::-1],M['scute'])
    bone('Spinal column',(0,.035,.53),(0,.035,1.57),.095,M['bone'])
    for z in (.73,.88,1.03,1.18,1.33):
        ellipsoid('Vertebral articulation',(0,-.03,z),(.12,.105,.075),M['bone'],16,8)
        for s in (-1,1):
            sweep('Curved rib',[(0,.015,z+.025),(s*.21,-.08,z+.055),(s*.34,-.18,z),(s*.23,-.29,z-.08),(s*.08,-.31,z-.09)], [.045,.045,.042,.035,.028], M['bone'])
    bone('Sternum',(0,-.31,.81),(0,-.31,1.32),.065,M['bone'])
    ellipsoid('Pelvic girdle',(0,-.025,.57),(.30,.19,.12),M['bone'])
    for s in (-1,1):
        bone('Femur',(s*.22,0,.59),(s*.25,-.01,.36),.095,M['bone'])
        bone('Tibia',(s*.25,-.01,.36),(s*.27,-.08,.19),.075,M['bone'])
        ellipsoid('Broad charcoal shoe',(s*.28,-.17,.13),(.22,.36,.13),M['shell'])
        for k in (-1,0,1):
            sweep('Shoe toe embossed seam',[(s*.28+k*.07,-.47,.13),(s*.28+k*.075,-.36,.245),(s*.28+k*.075,-.25,.256)],[.009]*3,M['scute'],8)
        bone('Humerus',(s*.36,-.035,1.29),(s*.58,-.1,1.02),.072,M['bone'])
        bone('Ulna',(s*.58,-.1,1.02),(s*.62,-.34,1.09),.061,M['bone'])
        ellipsoid('Knuckle palm',(s*.62,-.36,1.1),(.11,.10,.09),M['bone'],16,10)
        for f in range(3):
            x=s*(.56+f*.065)
            sweep('Segmented curled finger',[(x,-.39,1.12),(x,-.48,1.1),(x,-.50,1.02),(x,-.44,1.0)],[.032,.034,.027,.019],M['bone'],8)
    skull = ellipsoid('Cranium with carved orbital sockets',(0,-.11,1.80),(.38,.31,.38),M['bone'],40,24)
    for s in (-1,1):
        carve(skull,(s*.165,-.37,1.90),(.13,.18,.17),'Deep orbital socket')
        ellipsoid('Recessed orbital darkness',(s*.165,-.275,1.9),(.095,.035,.133),M['dark'],24,14)
        ellipsoid('Amber eye ember',(s*.165,-.317,1.90),(.042,.026,.066),M['amber'],20,12)
    muzzle=ellipsoid('Broad skull muzzle',(0,-.43,1.65),(.34,.31,.205),M['bone'],32,18)
    for s in (-1,1):
        carve(muzzle,(s*.105,-.71,1.70),(.045,.07,.057),'Nasal aperture')
        ellipsoid('Nasal recess',(s*.105,-.68,1.70),(.03,.02,.042),M['dark'],12,8)
    ellipsoid('Mouth separation',(0,-.44,1.48),(.29,.26,.035),M['dark'])
    ellipsoid('Lower mandible',(0,-.44,1.43),(.31,.27,.065),M['bone'])
    for x in (-.22,-.11,0,.11,.22):
        bone('Blunt upper tooth',(x,-.66,1.54),(x,-.66,1.465),.04,M['bone'])
    # Narrow, actual raised fracture lines, editable individually.
    sweep('Cranial fracture',[(.02,-.27,2.135),(.07,-.32,2.08),(.035,-.355,2.05),(.08,-.38,2.005)],[.006]*4,M['scute'],6)


def boo():
    root('boo')
    # A continuous shell starts at the open lip and wraps to the back pole.
    n=64; rows=[]
    for i in range(33):
        t=i/32; a=.77+(math.pi-.77)*t
        rows.append([(.88*math.sin(a)*math.cos(TAU*j/n),
                      -.79*math.cos(a),
                      .95+.88*math.sin(a)*math.sin(TAU*j/n)-.13*(1-t)**5) for j in range(n)])
    grid('Continuous ghost envelope with open mouth',rows[::-1],M['ghost'])
    # Cavity shares the exact opening ring; it retreats inside, never covers a sphere.
    boundary=rows[0]
    inner=[]
    for r,depth in ((1,0),(.94,.055),(.79,.17),(.45,.28),(0,.31)):
        inner.append([(x*r,y+depth,.82+(z-.82)*r) for x,y,z in boundary])
    grid('Recessed mouth bowl',inner,M['mouth'])
    loop('Soft porcelain lip',boundary,.022,M['ghost'],10)
    for s in (-1,1):
        ellipsoid('Tall black eye',(s*.255,-.57,1.48),(.069,.043,.16),M['dark'],24,16)
        # Brow contour follows sphere surface and gives recognizable mischievous eyes.
        sweep('Slanted heavy brow',[(s*.12,-.58,1.60),(s*.23,-.58,1.66),(s*.34,-.54,1.68)],[.026,.034,.013],M['dark'],10)
        sweep('Pointed ghost arm',[(s*.72,.015,.97),(s*.88,-.015,1.04),(s*1.02,-.035,1.19),(s*1.06,-.04,1.27)],[.19,.15,.085,.004],M['ghost'],20, .72)
        sweep('Upper fang',[(s*.39,-.58,1.14),(s*.36,-.615,1.02),(s*.32,-.605,.94)],[.095,.060,.001],M['bone'],16)
    # Thick flattened taper, curled forward and downward from the throat.
    sweep('Protruding curved tongue',[(0,-.34,.60),(0,-.52,.52),(0,-.72,.44),(0,-.86,.45),(0,-.90,.52)], [.16,.23,.225,.15,.012], M['tongue'],28,.28)
    sweep('Tongue central groove',[(0,-.55,.585),(0,-.70,.509),(0,-.80,.501)],[.009,.009,.004],M['mouth'],8)
    sweep('Swept spectral tail',[(0,.58,.54),(.08,.83,.41),(.23,1.01,.42),(.35,1.11,.53)],[.28,.20,.11,.002],M['ghost'],24)


def finish_asset(asset):
    objects=ASSETS[asset]; parent=objects[0].parent
    bpy.context.view_layer.update()
    coords=[o.matrix_world @ Vector(v) for o in objects for v in o.bound_box]
    lo=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    hi=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    for o in objects:o.location+=shift
    bpy.context.view_layer.update()
    path=OUT/'models'/f'{asset}.glb'
    bpy.ops.object.select_all(action='DESELECT')
    parent.select_set(True)
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=parent
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                              export_extras=True,export_apply=True,export_yup=True,
                              export_materials='EXPORT',export_image_format='AUTO')
    mats=sorted({m.name for o in objects for m in o.data.materials})
    features = {
        'dry-bones':['Carved orbital and nasal cavities','Broad muzzle and toothed mandible','Five paired curved ribs, sternum and vertebrae','Waisted limb bones and curled finger phalanges','Domed shell with raised beveled scutes and rolled rim','Broad shoes with toe seams'],
        'boo':['Continuous round envelope with genuine front opening','Deep recessed mouth bowl and lip','Thick curved grooved tongue and tapered fangs','Tall eyes and slanted brows','Pointed arms and swept tail']}
    return {'asset_id':asset,'path':f'models/{asset}.glb','nominaldimensions':list(hi-lo),
            'dimension_axes':'Blender X/Y/Z; units=16 NES pixels', 'materials':mats,
            'meshfeatures':features[asset],
            'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in objects),
            'sourcebasis':{'catalog':'smb3-rom-assets/catalog/binary-assets.json',
                'descriptor':63 if asset=='dry-bones' else 47,
                'symbol':'OBJ_DRYBONES / ObjP3F' if asset=='dry-bones' else 'OBJ_BOO / ObjP2F',
                'source':'PRG/prg002.asm:435' if asset=='dry-bones' else 'PRG/prg002.asm:401',
                'interpretation':'Recognizable silhouette from user brief; catalog descriptor unresolved, not a verified sprite reconstruction.'},
            'knownqualitylimitations':['Stylized procedural interpretation; no anatomical photorealism claim.','Unrigged; components remain individually editable.','No Blender execution or visual inspection performed during code authoring.','Small intersections at anatomical joins; not a unified watertight fabrication mesh.']}


def main():
    global OUT, M
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).expanduser().resolve()
    (OUT/'models').mkdir(parents=True,exist_ok=True);(OUT/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    M={
        'bone':material('Weathered warm ivory bone','DAD2BB',.68,.008),
        'shell':material('Charcoal fossil shell','555452',.72,.013),
        'scute':material('Muted grey shell plates','85817A',.64,.009),
        'dark':material('Deep eye and nasal recess','141016',.42,.003),
        'amber':material('Amber eye core','D69A42',.3,.002,'yellow_enamel'),
        'ghost':material('Cool ivory spectral surface','E4E5E2',.36,.004),
        'mouth':material('Dark wine mouth interior','331322',.52,.004),
        'tongue':material('Rose tongue','B94B67',.31,.007),
    }
    dry_bones();boo()
    records=[finish_asset(a) for a in ('dry-bones','boo')]
    # Exported independently at origin before moving roots for the inspection library.
    bpy.data.objects['dry-bones'].location.x=-1.65
    bpy.data.objects['boo'].location.x=1.65
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'assets':records,'warnings':WARNINGS,'style_contract':str(SHARED/'design/style.json')},indent=2))

if __name__=='__main__':
    main()
