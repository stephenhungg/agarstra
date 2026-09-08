"""Editable SMB3 accessory family; execute only through the central Blender queue."""
import argparse
import json
import math
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

TAU = 2 * math.pi
ASSETS = ['mario-glove', 'raccoon-tail', 'hammer-suit-shell']
WARNINGS = []
OUT = None


def fallback_material(name, color, roughness, metallic, fur=False):
    """Deterministic real image textures, including tangent-space micro-normal."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    size = 512
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(size):
            for x in range(size):
                grain = math.sin(x * 1.7 + math.sin(y * 2.1)) * math.cos(y * 1.3)
                weave = math.sin(TAU * x / 8) * math.sin(TAU * y / 8)
                variation = .025 * grain + .014 * weave
                if fur:
                    variation += .045 * math.sin(TAU * x / 4 + .5 * math.sin(TAU * y / 64))
                if channel == 'basecolor':
                    v = [max(0, min(1, c * (1 + variation))) for c in rgb]
                elif channel == 'roughness':
                    v = [max(.05, min(1, roughness + variation))] * 3
                else:
                    nx = .10 * math.cos(x * 1.7 + math.sin(y * 2.1))
                    ny = .07 * math.sin(y * 1.3)
                    if fur:
                        nx += .12 * math.cos(TAU * x / 4 + .5 * math.sin(TAU * y / 64))
                    v = [.5 + nx / 2, .5 + ny / 2, .5 + math.sqrt(1 - nx*nx - ny*ny) / 2]
                pixels.extend((*v, 1))
        image = bpy.data.images.new(name + '_' + channel, width=size, height=size, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(OUT / 'materials' / (image.name + '.png'))
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
    mat['texture_method'] = 'deterministic image-based PBR fallback'
    return mat


def material(name, kind, color, roughness, metallic=0):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=metallic, bake=True, resolution=512,
                                cache_dir=OUT / 'materials')
        except Exception as exc:
            WARNINGS.append('Shared material fallback for %s: %s' % (name, exc))
    return fallback_material(name, color, roughness, metallic, 'fur' in name)


def mesh(name, vertices, faces, mat, uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vi = data.loops[li].vertex_index
            co = vertices[vi]
            layer.data[li].uv = uvs[vi] if uvs else (co[0] * 5, co[2] * 5)
    return obj


def sweep(name, rows, mat, sides=20, caps=True, fixed_frame=False):
    """Rows: (center, horizontal radius, second radius). Parallel local frames."""
    verts, faces, uv = [], [], []
    for i, (pos, rx, ry) in enumerate(rows):
        tangent = Vector(rows[min(i+1, len(rows)-1)][0]) - Vector(rows[max(0, i-1)][0])
        tangent.normalize()
        ref = Vector((0, 1, 0)) if abs(tangent.y) < .9 else Vector((1, 0, 0))
        u = ref.cross(tangent).normalized()
        v = tangent.cross(u).normalized()
        if fixed_frame:
            u, v = Vector((1, 0, 0)), Vector((0, 1, 0))
        for j in range(sides+1):
            a = TAU*j/sides
            verts.append(tuple(Vector(pos) + u*(rx*math.cos(a)) + v*(ry*math.sin(a))))
            uv.append((j/sides, i/(len(rows)-1)))
    stride = sides+1
    for i in range(len(rows)-1):
        for j in range(sides):
            a = i*stride+j
            faces.append((a, a+1, a+1+stride, a+stride))
    if caps:
        faces.append(tuple(reversed(range(sides))))
        faces.append(tuple((len(rows)-1)*stride+j for j in range(sides)))
    return mesh(name, verts, faces, mat, uv)


def cord(name, points, radius, mat, sides=6):
    return sweep(name, [(p, radius, radius) for p in points], mat, sides)


def oval(name, center, radii, tube, mat, n=64):
    x,y,z = center
    return cord(name, [(x+radii[0]*math.cos(TAU*j/n), y+radii[1]*math.sin(TAU*j/n), z) for j in range(n+1)], tube, mat, 8)


def stitches(name, paths, mat, radius=.0014):
    # Batch disconnected stitch capsules into one editable mesh.
    verts, faces = [], []
    for a,b in paths:
        a,b = Vector(a),Vector(b)
        axis=(b-a).normalized()
        u=axis.cross(Vector((0,1,0)))
        if u.length < .1: u=axis.cross(Vector((1,0,0)))
        u.normalize(); v=axis.cross(u)
        start=len(verts)
        for p in (a,b):
            for j in range(5):
                verts.append(tuple(p+radius*(u*math.cos(TAU*j/5)+v*math.sin(TAU*j/5))))
        for j in range(5):
            k=(j+1)%5; faces.append((start+j,start+k,start+5+k,start+5+j))
        faces.extend([tuple(start+j for j in reversed(range(5))),tuple(start+5+j for j in range(5))])
    return mesh(name,verts,faces,mat)


def glove(m):
    parts=[]
    parts.append(sweep('Glove padded palm', [((0,0,z),x,y) for z,x,y in [(.065,.061,.039),(.09,.082,.048),(.14,.105,.052),(.205,.103,.053),(.235,.092,.042),(.246,.080,.032)]],m['ivory'],32))
    # Four gently curled fingers emerge from a broad palm, separate seam channels.
    for i,(x,length,r) in enumerate([(-.076,.083,.026),(-.026,.111,.027),(.027,.104,.026),(.076,.083,.023)]):
        rows=[]
        for j in range(9):
            t=j/8
            taper=1 if t<.68 else max(.06,math.sqrt(max(0,1-((t-.68)/.32)**2)))
            rows.append(((x+(i-1.5)*.006*t,-.032*t*t,.216+length*t),r*taper,.038*taper))
        parts.append(sweep('Padded finger %d'%i,rows,m['ivory'],20))
        for h in (.30,.53):
            z=.216+length*h
            parts.append(cord('Finger flex seam %d %.2f'%(i,h),[(x-r*.68,-.033,z),(x,-.041,z-.003),(x+r*.68,-.033,z)],.0017,m['seam']))
    parts.append(sweep('Opposed curved thumb', [((-.075,0,.123),.043,.040),((-.111,-.011,.149),.039,.038),((-.136,-.028,.180),.034,.032),((-.143,-.045,.209),.029,.029),((-.134,-.052,.227),.018,.020),((-.128,-.052,.232),.002,.003)],m['ivory'],24))
    # Hollow rolled wrist cuff: closed annular cross-section, open central aperture.
    profile=[(.061,.033,.004),(.073,.044,.009),(.078,.047,.024),(.076,.045,.070),(.069,.040,.080),(.058,.030,.071),(.057,.029,.015),(.061,.033,.004)]
    parts.append(sweep('Hollow rolled leather cuff',[((0,0,z),x,y) for x,y,z in profile],m['ivory'],40,False,True))
    for z in (.015,.065): parts.append(oval('Cuff welt', (0,0,z),(.076,.046),.003,m['seam']))
    paths=[]
    for j in range(48):
        a=TAU*j/48; b=a+.063
        paths.append(((.078*math.cos(a),.048*math.sin(a),.050),(.078*math.cos(b),.048*math.sin(b),.052)))
    parts.append(stitches('Cuff saddle stitching',paths,m['thread']))
    for x in (-.043,0,.043):
        points=[(x,-.052-.002*math.sin(math.pi*j/12),.129+.074*j/12) for j in range(13)]
        parts.append(cord('Raised back-of-hand dart',points,.0027,m['seam']))
        parts.append(stitches('Dart stitches',[((x-.004,-.055,.13+j*.009),(x+.004,-.055,.133+j*.009)) for j in range(8)],m['thread'],.001))
    return parts


def tail_center(t):
    return Vector((.18*math.sin(t*math.pi*.9), .07*math.sin(math.pi*t), .035+.76*t))


def tail_radius(t):
    return .040 + .108*math.sin(math.pi*t)**.75 if t < .96 else .010 + .06*(1-t)


def tail(m):
    parts=[]; rows=[]
    for j in range(49):
        t=j/48; r=tail_radius(t) if j<48 else .001
        rows.append((tail_center(t),r,r*.82))
    base=sweep('Continuous tapered curved tail',rows,m['fur_tan'],32)
    base.data.materials.append(m['fur_dark'])
    for poly in base.data.polygons:
        if poly.index < 48*32:
            t=(poly.index//32+.5)/48
            poly.material_index=int(t>.91 or any(a<t<b for a,b in [(.18,.29),(.41,.53),(.65,.77)]))
    parts.append(base)
    # Solid small tapered tufts follow the sweep and preserve a fuzzy silhouette in GLB.
    groups={0:([],[]),1:([],[])}
    for row in range(33):
        t=.04+.91*row/32
        center=tail_center(t)
        tangent=(tail_center(min(1,t+.001))-tail_center(max(0,t-.001))).normalized()
        u=Vector((0,1,0)).cross(tangent).normalized();v=tangent.cross(u)
        r=tail_radius(t)
        dark=int(t>.91 or any(a<t<b for a,b in [(.18,.29),(.41,.53),(.65,.77)]))
        verts,faces=groups[dark]
        for j in range(24):
            a=TAU*(j+.45*(row%2))/24
            normal=(u*math.cos(a)+v*math.sin(a)).normalized()
            cross=tangent.cross(normal).normalized()
            p=center+u*(r*math.cos(a))+v*(r*.82*math.sin(a))
            width=.009*(.7+.3*math.sin(j*7+row)**2)
            tip=p+tangent*.026+normal*.016
            k=len(verts)
            verts.extend([tuple(p-cross*width-tangent*.008),tuple(p+cross*width-tangent*.008),tuple(p+normal*.005+tangent*.009),tuple(tip)])
            faces.extend([(k,k+1,k+2),(k,k+3,k+1),(k+1,k+3,k+2),(k+2,k+3,k)])
    for index,(verts,faces) in groups.items():
        parts.append(mesh('Solid fur tufts '+str(index),verts,faces,m['fur_dark' if index else 'fur_tan']))
    parts.append(oval('Tail attachment leather binding',(0,0,.041),(.044,.036),.006,m['strap']))
    return parts


def shell_point(phi,theta,offset=0):
    # Face/body side is -Y; armored dome projects backwards +Y.
    return ((.30+offset)*math.sin(phi)*math.cos(theta),(.17+offset)*math.cos(phi),.34+(.33+offset)*math.sin(phi)*math.sin(theta))


def shell_patch(name,lo,hi,a,b,mat,offset=0,radial=6,angular=14):
    verts=[];faces=[];uv=[]
    for i in range(radial+1):
        p=lo+(hi-lo)*i/radial
        for j in range(angular+1):
            t=a+(b-a)*j/angular
            verts.append(shell_point(p,t,offset));uv.append((j/angular,i/radial))
    for i in range(radial):
        for j in range(angular):
            k=i*(angular+1)+j;faces.append((k,k+1,k+angular+2,k+angular+1))
    return mesh(name,verts,faces,mat,uv)


def shell(m):
    parts=[]
    base=shell_patch('Protective shell continuous hollow substrate',.001,math.pi/2,0,TAU,m['shell'],radial=16,angular=64)
    mod=base.modifiers.new('Real shell thickness','SOLIDIFY');mod.thickness=.020;mod.offset=-1
    parts.append(base)
    # Separate domed scutes leave narrow recessed channels showing dark substrate.
    parts.append(shell_patch('Central crown scute',.001,.51,0,TAU,m['scute'],.008,6,48))
    for ring,(lo,hi,count) in enumerate([(.54,1.02,6),(1.05,1.535,10)]):
        for j in range(count):
            a=TAU*j/count + (ring%2)*.18
            obj=shell_patch('Armor scute %d %02d'%(ring,j),lo,hi,a+.014,a+TAU/count-.014,m['scute'],.008,4,8)
            mod=obj.modifiers.new('Scute rolled thickness','SOLIDIFY');mod.thickness=.006
            bevel=obj.modifiers.new('Soft scute edge','BEVEL');bevel.width=.002;bevel.segments=2
            parts.append(obj)
    points=[shell_point(math.pi/2,TAU*j/96,.003) for j in range(97)]
    parts.append(cord('Warm ivory continuous shell rim',points,.021,m['rim'],10))
    inner=[(.278*math.cos(TAU*j/96),-.011,.34+.307*math.sin(TAU*j/96)) for j in range(97)]
    parts.append(cord('Inner leather rim welt',inner,.006,m['strap'],8))
    # Two curved leather harness bands across the open body-facing cavity.
    for sign in (-1,1):
        x=sign*.15
        points=[(x,-.019-.070*math.sin(math.pi*j/16),.105+.47*j/16) for j in range(17)]
        rows=[(p,.022,.006) for p in points]
        parts.append(sweep('Inner harness band '+str(sign),rows,m['strap'],12))
        paths=[]
        for j in range(25):
            t=j/25;tn=(j+.55)/25
            for side in (-1,1):
                paths.append(((x+side*.015,-.027-.07*math.sin(math.pi*t),.105+.47*t),(x+side*.015,-.027-.07*math.sin(math.pi*tn),.105+.47*tn)))
        parts.append(stitches('Harness saddle stitching '+str(sign),paths,m['thread']))
        # Rectangular brass buckle, formed from round metal stock, with crossbar.
        y=-.091; z=.30
        p=[(x-.03,y,z-.023),(x+.03,y,z-.023),(x+.03,y,z+.023),(x-.03,y,z+.023),(x-.03,y,z-.023)]
        parts.append(cord('Harness buckle '+str(sign),p,.004,m['brass'],8))
        parts.append(cord('Buckle tongue '+str(sign),[(x,y-.003,z-.023),(x,y-.005,z+.016)],.0026,m['brass'],6))
    return parts


FEATURES={
'mario-glove':['Padded palm and four curved fingers with opposed thumb','Open rolled cuff with inner wall','Physical cuff saddle stitches and three raised glove darts','Finger flex seam geometry'],
'raccoon-tail':['Curved continuous tapered volume','Three dark transverse bands and dark tapered tip','792 solid tapered fur tufts','Leather root binding'],
'hammer-suit-shell':['Hollow thick domed shell','17 separate raised crown and surrounding scutes with recessed channels','Ivory perimeter rim and inner welt','Two leather harness straps, physical saddle stitching and brass buckles']}
LIMITS={
'mario-glove':['Static unrigged right-hand accessory; overlapping finger/palm construction is not a unified deformation cage.','Interior modeled at cuff only; no complete finger cavities.'],
'raccoon-tail':['Fur is solid low-poly tufts plus baked microtexture, not a strand groom.','Static curve; no skinning or tail animation.'],
'hammer-suit-shell':['Scute layout and leather harness are interpretive additions, not recovered pixel details.','Shell interior is simplified for accessory use.']}


def bounds(parts):
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    pts=[obj.matrix_world @ Vector(c) for o in parts for obj in [o.evaluated_get(dg)] for c in obj.bound_box]
    lo=Vector(tuple(min(p[i] for p in pts) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in pts) for i in range(3)))
    return lo,hi


def main():
    global OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve();(OUT/'models').mkdir(parents=True,exist_ok=True);(OUT/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    m={}
    for key,kind,color,rough,metal in [
        ('ivory','leather','E6E1D2',.58,0),('seam','leather','B8AD98',.67,0),
        ('thread','cloth','DACCB0',.86,0),('fur_tan','cloth','A96C3A',.92,0),
        ('fur_dark','cloth','34231C',.94,0),('strap','leather','382D25',.68,0),
        ('shell','leather','15191B',.55,0),('scute','leather','252C2D',.39,0),
        ('rim','leather','BBAE88',.56,0),('brass','worn_brass','A58A50',.4,.8)]:
        m[key]=material(key,kind,color,rough,metal)
    manifest={'family':'character-kit-2','coordinate_system':'Z up, front -Y, X right; glTF Y up','unit':'one block = 1 Blender unit = 16 NES pixels','body_scale_reference':1.5,'assets':[],'warnings':WARNINGS}
    builders=[glove,tail,shell];roots=[]
    for asset_id,builder in zip(ASSETS,builders):
        collection=bpy.data.collections.new(asset_id);bpy.context.scene.collection.children.link(collection)
        parts=builder(m)
        root=bpy.data.objects.new(asset_id,None);collection.objects.link(root);root['asset_id']=asset_id;root['nominal_body_height']=1.5
        lo,hi=bounds(parts);shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
        for obj in parts:
            for old in list(obj.users_collection):old.objects.unlink(obj)
            collection.objects.link(obj);obj.location+=shift;obj.parent=root;obj['asset_id']=asset_id
        lo,hi=bounds(parts);dimensions=[round(v,5) for v in hi-lo]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [root]+parts:obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        path=OUT/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
        # Validate embedding and texture channel transfer directly from exported GLB.
        import struct
        raw=path.read_bytes();length=struct.unpack_from('<I',raw,12)[0];doc=json.loads(raw[20:20+length])
        assert doc.get('images') and all('bufferView' in im for im in doc['images']), 'Textures must be embedded'
        for mat in doc.get('materials',[]):
            assert 'baseColorTexture' in mat.get('pbrMetallicRoughness',{}),mat.get('name')
            assert 'metallicRoughnessTexture' in mat['pbrMetallicRoughness'],mat.get('name')
            assert 'normalTexture' in mat,mat.get('name')
        triangles=sum(doc['accessors'][p['indices']]['count']//3 for me in doc['meshes'] for p in me['primitives'])
        record={'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':dimensions,'dimension_order':'XYZ Blender units','materials':sorted({mat.name for obj in parts for mat in obj.data.materials}),'mesh_features':FEATURES[asset_id],'triangles':triangles,'source_basis':{'catalog':'smb3-rom-assets/catalog/binary-assets.json','sheet':'binary-player-templates-00.png and binary-player-templates-01.png','suit':{'mario-glove':'Big','raccoon-tail':'Leaf / Tanooki','hammer-suit-shell':'Hammer'}[asset_id],'reference_combination':{'mario-glove':'player-Big-PF00','raccoon-tail':'player-Leaf-PF00','hammer-suit-shell':'player-Hammer-PF00'}[asset_id],'qualification':'Suit templates are diagnostic, animation reachability unverified. Surface construction is an authored interpretation.'},'known_quality_limitations':LIMITS[asset_id]+['Not rendered or visually reviewed during isolated code authoring.']}
        manifest['assets'].append(record);roots.append(root)
    for i,root in enumerate(roots):root.location.x=(i-1)*1.1
    bpy.ops.object.select_all(action='DESELECT')
    for root in roots:root.select_set(True)
    bpy.context.view_layer.objects.active=roots[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
