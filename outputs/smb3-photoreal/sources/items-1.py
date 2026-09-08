"""Editable collectible family. Run only through the central Blender queue."""
import argparse
import json
import math
from pathlib import Path
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
ASSETS = ['coin', 'super-mushroom', 'one-up', 'super-leaf']
WARNINGS = []
OUT = None
ROOT = None
PARTS = []


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh(name, verts, faces, mat, smooth=True):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.parent = ROOT
    obj['asset_id'] = ROOT['asset_id']
    if mat:
        data.materials.append(mat)
    for face in data.polygons:
        face.use_smooth = smooth
    activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.000001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.02)
    bpy.ops.object.mode_set(mode='OBJECT')
    PARTS.append(obj)
    return obj


def fallback_material(name, color, roughness, metallic):
    """Deterministic image-backed fallback; all three channels survive glTF."""
    from array import array
    n = 256
    rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    rgb = [c/12.92 if c <= .04045 else ((c+.055)/1.055)**2.4 for c in rgb]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    for channel in ['basecolor', 'roughness', 'normal']:
        im = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        values = array('f')
        for y in range(n):
            for x in range(n):
                u,v = x/n,y/n
                wave = math.sin(TAU*13*u)*math.sin(TAU*17*v)
                grain = math.sin(TAU*(71*u+53*v))*.5
                if channel == 'basecolor':
                    px = [c*(.94+.045*wave+.015*grain) for c in rgb]
                elif channel == 'roughness':
                    px = [max(.05,min(.99,roughness+.035*wave+.018*grain))]*3
                else:
                    a = .075*math.cos(TAU*13*u)*math.sin(TAU*17*v)
                    b = .075*math.sin(TAU*13*u)*math.cos(TAU*17*v)
                    vec = Vector((a,b,1)).normalized()
                    px = [.5+.5*t for t in vec]
                values.extend((*px,1))
        im.pixels.foreach_set(values)
        im.filepath_raw = str(OUT/'materials'/f'{name}_{channel}.png')
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = nodes.new('ShaderNodeTexImage'); tex.image = im
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'],bsdf.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic image fallback'
    return mat


def material(name, kind, color, roughness, metallic=0, bump=.006):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=metallic, bump=bump, bake=True,
                                resolution=512, cache_dir=OUT/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed, image fallback used: {exc}')
    return fallback_material(name, color, roughness, metallic)


def lathe(name, profile, mat, n=64, coin=False, milling=False):
    verts=[]
    for row,(r,z) in enumerate(profile):
        for j in range(n):
            a=TAU*j/n
            rr=r
            if milling and row in (3,4):
                rr -= .0038*(.5+.5*math.cos(80*a))
            if coin:
                verts.append((rr*math.cos(a),z,.5+rr*math.sin(a)))
            else:
                verts.append((rr*math.cos(a),rr*math.sin(a)*.78,z))
    faces=[]
    for i in range(len(profile)-1):
        for j in range(n):
            k=(j+1)%n
            faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    return mesh(name,verts,faces,mat)


def tube(name, points, radius, mat, sides=8):
    verts=[]
    for i,p in enumerate(points):
        tangent=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)])
        tangent.normalize()
        axis=Vector((0,1,0))
        if abs(tangent.dot(axis))>.95: axis=Vector((1,0,0))
        u=tangent.cross(axis).normalized();v=tangent.cross(u).normalized()
        r=radius*(1-.55*i/(len(points)-1))
        for j in range(sides):
            verts.append(Vector(p)+r*(u*math.cos(j*TAU/sides)+v*math.sin(j*TAU/sides)))
    faces=[tuple(reversed(range(sides)))]
    for i in range(len(points)-1):
        for j in range(sides):
            k=(j+1)%sides
            faces.append((i*sides+j,i*sides+k,(i+1)*sides+k,(i+1)*sides+j))
    faces.append(tuple((len(points)-1)*sides+j for j in range(sides)))
    return mesh(name,verts,faces,mat)


