"""Editable SMB3 mechanism assets. Execute only through the central Blender queue."""
import argparse
import json
import math
import random
import sys
from pathlib import Path
from array import array

import bpy
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal')
sys.path.insert(0, str(SHARED / 'tools'))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

TAU = math.tau
PARTS = []
WARNINGS = []
OUT = None
M = {}


def image_material(name, color, roughness, metallic, wood=False):
    """Deterministic, image-backed fallback; all three maps survive glTF export."""
    n = 512
    rng = random.Random(923 + sum(map(ord, name)))
    height = []
    for y in range(n):
        for x in range(n):
            u, v = x / n, y / n
            if wood:
                phase = TAU * (u * 34 + .32 * math.sin(TAU*v) + .13*math.sin(TAU*3*v))
                h = .5 + .22*math.sin(phase) + .1*math.sin(phase*3) + rng.uniform(-.07, .07)
            else:
                h = .5 + .12*math.sin(TAU*(u*13 + .3*math.sin(TAU*v*7))) + rng.uniform(-.22,.22)
            height.append(h)
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    shader = nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value = metallic
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                h = height[y*n+x]
                if channel == 'basecolor':
                    factor = .66 + .55*h
                    rgb = tuple(min(1, c*factor) for c in color)
                elif channel == 'roughness':
                    r = min(.98,max(.08,roughness+(h-.5)*.23))
                    rgb = (r,r,r)
                else:
                    dx = (height[y*n+(x+1)%n]-height[y*n+(x-1)%n])*.28
                    dy = (height[((y+1)%n)*n+x]-height[((y-1)%n)*n+x])*.28
                    normal = Vector((-dx,-dy,1)).normalized()
                    rgb = tuple(c*.5+.5 for c in normal)
                pixels.extend((*rgb,1))
        image = bpy.data.images.new(name+'_'+channel, width=n,height=n,alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        image.pixels.foreach_set(pixels)
        path = OUT/'materials'/f'{name}-{channel}.png'
        image.filepath_raw = str(path)
        image.file_format = 'PNG'
        image.save()
        image.pack()
        tex = nodes.new('ShaderNodeTexImage'); tex.image=image; tex.extension='REPEAT'
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'], shader.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic sampled grain/pitting; tangent normal finite differences'
    return mat


def material(name, color, roughness, metallic, kind='worn_brass', wood=False):
    if pbr is not None and not wood:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=metallic,bump=.012,scale=18,bake=True,
                                resolution=512,cache_dir=OUT/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared material fallback: {type(exc).__name__}: {exc}')
    rgb = tuple(int(color[i:i+2],16)/255 for i in (0,2,4))
    return image_material(name,rgb,roughness,metallic,wood)


def mesh(name, verts, faces, mat, smooth=False, uvs=None):
    data=bpy.data.meshes.new(name)
    data.from_pydata(verts,[],faces); data.update()
    obj=bpy.data.objects.new(name,data); bpy.context.collection.objects.link(obj)
    data.materials.append(mat)
    layer=data.uv_layers.new(name='UVMap')
    for polygon in data.polygons:
        polygon.use_smooth=smooth
        axis=max(range(3),key=lambda i:abs(polygon.normal[i]))
        axes=[i for i in range(3) if i!=axis]
        for loopid in polygon.loop_indices:
            vertex=data.loops[loopid].vertex_index
            if uvs is not None:
                uv=uvs[loopid]
            else:
                co=data.vertices[vertex].co
                uv=(co[axes[0]]*1.6,co[axes[1]]*1.6)
            layer.data[loopid].uv=uv
    PARTS.append(obj)
    return obj


def bevel(obj, width=.02, segments=2):
    mod=obj.modifiers.new('Machined and worn edge radius','BEVEL')
    mod.width=width; mod.segments=segments
    mod=obj.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    mod.keep_sharp=True; mod.weight=40
    return obj


def box(name, size, loc, mat, radius=.025):
    x,y,z=(v/2 for v in size)
    verts=[(-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z)]
    faces=[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)]
    obj=mesh(name,verts,faces,mat);obj.location=loc
    return bevel(obj,min(radius,min(size)*.22)) if radius else obj


