"""Editable Mario fallback kit. Execute only through the central Blender queue."""
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
ASSETS = ['mario-body', 'mario-cap', 'mario-boot']
WARNINGS = []
M = {}
ROOT = None


def mesh(name, vertices, faces, material, uvs=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = ROOT
    data.materials.append(M[material])
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        coords = [uvs[data.loops[i].vertex_index] for i in poly.loop_indices] if uvs else [
            (vertices[data.loops[i].vertex_index][0] * 2,
             vertices[data.loops[i].vertex_index][2] * 2) for i in poly.loop_indices]
        if uvs and max(u for u, v in coords) - min(u for u, v in coords) > .7:
            coords = [(u + 1 if u < .3 else u, v) for u, v in coords]
        for i, uv in zip(poly.loop_indices, coords):
            layer.data[i].uv = uv
    return obj


def rings(name, profile, material, n=32, caps=True):
    # Entries: center x/y/z, x radius, y radius. All dimensions in mesh space.
    verts, uv = [], []
    for i, (x, y, z, rx, ry) in enumerate(profile):
        for j in range(n):
            a = TAU * j / n
            verts.append((x + rx * math.cos(a), y + ry * math.sin(a), z))
            uv.append((j / n, i / max(1, len(profile) - 1)))
    faces = []
    for i in range(len(profile)-1):
        for j in range(n):
            a = i*n+j; b = i*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    if caps:
        faces.extend([tuple(reversed(range(n))), tuple((len(profile)-1)*n+j for j in range(n))])
    return mesh(name, verts, faces, material, uv)


def oval(name, center, radii, mat, n=24, rows=12):
    x,y,z = center; rx,ry,rz = radii
    return rings(name, [(x,y,z-rz*math.cos(math.pi*i/rows),
                         max(.0001,rx*math.sin(math.pi*i/rows)),
                         max(.0001,ry*math.sin(math.pi*i/rows))) for i in range(rows+1)],mat,n)


def tube(name, points, radius, mat, sides=6):
    pts = [Vector(p) for p in points]
    vv, uv = [], []
    for i,p in enumerate(pts):
        tangent = (pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        ref = Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
        u = tangent.cross(ref).normalized(); v = tangent.cross(u).normalized()
        r = radius[i] if isinstance(radius,list) else radius
        for j in range(sides):
            vv.append(tuple(p+r*(math.cos(TAU*j/sides)*u+math.sin(TAU*j/sides)*v)))
            uv.append((j/sides,i/max(1,len(pts)-1)))
    ff=[]
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            ff.append((a,b,b+sides,a+sides))
    ff += [tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+j for j in range(sides))]
    return mesh(name,vv,ff,mat,uv)


def stitches(name, points, radius=.0015, mat='thread', step=2):
    # Batch independent stitch capsules into one editable mesh.
    vv=[]; ff=[]; uv=[]
    for i in range(0,len(points)-1,step):
        p=Vector(points[i]); q=Vector(points[i+1]); t=(q-p).normalized()
        ref=Vector((0,0,1)) if abs(t.z)<.9 else Vector((0,1,0))
        u=t.cross(ref).normalized(); v=t.cross(u).normalized(); base=len(vv)
        for k,c in enumerate((p,q)):
            for j in range(4):
                vv.append(tuple(c+radius*(u*math.cos(TAU*j/4)+v*math.sin(TAU*j/4))))
                uv.append((j/4,k))
        for j in range(4):ff.append((base+j,base+(j+1)%4,base+4+(j+1)%4,base+4+j))
        ff.extend([(base+3,base+2,base+1,base),tuple(base+4+j for j in range(4))])
    return mesh(name,vv,ff,mat,uv)


def curve_points(a,b,count=32,bow=0):
    return [(a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t-bow*math.sin(math.pi*t),a[2]+(b[2]-a[2])*t) for t in [i/(count-1) for i in range(count)]]


def panel(name, points, material, thickness=.007, bevel=.005):
    obj=mesh(name,points,[tuple(range(len(points)))],material)
    solid=obj.modifiers.new('Sewn panel thickness','SOLIDIFY'); solid.thickness=thickness
    if bevel:
        mod=obj.modifiers.new('Soft panel edge','BEVEL');mod.width=bevel;mod.segments=3
    return obj


def fallback_material(name,color,rough,metal,out):
    # Deterministic texture maps, not procedural-only nodes. Packed and exportable.
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF'); bs.inputs['Metallic'].default_value=metal
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    for channel in ('basecolor','roughness','normal'):
        im=bpy.data.images.new(name+'_'+channel,width=512,height=512,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        pix=array('f')
        for y in range(512):
            for x in range(512):
                sx=math.sin(TAU*x/8); sy=math.sin(TAU*y/8)
                grain=math.sin(x*12.9898+y*78.233)*43758.5453; grain=grain-math.floor(grain)-.5
                f=.94+.04*sx*sy+.035*grain
                if channel=='basecolor': c=[min(1,t*f) for t in rgb]
                elif channel=='roughness': c=[min(1,max(0,rough+.035*sx*sy+.03*grain))]*3
                else:
                    nx=.07*math.cos(TAU*x/8)*sy; ny=.07*sx*math.cos(TAU*y/8)
                    normal=Vector((nx,ny,1)).normalized(); c=[t*.5+.5 for t in normal]
                pix.extend((*c,1))
        im.pixels.foreach_set(pix); im.filepath_raw=str(out/(name+'_'+channel+'.png')); im.file_format='PNG'; im.save(); im.pack()
        node=mat.node_tree.nodes.new('ShaderNodeTexImage'); node.image=im
        if channel=='normal':
            normal=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(node.outputs['Color'],normal.inputs['Color']);mat.node_tree.links.new(normal.outputs['Normal'],bs.inputs['Normal'])
        else:mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked']=True;mat['fallback_texture_maps']=True
    return mat


def materials(out):
    recipes={
        'red':('cloth','B92522',.83,0), 'denim':('cloth','254C78',.87,0),
        'skin':('leather','E8AD82',.53,0), 'hair':('leather','332019',.8,0),
        'white':('leather','E9E2D0',.55,0), 'leather':('leather','633D28',.55,0),
        'rubber':('leather','241D19',.88,0), 'thread':('cloth','B8A176',.9,0),
        'brass':('worn_brass','B68A42',.37,.86), 'iris':('leather','326C93',.32,0),
        'pupil':('leather','101010',.3,0)}
    for name,(kind,color,rough,metal) in recipes.items():
        try:
            if pbr is None: raise RuntimeError('shared helper unavailable')
            M[name]=pbr.material(kind,name='Mario_'+name,color=color,roughness=rough,metallic=metal,bump=.004 if name in ('skin','white','iris','pupil') else .010,bake=True,resolution=512,cache_dir=out)
        except Exception as exc:
            WARNINGS.append(f'{name}: deterministic texture fallback: {exc}')
            M[name]=fallback_material(name,color,rough,metal,out)


def cap(origin=(0,0,0),scale=1,prefix='Cap'):
    before=set(ROOT.children)
    # Open underside with interior lining: profile returns down the inner wall.
    prof=[(0,0,.035,.214,.186),(0,0,.065,.230,.199),(0,.01,.13,.225,.192),
          (0,.016,.19,.175,.155),(0,.015,.23,.090,.085),(0,.015,.241,.003,.003),
          (0,.015,.229,.003,.003),(0,.015,.217,.084,.078),(0,.016,.178,.161,.142),
          (0,.01,.12,.211,.178),(0,0,.054,.216,.185),(0,0,.035,.201,.173)]
    rings(prefix+'_hollow_six_panel_crown',prof,'red',40,False)
    rings(prefix+'_sweatband',[(0,0,.035,.201,.173),(0,0,.059,.203,.175),(0,0,.059,.195,.167),(0,0,.035,.195,.167),(0,0,.035,.201,.173)],'leather',40,False)
    # Curved visor grid; solidify gives a real rim.
    verts=[]; faces=[]; uv=[]
    for i in range(7):
        t=i/6
        for j in range(25):
            a=-math.pi/2+math.pi*j/24
            x=math.sin(a)*(.204+.030*t)
            y=-.075-math.cos(a)*(.115+.174*t)
            z=.038+.019*math.cos(a)-.024*t*t
            verts.append((x,y,z));uv.append((j/24,t))
    for i in range(6):
        for j in range(24):
            a=i*25+j;faces.append((a,a+1,a+26,a+25))
    visor=mesh(prefix+'_curved_visored_brim',verts,faces,'red',uv)
    mod=visor.modifiers.new('Bound visor thickness','SOLIDIFY');mod.thickness=.013
    for t in (.88,.98):
        pts=[(math.sin(a)*(.204+.030*t),-.075-math.cos(a)*(.115+.174*t),.04+.019*math.cos(a)-.024*t*t) for a in [-math.pi/2+math.pi*j/80 for j in range(81)]]
        stitches(prefix+'_visor_topstitch',pts,.0012)
    for j in range(6):
        a=TAU*j/6
        pts=[]
        for i in range(31):
            t=i/30; ang=t*math.pi/2
            pts.append((.228*math.cos(ang)*math.cos(a),.012+.195*math.cos(ang)*math.sin(a),.067+.177*math.sin(ang)))
        tube(prefix+'_crown_seam',pts,.0024,'red',5)
        stitches(prefix+'_crown_stitches',[(x+.003,y,z+.001) for x,y,z in pts],.001)
    oval(prefix+'_top_button',(0,.015,.244),(.025,.025,.012),'red',20,8)
    oval(prefix+'_white_badge',(0,-.193,.133),(.068,.012,.067),'white',32,14)
    tube(prefix+'_embroidered_M',[(-.040,-.208,.098),(-.032,-.209,.163),(0,-.209,.126),(.032,-.209,.163),(.040,-.208,.098)],.009,'red',8)
    for obj in set(ROOT.children)-before:
        for v in obj.data.vertices:v.co=Vector(origin)+scale*v.co
        for mod in obj.modifiers:
            if mod.type=='SOLIDIFY':mod.thickness*=scale
            if mod.type=='BEVEL':mod.width*=scale


def boot(origin=(0,0,0),scale=1,prefix='Boot'):
    before=set(ROOT.children)
    rings(prefix+'_layered_outsole',[(0,-.065,.008,.113,.191),(0,-.065,.020,.123,.200),(0,-.065,.049,.123,.200),(0,-.063,.061,.115,.192)],'rubber',36)
    rings(prefix+'_leather_welt',[(0,-.063,.05,.124,.201),(0,-.063,.064,.125,.202),(0,-.063,.074,.116,.193)],'leather',40)
    # Sculpted toe/vamp flowing into a narrower ankle shaft.
    rings(prefix+'_lasted_upper',[(0,-.063,.066,.115,.191),(0,-.067,.105,.119,.188),(0,-.065,.148,.112,.178),
        (0,-.040,.18,.103,.150),(0,.005,.212,.089,.105),(0,.020,.28,.085,.090),
        (0,.020,.29,.084,.089),(0,.020,.29,.072,.077),(0,.020,.253,.072,.077)],'leather',36,False)
    rings(prefix+'_rolled_shaft_cuff',[(0,.02,.275,.085,.091),(0,.02,.292,.087,.093),(0,.02,.298,.080,.085),(0,.02,.289,.072,.077)],'leather',32,False)
    pts=[(.125*math.cos(a),-.063+.202*math.sin(a),.066) for a in [TAU*j/120 for j in range(121)]]
    stitches(prefix+'_welt_lockstitch',pts,.0018)
    for side in (-1,1):
        pts=curve_points((side*.082,.057,.269),(side*.108,-.090,.107),40,.028)
        tube(prefix+'_quarter_panel_piping',pts,.003,'leather')
        stitches(prefix+'_quarter_seam',[(x+side*.003,y,z) for x,y,z in pts],.0014)
    # Heel block and transverse tread ribs use solid mesh geometry.
    for j in range(7):
        y=-.215+j*.048
        panel(prefix+'_traction_lug', [(-.077,y,.006),(.077,y,.006),(.087,y+.017,.006),(-.087,y+.017,.006)],'rubber',.012,.003)
    panel(prefix+'_heel_pull_tab',[(-.019,.103,.20),(.019,.103,.20),(.018,.12,.31),(-.018,.12,.31)],'leather',.012,.004)
    for obj in set(ROOT.children)-before:
        for v in obj.data.vertices:v.co=Vector(origin)+scale*v.co
        for mod in obj.modifiers:
            if mod.type=='SOLIDIFY':mod.thickness*=scale
            if mod.type=='BEVEL':mod.width*=scale


def glove(x):
    s=1 if x>0 else -1
    rings('Glove_padded_cuff',[(x,0,.56,.072,.070),(x,0,.60,.078,.077),(x,0,.635,.067,.068)],'white',24)
    oval('Glove_palm',(x,-.015,.516),(.079,.068,.097),'white',24,12)
    for j in range(4):
        xx=x+(j-1.5)*.033
        tube('Glove_curled_finger',[(xx,-.019,.529),(xx,-.061,.502),(xx,-.060,.465),(xx,-.03,.452)], [.022,.023,.022,.016],'white',8)
    tube('Glove_thumb',[(x-s*.051,-.003,.559),(x-s*.091,-.054,.53),(x-s*.069,-.078,.495)],[.030,.029,.020],'white',10)
    for j in range(3):
        tube('Glove_back_crease',[(x+(j-1)*.025,.047,.495),(x+(j-1)*.025,.052,.54)],.002,'thread',5)


def body():
    # Continuous ring-shaped garment volumes overlap at natural anatomical joins.
    rings('Red_shirt_torso',[(0,0,.59,.14,.13),(0,0,.68,.23,.169),(0,.005,.84,.246,.171),(0,.008,.98,.205,.148),(0,.005,1.034,.141,.113),(0,0,1.043,.100,.089)],'red',36)
    rings('Denim_waist_and_seat',[(0,.008,.44,.163,.130),(0,0,.52,.211,.154),(0,-.003,.65,.244,.175),(0,-.002,.77,.236,.174)],'denim',36)
    for s in (-1,1):
        x=s*.119
        rings('Denim_trouser_leg',[(x,.016,.19,.084,.082),(x,.015,.24,.092,.091),(x,.012,.32,.098,.095),(x,.006,.43,.109,.111),(x,.01,.55,.113,.128)],'denim',28)
        for z in (.25,.27):
            pts=[(x+.094*math.cos(a),.015+.092*math.sin(a),z) for a in [TAU*j/60 for j in range(61)]]
            stitches('Trouser_hem_stitches',pts,.0015)
        stitches('Trouser_outseam',curve_points((x+s*.091,.01,.28),(x+s*.101,.01,.52),35),.0017)
        boot((x,-.019,0),.84,'Worn_boot')
        # Bent downward sleeve: hands are separated slightly from the hips.
        tube('Shirt_relaxed_sleeve',[(s*.176,.015,.949),(s*.258,.01,.91),(s*.299,.005,.813),(s*.325,-.007,.712),(s*.347,-.009,.621)],[.097,.103,.088,.074,.063],'red',16)
        glove(s*.351)
        pts=[(s*.11,-.162,.76),(s*.129,-.157,.88),(s*.145,-.126,.991),(s*.14,-.04,1.03),(s*.139,.083,1.005),(s*.142,.139,.89),(s*.137,.156,.764)]
        # Flattened strap ribbon follows shoulder front to back.
        vv=[]
        for x,y,z in pts:vv.extend([(x-.031,y,z),(x+.031,y,z)])
        strap=mesh('Overalls_shoulder_strap',vv,[(i*2,i*2+1,i*2+3,i*2+2) for i in range(len(pts)-1)],'denim')
        mod=strap.modifiers.new('Strap fabric thickness','SOLIDIFY');mod.thickness=.009
        for dx in (-.023,.023):
            for a,b in zip(pts,pts[1:]):stitches('Strap_edge_stitch',curve_points((a[0]+dx,a[1]-.004,a[2]),(b[0]+dx,b[1]-.004,b[2]),12),.0013)
        oval('Brass_dungaree_button',(s*.123,-.183,.839),(.025,.011,.025),'brass',20,8)
        tube('Button_recess',[(s*.123-.010,-.195,.84),(s*.123+.010,-.195,.84)],.002,'hair',5)
    panel('Raised_denim_bib',[(-.177,-.167,.70),(.177,-.167,.70),(.164,-.163,.867),(-.164,-.163,.867)],'denim',.015,.008)
    panel('Bib_patch_pocket',[(-.076,-.182,.747),(0,-.187,.729),(.076,-.182,.747),(.076,-.181,.814),(-.076,-.181,.814)],'denim',.007,.005)
    for a,b in [((-.071,-.190,.805),(-.071,-.190,.752)),((-.071,-.190,.752),(0,-.195,.735)),((0,-.195,.735),(.071,-.190,.752)),((.071,-.190,.752),(.071,-.190,.805))]:
        stitches('Pocket_lockstitch',curve_points(a,b,20),.0012)
    rings('Neck',[(0,0,.995,.082,.08),(0,-.003,1.11,.091,.087)],'skin',24)
    # Sculpted broad jaw, cheek and forehead silhouette, not a spherical head.
    rings('Head_sculpt',[(0,-.001,1.032,.065,.066),(0,-.018,1.057,.118,.103),(0,-.018,1.105,.165,.132),
        (0,-.010,1.18,.188,.149),(0,0,1.26,.182,.148),(0,.007,1.322,.162,.131),(0,.01,1.362,.105,.090),(0,.01,1.375,.007,.009)],'skin',40)
    for s in (-1,1):
        oval('Ear',(s*.184,.0,1.198),(.042,.035,.060),'skin',20,10)
        tube('Ear_concha',[(s*.19,-.031,1.168),(s*.207,-.032,1.194),(s*.197,-.033,1.222)],.005,'leather',6)
        oval('Sideburn',(s*.169,.029,1.24),(.026,.090,.075),'hair',16,10)
        oval('Eye_sclera',(s*.069,-.141,1.249),(.048,.024,.063),'white',24,12)
        oval('Blue_iris',(s*.065,-.164,1.251),(.024,.009,.039),'iris',20,10)
        oval('Pupil',(s*.065,-.173,1.251),(.012,.004,.027),'pupil',16,8)
        oval('Eye_catchlight',(s*.065-.005,-.177,1.267),(.006,.002,.009),'white',12,6)
        tube('Expressive_brow',[(s*.024,-.15,1.316),(s*.058,-.161,1.330),(s*.093,-.151,1.327),(s*.114,-.137,1.31)],[.010,.016,.015,.006],'hair',8)
    oval('Bulbous_nose',(0,-.187,1.194),(.068,.073,.060),'skin',28,14)
    tube('Smile_crease',[(-.068,-.143,1.103),(0,-.159,1.087),(.068,-.143,1.103)],.004,'leather',6)
    # A scalloped moustache surface swept across the upper lip.
    pts=[]; rad=[]
    for i in range(25):
        t=i/24; x=-.119+.238*t
        pts.append((x,-.163-.018*math.sin(math.pi*t),1.151-.014*math.sin(math.pi*t)))
        rad.append(.008+.021*math.sin(math.pi*t)+.009*abs(math.sin(6*math.pi*t)))
    tube('Six_lobed_moustache',pts,rad,'hair',12)
    for i in range(17):
        x=-.104+i*.013
        tube('Moustache_hair_ridge',[(x,-.193,1.156),(x*.99,-.199,1.138)],.0011,'hair',4)
    cap((0,.008,1.292),1,'Worn_cap')


def normalize(root,height=None):
    # Bake root normalization into vertices; root stays exactly at ground origin.
    verts=[v.co.copy() for o in root.children if o.type=='MESH' for v in o.data.vertices]
    lo=Vector(tuple(min(v[k] for v in verts) for k in range(3)))
    hi=Vector(tuple(max(v[k] for v in verts) for k in range(3)))
    fac=height/(hi.z-lo.z) if height else 1
    center=Vector(((hi.x+lo.x)/2,(hi.y+lo.y)/2,lo.z))
    for o in root.children:
        if o.type=='MESH':
            for v in o.data.vertices:v.co=(v.co-center)*fac
            for mod in o.modifiers:
                if mod.type=='SOLIDIFY':mod.thickness*=fac
                if mod.type=='BEVEL':mod.width*=fac
    return [round((hi[k]-lo[k])*fac,5) for k in range(3)]


def main():
    global ROOT
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve();(out/'models').mkdir(parents=True,exist_ok=True);(out/'materials').mkdir(exist_ok=True)
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    materials(out/'materials')
    entries=[];roots=[]
    for asset_id,builder in zip(ASSETS,(body,cap,boot)):
        ROOT=bpy.data.objects.new(asset_id,None);bpy.context.collection.objects.link(ROOT);ROOT['asset_id']=asset_id;ROOT['front']='-Y';ROOT['units']='1 unit = 16 NES pixels';roots.append(ROOT)
        builder()
        # Apply only thickness/bevel to geometry before measuring: no subsurf explosion.
        for obj in list(ROOT.children):
            bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
            for modifier in list(obj.modifiers):bpy.ops.object.modifier_apply(modifier=modifier.name)
        dims=normalize(ROOT,1.5 if asset_id=='mario-body' else None)
        objects=[ROOT]+list(ROOT.children)
        for obj in objects:obj['asset_id']=asset_id
        path=out/'models'/f'{asset_id}.glb'
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=ROOT
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
        used=sorted({m.name for obj in ROOT.children for m in obj.data.materials})
        tris=0
        for obj in ROOT.children:obj.data.calc_loop_triangles();tris+=len(obj.data.loop_triangles)
        audit=pbr.inspect_glb(path) if pbr and hasattr(pbr,'inspect_glb') else None
        if audit:
            assert not audit['externalImageURIs'], 'GLB contains external image references'
            assert audit['normalTextureMaterials']==audit['materials'], 'Missing exported normal textures'
            assert audit['roughnessTextureMaterials']==audit['materials'], 'Missing roughness textures'
            assert audit['baseColorTextureMaterials']==audit['materials'], 'Missing albedo textures'
        entries.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominaldimensions':dims,'dimensions_order':'XYZ, Blender Z-up','materials':used,'triangles':tris,
            'meshfeatures':{'mario-body':['Sculpted ring topology head and clothed torso','Relaxed bent sleeves and padded fingered leather gloves','Dimensional scalloped moustache, eyes, brows and nose','Bib pocket, shoulder straps, brass buttons and separate lockstitches','Detailed cap and welted boots'], 'mario-cap':['Hollow crown and sweatband','Curved thick visor','Six raised panel seams and separate stitches','White dimensional badge with raised red M'], 'mario-boot':['Lasted leather vamp and ankle shaft','Open lined ankle collar','Welt lockstitch and quarter seams','Layered outsole, tread lugs and heel pull tab']}[asset_id],
            'sourcebasis':['Shared design/style.json','catalog/observed-player-pose-00.png: observed compact Mario cap/nose/boot silhouette','catalog/README.md: runtime observed composites preferred to diagnostic templates', 'observed-assets.json: observed-player-pose-d7804d3e8042e9765221, 16x16 runtime pose','Requested red shirt, blue overalls and white M badge; material/construction details are authored interpretation'],
            'knownqualitylimitations':['Authored fallback; no Blender execution or render inspected by author','Static multipart mesh; overlapping anatomical joins, no rig or deformation weights','Fine stitches may require distance LOD','Tail and protective shell excluded: other forms outside assigned asset IDs','Slip-on Mario boots intentionally omit laces'], 'export_audit':audit})
    # Inspection layout only after all origin-centered exports are complete.
    for root,x in zip(roots,(0,1.15,1.85)):root.location.x=x
    bpy.ops.object.select_all(action='DESELECT')
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file:image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':entries,'material_warnings':WARNINGS,'style_contract':str(SHARED/'design/style.json'),'inspection_layout':'Roots offset along X in library only; GLBs bottom-centered at origin'},indent=2))

if __name__=='__main__':main()
