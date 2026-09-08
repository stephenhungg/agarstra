"""Four editable SMB3-inspired collectibles. Execute only through the central Blender queue."""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.path.insert(0, str(SHARED / 'tools'))
import pbr_common as pbr

IDS = ['star', 'fire-flower', 'music-block', 'pow-block']
PI = math.pi
M = {}
ROOT = None
PARTS = []


def attach(obj):
    obj.parent = ROOT
    obj['asset_id'] = ROOT['asset_id']
    PARTS.append(obj)
    return obj


def mesh(name, vertices, faces, material, smooth=False):
    obj = pbr.mesh(name, vertices, faces, material=material, smooth=smooth)
    # Consistent closed-volume normals, including custom concave prisms.
    pbr._activate(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')
    return attach(obj)


def bevel(obj, width, segments=3):
    mod = obj.modifiers.new('Machined or softened edge radius', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod = obj.modifiers.new('Face weighted normals', 'WEIGHTED_NORMAL')
    mod.keep_sharp = True
    return obj


def cube(name, size, location, material, radius=.025):
    # A directly constructed cube keeps geometry generation independent of operators.
    x, y, z = [a/2 for a in size]
    v = [(a*x,b*y,c*z) for a,b,c in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                                    (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
    f = [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    obj = mesh(name,v,f,material)
    obj.location = location
    return bevel(obj,radius)


def prism(name, outline, depth, y, material, radius=.01):
    n = len(outline)
    vertices = [(x,y+d,z) for d in (-depth/2,depth/2) for x,z in outline]
    faces = [tuple(range(n-1,-1,-1)),tuple(range(n,2*n))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,vertices,faces,material),radius)


def ellipsoid(name, center, radii, material, segments=32, rings=12):
    # Single poles rather than degenerate duplicated pole rings.
    cx,cy,cz=center; rx,ry,rz=radii
    v=[(cx,cy,cz-rz)]
    for i in range(1,rings):
        a=-PI/2+PI*i/rings
        for j in range(segments):
            t=2*PI*j/segments
            v.append((cx+rx*math.cos(a)*math.cos(t),cy+ry*math.cos(a)*math.sin(t),cz+rz*math.sin(a)))
    top=len(v); v.append((cx,cy,cz+rz))
    f=[(0,1+(j+1)%segments,1+j) for j in range(segments)]
    for i in range(rings-2):
        for j in range(segments):
            a=1+i*segments+j; b=1+i*segments+(j+1)%segments
            f.append((a,b,b+segments,a+segments))
    base=1+(rings-2)*segments
    f += [(base+j,base+(j+1)%segments,top) for j in range(segments)]
    return mesh(name,v,f,material,True)


def tube(name, points, radius, material, sides=8):
    pts=[Vector(p) for p in points]; v=[]
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        helper=Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
        u=tangent.cross(helper).normalized(); w=tangent.cross(u).normalized()
        r=radius[i] if isinstance(radius,list) else radius
        for j in range(sides):
            v.append(tuple(p+r*(u*math.cos(2*PI*j/sides)+w*math.sin(2*PI*j/sides))))
    f=[tuple(range(sides-1,-1,-1))]
    for i in range(len(pts)-1):
        for j in range(sides):
            a=i*sides+j; b=i*sides+(j+1)%sides
            f.append((a,b,b+sides,a+sides))
    f.append(tuple((len(pts)-1)*sides+j for j in range(sides)))
    return mesh(name,v,f,material,True)


def eye(x,z,y):
    ellipsoid('Obsidian inset eye', (x,y,z), (.028,.018,.086), M['black'],24,10)


def star():
    # Ten alternating radii preserve the unmistakable five-point contour.
    shape=[((.52 if i%2==0 else .242)*math.sin(i*PI/5),
            .52+(.52 if i%2==0 else .242)*math.cos(i*PI/5)) for i in range(10)]
    prism('Star solid gold body',shape,.24,0,M['gold'],.024)
    for side in (-1,1):
        inner=[(x*.90,.52+(z-.52)*.90) for x,z in shape]
        prism('Inset luminous enamel face',inner,.022,side*.127,M['yellow'],.012)
    eye(-.092,.56,-.158); eye(.092,.56,-.158)
    # A narrow metal reveal around the enamel reads as a continuous bevelled rim.


def blade(name, origin, direction, length, width, material, veins=False):
    o=Vector(origin); d=Vector(direction).normalized(); across=Vector((d.z,0,-d.x)).normalized()
    rows=15; cols=7; v=[]
    for i in range(rows):
        t=i/(rows-1); spread=width*math.sin(PI*t)**.8/2 + .001
        for j in range(cols):
            s=2*j/(cols-1)-1
            p=o+d*(length*t)+across*(spread*s)
            p.y += -.05*math.sin(PI*t)+.043*s*s*math.sin(PI*t)+.008*math.sin(5*PI*t)*abs(s)
            v.append(tuple(p))
    f=[]
    for i in range(rows-1):
        for j in range(cols-1):
            a=i*cols+j; f.append((a,a+1,a+cols+1,a+cols))
    obj=mesh(name,v,f,material,True)
    sub=obj.modifiers.new('Organic surface subdivision','SUBSURF');sub.levels=1;sub.render_levels=1
    solid=obj.modifiers.new('Living tissue thickness','SOLIDIFY');solid.thickness=.014
    if veins:
        spine=[]
        for i in range(12):
            t=.05+.9*i/11;p=o+d*length*t;p.y-=.05*math.sin(PI*t)+.010;spine.append(tuple(p))
        tube(name+' raised midrib',spine,.004,M['vein'],6)
        for t in (.3,.48,.65,.8):
            for sign in (-1,1):
                start=o+d*(length*t); start.y-=.05*math.sin(PI*t)+.008
                end=o+d*(length*(t+.1))+across*(sign*width*.35*math.sin(PI*t));end.y-=.020
                tube(name+' secondary vein',[tuple(start),tuple(start.lerp(end,.5)),tuple(end)],.0025,M['vein'],5)
    return obj


def flower():
    tube('Curved fleshy stem',[(0,0,.02),(.012,0,.17),(-.018,.015,.34),(0,.015,.60)], [.034,.038,.037,.045],M['green'],12)
    blade('Left lanceolate leaf', (0,-.006,.15),(-.9,0,.48),.47,.21,M['green'],True)
    blade('Right lanceolate leaf', (0,.005,.22),(.94,0,.35),.45,.22,M['green'],True)
    # Overlapping broad petals form a low oval corolla rather than a generic daisy.
    for j in range(8):
        a=2*PI*j/8
        d=(math.cos(a),0,math.sin(a))
        blade('Corolla petal %02d'%j,(.12*math.cos(a),.006,.74+.105*math.sin(a)),d,.2,.18,M['red'])
    ellipsoid('Orange corolla cushion',(0,-.018,.74),(.335,.097,.24),M['red'],40,14)
    ellipsoid('Golden inner corolla',(0,-.101,.75),(.254,.048,.183),M['yellow'],40,12)
    ellipsoid('Ivory living flower face',(0,-.14,.755),(.18,.045,.126),M['ivory'],32,12)
    eye(-.061,.77,-.182);eye(.061,.77,-.182)


def note_mark(y, back=False):
    sign=-1 if back else 1
    head=ellipsoid('Raised note head',(sign*-.10,y,.35),(.12,.025,.077),M['black'],32,10)
    cube('Raised note stem',(.051,.032,.39),(sign*-.007,y,.54),M['black'],.011)
    outline=[(-.032,.735),(.055,.745),(.17,.675),(.173,.59),(.09,.646),(-.032,.666)]
    if back: outline=[(-x,z) for x,z in outline]
    prism('Curved eighth-note flag',outline,.034,y,M['black'],.009)


def music():
    cube('Ivory ceramic shell',(1,.96,1),(0,0,.5),M['ivory'],.055)
    # Recessed panel illusion is constructed as a dark narrow reveal under a flush face.
    for s in (-1,1):
        cube('Fine panel shadow reveal',(.864,.019,.864),(0,s*.479,.5),M['seam'],.032)
        cube('Ivory face insert',(.842,.024,.842),(0,s*.491,.5),M['ivory'],.03)
        note_mark(s*.512,back=s==1)
    for x in (-.46,.46):
        cube('Top shell join',(.009,.78,.003),(x,0,.997),M['seam'],.001)


def lettering(text, y, material):
    curve=bpy.data.curves.new('POW raised lettering source','FONT');curve.body=text
    curve.align_x='CENTER';curve.align_y='CENTER';curve.size=.34
    curve.extrude=.011;curve.bevel_depth=.004;curve.bevel_resolution=2;curve.resolution_u=6
    obj=bpy.data.objects.new('POW embossed wordmark',curve);bpy.context.collection.objects.link(obj)
    obj.rotation_euler=(PI/2,0,0);obj.location=(0,y,.50)
    curve.materials.append(material)
    pbr._activate(obj);bpy.ops.object.convert(target='MESH');obj=bpy.context.object
    obj['editable_lettering']='POW';pbr.uv_smart(obj);attach(obj)


def pow_block():
    cube('Dark blue cast casing',(.98,.86,.85),(0,0,.5),M['blue'],.05)
    for z in (.085,.915):
        cube('Ivory reinforced bumper',(1,.92,.17),(0,0,z),M['ivory'],.023)
        cube('Blue bumper inset',(.90,.936,.048),(0,0,z),M['blue'],.012)
    for s in (-1,1):
        cube('Dark recessed wordmark gasket',(.884,.025,.53),(0,s*.432,.50),M['black'],.026)
        cube('Blue faceplate',(.848,.025,.493),(0,s*.450,.50),M['blue'],.019)
    lettering('POW',-.473,M['ivory'])
    for x in (-.37,.37):
        for z in (.31,.69):
            ellipsoid('Flush steel fastener',(x,-.471,z),(.018,.008,.018),M['steel'],16,8)
            cube('Fastener slot',(.019,.003,.003),(x,-.480,z),M['black'],.0008)
    for x in (-.493,.493):
        for z in (.34,.5,.66):
            cube('Side cast cooling rib',(.022,.59,.036),(x,0,z),M['blue'],.008)


SOURCE = {
 'star': 'OBJ_POWERUP_STARMAN=12; Star_Palettes ROM offset 10165; PUp_StarOrSuitFrames offset 10250. Five-point silhouette and paired eyes interpreted from collectible identity; no context-resolved sprite verified.',
 'fire-flower': 'OBJ_POWERUP_FIREFLOWER=25; PowerUp_Palettes offset 66873. Oval concentric flower face, stem and two leaves; organic petal relief is an authored interpretation.',
 'music-block': 'LATP_Notes offset 71301 and LATR_Notes offset 71333 in PRG/prg008.asm. Ivory cubic body and raised eighth note from brief; exact metatile variant not established.',
 'pow-block': 'Vs_POWPatterns offset 79337, bytes [185,187,153,155,137,139]; Vs_POWHeight offset 79343. Dark blue casing, light bumpers and POW wordmark; depth and mechanical fittings are authored.'
}
FEATURES = {
 'star':['Closed bevelled five-point solid','Inset emissive enamel front and back','Paired volumetric obsidian eyes','Continuous gold rim'],
 'fire-flower':['Curved ring-mesh stem','Eight subdivided thick organic petals','Layered oval corolla','Two curved leaves with modeled midrib and secondary veins','Volumetric eyes'],
 'music-block':['Rounded ceramic shell','Front and rear face inserts with narrow reveals','Raised three-part eighth notes','Top shell joints'],
 'pow-block':['Bevelled cast casing','Layered reinforced bumpers','Raised bevelled POW mesh lettering','Slotted fasteners','Side reinforcing ribs']
}


def bounds(parts):
    bpy.context.view_layer.update();dg=bpy.context.evaluated_depsgraph_get()
    points=[o.matrix_world @ Vector(c) for obj in parts for o in [obj.evaluated_get(dg)] for c in o.bound_box]
    lo=Vector([min(p[i] for p in points) for i in range(3)])
    hi=Vector([max(p[i] for p in points) for i in range(3)])
    return lo,hi


def main():
    global ROOT,PARTS
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True);out=Path(parser.parse_args(args).out).resolve()
    out.mkdir(parents=True,exist_ok=True);(out/'models').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    recipes={
      'gold':('worn_brass','DDB34D',.29,.82), 'yellow':('yellow_enamel','F4BF37',.30,.12),
      'black':('stone','121A20',.34,.0), 'ivory':('yellow_enamel','ECE8D8',.27,.0),
      'green':('leaf','44833D',.57,.0), 'vein':('leaf','739752',.59,.0),
      'red':('leaf','DB4925',.46,.0), 'blue':('green_metal','173C75',.34,.3),
      'steel':('worn_brass','9BABB6',.38,.8), 'seam':('stone','A5A394',.58,.0)}
    for key,(kind,color,rough,metal) in recipes.items():
        M[key]=pbr.material(kind,name='Items2_'+key,color=color,roughness=rough,metallic=metal,
                            bump=.0025 if key not in ('green','red','vein') else .006,
                            bake=True,resolution=512,cache_dir=out/'materials')
    # The star has its own emissive enamel; the flower reuses the non-emissive yellow.
    luminous=M['yellow'].copy();luminous.name='Items2_star_luminous_enamel'
    bsdf=next(n for n in luminous.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    bsdf.inputs['Emission Color'].default_value=(1,.42,.035,1);bsdf.inputs['Emission Strength'].default_value=.65
    entries=[];roots=[]
    for asset_id,build in zip(IDS,[star,flower,music,pow_block]):
        ROOT=bpy.data.objects.new(asset_id,None);bpy.context.collection.objects.link(ROOT)
        ROOT['asset_id']=asset_id;ROOT['units']='1 unit = 16 NES pixels';ROOT['front']='-Y';PARTS=[]
        normal_yellow=M['yellow']
        if asset_id=='star':M['yellow']=luminous
        build();M['yellow']=normal_yellow
        lo,hi=bounds(PARTS);offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
        for obj in PARTS:obj.location+=offset
        lo,hi=bounds(PARTS)
        dimensions=[round(v,6) for v in hi-lo]
        ROOT['nominal_dimensions']=dimensions
        stats=pbr.export_glb(out/'models'/f'{asset_id}.glb',[ROOT]+PARTS)
        if stats['externalImageURIs'] or stats['embeddedImages']==0:
            raise RuntimeError('GLB texture embedding failed: '+asset_id)
        if any(stats[k]!=stats['materials'] for k in ('baseColorTextureMaterials','roughnessTextureMaterials','normalTextureMaterials')):
            raise RuntimeError('Missing required texture channel: '+asset_id)
        dg=bpy.context.evaluated_depsgraph_get();tris=0
        for obj in PARTS:
            evaluated=obj.evaluated_get(dg);data=evaluated.to_mesh();data.calc_loop_triangles();tris+=len(data.loop_triangles);evaluated.to_mesh_clear()
        entries.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':dimensions,
                        'dimension_order':'Blender X/Y/Z','materials':sorted({m.name for o in PARTS for m in o.data.materials}),
                        'mesh_features':FEATURES[asset_id],'source_basis':SOURCE[asset_id],
                        'known_quality_limitations':['Authored reconstruction; central render and visual inspection pending.','No animation or baked ambient occlusion.','Microdetail uses reusable UV swatches; seam placement requires visual inspection.'],
                        'evaluated_triangles':tris,'glb_inspection':stats})
        roots.append(ROOT)
    for i,root in enumerate(roots):root.location=(i*1.65,0,0)
    for img in bpy.data.images:
        if img.source=='FILE' and not img.packed_file:img.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    manifest={'family':'items-2','coordinate_contract':'Z up; front -Y; bottom-center roots; GLB Y up',
              'style_contract':json.loads((SHARED/'design/style.json').read_text()),'assets':entries}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':
    main()
