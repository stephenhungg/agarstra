"""Deterministic editable creature authoring. Execute only through the central Blender queue."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools')
sys.path.insert(0, str(SHARED))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

TAU = math.tau
ASSETS = ('goomba', 'koopa-green', 'koopa-red')
ROOT = None
M = {}
OUT = None
FALLBACKS = []


def fallback_material(name, color, roughness, bump):
    """Deterministic image PBR fallback; no procedural-only export nodes."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    rgb = [int(color[i:i+2], 16)/255 for i in (0, 2, 4)]
    size = 512
    for channel in ('basecolor', 'roughness', 'normal'):
        im = bpy.data.images.new(name+'_'+channel, width=size, height=size, alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        pixels = []
        for y in range(size):
            v = y/size
            for x in range(size):
                u = x/size
                grain = math.sin(TAU*(47*u+3*math.sin(TAU*11*v))) * math.cos(TAU*53*v)
                mottling = math.sin(TAU*5*u)*math.cos(TAU*7*v)
                if channel == 'basecolor':
                    c = [max(0, min(1, a*(.94+.035*grain+.05*mottling))) for a in rgb]
                elif channel == 'roughness':
                    c = [max(.08, min(1, roughness+.065*grain))]*3
                else:
                    a = min(.16, bump*7)
                    nx = a*math.cos(TAU*47*u)*math.cos(TAU*53*v)
                    ny = a*math.sin(TAU*47*u)*math.sin(TAU*53*v)
                    c = [.5+.5*nx, .5+.5*ny, .5+.5*math.sqrt(1-nx*nx-ny*ny)]
                pixels.extend((*c, 1))
        im.pixels.foreach_set(pixels)
        im.filepath_raw = str(OUT/'materials'/f'{name}_{channel}.png')
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = im
        if channel == 'normal':
            normal = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            mat.node_tree.links.new(tex.outputs['Color'], normal.inputs['Color'])
            mat.node_tree.links.new(normal.outputs['Normal'], bs.inputs['Normal'])
        else:
            mat.node_tree.links.new(tex.outputs['Color'], bs.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    return mat


def material(name, color, rough=.6, bump=.008, kind='leather'):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=rough,
                                bump=bump, metallic=0, bake=True, resolution=512,
                                cache_dir=str(OUT/'materials'))
        except Exception as exc:
            FALLBACKS.append(f'{name}: {type(exc).__name__}: {exc}')
    return fallback_material(name, color, rough, bump)


def mesh(name, verts, faces, mat, uv=None):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    ob.parent = ROOT
    data.materials.append(mat)
    layer = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        poly.use_smooth = True
        for li in poly.loop_indices:
            vi = data.loops[li].vertex_index
            layer.data[li].uv = uv[vi] if uv else (verts[vi][0], verts[vi][2])
    return ob


def profile(name, rows, mat, center=(0, 0, 0), n=48, ripple=0):
    """Continuous Z-ring surface. Rows: z, x radius, y radius, y offset."""
    verts, uv, faces = [], [], []
    for i, (z, rx, ry, cy) in enumerate(rows):
        for j in range(n+1):
            t = TAU*j/n
            d = 1+ripple*math.cos(9*t)*math.sin(math.pi*i/(len(rows)-1))
            verts.append((center[0]+rx*math.cos(t)*d,
                          center[1]+cy+ry*math.sin(t)*d, center[2]+z))
            uv.append((j/n, i/(len(rows)-1)))
    for i in range(len(rows)-1):
        for j in range(n):
            a = i*(n+1)+j
            faces.append((a, a+1, a+n+2, a+n+1))
    faces.extend((tuple(reversed(range(n))), tuple((len(rows)-1)*(n+1)+j for j in range(n))))
    return mesh(name, verts, faces, mat, uv)


def organic(name, center, scale, mat, n=32, rings=18, shape=0):
    rows = []
    for i in range(rings+1):
        t = -math.pi/2+math.pi*i/rings
        rad = max(.0005, math.cos(t))
        rows.append((scale[2]*math.sin(t), scale[0]*rad*(1+shape*math.sin(t)),
                     scale[1]*rad, 0))
    return profile(name, rows, mat, center, n)


def tube(name, points, radius, mat, sides=10, closed=False):
    pts = [Vector(p) for p in points]
    if closed:
        pts.append(pts[0])
    verts, uv, faces = [], [], []
    for i, p in enumerate(pts):
        if closed and i in (0, len(pts)-1):
            tangent = (pts[1]-pts[-2]).normalized()
        else:
            tangent = (pts[min(i+1, len(pts)-1)]-pts[max(i-1, 0)]).normalized()
        ref = Vector((0, 1, 0)) if abs(tangent.y) < .9 else Vector((1, 0, 0))
        a = tangent.cross(ref).normalized()
        b = tangent.cross(a).normalized()
        r = radius[i] if isinstance(radius, list) else radius
        for j in range(sides+1):
            q = p+r*(a*math.cos(TAU*j/sides)+b*math.sin(TAU*j/sides))
            verts.append(tuple(q)); uv.append((j/sides, i/max(1,len(pts)-1)))
    for i in range(len(pts)-1):
        for j in range(sides):
            k = i*(sides+1)+j
            faces.append((k, k+1, k+sides+2, k+sides+1))
    if not closed:
        faces.extend((tuple(reversed(range(sides))), tuple((len(pts)-1)*(sides+1)+j for j in range(sides))))
    return mesh(name, verts, faces, mat, uv)


def arc(name, points, r, mat):
    # Catmull-Rom interpolation creates smooth eyelids, creases and lip ridges.
    ps = [Vector(points[0])]+[Vector(p) for p in points]+[Vector(points[-1])]
    out = []
    for i in range(1, len(ps)-2):
        a,b,c,d = ps[i-1:i+3]
        for j in range(6):
            t=j/6
            out.append(tuple(.5*((2*b)+(-a+c)*t+(2*a-5*b+4*c-d)*t*t+(-a+3*b-3*c+d)*t*t*t)))
    out.append(points[-1])
    return tube(name, out, r, mat)


def foot(name, x, y, color, size=1):
    rows = [(0,.105,.15,0),(.025,.14,.19,-.025),(.07,.155,.205,-.035),
            (.12,.145,.19,-.025),(.17,.115,.13,.01),(.185,.055,.07,.035)]
    rows = [(z*size,rx*size,ry*size,cy*size) for z,rx,ry,cy in rows]
    ob=profile(name, rows, color, (x,y,0), 32)
    ring=[(x+.142*size*math.cos(t),y-.025*size+.194*size*math.sin(t),.04*size) for t in [TAU*i/48 for i in range(48)]]
    sole=tube(name+'_welt',ring,.012*size,M['sole'],closed=True)
    pivot=bpy.data.objects.new(name+'_pivot',None)
    bpy.context.collection.objects.link(pivot); pivot.parent=ROOT
    pivot['role']='static foot pivot; no animation authored'
    pivot.location=(x,y,.11*size)
    for part in (ob,sole):
        part.parent=pivot
        part['foot_pivot']=pivot.name
        part.location=-pivot.location


def goomba():
    profile('Goomba_stem',[(.10,.13,.12,0),(.16,.205,.16,0),(.26,.205,.17,0),(.36,.17,.14,0),(.44,.15,.13,0)],M['belly'],n=40)
    # Deliberately broad low mushroom skirt, tapering to an arched crown.
    rows=[(.29,.26,.18,0),(.32,.39,.24,0),(.37,.49,.29,0),(.43,.50,.30,0),
          (.50,.465,.29,0),(.58,.405,.265,0),(.69,.34,.235,0),(.80,.27,.19,0),
          (.88,.19,.14,0),(.93,.10,.08,0),(.95,.001,.001,0)]
    cap=profile('Goomba_continuous_cap',rows,M['cap'],n=64,ripple=.012)
    sub=cap.modifiers.new('Soft sculpted cap transitions','SUBSURF');sub.levels=1;sub.render_levels=1
    for s in (-1,1):
        foot('Goomba_foot_'+str(s),s*.245,-.015,M['shoe'])
        organic('Goomba_eye_white_'+str(s),(s*.153,-.259,.62),(.115,.048,.15),M['ivory'])
        organic('Goomba_pupil_'+str(s),(s*.126,-.306,.61),(.038,.015,.079),M['dark'],24,14)
        arc('Goomba_scowling_brow_'+str(s),[(s*.285,-.235,.755),(s*.20,-.285,.767),(s*.105,-.306,.709),(s*.045,-.299,.69)],.035,M['dark'])
        arc('Goomba_lower_eyelid_'+str(s),[(s*.25,-.25,.56),(s*.16,-.296,.487),(s*.065,-.26,.55)],.014,M['cap'])
        # Cream pointed canine rises from each corner of the frown.
        profile('Goomba_fang_'+str(s),[(.379,.024,.015,0),(.40,.032,.019,0),(.453,.002,.002,0)],M['ivory'],(s*.16,-.299,0),16)
    arc('Goomba_frown', [(-.205,-.284,.405),(-.12,-.309,.438),(0,-.321,.45),(.12,-.309,.438),(.205,-.284,.405)],.014,M['dark'])
    arc('Goomba_lower_lip',[(-.15,-.292,.381),(0,-.308,.373),(.15,-.292,.381)],.018,M['cap'])


def shell_point(x,z,offset=0):
    d=max(0,1-x*x-z*z)
    return (x*.365,.15+.265*math.sqrt(d)+offset,.64+z*.425)


def shell(color):
    organic('Shell_continuous_carapace',(0,.15,.64),(.37,.265,.43),M['seam'],48,24)
    # Clipped hexagonal keratin plates follow the ellipsoidal carapace.
    rad=.36
    for row in range(-2,3):
        for col in range(-2,3):
            cx=math.sqrt(3)*rad*(col+.5*(row%2));cz=1.5*rad*row
            if cx*cx+cz*cz>1.1:continue
            poly=[(cx+rad*math.cos(math.pi/6+TAU*k/6),cz+rad*math.sin(math.pi/6+TAU*k/6)) for k in range(6)]
            # Sutherland-Hodgman clip against a 48-sided rim.
            for j in range(48):
                nx,nz=math.cos(TAU*j/48),math.sin(TAU*j/48)
                new=[]
                for a,b in zip(poly,poly[1:]+poly[:1]):
                    da=.965-a[0]*nx-a[1]*nz; db=.965-b[0]*nx-b[1]*nz
                    if da>=0:new.append(a)
                    if (da>=0)!=(db>=0):
                        t=da/(da-db);new.append((a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])))
                poly=new
                if not poly:break
            if len(poly)<3:continue
            center=(sum(p[0] for p in poly)/len(poly),sum(p[1] for p in poly)/len(poly))
            verts=[];uv=[];faces=[];count=len(poly)
            for scale,offset in ((.02,.018),(.55,.018),(.88,.013),(.955,.002)):
                for x,z in poly:
                    px=center[0]+(x-center[0])*scale;pz=center[1]+(z-center[1])*scale
                    verts.append(shell_point(px,pz,offset));uv.append(((px+1)/2,(pz+1)/2))
            faces.append(tuple(reversed(range(count))))
            for ring in range(3):
                for k in range(count):
                    a=ring*count+k;b=ring*count+(k+1)%count
                    faces.append((a,a+count,b+count,b))
            ob=mesh(f'Shell_scute_{row}_{col}',verts,faces,color,uv)
            solid=ob.modifiers.new('Keratin plate thickness','SOLIDIFY');solid.thickness=.009
            # Small concentric growth band near each plate perimeter.
            band=[shell_point(center[0]+(x-center[0])*.78,center[1]+(z-center[1])*.78,.019) for x,z in poly]
            tube(f'Scute_growth_band_{row}_{col}',band,.0025,color,sides=6,closed=True)
    rim=[shell_point(math.cos(TAU*i/64),math.sin(TAU*i/64)) for i in range(64)]
    tube('Shell_thick_cream_rim',rim,.038,M['belly'],12,True)


