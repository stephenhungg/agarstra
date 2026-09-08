"""Deterministic editable mechanisms family. Run only through the central Blender queue."""
import argparse
import json
import math
import random
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
ASSETS = ['firebar', 'spike-trap', 'chain-chomp']
TAU = 2 * math.pi
CURRENT = None
PARTS = []
WARNINGS = []


def mesh(name, vertices, faces, material, smooth=False, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(vertices, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    CURRENT.objects.link(ob)
    data.materials.append(material)
    # Deterministic box projection per polygon; textures are seamless repeating swatches.
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        axis = max(range(3), key=lambda i: abs(poly.normal[i]))
        axes = [i for i in range(3) if i != axis]
        for li in poly.loop_indices:
            co = data.vertices[data.loops[li].vertex_index].co
            uv.data[li].uv = (co[axes[0]] * 1.6, co[axes[1]] * 1.6)
        poly.use_smooth = smooth
    if bevel:
        mod = ob.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width = bevel
        mod.segments = 2
        mod.limit_method = 'ANGLE'
    PARTS.append(ob)
    return ob


def box(name, center, size, mat, bevel=.025):
    v = [(center[0]+x*size[0]/2, center[1]+y*size[1]/2, center[2]+z*size[2]/2)
         for x,y,z in [(-1,-1,-1), (1,-1,-1), (1,1,-1), (-1,1,-1),
                       (-1,-1,1), (1,-1,1), (1,1,1), (-1,1,1)]]
    return mesh(name,v,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat,bevel=bevel)


def lathe(name, center, profile, mat, n=24, axis=(0,0,1), wobble=0):
    q = Vector((0,0,1)).rotation_difference(Vector(axis).normalized())
    verts=[]
    for k,(r,z) in enumerate(profile):
        for j in range(n):
            a=j*TAU/n
            rr=r*(1+wobble*math.sin(7*a+k*.9))
            verts.append(Vector(center)+q@Vector((rr*math.cos(a),rr*math.sin(a),z)))
    faces=[]
    for k in range(len(profile)-1):
        for j in range(n):
            a=k*n+j;b=k*n+(j+1)%n
            faces.append((a,b,b+n,a+n))
    return mesh(name,verts,faces,mat,True)


def pin(name, center, radius, depth, mat, axis=(0,0,1), n=16):
    r=radius;h=depth/2
    return lathe(name,center,[(0,-h),(r*.87,-h),(r,-h+.009),(r,h-.009),(r*.87,h),(0,h)],mat,n,axis)


def ellipsoid(name, center, scale, mat, n=24, rows=12, wobble=0):
    verts=[]
    for i in range(rows+1):
        t=.0001+(math.pi-.0002)*i/rows
        for j in range(n):
            a=TAU*j/n;rr=1+wobble*math.sin(a*5+t*9)
            verts.append((center[0]+scale[0]*math.sin(t)*math.cos(a)*rr,
                          center[1]+scale[1]*math.sin(t)*math.sin(a)*rr,
                          center[2]+scale[2]*math.cos(t)*rr))
    faces=[(i*n+j,i*n+(j+1)%n,(i+1)*n+(j+1)%n,(i+1)*n+j) for i in range(rows) for j in range(n)]
    faces.extend([tuple(reversed(range(n))),tuple(rows*n+j for j in range(n))])
    return mesh(name,verts,[tuple(reversed(f)) for f in faces],mat,True)


def loop(name, center, radii, wire, mat, plane='XY', n=32, sides=8):
    # Elliptical forged link, actual open center and circular wire cross-section.
    axes={'XY':((1,0,0),(0,1,0)), 'XZ':((1,0,0),(0,0,1)), 'YZ':((0,1,0),(0,0,1))}
    u,v=map(Vector,axes[plane]);normal=u.cross(v);center=Vector(center)
    verts=[]
    for i in range(n):
        a=i*TAU/n
        c=center+u*radii[0]*math.cos(a)+v*radii[1]*math.sin(a)
        outward=(u*math.cos(a)/radii[0]+v*math.sin(a)/radii[1]).normalized()
        for j in range(sides):
            b=j*TAU/sides
            verts.append(c+wire*(outward*math.cos(b)+normal*math.sin(b)))
    faces=[]
    for i in range(n):
        for j in range(sides):
            faces.append((i*sides+j,((i+1)%n)*sides+j,((i+1)%n)*sides+(j+1)%sides,i*sides+(j+1)%sides))
    return mesh(name,verts,faces,mat,True)


def fallback_material(name,color,rough,metal,out):
    """Image-based fallback, no Blender-only shader texture dependencies."""
    rng=random.Random(name)
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF');bs.inputs['Metallic'].default_value=metal
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    size=512
    noise=[rng.uniform(-1,1) for _ in range(size*size)]
    for channel in ('basecolor','roughness','normal'):
        image=bpy.data.images.new(name+'_'+channel,width=size,height=size,alpha=False)
        image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        values=[]
        for y in range(size):
            for x in range(size):
                i=y*size+x;v=noise[i]
                if channel=='basecolor': c=[max(0,min(1,k*(.92+.08*v))) for k in rgb]
                elif channel=='roughness':c=[max(.05,min(1,rough+v*.065))]*3
                else:
                    dx=(noise[y*size+(x+1)%size]-v)*.10
                    dy=(noise[((y+1)%size)*size+x]-v)*.10
                    nn=Vector((-dx,-dy,1)).normalized();c=[k*.5+.5 for k in nn]
                values.extend((*c,1))
        image.pixels.foreach_set(values)
        image.filepath_raw=str(out/'materials'/f'{name}_{channel}.png');image.file_format='PNG';image.save();image.pack()
        node=mat.node_tree.nodes.new('ShaderNodeTexImage');node.image=image
        if channel=='normal':
            norm=mat.node_tree.nodes.new('ShaderNodeNormalMap');mat.node_tree.links.new(node.outputs['Color'],norm.inputs['Color']);mat.node_tree.links.new(norm.outputs['Normal'],bs.inputs['Normal'])
        else:mat.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked']=True
    return mat


def materials(out):
    recipes={'iron':('24282B',.56,.88), 'steel':('83878A',.36,.95),
             'black':('10151C',.22,.82), 'tooth':('D5CCAD',.38,.22),
             'ember':('D7490F',.6,.12)}
    result={}
    for name,(color,rough,metal) in recipes.items():
        try:
            if pbr is None:raise ImportError('shared helper absent')
            mat=pbr.material('worn_brass',name=name,color=color,roughness=rough,metallic=metal,
                             bump=.007 if name=='black' else .018,bake=True,resolution=512,cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake fallback: {exc}')
            mat=fallback_material(name,color,rough,metal,out)
        if name=='ember':
            bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
            bs.inputs['Emission Color'].default_value=(1,.075,.002,1)
            bs.inputs['Emission Strength'].default_value=2.8
        result[name]=mat
    return result


def wear(name,center,length,mat,axis='X'):
    # A physical chipped sliver at an exposed edge; small brighter substrate patch.
    x,y,z=center
    if axis=='X':v=[(x-length/2,y,z),(x+length/2,y,z+.001),(x+length*.22,y-.003,z+.009),(x-length*.4,y-.002,z+.006)]
    else:v=[(x,y,z-length/2),(x+.007,y-.002,z-length*.3),(x+.004,y-.003,z+length/2)]
    return mesh(name,v,[tuple(range(len(v)))],mat)


def firebar(m):
    box('Pivot mounting block',(0,0,.30),(.60,.42,.60),m['iron'])
    pin('Rotating axle',(0,-.28,.32),.16,.25,m['steel'],(0,1,0))
    for x in (-.21,.21):
        for z in (.11,.49):pin('Mount bolt',(x,-.222,z),.042,.04,m['steel'],(0,1,0),6)
    pivot=bpy.data.objects.new('Firebar articulation pivot',None);CURRENT.objects.link(pivot);PARTS.append(pivot)
    pivot.location=(0,-.33,.32);pivot['joint_axis']='Y';pivot['pose']='static articulated chain; rotate this pivot about local Y'
    moving=[]
    for i in range(6):
        x=.51+i*.49;z=.36+i*.10
        start=len(PARTS)
        loop(f'Articulated link {i}',(x-.24,-.33,z-.045),(.19,.095),.026,m['steel'],'XY' if i%2==0 else 'XZ',24,6)
        ellipsoid(f'Incandescent forged core {i}',(x,-.33,z),(.185,.17,.19),m['ember'],20,10,.045)
        for plane in ('XY','XZ','YZ'):
            loop(f'Iron cage band {i} {plane}',(x,-.33,z),(.183,.183),.019,m['iron'],plane,24,6)
        pin(f'Cage connector {i}',(x-.17,-.33,z),.045,.07,m['steel'],(1,0,0),12)
        # Solid sculpted tongues communicate fire without planes or transparency.
        for j in range(2):
            lathe(f'Flame tongue {i}.{j}',(x+(.07 if j else -.055),-.33,z+.13),[(.055,0),(.063,.045),(.035,.115),(.004,.23),(0,.235)],m['ember'],10,axis=(.25,0,1),wobble=.12)
        moving.extend(PARTS[start:])
    for ob in moving:
        ob.parent=pivot;ob.matrix_parent_inverse=pivot.matrix_basis.inverted()
    return ['Six caged ember cores, solid flame tongues','Alternating open links and pin connectors','Parented Y-axis articulation pivot and bolted mounting block']


def spike_trap(m):
    box('Lower mechanism housing',(0,0,.14),(1.9,1.20,.28),m['iron'],.045)
    box('Inset moving platen',(0,0,.32),(1.72,1.02,.12),m['black'],.022)
    for x in (-.79,.79):
        for y in (-.43,.43):
            pin('Guide sleeve',(x,y,.32),.069,.19,m['steel'])
            pin('Hex socket cap',(x,y,.435),.052,.04,m['iron'],n=6)
            box('Cap drive recess',(x,y-.001,.457),(.055,.012,.004),m['black'],.002)
    for y in (-.31,.31):
        for x in (-.59,0,.59):
            lathe('Replaceable spike collar',(x,y,.37),[(.074,0),(.146,0),(.146,.055),(.107,.080),(.074,.080),(.074,0)],m['steel'],20)
            # Square forged pyramid with an octagonal root and slight unevenness.
            lathe('Tempered piercing spike',(x,y,.40),[(0,0),(.113,0),(.126,.075),(.094,.22),(.049,.43),(.002,.67),(0,.672)],m['steel'],8,wobble=.025)
    for x in (-.6,-.3,0,.3,.6):
        box('Front housing cooling recess',(x,-.604,.14),(.12,.008,.065),m['black'],.012)
    for x in (-.88,.88):
        pin('Service panel fastener',(x,-.61,.13),.037,.026,m['steel'],(0,1,0),6)
    rng=random.Random(98)
    for i in range(18):wear(f'Chipped exposed housing edge {i}',(rng.uniform(-.85,.85),-.608,.27),rng.uniform(.018,.08),m['steel'])
    return ['Six individually modeled forged spikes with collars','Beveled housing, moving platen, four guide sleeves','Hex hardware, drive slots, face recesses and physical chipped edge slivers']


def chain_chomp(m):
    R=.83;cz=.88;gap=.38;n=48;rows=24
    verts=[]
    # Outer and inner surfaces: leave the front equatorial wedge genuinely open.
    for radius in (R,R-.075):
        for i in range(rows+1):
            t=.002+(math.pi-.004)*i/rows
            x=radius*math.cos(t);s=radius*math.sin(t)
            for j in range(n+1):
                phi=gap+(TAU-2*gap)*j/n
                verts.append((x,-s*math.cos(phi),cz+s*math.sin(phi)))
    layer=(rows+1)*(n+1);faces=[]
    for k in (0,1):
        for i in range(rows):
            for j in range(n):
                a=k*layer+i*(n+1)+j;f=(a,a+1,a+n+2,a+n+1)
                faces.append(f if k==0 else tuple(reversed(f)))
    for i in range(rows):
        a=i*(n+1);b=(i+1)*(n+1)
        faces.extend([(a,b,b+layer,a+layer),(a+n,a+n+layer,b+n+layer,b+n)])
    for j in range(n):
        a=j;b=rows*(n+1)+j
        faces.extend([(a,a+layer,a+layer+1,a+1),(b,b+1,b+layer+1,b+layer)])
    shell=mesh('Hollow black enamel jaw shell',verts,faces,m['black'],True)
    shell['wall_thickness']=.075
    for sign in (-1,1):
        for i,x in enumerate((-.60,-.40,-.20,0,.20,.40,.60)):
            s=math.sqrt(R*R-x*x);y=-s*math.cos(gap);z=cz+sign*s*math.sin(gap)
            half=.087;depth=.080;tip=z-sign*(.18 if abs(x)<.5 else .12)
            v=[(x-half,y-.015,z),(x+half,y-.015,z),(x,y-.035,tip),
               (x-half,y+depth,z),(x+half,y+depth,z),(x,y+depth*.5,tip)]
            ob=mesh(f'Individual tooth {sign} {i}',v,[(0,2,1),(3,4,5),(0,1,4,3),(1,2,5,4),(2,0,3,5)],m['tooth'],bevel=.007)
            ob['replaceable_tooth']=True
    for x in (-.30,.30):
        ellipsoid('Raised ivory eye',(x,-.626,1.36),(.18,.087,.23),m['tooth'])
        ellipsoid('Black forward pupil',(x,-.705,1.35),(.076,.033,.115),m['black'],20,10)
    for x in (-.819,.819):
        pin('Jaw hinge trunnion',(x,0,cz),.11,.075,m['steel'],(1,0,0),20)
        pin('Recessed hinge bolt',(x*1.05,0,cz),.052,.024,m['iron'],(1,0,0),6)
    pin('Rear tether socket',(0,.79,.84),.125,.16,m['iron'],(0,1,0))
    loop('Tether eye',(0,.96,.84),(.15,.13),.044,m['steel'],'YZ')
    for i in range(7):
        y=1.17+i*.255;z=.78-i*.074
        loop(f'Forged tether link {i}',(0,y,z),(.19,.103) if i%2==0 else (.103,.19),.035,m['iron'],'YZ' if i%2==0 else 'XY',28,8)
        pin(f'Link weld bead {i}',(.0 if i%2==0 else .103,y,z),.037,.032,m['steel'],(0,1,0),8)
    pin('Anchor post',(0,2.91,.28),.12,.56,m['iron'],n=16)
    pin('Anchor mushroom head',(0,2.91,.58),.185,.105,m['steel'])
    loop('Anchor attachment eye',(0,2.81,.35),(.12,.10),.032,m['steel'],'YZ')
    rng=random.Random(89)
    for i in range(16):
        x=rng.uniform(-.65,.65);s=math.sqrt(R*R-x*x)
        wear(f'Jaw rim enamel chip {i}',(x,-s*math.cos(gap)-.002,cz+s*math.sin(gap)),rng.uniform(.012,.034),m['steel'])
    return ['Thick hollow spherical shell with open jaw and visible inside','14 separate beveled tooth prisms, raised eyes and pupils','Side hinge bolts, rear tether socket, seven alternating forged links and anchor post','Physical enamel chips along upper mouth rim']


def bounds(objects):
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    pts=[]
    for ob in objects:
        if ob.type=='MESH':
            ev=ob.evaluated_get(deps)
            pts.extend(ev.matrix_world@Vector(c) for c in ev.bound_box)
    return [min(p[i] for p in pts) for i in range(3)], [max(p[i] for p in pts) for i in range(3)]


def export(path,objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in objects:ob.select_set(True)
    bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)


def main():
    global CURRENT,PARTS
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'models').mkdir(exist_ok=True);(out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    m=materials(out);entries=[];roots=[]
    makers=[firebar,spike_trap,chain_chomp]
    for asset_id,maker in zip(ASSETS,makers):
        CURRENT=bpy.data.collections.new(asset_id);bpy.context.scene.collection.children.link(CURRENT);PARTS=[]
        root=bpy.data.objects.new(asset_id,None);CURRENT.objects.link(root);root['asset_id']=asset_id
        features=maker(m)
        for ob in PARTS:
            if ob.parent is None:ob.parent=root
            ob['asset_id']=asset_id
        low,high=bounds(PARTS)
        offset=Vector((-(low[0]+high[0])/2,-(low[1]+high[1])/2,-low[2]))
        # Translate top-level authored geometry, keeping the root exactly at (0,0,0).
        for ob in PARTS:
            if ob.parent==root:ob.location+=offset
        bpy.context.view_layer.update()
        export(out/'models'/f'{asset_id}.glb',[root]+PARTS)
        deps=bpy.context.evaluated_depsgraph_get();triangles=0
        for ob in PARTS:
            if ob.type=='MESH':
                ev=ob.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();triangles+=len(me.loop_triangles);ev.to_mesh_clear()
        basis={'catalog':'smb3-rom-assets/catalog/binary-assets.json; catalog/README.md',
               'interpretation':'User brief and recognizable source-inspired silhouette; no verified assembled sprite match.'}
        if asset_id=='chain-chomp':basis.update(descriptor='OBJ_CHAINCHOMP, id 137, ObjP89, PRG/prg004.asm:396',resolution='unresolved specialized compositor; not a pixel-exact reconstruction')
        else:basis['resolution']='No exact semantic sprite established for this prop; authored mechanical interpretation.'
        entries.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominaldimensions':[round(high[i]-low[i],4) for i in range(3)],
            'dimension_axes':'Blender XYZ; scene units; one block=1', 'materials':sorted({s.name for o in PARTS if o.type=='MESH' for s in o.data.materials}),
            'meshfeatures':features,'triangles':triangles,'sourcebasis':basis,
            'knownqualitylimitations':['Not rendered or visually validated during authoring.','Static pose; no animation clips or physics.',
                'Microtexture swatches are UV projected; physical edge chips supplement generic texture wear.'] +
                (['Fire is stylized solid emissive geometry, not a fluid or volumetric simulation.'] if asset_id=='firebar' else [])})
        roots.append(root)
    for i,root in enumerate(roots):root.location.x=(i-1)*4.5
    bpy.context.view_layer.update()
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file:image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':entries,'warnings':WARNINGS,'style_contract':str(SHARED/'design/style.json'),
        'coordinates':'Z up; front -Y; bottom-center root. GLB converts to Y up. Library uses spaced roots.'},indent=2)+'\n')

if __name__=='__main__':main()
