"""World-map prop family. Run only through the central Blender build queue."""
import argparse
import json
import math
import sys
from array import array
from pathlib import Path

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools')
sys.path.insert(0, str(SHARED))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

ASSETS = ['map-bridge', 'map-lock', 'map-boat']
CATALOG = '/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-rom-assets/catalog'
WARNINGS = []
PARTS = []
MAT = {}
OUT = None


def texture_material(name, rgb, roughness, metallic=0, wood=False):
    """Deterministic tileable image PBR fallback; wood uses directional growth grain."""
    n = 512
    heights = []
    for y in range(n):
        v = y / n
        for x in range(n):
            u = x / n
            warp = .23 * math.sin(2*math.pi*u) + .10*math.sin(6*math.pi*u)
            grain = math.sin(2*math.pi*(v*34 + warp))
            fine = math.sin(2*math.pi*(u*113+v*79)) * math.sin(2*math.pi*(v*131-u*47))
            coarse = math.sin(2*math.pi*(u*5+v*3)) * math.cos(2*math.pi*(v*7-u*2))
            heights.append(.5 + (.28*grain + .08*fine + .09*coarse if wood else .22*fine+.18*coarse))
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    links = material.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                h = heights[y*n+x]
                if channel == 'basecolor':
                    value = tuple(min(1, c*(.76+.40*h)) for c in rgb)
                elif channel == 'roughness':
                    r = max(.05, min(1, roughness+(h-.5)*.22))
                    value = (r,r,r)
                else:
                    dx = heights[y*n+(x+1)%n]-heights[y*n+(x-1)%n]
                    dy = heights[((y+1)%n)*n+x]-heights[((y-1)%n)*n+x]
                    normal = Vector((-dx*.65,-dy*.65,1)).normalized()
                    value = tuple(c*.5+.5 for c in normal)
                pixels.extend((*value,1))
        img = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        img.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        img.pixels.foreach_set(pixels)
        img.filepath_raw = str(OUT/'materials'/f'{name}-{channel}.png')
        img.file_format = 'PNG'
        img.save()
        img.pack()
        node = nodes.new('ShaderNodeTexImage')
        node.image = img
        node.extension = 'REPEAT'
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(node.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(node.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    material['pbr_baked'] = True
    material['texture_method'] = 'deterministic tileable image synthesis'
    return material


def material(name, kind, color, roughness, metallic=0):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=metallic, bake=True, resolution=512,
                                cache_dir=OUT/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed; image fallback used: {exc}')
    rgb = tuple(int(color[i:i+2],16)/255 for i in (0,2,4))
    return texture_material(name, rgb, roughness, metallic)


def mesh(name, vertices, faces, mat, smooth=False):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    uv = data.uv_layers.new(name='UVMap')
    # Planar local projections preserve physical grain scale and work without edit operators.
    for poly in data.polygons:
        poly.use_smooth = smooth
        axis = max(range(3), key=lambda a: abs(poly.normal[a]))
        axes = ((1,2),(0,2),(0,1))[axis]
        for loop in poly.loop_indices:
            v = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (v[axes[0]]*.65,v[axes[1]]*.65)
    PARTS.append(obj)
    return obj


def bevel(obj, width=.02, segments=2):
    mod = obj.modifiers.new('Soft worn edges', 'BEVEL')
    mod.width = width
    mod.segments = segments
    return obj


def box(name, pos, size, mat, edge=.015):
    x,y,z = [s/2 for s in size]
    vertices = [(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),
                (-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces = [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    obj = mesh(name, vertices, faces, mat)
    obj.location = pos
    if edge: bevel(obj, edge)
    return obj


def tube(name, points, radius, mat, sides=8):
    points = [Vector(p) for p in points]
    vertices=[]
    for i,p in enumerate(points):
        tangent = (points[min(i+1,len(points)-1)]-points[max(0,i-1)]).normalized()
        reference = Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        a = tangent.cross(reference).normalized()
        b = tangent.cross(a).normalized()
        vertices.extend(tuple(p+radius*(a*math.cos(j*2*math.pi/sides)+b*math.sin(j*2*math.pi/sides))) for j in range(sides))
    faces=[tuple(reversed(range(sides)))]
    for i in range(len(points)-1):
        for j in range(sides):
            k=i*sides+j; q=i*sides+(j+1)%sides
            faces.append((k,q,q+sides,k+sides))
    faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    obj = mesh(name,vertices,faces,mat,True)
    uv = obj.data.uv_layers.active
    for poly in obj.data.polygons:
        for li in poly.loop_indices:
            vi=obj.data.loops[li].vertex_index
            row,col=divmod(vi,sides)
            uv.data[li].uv=(row/max(1,len(points)-1)*2, col/sides)
    return obj


def ring(name, center, radius, minor, mat, plane='XY', count=32):
    pts=[]
    for i in range(count+1):
        t=i/count*2*math.pi
        v = (radius*math.cos(t),radius*math.sin(t),0) if plane=='XY' else (radius*math.cos(t),0,radius*math.sin(t))
        pts.append(tuple(center[j]+v[j] for j in range(3)))
    return tube(name,pts,minor,mat,6)


def bridge():
    wood,rope,iron=MAT['wood'],MAT['rope'],MAT['iron']
    for x in (-1.35,1.35):
        for y in (-.57,.57):
            box('Anchoring timber post',(x,y,.79),(.17,.17,1.58),wood,.022)
            box('Iron foot strap',(x,y,.20),(.183,.183,.16),iron,.009)
            for z in (1.23,1.29,1.35):
                ring('Post rope binding',(x,y,z),.105,.023,rope,count=12)
    def sag(x):return .39+.23*(x/1.35)**2
    for i in range(15):
        x=-1.30+i*2.6/14
        obj=box(f'Deck plank {i+1:02}',(x,0,sag(x)),(.169,1.06,.12),wood,.014)
        obj.rotation_euler[1]=-.12*x
        for y in (-.43,.43):
            tube('Forged deck nail',[(x,y,sag(x)+.053),(x,y,sag(x)+.069)],.021,iron,8)
    for y in (-.57,.57):
        for offset,rad in ((0,.042),(.73,.038)):
            tube('Continuous sagging rope',[(x,y,sag(x)+offset) for x in [-1.35+i*2.7/32 for i in range(33)]],rad,rope,10)
        for i in range(1,10):
            x=-1.35+i*.27
            tube('Vertical rope suspender',[(x,y,sag(x)),(x+.018,y,sag(x)+.35),(x,y,sag(x)+.73)],.024,rope,6)
        # Cross lashings at bridge approaches.
        for x in (-1.25,1.25):
            tube('Approach diagonal lashing',[(x,y,.65),(x*.68,y,1.06)],.026,rope)
    return ['15 individually beveled deck boards','four anchored timber posts','continuous sagging hand and bearer ropes','rope bindings, suspenders, forged nails']


def prism(name, outline, y0,y1, mat):
    n=len(outline)
    vertices=[(x,y,z) for y in (y0,y1) for x,z in outline]
    faces=[tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces.extend((i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n))
    return mesh(name,vertices,faces,mat)


def cut(target,cutter):
    bpy.context.view_layer.objects.active=target
    mod=target.modifiers.new('Actual keyway opening','BOOLEAN')
    mod.operation='DIFFERENCE';mod.solver='EXACT';mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    PARTS.remove(cutter)
    bpy.data.objects.remove(cutter,do_unlink=True)


def lock():
    iron,brass=MAT['iron'],MAT['brass']
    body=box('Cast iron lock case',(0,0,.64),(1.38,.58,1.28),iron,0)
    # A single concave extruded outline gives a connected circular/key-stem hole.
    outline=[(-.11,.34),(.11,.34),(.075,.59)]
    for i in range(29):
        a=math.radians(-60+i*300/28)
        outline.append((.15*math.cos(a),.72+.15*math.sin(a)))
    outline.append((-.075,.59))
    cut(body,prism('Keyway cutter',outline,-.45,.45,iron))
    bevel(body,.065,3)
    # Rim surrounds rather than covers the keyway.
    tube('Raised keyway rim',[(x,-.307,z) for x,z in outline+[outline[0]]],.017,brass,8)
    pts=[(-.47,0,1.15)]
    pts += [(.47*math.cos(math.pi-i*math.pi/28),0,1.70+.47*math.sin(math.pi-i*math.pi/28)) for i in range(29)]
    pts += [(.47,0,1.15)]
    tube('Solid curved steel shackle',pts,.108,iron,16)
    for x in (-.47,.47):
        ring('Shackle socket collar',(x,0,1.29),.123,.028,brass,count=20)
    for y in (-.309,.309):
        for x in (-.50,.50):
            for z in (.23,1.05):
                tube('Case rivet',[(x,y,z),(x,y+math.copysign(.025,y),z)],.045,brass,12)
    for x in (-.67,.67):
        box('Case edge seam',(x,0,.64),(.018,.59,.90),brass,.004)
    return ['rounded iron case','connected through-cut keyhole with raised rim','arched round-section shackle','socket collars and eight case rivets']


def boat():
    wood,trim,iron=MAT['wood'],MAT['darkwood'],MAT['iron']
    # Longitudinal clinker strakes: five separate thick curved planks per side.
    def hull(t,v,side):
        x=-1.38+2.76*t
        width=.045+.61*math.sin(math.pi*t)**.72
        y=side*width*(.18+.82*v)
        z=.13+.18*abs(2*t-1)**2+.68*v**1.35+.13*abs(2*t-1)**3*v
        return (x,y,z)
    for side in (-1,1):
        for band in range(5):
            verts=[]
            for i in range(25):
                t=i/24
                for v in (band/5,(band+1)/5+.012):verts.append(hull(t,v,side))
            faces=[]
            for i in range(24):
                f=(i*2,i*2+2,i*2+3,i*2+1)
                faces.append(f if side==-1 else tuple(reversed(f)))
            obj=mesh(f'Clinker hull side {side} strake {band+1}',verts,faces,wood,True)
            mod=obj.modifiers.new('Real plank thickness','SOLIDIFY');mod.thickness=.037
            bevel(obj,.008,2)
        tube('Continuous gunwale',[hull(i/32,1.035,side) for i in range(33)],.046,trim,10)
    tube('Keel timber',[(-1.39,0,.34),(-1.10,0,.12),(0,0,.065),(1.10,0,.12),(1.39,0,.34)],.065,trim,8)
    for x in (-1.38,1.38):
        tube('Stem post',[(x,0,.26),(x,0,1.035)],.057,trim,10)
    for i in range(7):
        y=(i-3)*.115
        box('Interior floorboard',(0,y,.30),(1.92,.105,.065),wood,.008)
    for x in (-.75,0,.75):
        t=(x+1.38)/2.76
        width=.045+.61*math.sin(math.pi*t)**.72
        box('Thwart seat',(x,0,.73),(.22,width*1.76,.09),wood,.016)
        for side in (-1,1):
            tube('Curved internal frame',[hull(t,v,side) for v in (.05,.24,.45,.65,.90)],.033,trim,8)
            tube('Seat fixing pin',[(x,side*width*.71,.77),(x,side*width*.71,.79)],.022,iron,8)
    for side in (-1,1):
        for i in range(1,12):
            t=i/12
            for v in (.23,.63):
                x,y,z=hull(t,v,side)
                tube('Copper hull fastener',[(x,y,z),(x,y+side*.018,z)],.012,MAT['brass'],6)
    # One stowed oar stays within the low open-boat silhouette.
    tube('Oar shaft',[(-1.10,-.28,.84),(.94,.25,.87)],.026,trim,10)
    blade=box('Oar blade',(-1.07,-.28,.85),(.47,.19,.045),wood,.018)
    blade.rotation_euler[2]=.255
    ring('Bow mooring eye',(1.40,0,.79),.083,.016,iron,plane='XZ',count=20)
    return ['open hollow clinker hull with ten thick curved strakes','raised gunwales, keel and stems','interior floorboards, curved frames and three seats','stowed oar and hull fasteners']


def bounds(objects):
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[ob.matrix_world@Vector(c) for obj in objects for ob in [obj.evaluated_get(deps)] for c in ob.bound_box]
    lo=Vector(tuple(min(p[a] for p in pts) for a in range(3)))
    hi=Vector(tuple(max(p[a] for p in pts) for a in range(3)))
    return lo,hi


def main():
    global OUT,PARTS
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve()
    (OUT/'models').mkdir(parents=True,exist_ok=True)
    (OUT/'materials').mkdir(parents=True,exist_ok=True)
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    MAT['wood']=texture_material('Weathered oak',(.40,.245,.125),.77,wood=True)
    MAT['darkwood']=texture_material('Tarred oak',(.18,.105,.055),.69,wood=True)
    MAT['rope']=material('Hemp rope','cloth','A99870',.92)
    MAT['iron']=material('Pitted forged iron','worn_brass','454950',.48,.88)
    MAT['brass']=material('Aged brass hardware','worn_brass','A17B43',.43,.83)
    records=[]
    for index,(asset_id,builder) in enumerate(zip(ASSETS,(bridge,lock,boat))):
        collection=bpy.data.collections.new(asset_id)
        bpy.context.scene.collection.children.link(collection)
        PARTS=[]
        features=builder()
        root=bpy.data.objects.new(asset_id,None)
        collection.objects.link(root)
        root['asset_id']=asset_id
        for obj in PARTS:
            for col in list(obj.users_collection):col.objects.unlink(obj)
            collection.objects.link(obj)
            obj.parent=root
            obj['asset_id']=asset_id
        bpy.context.view_layer.update()
        lo,hi=bounds(PARTS)
        shift=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
        for obj in PARTS:obj.location+=shift
        bpy.context.view_layer.update()
        dims=[round(v,5) for v in hi-lo]
        bpy.ops.object.select_all(action='DESELECT')
        for obj in [root]+PARTS:obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        path=OUT/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                 export_apply=True,export_extras=True,export_materials='EXPORT')
        tri_count=0
        deps=bpy.context.evaluated_depsgraph_get()
        for obj in PARTS:
            evaluated=obj.evaluated_get(deps)
            data=evaluated.to_mesh();data.calc_loop_triangles()
            tri_count+=len(data.loop_triangles);evaluated.to_mesh_clear()
        records.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb',
                        'nominaldimensions':dims,'dimensions_axes':'Blender XYZ',
                        'materials':sorted({m.name for o in PARTS for m in o.data.materials}),
                        'meshfeatures':features,'triangles':tri_count,
                        'sourcebasis':{'catalog':CATALOG+'/worldmap-assets.json',
                            'visual_reference':'worldmap-metatiles-00.png',
                            'interpretation':'Source-inspired silhouette, not a pixel-exact reconstruction; physical construction follows family brief.',
                            'bridge_context':'WORLDMAP.md: world 3 phases 0/1 bridges down; authored as a fixed span.'},
                        'knownqualitylimitations':['Pending central Blender render and visual inspection.',
                            'No rig, animation or collision mesh.',
                            'Microdetail is tileable image PBR; wear is not individually baked per part.']})
        root.location.x=index*4.3
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'assets':records,'warnings':WARNINGS,
        'units':'1 unit = 1 block = 16 NES pixels','front':'-Y','up':'Z',
        'library_layout':'Roots translated along X for inspection; independent GLBs exported at origin.'},indent=2))


if __name__=='__main__':main()