def koopa(color):
    shell(color)
    organic('Koopa_torso',(0,-.035,.64),(.27,.225,.365),M['skin'],40,22)
    organic('Koopa_cream_plastron',(0,-.21,.625),(.237,.061,.295),M['belly'],40,22)
    for i,z in enumerate((.44,.54,.65,.76)):
        width=.22*math.sqrt(max(.1,1-((z-.625)/.295)**2))
        pts=[]
        for j in range(17):
            x=width*(j/8-1)
            y=-.213-.06*math.sqrt(max(0,1-(x/.24)**2-((z-.625)/.30)**2))
            pts.append((x,y-.002,z+.013*(x/width)**2))
        tube('Plastron_segment_crease_'+str(i),pts,.006,M['crease'],8)
    profile('Koopa_neck',[(.86,.105,.095,0),(.97,.092,.085,-.015),(1.09,.105,.09,-.045),(1.14,.13,.12,-.065)],M['skin'],(0,-.09,0),32)
    organic('Koopa_cranium',(0,-.17,1.225),(.18,.185,.24),M['skin'],40,24,shape=-.12)
    # Broad protruding muzzle is a shaped ring surface, with actual lip and nostrils.
    organic('Koopa_muzzle',(0,-.335,1.135),(.203,.187,.122),M['skin'],40,20,shape=-.12)
    for s in (-1,1):
        organic('Koopa_eye_white_'+str(s),(s*.09,-.286,1.32),(.075,.052,.12),M['ivory'],28,18)
        organic('Koopa_pupil_'+str(s),(s*.083,-.335,1.31),(.027,.014,.065),M['dark'],20,14)
        arc('Koopa_upper_eyelid_'+str(s),[(s*.164,-.275,1.34),(s*.115,-.306,1.437),(s*.046,-.305,1.397)],.015,M['skin'])
        organic('Koopa_nostril_'+str(s),(s*.091,-.483,1.173),(.019,.008,.013),M['crease'],16,10)
        arc('Koopa_arm_'+str(s),[(s*.21,-.02,.83),(s*.285,-.09,.71),(s*.302,-.16,.56)],.063,M['skin'])
        organic('Koopa_hand_'+str(s),(s*.302,-.167,.545),(.078,.078,.085),M['skin'],24,14)
        for k in range(3):
            arc(f'Koopa_finger_fold_{s}_{k}',[(s*(.263+k*.026),-.224,.54),(s*(.263+k*.026),-.238,.568)],.004,M['crease'])
        organic('Koopa_leg_'+str(s),(s*.185,.025,.255),(.091,.098,.18),M['skin'],28,16)
        foot('Koopa_foot_'+str(s),s*.203,-.07,color,1.12)
    arc('Koopa_mouth_crease',[(-.155,-.425,1.077),(-.08,-.488,1.061),(0,-.509,1.06),(.08,-.488,1.061),(.155,-.425,1.077)],.006,M['crease'])
    organic('Koopa_tail',(0,.30,.30),(.065,.14,.062),M['skin'],24,14)