def eye(name, center, scale, mat):
    n=20;rows=12
    verts=[]
    for i in range(rows+1):
        t=math.pi*i/rows
        for j in range(n):
            a=j*TAU/n
            verts.append((center[0]+scale[0]*math.sin(t)*math.cos(a),
                          center[1]+scale[1]*math.sin(t)*math.sin(a),
                          center[2]+scale[2]*math.cos(t)))
    faces=[]
    for i in range(rows):
        for j in range(n):
            k=(j+1)%n;faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    return mesh(name,verts,faces,mat)


def coin(m):
    # Total front-to-back thickness INCLUDING relief is exactly .14.
    profile=[(0,-.050),(.424,-.050),(.5,-.058),(.499,-.052),
             (.499,.052),(.5,.058),(.424,.050),(0,.050)]
    lathe('Coin / milled blank',profile,m['gold'],n=320,coin=True,milling=True)
    for side in (-1,1):
        lathe('Coin / rolled perimeter '+str(side),
              [(.437,side*.051),(.448,side*.063),(.461,side*.065),
               (.468,side*.060),(.460,side*.051),(.437,side*.051)],
              m['gold'],n=96,coin=True)
        # Hand-authored numeral silhouette: no font or external dependency.
        outline=[(-.105,.695),(-.015,.77),(.065,.77),(.065,.30),
                 (.145,.30),(.145,.235),(-.13,.235),(-.13,.30),
                 (-.045,.30),(-.045,.65),(-.105,.615)]
        vs=[(x*side,y,z) for y in (side*.049,side*.070) for x,z in outline]
        n=len(outline)
        fs=[tuple(reversed(range(n))),tuple(range(n,2*n))]
        fs += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
        obj=mesh('Coin / embossed numeral 1 '+str(side),vs,fs,m['gold'],False)
        mod=obj.modifiers.new('Soft die-struck relief edges','BEVEL');mod.width=.007;mod.segments=3
    return ['320-sample milled edge with 80 reeds','rolled concentric rim','beveled numeral 1 relief on both faces']


def mushroom(m,green=False):
    capmat=m['green' if green else 'red']
    lathe('Mushroom / tapered organic foot',[(0,0),(.18,0),(.235,.025),(.255,.08),
          (.255,.19),(.235,.31),(.19,.43),(.13,.52),(0,.54)],m['ivory'])
    profile=[(0,.94)]
    for i in range(1,19):
        t=math.pi*.5*i/18
        profile.append((.51*math.sin(t),.47+.47*math.cos(t)))
    profile += [(.50,.435),(.475,.42),(.38,.426),(.26,.45),(.12,.48),(0,.49)]
    lathe('Mushroom / fleshy umbrella cap',profile,capmat)
    lathe('Mushroom / pale rolled lip',[(.48,.426),(.503,.438),(.508,.454),
          (.50,.467),(.49,.455),(.48,.426)],m['ivory'])
    # Small closed spot patches conform exactly to the cap's ellipsoidal dome.
    spots=[(1.00,-math.pi/2,.25),(.98,-2.62,.28),(.98,-.48,.28),
           (.35,.4,.24),(1.05,1.0,.25),(1.04,2.32,.23)]
    for idx,(theta,phi,size) in enumerate(spots):
        c=Vector((math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta)))
        u=Vector((-math.sin(phi),math.cos(phi),0));v=c.cross(u)
        verts=[];n=28
        for layer in (0,1):
            for ring in range(5):
                r=size*ring/4
                for j in range(n):
                    a=j*TAU/n
                    d=(c+math.tan(r)*(u*math.cos(a)+v*math.sin(a))).normalized()
                    offset=.001 if layer==0 else .0035+.002*math.sin(math.pi*ring/4)
                    verts.append((d.x*(.51+offset),d.y*(.3978+offset),.47+d.z*(.47+offset)))
        faces=[]
        for layer in (0,1):
            for ring in range(4):
                for j in range(n):
                    a=layer*5*n+ring*n+j;b=layer*5*n+ring*n+(j+1)%n
                    face=(a,b,b+n,a+n);faces.append(face if layer else tuple(reversed(face)))
        for j in range(n):
            a=4*n+j;b=4*n+(j+1)%n;faces.append((a,b,b+5*n,a+5*n))
        mesh(f'Mushroom / cap spot {idx+1}',verts,faces,m['ivory'])
    # Radial underside folds are mesh ridges, separate and editable.
    for j in range(32):
        a=j*TAU/32
        points=[(r*math.cos(a),r*.78*math.sin(a),.474-.10*(r-.20)) for r in (.19,.26,.34,.43,.47)]
        tube(f'Mushroom / gill {j+1:02}',points,.006,m['gill'],sides=5)
    for x in (-.085,.085):
        eye('Mushroom / obsidian eye', (x,-.185,.245),(.028,.025,.074),m['dark'])
    return ['rounded tapered stem','ellipsoidal umbrella with rolled lip','six surface-conforming ivory patches','32 modeled underside gills','two inset dark eyes']


