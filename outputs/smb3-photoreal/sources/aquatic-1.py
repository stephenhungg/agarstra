"""Editable aquatic creature family; run only through the central Blender queue."""
import argparse
import json
import math
import sys
from pathlib import Path
from array import array
import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools')
sys.path.insert(0, str(SHARED))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None
PI = math.pi
ASSETS = ['cheep-cheep', 'blooper', 'piranha-plant']
WARNINGS = []
ROOT = None
OUT = None


def texture_material(name, color, rough):
    """Deterministic image-backed fallback, with tangent-space microrelief."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    for kind in ('basecolor', 'roughness', 'normal'):
        n = 512
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                u, v = x/n, y/n
                a, b = 2*PI*(32*u+0.12*math.sin(2*PI*16*v)), 2*PI*32*v
                grain = math.sin(a)*math.sin(b)
                if kind == 'basecolor':
                    c = [max(0, min(1, t*(0.94+0.055*grain))) for t in rgb]
                elif kind == 'roughness':
                    c = [max(.05, min(.98, rough+.035*grain))]*3
                else:
                    nx, ny = -.11*math.cos(a)*math.sin(b), -.11*math.sin(a)*math.cos(b)
                    nz = math.sqrt(1-nx*nx-ny*ny)
                    c = [nx*.5+.5, ny*.5+.5, nz*.5+.5]
                pixels.extend((*c, 1))
        img = bpy.data.images.new(name+'_'+kind, width=n, height=n, alpha=False)
        img.colorspace_settings.name = 'sRGB' if kind == 'basecolor' else 'Non-Color'
        img.pixels.foreach_set(pixels)
        img.filepath_raw = str(OUT/'materials'/f'{name}_{kind}.png')
        img.file_format = 'PNG'
        img.save()
        img.pack()
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = img
        if kind == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color' if kind == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic sampled texture fallback'
    return mat


def material(name, color, rough=.45, kind='leather', bump=.006):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=rough,
                                metallic=0, bump=bump, bake=True, resolution=512,
                                cache_dir=OUT/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed; image fallback: {exc}')
    return texture_material(name, color, rough)


def mesh(name, verts, faces, mat, uv=None, indices=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.parent = ROOT
    for m in (mat if isinstance(mat, list) else [mat]):
        data.materials.append(m)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        if indices:
            poly.material_index = indices[poly.index]
        for li in poly.loop_indices:
            vi = data.loops[li].vertex_index
            layer.data[li].uv = uv[vi] if uv else (verts[vi][0], verts[vi][2])
    ob['asset_id'] = ROOT['asset_id']
    return ob


def rings(name, rows, mat, indices=None, caps=False, flip=False):
    # Duplicate seam vertices give unambiguous UVs, including tangent normals.
    n = len(rows[0])-1
    verts = [v for row in rows for v in row]
    uv = [(j/n, i/(len(rows)-1)) for i in range(len(rows)) for j in range(n+1)]
    faces = []
    for i in range(len(rows)-1):
        for j in range(n):
            a = i*(n+1)+j
            faces.append((a, a+1, a+n+2, a+n+1))
    if caps:
        faces.append(tuple(reversed(range(n))))
        faces.append(tuple((len(rows)-1)*(n+1)+j for j in range(n)))
    if flip:
        faces = [tuple(reversed(face)) for face in faces]
    return mesh(name, verts, faces, mat, uv, indices)


def ellipsoid(name, center, scale, mat, n=32, m=20, relief=0):
    rows = []
    for i in range(m+1):
        t = PI*i/m
        row = []
        for j in range(n+1):
            a = 2*PI*j/n
            r = 1+relief*math.sin(12*t)**2*math.cos(16*a+int(i%2)*PI)**2
            row.append((center[0]+scale[0]*math.sin(t)*math.cos(a)*r,
                        center[1]+scale[1]*math.sin(t)*math.sin(a)*r,
                        center[2]+scale[2]*math.cos(t)*r))
        rows.append(row)
    # Reverse latitude order so winding faces outward.
    return rings(name, rows[::-1], mat)


def tube(name, points, radii, mat, sides=10):
    pts = [Vector(p) for p in points]
    rows = []
    for i, p in enumerate(pts):
        tangent = (pts[min(i+1, len(pts)-1)]-pts[max(0, i-1)]).normalized()
        helper = Vector((0, 1, 0)) if abs(tangent.y)<.9 else Vector((1, 0, 0))
        u = tangent.cross(helper).normalized()
        v = tangent.cross(u).normalized()
        rows.append([tuple(p+radii[i]*(u*math.cos(2*PI*j/sides)+v*math.sin(2*PI*j/sides))) for j in range(sides+1)])
    ob = rings(name, rows, mat, caps=(pts[0]-pts[-1]).length > 1e-6)
    return ob


def rim(name, cx, cy, cz, rx, rz, radius, mat, n=64):
    pts = [(cx+rx*math.cos(2*PI*i/n), cy, cz+rz*math.sin(2*PI*i/n)) for i in range(n+1)]
    return tube(name, pts, [radius]*(n+1), mat, 10)


def blade(name, start, end, width, mat, ribmat, bend=.10):
    a, b = Vector(start), Vector(end)
    axis = (b-a).normalized()
    side = axis.cross(Vector((0,-1,0))).normalized()
    rows = []
    for i in range(17):
        t = i/16
        center = a.lerp(b,t)+Vector((0,-bend*math.sin(PI*t),0))
        w = width*math.sin(PI*t)**.85
        rows.append([tuple(center+side*w*s+Vector((0,.05*abs(s)*math.sin(PI*t),0))) for s in (-1,-.5,0,.5,1)])
    verts = [v for row in rows for v in row]
    faces = [(i*5+j,i*5+j+1,(i+1)*5+j+1,(i+1)*5+j) for i in range(16) for j in range(4)]
    ob = mesh(name, verts, faces, mat, [(j/4,i/16) for i in range(17) for j in range(5)])
    solid = ob.modifiers.new('Physical membrane thickness','SOLIDIFY')
    solid.thickness = .018
    sub = ob.modifiers.new('Soft membrane edge','SUBSURF')
    sub.levels = 1
    sub.render_levels = 1
    centers = [row[2] for row in rows]
    tube(name+'_midrib', centers, [.008+.01*math.sin(PI*i/16) for i in range(17)], ribmat, 6)
    for k in (4,7,10,13):
        for side_index in (0,4):
            tube(name+f'_vein_{k}_{side_index}', [centers[k-2], rows[k][1 if side_index==0 else 3], rows[min(16,k+2)][side_index]], [.009,.006,.001], ribmat,6)
    return ob


def eyes(z, y, spacing, white, dark, size=.17):
    for s in (-1,1):
        ellipsoid(f'Eye_{s}', (s*spacing,y,z), (size,size*.55,size*1.25),white)
        ellipsoid(f'Pupil_{s}', (s*spacing,y-size*.51,z), (size*.48,size*.18,size*.76),dark,24,16)


def fish(m):
    red, cream, fin, dark = m['red'],m['ivory'],m['fin'],m['dark']
    body = ellipsoid('Continuous_scaled_body',(0,0,.78),(.57,.55,.62),red,64,40,.009)
    body.data.materials.append(cream)
    for f in body.data.polygons:
        if f.center.z < .62:  # update() supplies polygon centers
            f.material_index = 1
    # Shallow embossed scallop seams over the lateral body, each follows its ellipsoid.
    for s in (-1,1):
        for row in range(5):
            z = .57+row*.125
            for col in range(6):
                y = -.32+col*.12+(row%2)*.035
                pts=[]
                for k in range(7):
                    ang=PI*k/6
                    yy=y+.054*math.cos(ang)
                    zz=z-.037*math.sin(ang)
                    q=max(.001,1-(yy/.55)**2-((zz-.78)/.62)**2)
                    pts.append((s*(.57*math.sqrt(q)+.004),yy,zz))
                tube(f'Scale_seam_{s}_{row}_{col}',pts,[.006]*7,red,5)
    eyes(1.05,-.475,.22,cream,dark,.18)
    ellipsoid('Mouth_recess',(0,-.555,.70),(.18,.075,.115),dark)
    rim('Fleshy_pursed_lips',0,-.61,.70,.17,.11,.038,fin,40)
    for s in (-1,1):
        blade(f'Pectoral_fin_{s}',(s*.42,-.02,.67),(s*.91,.11,.83),.22,fin,cream)
    blade('Dorsal_fin',(0,.03,1.25),(0,.48,1.58),.18,fin,cream)
    # Two broad lobes on a rear caudal peduncle, visible in three-quarter inspection.
    tube('Tail_peduncle',[(0,.42,.78),(0,.65,.78),(0,.73,.78)],[.20,.12,.10],red,20)
    for s in (-1,1):
        blade(f'Caudal_lobe_{s}',(0,.63,.78),(s*.42,1.00,.80+s*.20),.23,fin,cream,.04)


def squid(m):
    ivory, dark, pink = m['ivory'],m['dark'],m['sucker']
    profile=[(.32,.65),(.48,.76),(.50,.91),(.43,1.12),(.34,1.34),(.23,1.52),(.10,1.69),(.0,1.77)]
    rows=[]
    for r,z in profile:
        rows.append([(r*math.cos(2*PI*j/48)*(1+.025*math.cos(8*PI*j/48)),r*.76*math.sin(2*PI*j/48),z) for j in range(49)])
    rings('Pointed_continuous_mantle',rows,ivory)
    ellipsoid('Mantle_underweb',(0,0,.71),(.34,.27,.12),ivory)
    ellipsoid('Ink_eye_mask',(0,-.319,.93),(.35,.065,.16),dark)
    eyes(.95,-.379,.16,ivory,dark,.102)
    for arm in range(8):
        a=2*PI*arm/8
        pts=[]
        for k in range(25):
            t=k/24
            radial=.22+.40*t+.11*math.sin(PI*t)
            angle=a+.22*math.sin(PI*t)
            pts.append((radial*math.cos(angle),radial*.72*math.sin(angle),.72-.66*t+.11*t**5))
        tube(f'Tapered_arm_{arm+1}',pts,[.092*(1-k/25)**.75+.008 for k in range(25)],ivory,12)
        for k in (5,9,13,17,21):
            x,y,z=pts[k]
            r=.032*(1-k/30)
            # Separate inset pads and small raised annuli on the front-facing arm surface.
            ellipsoid(f'Sucker_pad_{arm}_{k}',(x,y-.066*(1-k/28),z),(r,.009,r),pink,12,8)
            rim(f'Sucker_rim_{arm}_{k}',x,y-.073*(1-k/28),z,r,r,.006,ivory,12)


def plant(m):
    red, ivory, dark, green = m['red'],m['ivory'],m['dark'],m['green']
    points=[(.04*math.sin(i/19*PI),.045*math.sin(i/19*PI),i/19*1.16) for i in range(20)]
    tube('Curved_green_stem',points,[.105-.02*i/19 for i in range(20)],green,20)
    for s in (-1,1):
        blade(f'Leaf_{s}',(0,0,.43+s*.05),(s*.68,-.07,.86+s*.10),.22,green,m['vein'],.13)
    # Axis is -Y. Head is an open ellipsoidal shell with a deep lined oral bowl.
    center=Vector((0,0,1.65))
    rows=[]
    for i in range(25):
        t=.89+(PI-.89)*i/24
        rows.append([( .62*math.sin(t)*math.cos(2*PI*j/64),-.57*math.cos(t),1.65+.61*math.sin(t)*math.sin(2*PI*j/64)) for j in range(65)])
    # Reverse shell winding: angular tangent crosses latitude inward.
    spots=[(1.15,.55,.18),(1.30,2.15,.21),(1.75,3.2,.22),(1.9,5.0,.20),(2.35,1.1,.22),(1.1,4.4,.15),(2.1,2.3,.15),(1.6,6.0,.17)]
    ids=[]
    for i in range(24):
        t=.89+(PI-.89)*(i+.5)/24
        for j in range(64):
            a=2*PI*(j+.5)/64
            spotted=any((t-st)**2+(math.atan2(math.sin(a-sa),math.cos(a-sa))*math.sin(t))**2<r*r for st,sa,r in spots)
            ids.append(1 if spotted else 0)
    rings('Spotted_head_shell', rows,[red,ivory],ids,flip=True)
    rx=.62*math.sin(.89); rz=.61*math.sin(.89); front=-.57*math.cos(.89)
    mouth=[]
    for i in range(13):
        t=i/12
        mouth.append([(rx*(1-t)*math.cos(2*PI*j/64), front+.39*math.sin(t*PI/2),1.65+rz*(1-t)*math.sin(2*PI*j/64)) for j in range(65)])
    rings('Deep_recessed_oral_cavity',mouth,dark)
    rim('Thick_ivory_lip',0,front-.008,1.65,rx,rz,.058,ivory)
    for upper in (-1,1):
        for k in range(7):
            a=(.25+(PI-.5)*k/6)*upper
            x=rx*math.cos(a); z=1.65+rz*math.sin(a)
            pts=[(x,front-.01,z),(x*.94,front-.045,z-upper*.065),(x*.82,front+.005,z-upper*(.15+.035*math.sin(k)))]
            tube(f'Curved_tooth_{upper}_{k}',pts,[.046,.028,.001],ivory,10)
    ellipsoid('Tongue_in_cavity',(0,front+.20,1.40),(.19,.17,.045),m['sucker'])


def finish_asset(asset_id, builder, mats):
    global ROOT
    ROOT=bpy.data.objects.new(asset_id,None)
    bpy.context.collection.objects.link(ROOT)
    ROOT['asset_id']=asset_id
    ROOT['units']='1 unit = 16 NES pixels'
    builder(mats)
    objects=[ROOT]+list(ROOT.children)
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    bounds=[ob.evaluated_get(dg).matrix_world @ Vector(c) for ob in objects if ob.type=='MESH' for c in ob.evaluated_get(dg).bound_box]
    lo=Vector(tuple(min(p[a] for p in bounds) for a in range(3)))
    hi=Vector(tuple(max(p[a] for p in bounds) for a in range(3)))
    offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    for ob in ROOT.children:
        ob.location += offset
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=ROOT
    path=OUT/'models'/f'{asset_id}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
    tris=0
    for ob in ROOT.children:
        eo=ob.evaluated_get(dg)
        em=eo.to_mesh()
        em.calc_loop_triangles()
        tris+=len(em.loop_triangles)
        eo.to_mesh_clear()
    return {'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominaldimensions':list(hi-lo),
            'dimensions_axes':'Blender XYZ; measured evaluated bounds in units',
            'materials':sorted({m.name for ob in objects if ob.type=='MESH' for m in ob.data.materials}),
            'meshfeatures':[ob.name for ob in ROOT.children], 'evaluated_triangles':tris,
            'sourcebasis':SOURCE[asset_id], 'knownqualitylimitations':LIMITS,
            'root':ROOT.name}

SOURCE={
 'cheep-cheep':'Catalog binary-asset-manifest.json OBJ_CHEEPCHEEPHOPPER=100 and OBJ_JUMPINGCHEEPCHEEP=118; compact fish, expressive eyes, red/white palette and fins interpreted from family brief.',
 'blooper':'Catalog binary-asset-manifest.json OBJ_BLOOPER=98; all-byte-data-labels.json Blooper_FlipTowardsPlayer PRG/prg003.asm:4532. Pointed pale mantle and dangling arms interpreted from family brief.',
 'piranha-plant':'Catalog binary-asset-manifest.json OBJ_REDPIRANHA=162 (tall pipe muncher); Piranha_Style PRG/prg005.asm:1268. Red spotted head, pale jaws, green stem and paired leaves interpreted from family brief.'}
LIMITS=['Procedural source-inspired reconstruction; no anatomical photorealism claim.',
 'Catalog README says standard-object frame boundaries and palette/bank contexts remain unresolved; no verified enemy PNG composite was identified.',
 'Static editable meshes without skeletal rig or animation; attached organs overlap at joins.',
 'Baked shared material swatches supply microvariation; not scanned biological surfaces.',
 'Central queue must render and inspect silhouettes, texture transfer, normals and intersections.']


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve()
    (OUT/'models').mkdir(parents=True,exist_ok=True)
    (OUT/'materials').mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    mats={
      'red':material('Aquatic_crimson','B73832',.39),
      'ivory':material('Warm_ivory','E9E1CA',.43,bump=.003),
      'fin':material('Fin_ochre','DBA652',.46),
      'dark':material('Oral_ink','201520',.34,bump=.002),
      'sucker':material('Soft_coral','BB6E75',.47),
      'green':material('Plant_cuticle','3F7738',.49,'leaf'),
      'vein':material('Leaf_veins','6C9146',.56,'leaf')}
    records=[]
    for asset_id,builder in zip(ASSETS,(fish,squid,plant)):
        records.append(finish_asset(asset_id,builder,mats))
    # Exported models remain at origin; only the inspection library is spread out.
    for i,asset_id in enumerate(ASSETS):bpy.data.objects[asset_id].location.x=(i-1)*2.8
    for img in bpy.data.images:
        if img.source=='FILE' and not img.packed_file:img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    manifest={'assets':records,'coordinate_contract':'Z up, face -Y, bottom-center root; glTF Y up',
              'style_contract':'smb3-photoreal/design/style.json', 'build_warnings':WARNINGS}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')

if __name__=='__main__':main()