def descendants(root):
    return [root]+list(root.children_recursive)


def normalize(root, height):
    bpy.context.view_layer.update()
    obs=[o for o in root.children_recursive if o.type=='MESH']
    dg=bpy.context.evaluated_depsgraph_get()
    bounds=[o.matrix_world@Vector(c) for o in obs for c in o.evaluated_get(dg).bound_box]
    lo=Vector(tuple(min(p[i] for p in bounds) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in bounds) for i in range(3)))
    factor=height/(hi.z-lo.z)
    shift=Vector(((lo.x+hi.x)/2,(lo.y+hi.y)/2,lo.z))
    # Bake normalization into each editable mesh, retaining true unit root scale.
    for ob in obs:
        world=ob.matrix_world.copy()
        points=[(world@v.co-shift)*factor for v in ob.data.vertices]
        ob.location=(0,0,0);ob.rotation_euler=(0,0,0);ob.scale=(1,1,1)
        ob.parent=root
        for vertex,point in zip(ob.data.vertices,points):vertex.co=point
        for mod in ob.modifiers:
            if mod.type=='SOLIDIFY':mod.thickness*=factor
    for pivot in [o for o in root.children if o.type=='EMPTY']:
        pivot.location=(pivot.location-shift)*factor
        for ob in obs:
            if ob.get('foot_pivot') == pivot.name:
                ob.parent=pivot;ob.location=-pivot.location
    return [round((hi[i]-lo[i])*factor,5) for i in range(3)]