def leaf(m):
    # Asymmetric two-lobed warm leaf with an upper cleft and diagonal main tip.
    outline=[(-.06,.15),(-.26,.23),(-.40,.41),(-.44,.62),(-.39,.83),
             (-.26,.98),(-.19,.78),(-.04,.92),(.18,1.08),(.42,1.16),
             (.41,.91),(.39,.67),(.30,.44),(.17,.26)]
    center=Vector((-.015,0,.59));n=len(outline);verts=[]
    def pos(x,z,fac):
        return (x,-.075*(1-fac*fac)+.025*math.sin(z*5)*fac,z)
    for i in range(9):
        t=i/8
        for x,z in outline:
            verts.append(pos(center.x+(x-center.x)*t,center.z+(z-center.z)*t,t))
    faces=[]
    for i in range(8):
        for j in range(n):
            k=(j+1)%n;faces.append((i*n+j,i*n+k,(i+1)*n+k,(i+1)*n+j))
    obj=mesh('Super Leaf / curved lobed blade',verts,faces,m['leaf'])
    sub=obj.modifiers.new('Organic blade smoothing','SUBSURF');sub.levels=2;sub.render_levels=2
    thick=obj.modifiers.new('Real blade thickness','SOLIDIFY');thick.thickness=.014
    bevel=obj.modifiers.new('Soft blade edge','BEVEL');bevel.width=.003;bevel.segments=2
    tube('Super Leaf / petiole',[(-.12,0,.01),(-.10,-.012,.075),(-.06,-.025,.17),(-.035,-.055,.28)],.025,m['vein'])
    mid=[(-.055,-.050,.19),(-.03,-.074,.35),(.015,-.080,.54),(.09,-.079,.73),(.20,-.058,.92),(.35,-.018,1.10)]
    tube('Super Leaf / central raised midrib',mid,.012,m['vein'])
    for idx,(start,end) in enumerate([
        ((-.025,.35),(-.27,.38)),((.01,.49),(-.34,.58)),((.075,.68),(-.30,.79)),
        ((.13,.81),(-.12,.85)),((-.025,.35),(.18,.37)),((.015,.52),(.29,.57)),
        ((.08,.69),(.33,.79)),((.18,.90),(.35,.99))]):
        x,z=start;ex,ez=end
        tube(f'Super Leaf / branch vein {idx+1}',[(x,-.084,z),((x+ex)*.5,-.072,(z+ez)*.5),(ex,-.042,ez)],.005,m['vein'])
    for x in (-.115,.025):
        eye('Super Leaf / dark eye',(x,-.084,.55),(.024,.018,.069),m['dark'])
    return ['thick curled asymmetric two-lobed blade','subdivision-ready editable surface','raised branching veins','tapered curved petiole','paired dark face marks']