def lathe(name, profile, loc, mat, segments=48, axis='Z', scale=(1,1,1)):
    # A closed profile is an editable solid wall, not an opaque bore disk.
    verts=[(r*math.cos(TAU*j/segments)*scale[0],r*math.sin(TAU*j/segments)*scale[1],z*scale[2]) for r,z in profile for j in range(segments)]
    faces=[];uv=[]
    lengths=[0]
    for a,b in zip(profile,profile[1:]):lengths.append(lengths[-1]+math.hypot(b[0]-a[0],b[1]-a[1]))
    total=lengths[-1] or 1
    for i in range(len(profile)-1):
        for j in range(segments):
            k=(j+1)%segments
            faces.append((i*segments+j,i*segments+k,(i+1)*segments+k,(i+1)*segments+j))
            uv.extend([(j/segments,lengths[i]/total),((j+1)/segments,lengths[i]/total),((j+1)/segments,lengths[i+1]/total),(j/segments,lengths[i+1]/total)])
    obj=mesh(name,verts,faces,mat,True,uv);obj.location=loc
    if axis=='-Y':obj.rotation_euler.x=math.pi/2
    elif axis=='X':obj.rotation_euler.y=math.pi/2
    return obj


def ring(name,r,depth,loc,mat,axis='Z',thickness=.035,segments=48):
    t=depth/2; b=min(.009,depth*.2,thickness*.2)
    return lathe(name,[(r-thickness,-t),(r-b,-t),(r,-t+b),(r,t-b),(r-b,t),(r-thickness,t),(r-thickness,-t)],loc,mat,segments,axis)


def ellipsoid(name,loc,scale,mat,segments=24,rings=12):
    # Small polar radius avoids degenerate pole quads.
    p=[(.0001,-1)]+[(math.sin(math.pi*i/rings),-math.cos(math.pi*i/rings)) for i in range(1,rings)]+[(.0001,1),(.0001,-1)]
    return lathe(name,p,loc,mat,segments,scale=scale)


def rod(name,a,b,r,mat,segments=12):
    a,b=Vector(a),Vector(b);length=(b-a).length
    obj=lathe(name,[(0,0),(r*.85,0),(r,r*.2),(r,length-r*.2),(r*.85,length),(0,length),(0,0)],a,mat,segments)
    obj.rotation_mode='QUATERNION';obj.rotation_quaternion=(b-a).to_track_quat('Z','Y')
    return obj


def rivet(name,point,normal,r=.025):
    normal=Vector(normal);obj=lathe(name,[(0,0),(r,0),(r,r*.2),(r*.8,r*.65),(r*.3,r*.86),(0,r*.86),(0,0)],point,M['steel'],12)
    obj.rotation_mode='QUATERNION';obj.rotation_quaternion=normal.to_track_quat('Z','Y')
    return obj


def wear_arc(name, radius, loc, axis='-Y', seed=8):
    """Sparse irregular exposed metal chips on a real rim; thin volumetric strips."""
    rng=random.Random(seed)
    for i in range(9):
        a=rng.uniform(0,TAU);span=rng.uniform(.025,.09)
        verts=[]
        for rr,z in ((radius-.008,-.002),(radius+.001,-.002),(radius+.001,.002),(radius-.008,.002)):
            verts.extend((rr*math.cos(a+span*j/7),rr*math.sin(a+span*j/7),z) for j in range(8))
        faces=[]
        for row in range(4):
            nxt=(row+1)%4
            for j in range(7):faces.append((row*8+j,row*8+j+1,nxt*8+j+1,nxt*8+j))
        faces.extend([(0,24,16,8),(7,15,23,31)])
        obj=mesh(name+f'_{i}',verts,faces,M['steel'],True);obj.location=loc
        if axis=='-Y':obj.rotation_euler.x=math.pi/2
        elif axis=='X':obj.rotation_euler.y=math.pi/2