def export(path, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)


def main():
    global OUT, ROOT, M
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve();(OUT/'models').mkdir(parents=True,exist_ok=True);(OUT/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    recipes={
        'cap':('A16A35',.73,.009),'shoe':('503021',.65,.01),
        'sole':('30251C',.82,.008),'belly':('D9C49A',.66,.005),
        'ivory':('F0E8CD',.29,.001),'dark':('201B15',.33,.001),
        'skin':('C7A447',.64,.008),'crease':('796340',.78,.004),
        'seam':('42452A',.75,.006),'green':('426D35',.43,.006),
        'red':('A44832',.43,.006)}
    M={k:material('creature_'+k,*v) for k,v in recipes.items()}
    entries=[];roots=[]
    for aid in ASSETS:
        collection=bpy.data.collections.new(aid);bpy.context.scene.collection.children.link(collection)
        layer=bpy.context.view_layer.layer_collection.children.get(collection.name)
        bpy.context.view_layer.active_layer_collection=layer
        ROOT=bpy.data.objects.new(aid,None);collection.objects.link(ROOT)
        ROOT['asset_id']=aid;ROOT['front_axis']='-Y';ROOT['units']='one block = 1 unit'
        roots.append(ROOT)
        if aid=='goomba':goomba()
        else:koopa(M['green' if aid.endswith('green') else 'red'])
        dimensions=normalize(ROOT,1 if aid=='goomba' else 1.5)
        bpy.context.view_layer.update()
        objects=descendants(ROOT)
        export(OUT/'models'/f'{aid}.glb',objects)
        triangles=0
        dg=bpy.context.evaluated_depsgraph_get()
        for ob in objects:
            if ob.type=='MESH':
                ev=ob.evaluated_get(dg);data=ev.to_mesh();data.calc_loop_triangles();triangles+=len(data.loop_triangles);ev.to_mesh_clear()
        entries.append({'asset_id':aid,'path':f'models/{aid}.glb','nominaldimensions':dimensions,
            'nominal_dimensions':dict(zip(('x','y','z'),dimensions)),
            'materials':sorted({m.name for o in objects if o.type=='MESH' for m in o.data.materials}),
            'meshfeatures':['continuous UV ring surfaces','sculpted eyelids and facial creases','named foot pivots','leather welted footwear']+(['raised keratin scutes','growth ridges','thick shell rim','segmented cream plastron'] if aid!='goomba' else ['broad mushroom skirt','arched crown','scowling brows','canine teeth']),
            'sourcebasis':{'contract':'smb3-photoreal/design/style.json','catalog':'smb3-rom-assets/catalog/observed-sprite-group-00.png','evidence':'Observed first sprite groups support broad Goomba cap and short footwear; catalog semantic identities are unresolved. Koopa proportions and color variants follow task silhouette brief, not an identified catalog pose.'},
            'evaluated_triangles':triangles,
            'knownqualitylimitations':['Authored without Blender execution or render inspection by the asset worker.','Separate overlapping anatomical surfaces; no welded rig-ready topology.','Static neutral pose, no skeleton or animation.','Texture detail is reusable UV material swatches; no unique curvature or cavity bake.']})
    for i,root in enumerate(roots):root.location.x=(i-1)*1.9
    bpy.context.view_layer.update()
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    (OUT/'manifest.json').write_text(json.dumps({'assets':entries,'material_fallbacks':FALLBACKS,'coordinate_system':'Blender Z up, front -Y; GLB Y up. Exported roots bottom-centered; library roots spaced for inspection.'},indent=2))


if __name__=='__main__':
    main()