def bounds(objects):
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    points=[];tris=0
    for ob in objects:
        ev=ob.evaluated_get(dg)
        points.extend(ev.matrix_world@Vector(v) for v in ev.bound_box)
        data=ev.to_mesh();data.calc_loop_triangles();tris+=len(data.loop_triangles);ev.to_mesh_clear()
    low=[min(p[i] for p in points) for i in range(3)]
    high=[max(p[i] for p in points) for i in range(3)]
    return low,high,tris


def main():
    global OUT,ROOT,PARTS
    ap=argparse.ArgumentParser();ap.add_argument('--out',required=True)
    args=ap.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve();(OUT/'models').mkdir(parents=True,exist_ok=True);(OUT/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    m={
        'gold':material('Machined warm gold','worn_brass','DBAB42',.27,.92,.002),
        'ivory':material('Ivory fungal flesh','leather','EAD8AB',.53,0,.004),
        'gill':material('Warm underside folds','leather','B6A080',.69,0,.004),
        'red':material('Red mushroom cuticle','leather','BD3024',.39,0,.004),
        'green':material('Green mushroom cuticle','leaf','398244',.40,0,.004),
        'dark':material('Dark face pigment','leather','211B15',.29,0,.001),
        'leaf':material('Warm ochre leaf blade','leaf','CB8A3D',.58,0,.005),
        'vein':material('Amber leaf veins','leaf','8F5424',.65,0,.003),
    }
    entries=[];roots=[]
    for asset_id in ASSETS:
        ROOT=bpy.data.objects.new(asset_id,None);bpy.context.collection.objects.link(ROOT)
        ROOT['asset_id']=asset_id;ROOT['units']='1 unit = 16 NES pixels';PARTS=[]
        if asset_id=='coin':features=coin(m)
        elif asset_id=='super-leaf':features=leaf(m)
        else:features=mushroom(m,asset_id=='one-up')
        low,high,tris=bounds(PARTS)
        # Normalize geometry, keeping the root exactly at local origin for export.
        delta=Vector((-(low[0]+high[0])/2,-(low[1]+high[1])/2,-low[2]))
        for ob in PARTS:ob.location+=delta
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT')
        for ob in [ROOT]+PARTS:ob.select_set(True)
        bpy.context.view_layer.objects.active=ROOT
        target=OUT/'models'/f'{asset_id}.glb'
        bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,
                                  export_extras=True,export_apply=True,export_yup=True,export_materials='EXPORT')
        limits=['Authored but not rendered or visually inspected by this worker.',
                'Organic relief and surface microdetail are artistic reconstruction, not ROM-derived topology.']
        if asset_id!='coin':limits.append('No confidently labeled asset-specific catalog sprite identified; silhouette follows the supplied brief and recognizable collectible conventions.')
        if tris>8000:limits.append(f'Evaluated triangle count {tris} exceeds approximate 8000 prop target.')
        entries.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb',
                        'nominal_dimensions':{'x':round(high[0]-low[0],5),'y':round(high[1]-low[1],5),'z':round(high[2]-low[2],5)},
                        'materials':sorted({s.material.name for ob in PARTS for s in ob.material_slots if s.material}),
                        'mesh_features':features,'triangles':tris,
                        'source_basis':{'brief':'User collectible-family brief and shared style.json',
                                        'catalog':'observed-sprite-group-00.png; observed-assets.json',
                                        'evidence':'Coin shown as upright gold rim and vertical interior mark; circular 1-unit reconstruction and numeral 1 follow explicit brief.' if asset_id=='coin' else 'Catalog inspected; exact named mushroom/leaf reference not established.'},
                        'known_quality_limitations':limits})
        roots.append(ROOT)
    for i,root in enumerate(roots):root.location=(i*1.55,0,0)
    bpy.context.view_layer.update()
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'assets':entries,'coordinate_contract':'Z up, face -Y, bottom-center roots; GLB Y up','material_warnings':WARNINGS},indent=2)+'\n')


if __name__=='__main__':
    main()