def cannon():
    box('Foundation casting',(1.02,.90,.17),(0,0,.085),M['iron'],.045)
    box('Stepped base',( .86,.76,.12),(0,0,.22),M['iron'])
    box('Upright pedestal',(.73,.63,.91),(0,.045,.70),M['iron'],.045)
    for z in (.35,.83):
        box('Pedestal reinforcing belt',(.78,.68,.085),(0,.045,z),M['iron'],.016)
        for x in (-.27,.27):rivet('Belt fastener',(x,-.302,z),(0,-1,0))
    # + local z is muzzle direction, facing -Y. Outer profile proceeds rear to front.
    profile=[(0,-.46),(.29,-.46),(.36,-.40),(.39,-.24),(.40,.32),(.44,.39),(.445,.49),(.43,.53),(.315,.53),(.295,.49),(.295,-.27),(0,-.29),(0,-.46)]
    lathe('Hollow cast barrel',profile,(0,-.015,1.16),M['iron'],64,'-Y')
    lathe('Sooted bore liner',[(.294,-.22),(.294,.44),(.287,.44),(.287,-.22),(.294,-.22)],(0,-.015,1.16),M['soot'],48,'-Y')
    for y in (-.27,.27):
        ring('Shrunk iron barrel band',.415,.075,(0,y,1.16),M['iron'],'-Y')
        for j in range(10):
            a=TAU*j/10
            rivet('Band rivet',(.415*math.cos(a),y,1.16+.415*math.sin(a)),(math.cos(a),0,math.sin(a)),.019)
    for sign in (-1,1):
        rod('Trunnion axle',(sign*.30,.05,1.08),(sign*.48,.05,1.08),.10,M['steel'],20)
        box('Trunnion bearing',( .13,.25,.27),(sign*.405,.05,.99),M['iron'],.025)
        rivet('Axle cap',(sign*.485,.05,1.08),(sign,0,0),.063)
    for x in (-.41,.41):
        for y in (-.32,.32):rivet('Foundation anchor',(x,y,.171),(0,0,1),.031)
    wear_arc('Muzzle edge chips',.438,(0,-.545,1.16))
    for x in (-.16,.16):
        box('Recessed casting seam',(.008,.003,.29),(x,-.273,.58),M['soot'],0)


def bullet_bill():
    profile=[(0,-.68),(.37,-.68),(.43,-.63),(.45,-.53),(.45,.13),(.435,.30),(.385,.48),(.30,.62),(.18,.71),(.065,.755),(0,.763),(0,-.68)]
    lathe('Riveted projectile shell',profile,(0,0,.51),M['iron'],64,'-Y')
    ring('Rear rolled flange',.475,.105,(0,.57,.51),M['iron'],'-Y',.058)
    lathe('Recessed rear plug',[(0,-.01),(.365,-.01),(.38,0),(.365,.025),(0,.025),(0,-.01)],(0,.67,.51),M['soot'],40,'-Y')
    ring('Rear plug seat',.39,.035,(0,.676,.51),M['steel'],'-Y',.025)
    for j in range(12):
        a=TAU*j/12
        rivet('Circumferential body rivet',(.455*math.cos(a),.43,.51+.455*math.sin(a)),(math.cos(a),0,math.sin(a)),.019)
    # White eye inlays are visible from front and quarter views, beneath metal brows.
    for sign in (-1,1):
        eye=ellipsoid('Porcelain eye inlay',(sign*.215,-.502,.729),(.157,.088,.185),M['ivory'],28,14)
        eye.rotation_euler.z=sign*.28
        ellipsoid('Focused black pupil',(sign*.205,-.586,.723),(.061,.025,.10),M['soot'],20,12)
        brow=box('Stern forged brow',(.315,.13,.086),(sign*.213,-.506,.845),M['iron'],.025)
        brow.rotation_euler.y=-sign*.29
        rod('Arm socket',(sign*.37,.15,.47),(sign*.51,.15,.40),.10,M['iron'],16)
        ring('Cuff retaining collar',.115,.065,(sign*.51,.15,.40),M['steel'],'X',.025,24)
        fist=box('Clenched ivory glove',(.25,.29,.24),(sign*.62,.09,.345),M['ivory'],.065)
        for j in range(3):
            box('Separate knuckle',(.075,.092,.102),(sign*(.53+j*.076),-.073,.383),M['ivory'],.027)
        ellipsoid('Folded thumb',(sign*.57,-.02,.254),(.091,.115,.065),M['ivory'],20,10)
        for j in range(2):
            rod('Glove stitched crease',(sign*(.57+j*.077),-.121,.34),(sign*(.57+j*.077),-.121,.39),.005,M['soot'],6)
    wear_arc('Flange scuffs',.473,(0,.619,.51),seed=52)


