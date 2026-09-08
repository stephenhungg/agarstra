"""Deterministic vegetation family; run only through the central Blender queue."""
import argparse
import json
import math
from pathlib import Path
import random
import sys
import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.path.insert(0, str(SHARED / 'tools'))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None
TAU = math.tau
RNG = random.Random(4821)
WARNINGS = []


def fallback_material(name, color, roughness, out):
    """Portable image PBR fallback, with deterministic multiscale mineral/leaf grain."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    size = 512
    heights = []
    rand = random.Random(92)
    for y in range(size):
        for x in range(size):
            u, v = x/size, y/size
            heights.append(.5 + .14*math.sin(TAU*(9*u+3*v)) + .09*math.cos(TAU*(17*v-5*u)) + .035*rand.uniform(-1, 1))
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = []
        for y in range(size):
            for x in range(size):
                h = heights[y*size+x]
                if channel == 'basecolor':
                    c = [min(1, k*(.74+.44*h)) for k in rgb]
                elif channel == 'roughness':
                    c = [max(.2, min(1, roughness + (h-.5)*.3))]*3
                else:
                    dx = heights[y*size+(x+1)%size]-heights[y*size+(x-1)%size]
                    dy = heights[((y+1)%size)*size+x]-heights[((y-1)%size)*size+x]
                    n = Vector((-dx*1.8, -dy*1.8, 1)).normalized()
                    c = [a*.5+.5 for a in n]
                pixels.extend((*c, 1))
        im = bpy.data.images.new(name+'_'+channel, width=size, height=size, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels)
        im.filepath_raw = str(out/'materials'/f'{name}_{channel}.png')
        im.file_format = 'PNG'
        im.save()
        im.pack()
        node = nodes.new('ShaderNodeTexImage')
        node.image = im
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(node.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(node.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic image fallback'
    return mat


def material(kind, name, color, roughness, out):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                bake=True, resolution=512, cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: helper failed; image fallback used: {exc}')
    return fallback_material(name, color, roughness, out)


class Mesh:
    def __init__(self):
        self.v, self.f, self.uv = [], [], []

    def vert(self, p, uv=(0, 0)):
        self.v.append(tuple(p)); self.uv.append(uv)
        return len(self.v)-1

    def object(self, name, mat, root):
        data = bpy.data.meshes.new(name)
        data.from_pydata(self.v, [], self.f)
        data.update()
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.parent = root
        data.materials.append(mat)
        uv = data.uv_layers.new(name='UVMap')
        for face in data.polygons:
            face.use_smooth = True
            for loop in face.loop_indices:
                uv.data[loop].uv = self.uv[data.loops[loop].vertex_index]
        return obj

    def tube(self, points, radii, sides=7):
        pts = [Vector(p) for p in points]
        start = len(self.v)
        for i, p in enumerate(pts):
            tangent = (pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
            ref = Vector((0, 1, 0)) if abs(tangent.y)<.9 else Vector((1, 0, 0))
            a = tangent.cross(ref).normalized(); b = tangent.cross(a).normalized()
            for j in range(sides):
                ang = TAU*j/sides
                self.vert(p+radii[i]*(a*math.cos(ang)+b*math.sin(ang)), (j/sides, i/(len(pts)-1)))
        for i in range(len(pts)-1):
            for j in range(sides):
                a = start+i*sides+j; b = start+i*sides+(j+1)%sides
                self.f.append((a,b,b+sides,a+sides))
        self.f.append(tuple(start+j for j in reversed(range(sides))))
        self.f.append(tuple(start+(len(pts)-1)*sides+j for j in range(sides)))

    def leaf(self, start, end, width, twist=0):
        """Closed folded lamina: asymmetric serrated edges, central ridge, curled tip."""
        start, end = Vector(start), Vector(end)
        d = end-start
        axis = d.normalized()
        ref = Vector((0, -1, .2))
        a = axis.cross(ref).normalized()
        if a.length < .1: a = axis.cross(Vector((1,0,0))).normalized()
        n = a.cross(axis).normalized()
        a, n = a*math.cos(twist)+n*math.sin(twist), n*math.cos(twist)-a*math.sin(twist)
        base = len(self.v)
        for layer in (1, -1):
            for i in range(4):
                t = i/3
                breadth = max(.012, math.sin(math.pi*t)**.72)*width/2
                for side in (-1,0,1):
                    asym = 1 + .12*math.sin(i*4.3+side)
                    p = start+d*t + a*side*breadth*asym
                    p += n*(width*.23*math.sin(math.pi*t)*(1-abs(side)) + width*.15*t*t + layer*.0025)
                    self.vert(p, ((side+1)/2,t))
        for layer in range(2):
            for i in range(3):
                for j in range(2):
                    k=base+layer*12+i*3+j
                    face=(k,k+1,k+4,k+3)
                    self.f.append(face if layer==0 else tuple(reversed(face)))
        boundary=[0,1,2,5,8,11,10,9,6,3]
        for i, aidx in enumerate(boundary):
            bidx=boundary[(i+1)%len(boundary)]
            self.f.append((base+aidx,base+aidx+12,base+bidx+12,base+bidx))


def rock(root, mats, sx, sy, height):
    mesh=Mesh(); sides=15
    for row, (r,z) in enumerate(((.76,0),(1,.09),(.94,.52),(.63,.9),(.08,1))):
        for j in range(sides):
            a=TAU*j/sides; noise=1+.1*math.sin(j*7.4+row*3.2)
            mesh.vert((sx*r*math.cos(a)*noise,sy*r*math.sin(a)*noise,height*z), (j/sides,row/4))
    for row in range(4):
        for j in range(sides):
            a=row*sides+j; b=row*sides+(j+1)%sides
            mesh.f.append((a,b,b+sides,a+sides))
    mesh.f.extend([tuple(reversed(range(sides))),tuple(4*sides+j for j in range(sides))])
    obj=mesh.object('Earthy fractured rootstone',mats['rock'],root)
    bevel=obj.modifiers.new('Soft weathered fracture edges','BEVEL'); bevel.width=.018; bevel.segments=2


def fern(root, mats):
    rock(root,mats,.58,.34,.22)
    stems=Mesh(); leaves=[Mesh(),Mesh()]
    for j in range(10):
        a=TAU*j/10+.16; extent=.72+.19*RNG.random()
        pts=[]
        for k in range(13):
            t=k/12
            pts.append(Vector((math.cos(a)*extent*t,math.sin(a)*extent*t*.72,.15+.83*math.sin(t*1.7))))
        stems.tube(pts,[.019*(1-k/14) for k in range(13)],6)
        side=Vector((-math.sin(a),math.cos(a),0))
        for k in range(3,10):
            t=k/12; p=pts[k]
            length=.30*(1-t)**.45
            for sign in (-1,1):
                tip=p+side*length*sign+Vector((math.cos(a)*.11,math.sin(a)*.11,.055))
                leaves[(k+j)%2].leaf(p,tip,.12*(1-t*.55),sign*.23)
    stems.object('Ten arched fern rachises',mats['stem'],root)
    for i,m in enumerate(leaves):m.object('Paired folded pinnae '+str(i),mats['leaf'+str(i)],root)


def vine(root,mats):
    rock(root,mats,.3,.25,.24)
    stalk=Mesh(); leaves=[Mesh(),Mesh()]; tendrils=Mesh()
    for strand in range(2):
        pts=[Vector((.09*math.sin(k*.34+strand*math.pi),.075*math.cos(k*.34+strand*math.pi),.13+k*.075)) for k in range(37)]
        stalk.tube(pts,[.035-k*.00065 for k in range(37)],8)
        for k in range(3,36,2):
            p=pts[k]; sign=(-1)**(k//2+strand)
            end=p+Vector((sign*(.30+RNG.random()*.16),-.14 if strand==0 else .14,.18))
            mid=p.lerp(end,.22)
            stalk.tube([p,mid],[.014,.008],5)
            leaves[(k+strand)%2].leaf(mid,end,.27,RNG.uniform(-.35,.35))
        for k in (7,17,27):
            p=pts[k]; sign=(-1)**k
            curl=[p+Vector((sign*(.035*t+.06*math.sin(t)),.06*(1-math.cos(t)),.025*t)) for t in [i*.32 for i in range(24)]]
            tendrils.tube(curl,[.009*(1-i/26) for i in range(24)],5)
    stalk.object('Twining living stems and petioles',mats['stem'],root)
    tendrils.object('Six helical climbing tendrils',mats['stem'],root)
    for i,m in enumerate(leaves):m.object('Alternating cupped vine leaves '+str(i),mats['leaf'+str(i)],root)


def mushroom_tree(root,mats):
    rock(root,mats,.78,.58,.3)
    trunk=Mesh()
    pts=[(.10*math.sin(i*.6),.04*math.sin(i),.13+i*.19) for i in range(12)]
    trunk.tube(pts,[.29-.013*i+.025*math.sin(i*1.4) for i in range(12)],14)
    for j in range(7):
        a=j*TAU/7
        trunk.tube([(0,0,.6),(.30*math.cos(a),.26*math.sin(a),.26),(.66*math.cos(a),.49*math.sin(a),.10)],[.10,.08,.025],7)
    trunk.object('Fluted stem and buttress roots',mats['stem'],root)
    cap=Mesh(); N=48
    profile=[(.02,2.86),(.32,2.84),(.68,2.70),(.89,2.47),(1,2.16),(.98,2.06),(.88,2.01),(.60,2.04),(.24,2.15),(.02,2.19)]
    for row,(r,z) in enumerate(profile):
        for j in range(N):
            a=TAU*j/N; w=1+.017*math.sin(7*a)+.012*math.sin(11*a+.8)
            cap.vert((1.85*r*math.cos(a)*w,.99*r*math.sin(a)*w,z+.022*r*math.sin(a*9)),(j/N,row/(len(profile)-1)))
    for row in range(len(profile)-1):
        for j in range(N):
            a=row*N+j; b=row*N+(j+1)%N
            cap.f.append((a,a+N,b+N,b))
    cap.f.append(tuple(range(N)))
    cap.f.append(tuple(reversed([(len(profile)-1)*N+j for j in range(N)])))
    cap.object('Lobed moss-green mushroom crown',mats['leaf0'],root)
    gills=Mesh()
    for j in range(40):
        a=TAU*j/40
        points=[(1.85*r*math.cos(a),.99*r*math.sin(a),z) for r,z in ((.12,2.15),(.35,2.06),(.65,2.005),(.90,2.00),(.97,2.065))]
        gills.tube(points,[.012,.024,.03,.024,.009],4)
    gills.object('Forty raised radial underside gills',mats['gill'],root)
    leaves=[Mesh(),Mesh()]
    for j in range(82):
        a=j*2.399963; r=math.sqrt((j+.5)/82)*.98
        p=Vector((1.82*r*math.cos(a),.98*r*math.sin(a),2.13+.74*math.sqrt(1-r*r)))
        end=p+Vector((.24*math.cos(a+.7),.16*math.sin(a+.7),.10))
        leaves[j%2].leaf(p,end,.23,RNG.uniform(-.4,.4))
    for i,m in enumerate(leaves):m.object('Layered canopy leaf rosettes '+str(i),mats['leaf'+str(i)],root)


SPECS={
 'fern':((2,1.35,1),fern,['TILE1_LITTLE_BUSH','TILE3_BGBUSH_L/M/R'],['10 arched fronds','140 closed folded pinnae','weathered rootstone']),
 'vine':((1.1,.65,3),vine,['TILE1_VINE','OBJ_GROWINGVINE'],['two twining stems','alternating closed leaves','six coil tendrils','rootstone']),
 'mushroom-tree':((4,2.2,3),mushroom_tree,['TILE1_BUSH_UL/UR','TILE11_HILL_PEAK'],['lobed canopy','82 folded leaves','40 underside gills','fluted stem','buttress roots'])}


def normalize(root, dims):
    objects=list(root.children)
    coords=[v.co.copy() for o in objects if o.type=='MESH' for v in o.data.vertices]
    low=Vector(tuple(min(v[i] for v in coords) for i in range(3)))
    high=Vector(tuple(max(v[i] for v in coords) for i in range(3)))
    center=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
    scale=Vector(tuple(dims[i]/(high[i]-low[i]) for i in range(3)))
    for o in objects:
        for v in o.data.vertices:
            p=v.co-center; v.co=Vector(tuple(p[i]*scale[i] for i in range(3)))
        o.data.update()
    return objects


def inspect(path):
    import struct
    raw=path.read_bytes(); length,kind=struct.unpack_from('<II',raw,12)
    assert kind==0x4e4f534a
    doc=json.loads(raw[20:20+length])
    assert all('bufferView' in image for image in doc.get('images',[])), 'Nonembedded images'
    for mat in doc.get('materials',[]):
        assert 'baseColorTexture' in mat.get('pbrMetallicRoughness',{}), 'Missing albedo'
        assert 'metallicRoughnessTexture' in mat.get('pbrMetallicRoughness',{}), 'Missing roughness'
        assert 'normalTexture' in mat, 'Missing normal'
    triangles=sum(doc['accessors'][p['indices']]['count']//3 for m in doc.get('meshes',[]) for p in m['primitives'] if 'indices' in p)
    return {'triangles':triangles,'embedded_images':len(doc.get('images',[]))}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve(); (out/'models').mkdir(parents=True,exist_ok=True);(out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    recipes={'leaf0':('leaf','Forest frond','365C27',.78),'leaf1':('leaf','Young frond','668D3B',.72), 'stem':('soil','Fibrous woody stem','756043',.85), 'rock':('stone','Earthy rootstone','655847',.93), 'gill':('soil','Warm mushroom gills','B5A076',.89)}
    mats={key:material(*recipe,out) for key,recipe in recipes.items()}
    records=[]; roots=[]
    for asset_id,(dims,builder,symbols,features) in SPECS.items():
        root=bpy.data.objects.new(asset_id,None);bpy.context.collection.objects.link(root);root['asset_id']=asset_id;root['units']='1 unit = 16 NES pixels';roots.append(root)
        builder(root,mats);objects=normalize(root,dims)
        for obj in objects:obj['asset_id']=asset_id
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [root]+objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        path=out/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_yup=True,export_materials='EXPORT')
        verification=inspect(path)
        records.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':dict(zip(('width','depth','height'),dims)),'materials':sorted({m.name for o in objects for m in o.data.materials}),'mesh_features':features,'source_basis':{'catalog':'smb3-rom-assets/catalog','symbols':symbols,'visual_reference':'observed-metatile-00.png: rounded green bush crowns and layered borders','interpretation':'Botanical interpretation; fern and mushroom-tree are not verified exact named ROM objects.'},'known_quality_limitations':['Central queue render review pending; no visual quality claim.','Deterministic material swatches are not photographic scans.','Thin closed leaves use low polygon folded laminae; no botanical vein scan.','Nominal bounds exclude small rock bevel changes.'], 'export_verification':verification})
    for i,root in enumerate(roots):root.location.x=i*5
    bpy.ops.object.select_all(action='DESELECT')
    for root in roots:root.select_set(True)
    bpy.context.view_layer.objects.active=roots[0]
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    style=json.loads((SHARED/'design/style.json').read_text()) if (SHARED/'design/style.json').exists() else {'units':'Blender Z up; front -Y'}
    (out/'manifest.json').write_text(json.dumps({'assets':records,'style_contract':style,'warnings':WARNINGS,'library_layout':'Roots spaced 5 units along X; GLBs independently exported at origin.'},indent=2))

if __name__=='__main__':main()
