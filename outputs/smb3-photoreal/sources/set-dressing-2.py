"""Authored asset family; run exclusively through the central Blender queue."""
import argparse
import json
import math
import random
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

ASSETS = ['wood-crate', 'wood-fence', 'metal-gate']
RNG = random.Random(8317)
MATS = {}
ROOT = None
COL = None
PARTS = []
NOTES = []


def raster_material(name, out, wood=True, pale=False):
    """Deterministic tileable raster PBR; tangent normals from periodic height field."""
    n = 512
    heights = []
    for y in range(n):
        v = y / n
        for x in range(n):
            u = x / n
            if wood:
                bend = .045*math.sin(2*math.pi*v) + .016*math.sin(6*math.pi*v)
                # Periodic knots distort longitudinal fibers without a tile seam.
                knot = math.exp(-((math.sin(math.pi*(u-.42))/.24)**2 + (math.sin(math.pi*(v-.55))/.37)**2))
                grain = math.sin(2*math.pi*(u*34 + bend*18 + knot*.9))
                fine = math.sin(2*math.pi*(u*113 + .8*math.sin(4*math.pi*v)))
                h = .5 + .21*grain + .07*fine + .12*math.sin(2*math.pi*u*7)
            else:
                h = .5 + .16*math.sin(2*math.pi*(u*43+v*29))*math.sin(2*math.pi*(v*57-u*17))
            heights.append(h)
    maps = {k: array('f') for k in ('basecolor','roughness','normal')}
    base = ((.34,.255,.167) if not pale else (.43,.355,.25)) if wood else (.074,.081,.078)
    for y in range(n):
        for x in range(n):
            i=y*n+x; h=heights[i]
            value=.69+.54*h
            maps['basecolor'].extend((*[c*value for c in base],1))
            r=min(.98,(.76 if wood else .57)+.18*h)
            maps['roughness'].extend((r,r,r,1))
            dx=heights[y*n+(x+1)%n]-heights[y*n+(x-1)%n]
            dy=heights[((y+1)%n)*n+x]-heights[((y-1)%n)*n+x]
            normal=Vector((-dx*.65,-dy*.65,1)).normalized()
            maps['normal'].extend((normal.x*.5+.5,normal.y*.5+.5,normal.z*.5+.5,1))
    mat=bpy.data.materials.new(name); mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    bs=nodes.get('Principled BSDF'); bs.inputs['Metallic'].default_value=0 if wood else .82
    for channel,pixels in maps.items():
        img=bpy.data.images.new(name+'_'+channel,width=n,height=n,alpha=False)
        img.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        img.pixels.foreach_set(pixels); img.update()
        img.filepath_raw=str(out/'materials'/f'{name}_{channel}.png'); img.file_format='PNG'; img.save(); img.pack()
        node=nodes.new('ShaderNodeTexImage');node.image=img;node.extension='REPEAT'
        if channel=='normal':
            nm=nodes.new('ShaderNodeNormalMap');links.new(node.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:links.new(node.outputs['Color'],bs.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_method']='deterministic raster height-derived tangent normals'
    return mat


def mesh(name, verts, faces, mat, uv=None, bevel=0, detail=False):
    data=bpy.data.meshes.new(name);data.from_pydata(verts,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);COL.objects.link(obj);obj.parent=ROOT
    obj.data.materials.append(mat); obj['asset_id']=ROOT['asset_id'];obj['detail_only']=detail
    layer=data.uv_layers.new(name='UVMap')
    for face in data.polygons:
        for j,li in enumerate(face.loop_indices):
            if uv: co=uv[face.index][j]
            else:
                pt=data.vertices[data.loops[li].vertex_index].co
                axis=max(range(3),key=lambda a:abs(face.normal[a]))
                co=(pt.y,pt.z) if axis==0 else ((pt.x,pt.z) if axis==1 else (pt.x,pt.y))
            layer.data[li].uv=co
    if bevel:
        mod=obj.modifiers.new('Soft worn edges','BEVEL');mod.width=bevel;mod.segments=2
    PARTS.append(obj)
    return obj


def plank(name, a, b, width, depth, mat=None, weather=True):
    """Ring-subdivided solid plank with chipped corner cross sections and long-axis UVs."""
    a=Vector(a); b=Vector(b); length=(b-a).length
    verts=[]; rings=5 if weather else 2
    profile=[(-.5,-.35),(-.35,-.5),(.35,-.5),(.5,-.35),(.5,.35),(.35,.5),(-.35,.5),(-.5,.35)]
    for k in range(rings):
        t=k/(rings-1)
        for x,y in profile:
            jitter=RNG.uniform(-.009,.009) if weather and k not in (0,rings-1) else 0
            verts.append((x*width+jitter,y*depth,t*length))
    faces=[tuple(reversed(range(8)))];uv=[[(x+.5,y+.5) for x,y in reversed(profile)]]
    for k in range(rings-1):
        for j in range(8):
            faces.append((k*8+j,k*8+(j+1)%8,(k+1)*8+(j+1)%8,(k+1)*8+j))
            u0=j/8;u1=(j+1)/8
            uv.append([(u0,k/(rings-1)),(u1,k/(rings-1)),(u1,(k+1)/(rings-1)),(u0,(k+1)/(rings-1))])
    faces.append(tuple((rings-1)*8+j for j in range(8)));uv.append([(x+.5,y+.5) for x,y in profile])
    obj=mesh(name,verts,faces,mat or MATS['wood'],uv,.004 if weather else .002)
    obj.location=a;obj.rotation_mode='QUATERNION';obj.rotation_quaternion=Vector((0,0,1)).rotation_difference(b-a)
    return obj


def tube(name, points, radius, mat=None, sides=8, detail=False, radii=None):
    pts=[Vector(p) for p in points];verts=[];faces=[];uv=[];dist=0;lengths=[0]
    for i in range(1,len(pts)):lengths.append(lengths[-1]+(pts[i]-pts[i-1]).length)
    for i,p in enumerate(pts):
        tangent=(pts[min(i+1,len(pts)-1)]-pts[max(0,i-1)]).normalized()
        ref=Vector((0,1,0)) if abs(tangent.y)<.9 else Vector((1,0,0))
        u=tangent.cross(ref).normalized();v=tangent.cross(u).normalized()
        r=radius if radii is None else radii[i]
        for j in range(sides):verts.append(p+r*(math.cos(j*2*math.pi/sides)*u+math.sin(j*2*math.pi/sides)*v))
    for i in range(len(pts)-1):
        for j in range(sides):
            faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
            uv.append([(j/sides,lengths[i]),((j+1)/sides,lengths[i]),((j+1)/sides,lengths[i+1]),(j/sides,lengths[i+1])])
    faces.extend([tuple(reversed(range(sides))),tuple((len(pts)-1)*sides+j for j in range(sides))]);uv.extend([[(0,0)]*sides,[(0,0)]*sides])
    obj=mesh(name,verts,faces,mat or MATS['iron'],uv,detail=detail)
    for p in obj.data.polygons:p.use_smooth=len(p.vertices)==4
    return obj


def nail(x,y,z,side=-1):
    tube('Forged square-ish nail head',[(x,y,z),(x,y+side*.012,z)],.014,sides=6,detail=True)


def crate():
    # Five real boards on each of six sides; air gaps and recessed butt joints.
    for y in (-.445,.445):
        for i in range(5):
            x=(i-2)*.18
            plank('Vertical face plank', (x,y,.025),(x,y,.975),.173,.085,MATS['wood' if i%2 else 'pale'])
        for z in (.13,.87):
            plank('Cross batten',(-.49,y*1.17,z),(.49,y*1.17,z),.15,.058)
            for x in (-.39,.39):nail(x,y*1.17+(-.03 if y<0 else .03),z,-1 if y<0 else 1)
        plank('Diagonal shipping brace',(-.34,y*1.26,.22),(.34,y*1.26,.78),.105,.035)
    for x in (-.447,.447):
        for i in range(5):
            o=plank('Side return plank',(x,(i-2)*.166,.025),(x,(i-2)*.166,.975),.158,.07)
            o.rotation_mode='XYZ';o.rotation_euler.z=math.pi/2
    for z in (.045,.955):
        for i in range(5):
            plank('Lid and base boards',((i-2)*.18,-.40,z),((i-2)*.18,.40,z),.172,.065,MATS['pale'])
    for x in (-.38,.38):
        for y in (-.36,.36):plank('Interior corner join', (x,y,.065),(x,y,.935),.075,.075)


def fence():
    for x in (-1.10,1.10):
        plank('Mortised end post',(x,0,0),(x,0,1.28),.16,.18)
        # Solid faceted tapered cap rather than flat-cut post end.
        tube('Weathered post cap',[(x,0,1.25),(x,0,1.32),(x,0,1.39)],.10,MATS['wood'],4,radii=[.12,.12,.015])
    for z in (.38,.91):
        plank('Continuous fence rail',(-1.11,.045,z),(1.11,.045,z),.125,.11)
    for i in range(9):
        x=(i-4)*.235;h=1.15+.025*math.sin(i*2)
        plank('Uneven vertical pale',(x,-.06,.15),(x,-.06,h),.13,.073,MATS['pale' if i%3 else 'wood'])
        for z in (.38,.91):nail(x,-.103,z)
    plank('Back diagonal support',(-.99,.13,.35),(.99,.13,.95),.08,.045)
    for z in (.38,.91):
        plank('Hammered iron hinge strap',(-1.10,-.123,z),(-.65,-.123,z),.055,.022,MATS['iron'],False)
        tube('Hinge barrel',[(-1.12,-.105,z-.075),(-1.12,-.105,z+.075)],.029)
        for x in (-1.02,-.72):nail(x,-.139,z)


def gate():
    for x in (-1.16,1.16):
        plank('Iron gate pier',(x,0,0),(x,0,1.88),.105,.13,MATS['iron'],False)
        tube('Pier spear',[(x,0,1.86),(x,0,1.95),(x,0,2.10)],.08,sides=4,radii=[.027,.085,.002])
        for z in (.08,1.77):plank('Pier collar',(x,0,z-.025),(x,0,z+.025),.145,.165,MATS['iron'],False)
    for sign in (-1,1):
        # Separate closed leaf assembly with center meeting stiles.
        lo,hi=(-1.08,-.025) if sign<0 else (.025,1.08)
        for z in (.21,.45,1.35):plank('Forged leaf rail',(lo,0,z),(hi,0,z),.046,.046,MATS['iron'],False)
        for x in (lo,hi):plank('Leaf stile',(x,0,.19),(x,0,1.48),.044,.044,MATS['iron'],False)
        pts=[]
        for i in range(25):
            x=lo+(hi-lo)*i/24;z=1.50+.36*(1-(x/1.10)**2);pts.append((x,0,z))
        tube('Arched upper rail',pts,.026)
        for i in range(5):
            x=lo+.12+i*(hi-lo-.24)/4;top=1.50+.36*(1-(x/1.10)**2)
            tube('Forged upright',[(x,0,.22),(x+.005,0,.94),(x,0,top+.06)],.015,sides=8)
            tube('Lance finial',[(x,0,top+.04),(x,0,top+.105),(x,0,top+.19)],.045,sides=4,radii=[.014,.047,.001])
            for z in (.45,1.35):tube('Upright weld collar',[(x,0,z-.026),(x,0,z+.026)],.022,sides=8,detail=True)
        # Mirrored C scrolls, joined to rails by a curled tail.
        for cx in (lo+.28,hi-.28):
            for flip in (-1,1):
                points=[]
                for k in range(29):
                    t=k/28;theta=-math.pi/2+1.75*math.pi*t;r=.19*(1-.75*t)
                    points.append((cx+flip*r*math.cos(theta),0,.70+r*math.sin(theta)))
                tube('Hand forged C scroll',points,.012,sides=6)
        for z in (.43,1.31):
            x=sign*1.10
            tube('Functional hinge knuckle',[(x,0,z-.075),(x,0,z+.075)],.037)
            plank('Hinge attachment',(x,-.027,z),(x-sign*.18,-.027,z),.06,.026,MATS['iron'],False)
    plank('Latch keeper',(-.10,-.045,.92),(.10,-.045,.92),.075,.035,MATS['iron'],False)
    tube('Drop latch handle',[(.065,-.065,.94),(.065,-.11,.94),(.065,-.11,.82)],.018)


def bounds(objects):
    dg=bpy.context.evaluated_depsgraph_get();coords=[];tris=0
    for obj in objects:
        ev=obj.evaluated_get(dg);me=ev.to_mesh();me.calc_loop_triangles();tris+=len(me.loop_triangles)
        coords.extend(ev.matrix_world@v.co for v in me.vertices);ev.to_mesh_clear()
    low=[min(v[i] for v in coords) for i in range(3)];high=[max(v[i] for v in coords) for i in range(3)]
    return low,high,tris


def main():
    global ROOT,COL,PARTS
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve();(out/'models').mkdir(parents=True,exist_ok=True);(out/'materials').mkdir(exist_ok=True)
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    MATS['wood']=raster_material('Weathered oak',out)
    MATS['pale']=raster_material('Sun silvered oak',out,pale=True)
    try:
        if pbr is None:raise ImportError('shared helper unavailable')
        MATS['iron']=pbr.material('worn_brass',name='Blackened wrought iron',color='41433F',metallic=.83,roughness=.65,bump=.012,bake=True,resolution=512,cache_dir=out/'materials')
    except Exception as exc:
        NOTES.append('Shared iron bake unavailable; used raster PBR fallback: '+str(exc))
        MATS['iron']=raster_material('Blackened wrought iron fallback',out,wood=False)
    manifest=[]
    for index,(aid,build) in enumerate(zip(ASSETS,(crate,fence,gate))):
        COL=bpy.data.collections.new(aid);bpy.context.scene.collection.children.link(COL)
        ROOT=bpy.data.objects.new(aid,None);COL.objects.link(ROOT);ROOT['asset_id']=aid;ROOT['lod']=0;PARTS=[]
        build();bpy.context.view_layer.update()
        low,high,tris=bounds(PARTS)
        shift=Vector((-(low[0]+high[0])/2,-(low[1]+high[1])/2,-low[2]))
        for obj in PARTS:obj.location+=shift
        bpy.context.view_layer.update()
        bpy.ops.object.select_all(action='DESELECT');ROOT.select_set(True)
        for obj in PARTS:obj.select_set(True)
        bpy.context.view_layer.objects.active=ROOT
        path=out/'models'/f'{aid}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_yup=True,export_materials='EXPORT')
        check=pbr.inspect_glb(path) if pbr and hasattr(pbr,'inspect_glb') else {}
        if check:
            assert not check['externalImageURIs'],check
            assert check['normalTextureMaterials']==check['materials'],check
            assert check['baseColorTextureMaterials']==check['materials'],check
            assert check['roughnessTextureMaterials']==check['materials'],check
        # Editable alternate LOD in library only: omit small fasteners/collars; simplify surfaces.
        lodcol=bpy.data.collections.new(aid+'__LOD1');bpy.context.scene.collection.children.link(lodcol)
        lodroot=bpy.data.objects.new(aid+'__LOD1',None);lodcol.objects.link(lodroot);lodroot['asset_id']=aid;lodroot['lod']=1
        for obj in PARTS:
            if obj.get('detail_only'):continue
            clone=obj.copy();clone.data=obj.data.copy();lodcol.objects.link(clone);clone.parent=lodroot
            for mod in list(clone.modifiers):clone.modifiers.remove(mod)
            dec=clone.modifiers.new('Gameplay simplification','DECIMATE');dec.ratio=.55
        ROOT.location.x=index*3.25;lodroot.location=(index*3.25,3.0,0)
        source=('TILE1_LITTLEFENCE: repeated posts and horizontal rails; catalog binary-metatiles-00.png visually inspected.' if aid=='wood-fence' else 'TILE4_LARGEWOOD_UL / TILE4_LONGWOOD_M: framed rectangular wooden block vocabulary; catalog binary-metatiles-00.png visually inspected.' if aid=='wood-crate' else 'Original wrought-iron companion design; no exact gate ROM identification established.')
        features={'wood-crate':['six boarded faces','recessed seams','cross battens','diagonal braces','interior corner joins','forged nail heads'], 'wood-fence':['nine uneven pales','two mortised posts','two rails','rear diagonal brace','hinge straps and barrels','nail heads'], 'metal-gate':['two closed leaves','arched rails','ten lance finials','eight curled scrolls','hinge knuckles','center drop latch']}[aid]
        manifest.append({'asset_id':aid,'path':f'models/{aid}.glb','nominal_dimensions':[round(high[i]-low[i],4) for i in range(3)],'dimension_axes':'X width, Y depth, Z height; Blender units','materials':sorted({m.name for o in PARTS for m in o.data.materials}),'mesh_features':features,'source_basis':source,'triangles_lod0':tris,'export_check':check,'lod':'LOD0 exported; editable decimated LOD1 arranged behind LOD0 in library, not embedded in GLB','known_quality_limitations':['Not rendered or visually reviewed during authoring.','Repeated 512px material swatches; no unique baked ambient occlusion.','LOD1 simplification needs central visual review.']+(['Gate is static; leaves and hardware are separately editable but unrigged.'] if aid=='metal-gate' else [])})
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':manifest,'coordinate_contract':'Z up; front -Y; bottom-center roots; 1 unit = 16 NES pixels; glTF Y up','build_notes':NOTES},indent=2))

if __name__=='__main__':main()