def hammer():
    # Oval handle, longitudinal UV grain, flared heel, seated through the open head eye.
    lathe('Carved ash handle',[(0,0),(.102,0),(.12,.035),(.12,.14),(.095,.24),(.078,.50),(.083,.80),(.096,1.07),(.097,1.48),(0,1.48),(0,0)],(0,0,0),M['wood'],24,scale=(1,.72,1))
    ring('Lower heel ferrule',.124,.055,(0,0,.08),M['iron'],thickness=.023,segments=24).scale.y=.74
    ring('Head seating ferrule',.119,.15,(0,0,1.055),M['steel'],thickness=.025,segments=24).scale.y=.78
    # Rectangular annular head with a genuine through-eye; four loops form all walls.
    outer=[(-.55,-.235),(.55,-.235),(.55,.235),(-.55,.235)]
    inner=[(-.104,-.078),(.104,-.078),(.104,.078),(-.104,.078)]
    verts=[]
    for points,z in ((outer,1.13),(outer,1.49),(inner,1.13),(inner,1.49)):
        verts.extend((x,y,z) for x,y in points)
    faces=[]
    for j in range(4):
        k=(j+1)%4
        faces.extend([(j,k,k+4,j+4),(8+k,8+j,12+j,12+k),(j,8+j,8+k,k),(4+j,4+k,12+k,12+j)])
    bevel(mesh('Forged steel head with through eye',verts,faces,M['steel']),.025,3)
    # Distinct, slightly mushroomed octagonal striking cheeks, with edge notches.
    for sign in (-1,1):
        cheek=lathe('Mushroomed striking cheek',[(0,0),(.24,0),(.265,.025),(.268,.09),(.244,.12),(0,.12),(0,0)],(sign*.50,0,1.31),M['steel'],8,'X',scale=(1,.93,1))
        if sign<0:cheek.rotation_euler.y=-math.pi/2
        for j in range(3):
            z=1.23+j*.07
            rod('Impact scar',(sign*.617,-.08,z),(sign*.617,.015,z+.028),.0045,M['soot'],6)
    box('Exposed handle tenon',(.19,.139,.028),(0,0,1.492),M['wood'],.007)
    wedge=box('Steel retaining wedge',(.032,.135,.072),(0,0,1.492),M['iron'],.005)
    wedge.rotation_euler.y=.13
    rivet('Head maker stamp',(.26,-.237,1.31),(0,-1,0),.039)
    # A few recessed-looking splinter grooves are physical thin dark wood ribbons.
    for j in range(4):
        a=-math.pi/2+(j-1.5)*.22
        r=.087
        rod('Longitudinal wood check',(r*math.cos(a),r*.72*math.sin(a)-.003,.35+j*.035),(r*math.cos(a),r*.72*math.sin(a)-.003,.60+j*.035),.0025,M['wood_dark'],6)


SOURCE = {
 'cannon': {'catalog':'binary-assets.json','definition':'Tile_Layout_TS1-118','labels':['TILE1_CANNONTOP1','TILE1_CANNONTOP2','TILE1_CANNONMID'],'example_variant':'binary-metatile-4c8f85e0f8a15da87cb4','inspected_png':'binary-clips/binary-metatile-4c8f85e0f8a15da87cb4.png','interpretation':'Stacked upright cannon support and projecting muzzle; depth, trunnions, bore and bands are authored reconstruction.'},
 'bullet-bill': {'catalog':'binary-assets.json','descriptor':120,'label':'OBJ_BULLETBILL','source':'PRG/prg004.asm:428','rom_offset':33339,'interpretation':'Compact rounded projectile, stern white eyes, clenched gloves; descriptor sprite assembly is unresolved in catalog.'},
 'hammer': {'catalog':'binary-assets.json','descriptor':129,'label':'OBJ_HAMMERBRO','source':'PRG/prg004.asm:445','interpretation':'Hammer-family identity only. Heavy transverse head and narrow handle are brief-driven; no verified standalone projectile sprite was identified.'}
}
FEATURES = {
 'cannon':['Deep sealed-back bore with separate soot liner','Stepped cast pedestal','Shrunk reinforcement bands and individual rivets','Trunnion shafts and bearing blocks','Foundation anchors','Volumetric exposed muzzle edge chips'],
 'bullet-bill':['Rounded revolved projectile shell','Rear flange and recessed plug','Individual body rivets','Separate porcelain eyes, pupils and slanted metal brows','Connected arm sockets, retaining cuffs and modeled clenched gloves','Physical flange chips'],
 'hammer':['Forged annular head with real through-eye','Octagonal mushroomed striking cheeks','Continuous flared oval wooden handle','Ferrules, exposed tenon and retaining wedge','Directional wood grain maps','Physical impact scars and wood checks']
}


