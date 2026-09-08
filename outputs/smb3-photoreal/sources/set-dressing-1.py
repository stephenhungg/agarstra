"""Deterministic environment dressing; execute only in the central Blender queue."""
import argparse
import json
import math
import random
import struct
import sys
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
WARNINGS = []


def fallback_material(name, color, roughness, out, organic=False):
    """CPU-generated tileable color, roughness and tangent normal image maps."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    base = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    size = 512
    def height(u, v):
        if organic:
            return .5 + .13*math.sin(TAU*(u*34 + .2*math.sin(TAU*v))) + .04*math.sin(TAU*(u*93+v*5))
        return .5 + .14*math.sin(TAU*(u*7+v*9)) + .10*math.sin(TAU*(u*29-v*19)) + .06*math.sin(TAU*(u*117+v*97))
    pixels = {k: [] for k in ('basecolor', 'roughness', 'normal')}
    for y in range(size):
        for x in range(size):
            u, v = x/size, y/size
            h = height(u, v)
            pixels['basecolor'].extend([min(1, c*(.78+.36*h)) for c in base] + [1])
            r = max(.05, min(1, roughness + (h-.5)*.22))
            pixels['roughness'].extend((r,r,r,1))
            dx = (height(u+1/size,v)-height(u-1/size,v))*1.3
            dy = (height(u,v+1/size)-height(u,v-1/size))*1.3
            n = Vector((-dx,-dy,1)).normalized()
            pixels['normal'].extend((n.x*.5+.5,n.y*.5+.5,n.z*.5+.5,1))
    for channel, data in pixels.items():
        im = bpy.data.images.new(name+'_'+channel, width=size, height=size, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        im.pixels.foreach_set(data)
        im.filepath_raw = str(out / 'materials' / (name+'_'+channel+'.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = nodes.new('ShaderNodeTexImage')
        tex.image = im
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['texture_method'] = 'deterministic image fallback'
    return mat


def material(kind, name, color, roughness, out):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                bake=True, resolution=512, cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: helper failed; image fallback used: {exc}')
    return fallback_material(name, color, roughness, out, kind=='leaf')


def mesh(name, verts, faces, mat, root, uvs=None, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    root.users_collection[0].objects.link(obj)
    obj.parent = root
    data.materials.append(mat)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = smooth
        for li in poly.loop_indices:
            vi = data.loops[li].vertex_index
            layer.data[li].uv = uvs[vi] if uvs else (verts[vi][0], verts[vi][2])
    return obj


def ringmesh(name, centers, radii, sides, mat, root, rough=0, seed=0):
    """Closed seam-duplicated tube with transported local cross sections."""
    rng = random.Random(seed)
    verts, faces, uv = [], [], []
    for i, center in enumerate(centers):
        c = Vector(center)
        tangent = Vector(centers[min(i+1,len(centers)-1)]) - Vector(centers[max(i-1,0)])
        tangent.normalize()
        axis = Vector((1,0,0))
        if abs(tangent.dot(axis)) > .95:
            axis = Vector((0,1,0))
        a = tangent.cross(axis).normalized()
        b = tangent.cross(a).normalized()
        row = []
        for j in range(sides):
            angle = TAU*j/sides
            radius = radii[i]*(1+rng.uniform(-rough,rough))
            row.append(tuple(c + radius*(math.cos(angle)*a + math.sin(angle)*b)))
        row.append(row[0])
        verts.extend(row)
        uv.extend((j/sides,i/(len(centers)-1)) for j in range(sides+1))
    stride = sides+1
    for i in range(len(centers)-1):
        for j in range(sides):
            k=i*stride+j
            faces.append((k,k+1,k+1+stride,k+stride))
    faces.append(tuple(reversed(range(sides))))
    faces.append(tuple((len(centers)-1)*stride+j for j in range(sides)))
    return mesh(name, verts, faces, mat, root, uv)


def blade(name, start, length, width, angle, lean, mat, root, segments=9):
    """Closed diamond section: raised midrib, sharp edges, solid underside."""
    verts, uv, faces = [], [], []
    forward = Vector((math.cos(angle), math.sin(angle), 0))
    side = Vector((-math.sin(angle),math.cos(angle),0))
    for i in range(segments+1):
        t=i/segments
        c=Vector(start) + forward*(lean*t*t) + Vector((0,0,length*(t-.17*t**3)))
        w=width*(.32+.68*math.sin(math.pi*t*.85))*(1-t)**.55 + .00035
        thick = max(.0007,width*.10*(1-t))
        for j, offset in enumerate((side*w/2,-forward*thick, -side*w/2,forward*thick)):
            verts.append(tuple(c+offset)); uv.append((j/3,t))
    for i in range(segments):
        for j in range(4):
            k=i*4+j; nxt=i*4+(j+1)%4
            faces.append((k,nxt,nxt+4,k+4))
    faces.extend(((3,2,1,0),tuple(segments*4+j for j in range(4))))
    return mesh(name,verts,faces,mat,root,uv)


def rock(root, mats):
    rng=random.Random(618)
    specs=[(-.32,.11,.43,.32,.59),(.27,.13,.38,.30,.43),(-.01,-.26,.30,.25,.29),(-.59,-.18,.17,.14,.19),(.54,-.16,.20,.16,.23),(.16,.40,.21,.15,.24)]
    for idx,(x,y,rx,ry,h) in enumerate(specs):
        sides=11
        angles=[TAU*j/sides+rng.uniform(-.07,.07) for j in range(sides)]
        angular=[rng.uniform(.84,1.14) for _ in range(sides)]
        verts=[]; uv=[]; faces=[]
        for k,(z,scale) in enumerate(((0,.70),(.13,1),(.46,1.02),(.77,.83),(1,.43))):
            for j,a in enumerate(angles):
                f=angular[j]*rng.uniform(.90,1.08)*scale
                verts.append((x+math.cos(a)*rx*f+.04*k/4,y+math.sin(a)*ry*f,h*(z+(rng.uniform(-.05,.05) if k not in (0,) else 0))))
                uv.append((j/sides,k/4))
        for k in range(4):
            for j in range(sides):
                a=k*sides+j; b=k*sides+(j+1)%sides
                faces.append((a,b,b+sides,a+sides))
        faces.extend((tuple(reversed(range(sides))),tuple(4*sides+j for j in range(sides))))
        obj=mesh(f'Fractured stone {idx+1:02}',verts,faces,mats['stone'],root,uv,smooth=False)
        bevel=obj.modifiers.new('Weathered fracture edges','BEVEL'); bevel.width=.012; bevel.segments=2
        bevel.limit_method='ANGLE'
        # Give broad stone faces independent, non-stretched UV islands.
        if pbr:
            pbr.uv_smart(obj)
        else:
            for poly in obj.data.polygons:
                n=poly.normal; axis=max(range(3),key=lambda a:abs(n[a]))
                axes=[a for a in range(3) if a!=axis]
                for li in poly.loop_indices:
                    co=obj.data.vertices[obj.data.loops[li].vertex_index].co
                    obj.data.uv_layers.active.data[li].uv=(co[axes[0]],co[axes[1]])
    # Scattered angular chips create a graduated contact silhouette, no floor slab.
    for i in range(9):
        a=rng.uniform(0,TAU); r=rng.uniform(.35,.68); x=math.cos(a)*r; y=math.sin(a)*r*.7
        s=rng.uniform(.025,.065)
        mesh(f'Loose stone flake {i:02}',[(x-s,y-s,0),(x+s,y-s*.6,0),(x+s*.6,y+s,0),(x-s*.6,y+s*.6,.012),(x,y,s)],[(0,1,4),(1,2,4),(2,3,4),(3,0,4),(3,2,1,0)],mats['stone'],root,smooth=False)


def grass(root,mats):
    rng=random.Random(141)
    for i in range(46):
        a=rng.uniform(0,TAU); r=.25*math.sqrt(rng.random())
        start=(r*math.cos(a),r*math.sin(a)*.7,0)
        length=rng.uniform(.28,.62)*(1-.28*r/.25)
        mat=mats['dry'] if i%7==0 else mats['leaf']
        blade(f'Folded grass blade {i+1:02}',start,length,rng.uniform(.019,.043),a+rng.uniform(-.7,.7),rng.uniform(.09,.26),mat,root)
    for i in range(8):
        a=TAU*i/8
        blade(f'Curled basal thatch {i:02}',(.08*math.cos(a),.06*math.sin(a),.003),.12,.020,a,.20,mats['dry'],root,6)


def reeds(root,mats):
    rng=random.Random(214)
    for i in range(9):
        a=i*2.39996; r=.22*math.sqrt((i+.5)/9)
        base=Vector((math.cos(a)*r,math.sin(a)*r*.72,0))
        h=rng.uniform(.91,1.49); drift=Vector((rng.uniform(-.14,.14),rng.uniform(-.09,.09),0))
        def center(t): return base+drift*t*t+Vector((0,0,h*t))
        ringmesh(f'Reed culm {i+1:02}',[center(j/10) for j in range(11)],[.012*(1-.45*j/10) for j in range(11)],8,mats['leaf'],root)
        for k,t in enumerate((.22,.45,.67)):
            c=center(t)
            ringmesh(f'Culm node {i:02}.{k}',[c+Vector((0,0,z)) for z in (-.009,-.006,.006,.009)],[.011,.014,.014,.010],6,mats['dry'],root)
            blade(f'Reed lance leaf {i:02}.{k}',c,h*rng.uniform(.30,.48),rng.uniform(.025,.043),a+k*2.2,rng.uniform(.18,.31),mats['leaf'],root,8)
        if i%3!=2:
            length=rng.uniform(.17,.25)
            cs=[center(1)+Vector((0,0,length*t)) for t in (0,.08,.22,.4,.6,.8,.94,1)]
            rs=[.012,.032,.036,.037,.036,.033,.025,.004]
            ringmesh(f'Cattail seed spike {i:02}',cs,rs,14,mats['seed'],root,.12,90+i)
            ringmesh(f'Seed spike terminal {i:02}',[cs[-1],cs[-1]+Vector((0,0,.05))],[.003,.0008],6,mats['dry'],root)
            # Real pointed seed scales along silhouette; batched into a single mesh.
            vs=[]; fs=[]; uvs=[]
            for j in range(36):
                t=rng.uniform(.12,.90); theta=j*2.39996
                c=center(1)+Vector((.034*math.cos(theta),.034*math.sin(theta),length*t))
                side=Vector((-math.sin(theta),math.cos(theta),0))*.005
                tip=c+Vector((.007*math.cos(theta),.007*math.sin(theta),.007))
                off=len(vs)
                vs.extend((tuple(c-side),tuple(c+side),tuple(c+Vector((0,0,-.008))),tuple(tip)))
                uvs.extend(((0,0),(1,0),(.5,1),(.5,.5)))
                fs.extend(tuple(off+k for k in f) for f in ((0,2,1),(0,1,3),(1,2,3),(2,0,3)))
            mesh(f'Individual seed scales {i:02}',vs,fs,mats['seed'],root,uvs)


def inspect_glb(path):
    raw=path.read_bytes(); size,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4E4F534A
    doc=json.loads(raw[20:20+size])
    images=doc.get('images',[])
    assert images and all('bufferView' in im for im in images), 'Textures must be embedded'
    for mat in doc.get('materials',[]):
        params=mat.get('pbrMetallicRoughness',{})
        assert 'baseColorTexture' in params and 'metallicRoughnessTexture' in params and 'normalTexture' in mat, mat.get('name')
    assert not doc.get('cameras')
    return {'embedded_images':len(images),'bytes':len(raw)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).expanduser().resolve()
    (out/'models').mkdir(parents=True,exist_ok=True)
    (out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    mats={key:material(kind,name,color,rough,out) for key,kind,name,color,rough in [
        ('stone','stone','Weathered limestone','77766B',.88),
        ('leaf','leaf','Muted olive foliage','566344',.73),
        ('dry','leaf','Dry straw and stem nodes','918367',.85),
        ('seed','soil','Cattail seed felt','594434',.94)]}
    manifest={'schema_version':1,'units':'1 unit = 1 block = 16 NES pixels','coordinates':'Z up; front -Y; GLB Y up','assets':[]}
    features={
        'rock-cluster':['six asymmetric fractured ring-mesh stones','two-segment edge bevels','nine angular loose flakes'],
        'grass-clump':['46 curved tapered solid blades with raised midribs','8 curled dry basal leaves','varied radial growth and muted dry tips'],
        'reeds':['9 bent tapered eight-sided culms','27 raised stem joints and lance leaves','6 cattail spikes with 216 volumetric seed scales']}
    roots=[]
    for asset_id, builder in [('rock-cluster',rock),('grass-clump',grass),('reeds',reeds)]:
        collection=bpy.data.collections.new(asset_id); bpy.context.scene.collection.children.link(collection)
        root=bpy.data.objects.new(asset_id,None); collection.objects.link(root)
        root['asset_id']=asset_id; root['units_per_block']=1.0
        builder(root,mats)
        objs=list(root.children)
        # Recenter bounds in XY and ground every asset at its lowest vertex.
        coords=[v.co for obj in objs for v in obj.data.vertices]
        low=Vector(tuple(min(v[k] for v in coords) for k in range(3)))
        high=Vector(tuple(max(v[k] for v in coords) for k in range(3)))
        shift=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
        for obj in objs:
            for v in obj.data.vertices: v.co-=shift
            obj['asset_id']=asset_id
        bpy.context.view_layer.update()
        deps=bpy.context.evaluated_depsgraph_get()
        bounds=[]; triangles=0
        for obj in objs:
            evaluated=obj.evaluated_get(deps); temp=evaluated.to_mesh()
            temp.calc_loop_triangles(); triangles+=len(temp.loop_triangles)
            bounds.extend(v.co.copy() for v in temp.vertices)
            evaluated.to_mesh_clear()
        dimensions=[round(max(v[k] for v in bounds)-min(v[k] for v in bounds),4) for k in range(3)]
        path=out/'models'/f'{asset_id}.glb'
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [root]+objs: obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_yup=True,export_materials='EXPORT')
        inspection=inspect_glb(path)
        manifest['assets'].append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':dict(zip(('x','y','z'),dimensions)),
            'materials':sorted({m.name for o in objs for m in o.data.materials}), 'mesh_features':features[asset_id],
            'triangles':triangles,'export_validation':inspection,
            'source_basis':{'catalog':'smb3-rom-assets/catalog/binary-assets.json','evidence':'TILE1_LITTLE_BUSH and TILE1_BUSH_UL/UR/BL/BR describe compact layered environment foliage; 16-pixel block scale from shared contract.','interpretation':'Natural set-dressing interpretation; no direct loose-rock, grass, or reed semantic reference found. No claimed exact ROM match.'},
            'known_quality_limitations':['Central queue render and visual review required.','No authored alternate LOD meshes or wind animation; compact base topology only.','Baked microdetail is generic material grain; foliage veins are represented by folded geometry.']})
        roots.append(root)
    for i,root in enumerate(roots): root.location.x=(i-1)*2.1
    # Inspection layout only; each GLB was exported with its root at the origin.
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file: image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    manifest['material_warnings']=WARNINGS
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