def finalize(asset_id, parts):
    root=bpy.data.objects.new(asset_id,None);bpy.context.collection.objects.link(root)
    root['asset_id']=asset_id;root['front']='-Y';root['units_per_block']=1.0
    bpy.context.view_layer.update()
    points=[obj.matrix_world @ Vector(corner) for obj in parts for corner in obj.bound_box]
    lo=Vector(tuple(min(p[i] for p in points) for i in range(3)))
    hi=Vector(tuple(max(p[i] for p in points) for i in range(3)))
    offset=Vector((-(lo.x+hi.x)/2,-(lo.y+hi.y)/2,-lo.z))
    for obj in parts:
        obj.location+=offset;obj.parent=root;obj['asset_id']=asset_id
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    for obj in [root]+parts:obj.select_set(True)
    bpy.context.view_layer.objects.active=root
    path=OUT/'models'/f'{asset_id}.glb'
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
        export_extras=True,export_apply=True,export_materials='EXPORT',export_yup=True)
    deps=bpy.context.evaluated_depsgraph_get();triangles=0
    for obj in parts:
        evaluated=obj.evaluated_get(deps);data=evaluated.to_mesh()
        data.calc_loop_triangles();triangles+=len(data.loop_triangles);evaluated.to_mesh_clear()
    entry={'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':dict(zip(('x','y','z'),[round(float(v),4) for v in hi-lo])),
        'materials':sorted({slot.material.name for obj in parts for slot in obj.material_slots if slot.material}),
        'mesh_features':FEATURES[asset_id],'source_basis':SOURCE[asset_id],'triangles_evaluated':triangles,
        'known_quality_limitations':['Central queue render and visual inspection pending.','Source-inspired reconstruction; not an exact ROM sprite extrusion.','Wear maps are reusable swatches, not unique whole-object curvature bakes.']}
    if pbr is not None and hasattr(pbr,'inspect_glb'):
        entry['glb_inspection']=pbr.inspect_glb(path)
        info=entry['glb_inspection']
        if info['externalImageURIs'] or info['images']!=info['embeddedImages']:
            raise RuntimeError(f'{asset_id}: GLB textures not fully embedded')
        if not all(info[k]==info['materials'] for k in ('baseColorTextureMaterials','roughnessTextureMaterials','normalTextureMaterials')):
            raise RuntimeError(f'{asset_id}: material lacks transferable PBR texture channel')
    return root,entry


def main():
    global OUT
    args=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    OUT=Path(parser.parse_args(args).out).resolve()
    (OUT/'models').mkdir(parents=True,exist_ok=True);(OUT/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    specs={'iron':('Black cast iron','24282C',.49,.88), 'steel':('Worn forged steel','737A7D',.37,.95),
           'soot':('Soot and dark recesses','101113',.78,.18), 'ivory':('Warm ivory glove and eye','E0DACA',.49,0),
           'wood':('Oiled ash longitudinal grain','86512B',.64,0), 'wood_dark':('Ash checks','352319',.85,0)}
    for key,(name,color,rough,metal) in specs.items():
        M[key]=material(name,color,rough,metal,wood=key.startswith('wood'))
    entries=[];roots=[]
    for asset_id,builder in [('cannon',cannon),('bullet-bill',bullet_bill),('hammer',hammer)]:
        PARTS.clear();builder();root,entry=finalize(asset_id,list(PARTS));entries.append(entry);roots.append(root)
    for i,root in enumerate(roots):root.location.x=(i-1)*2.5
    bpy.context.scene['asset_layout']='Inspection library only: roots at X = -2.5, 0, +2.5. Individual GLBs exported at origin.'
    bpy.context.scene.unit_settings.system='METRIC';bpy.context.scene.unit_settings.scale_length=1
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    contract=json.loads((SHARED/'design/style.json').read_text()) if (SHARED/'design/style.json').exists() else {'units':'Z up; front -Y; one block=1'}
    manifest={'family':'mechanisms-1','coordinate_contract':contract.get('units'), 'assets':entries,'warnings':WARNINGS,'validation':'Export and texture structure checked at runtime; visual review not performed by author.'}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':'built','assets':[e['asset_id'] for e in entries],'warnings':WARNINGS}))


if __name__=='__main__':main()
