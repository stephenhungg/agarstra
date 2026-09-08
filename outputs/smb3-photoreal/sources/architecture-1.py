"""Editable architectural platform family; run only through the central Blender queue."""
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
IDS = ['platform-coral', 'platform-cream', 'platform-blue', 'wood-platform']
WARNINGS = []
ROOT = None
COLLECTION = None


def mesh(name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    COLLECTION.objects.link(obj)
    obj.parent = ROOT
    obj['asset_id'] = ROOT['asset_id']
    data.materials.append(mat)
    # Stable physical planar UVs: front grain follows X, side/end grain remains mapped.
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        axis = max(range(3), key=lambda a: abs(poly.normal[a]))
        axes = (0, 2) if axis == 1 else ((0, 1) if axis == 2 else (1, 2))
        for loop in poly.loop_indices:
            co = data.vertices[data.loops[loop].vertex_index].co
            uv.data[loop].uv = (co[axes[0]], co[axes[1]])
    return obj


def bevel(obj, width=.015, segments=3):
    mod = obj.modifiers.new('Physical softened edges', 'BEVEL')
    mod.width = width
    mod.segments = segments
    mod.limit_method = 'ANGLE'
    return obj


def box(name, size, center, mat, edge=.015):
    x, y, z = [v / 2 for v in size]
    verts = [(a*x+center[0], b*y+center[1], c*z+center[2])
             for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                           (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces = [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return bevel(mesh(name, verts, faces, mat), edge)


def panel(name, width, height, front, rear, radius, mat, bottom=0):
    contour = []
    for cx,cz,start in [(width/2-radius,bottom+height-radius,0),
                         (-width/2+radius,bottom+height-radius,90),
                         (-width/2+radius,bottom+radius,180),
                         (width/2-radius,bottom+radius,270)]:
        for i in range(7):
            a = math.radians(start+i*90/6)
            contour.append((cx+radius*math.cos(a),cz+radius*math.sin(a)))
    n = len(contour)
    verts = [(x,y,z) for y in (front,rear) for x,z in contour]
    faces = [tuple(range(n)),tuple(reversed(range(n,2*n)))]
    faces += [(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)]
    return bevel(mesh(name,verts,faces,mat),.008,2)


def ring(name, x, z, profile, mat, segments=24):
    # Profile traverses radius/depth; face points toward -Y.
    verts = [(x+r*math.cos(2*math.pi*j/segments),y,z+r*math.sin(2*math.pi*j/segments))
             for r,y in profile for j in range(segments)]
    faces = []
    for row in range(len(profile)-1):
        for j in range(segments):
            a=row*segments+j; b=row*segments+(j+1)%segments
            faces.append((a,b,b+segments,a+segments))
    signed_area = sum(profile[i][0]*profile[(i+1)%len(profile)][1]
                      - profile[(i+1)%len(profile)][0]*profile[i][1] for i in range(len(profile)))
    if signed_area > 0:
        faces = [tuple(reversed(f)) for f in faces]
    return mesh(name,verts,faces,mat)


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj


def bore(obj,x,z,radius,mat):
    cutter=ring('temporary bore',x,z,[(0,-.35),(radius,-.35),(radius,-.14),(0,-.14)],mat,32)
    activate(obj)
    # Applying the bevel before the boolean gives the rim an uninterrupted round silhouette.
    for mod in list(obj.modifiers):
        bpy.ops.object.modifier_apply(modifier=mod.name)
    mod=obj.modifiers.new('True recessed fastener pocket','BOOLEAN')
    mod.operation='DIFFERENCE'; mod.solver='EXACT'; mod.object=cutter
    bpy.ops.object.modifier_apply(modifier=mod.name)
    data=cutter.data
    bpy.data.objects.remove(cutter,do_unlink=True)
    bpy.data.meshes.remove(data)


def fastener(x,z,iron,front=-.228):
    ring('Recessed dished washer',x,z,[(.078,front+.035),(.102,front+.035),(.102,front+.006),
         (.086,front),(.060,front+.024),(.060,front+.035),(.078,front+.035)],iron)
    head=ring('Inset hexagonal bolt',x,z,[(0,front+.030),(.053,front+.030),(.053,front+.013),
         (.047,front+.007),(0,front+.007)],iron,6)
    bevel(head,.002,2)


def pixel_material(name,color,rough,metal,out,wood=False):
    """Deterministic image PBR fallback and purpose-built directional wood textures."""
    n=512
    rng=random.Random(name)
    heights=[]; shades=[]
    for y in range(n):
        for x in range(n):
            u=x/n; v=y/n
            grain=math.sin(2*math.pi*(v*48+.32*math.sin(u*2*math.pi)+.11*math.sin(u*12*math.pi)))
            pore=rng.random()
            h=(.5+.30*grain+.08*math.sin(v*2*math.pi*173)+.1*pore) if wood else (.45+.18*math.sin(u*38)*math.sin(v*43)+.22*pore)
            heights.append(h)
            shades.append((.80+.20*h)-(.10*max(0,grain)**12 if wood else 0))
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    mat=bpy.data.materials.new(name);mat.use_nodes=True
    nodes=mat.node_tree.nodes; links=mat.node_tree.links
    bsdf=nodes.get('Principled BSDF');bsdf.inputs['Metallic'].default_value=metal
    for channel in ('basecolor','roughness','normal'):
        pixels=[]
        for y in range(n):
            for x in range(n):
                i=y*n+x
                if channel=='basecolor':
                    # Blender stores generated image pixels in linear space.
                    vals=[max(0,min(1,c*shades[i])) for c in rgb]
                    vals=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in vals]
                elif channel=='roughness':vals=[min(1,max(.05,rough+(heights[i]-.5)*.20))]*3
                else:
                    dx=(heights[y*n+(x+1)%n]-heights[y*n+(x-1)%n])*.6
                    dy=(heights[((y+1)%n)*n+x]-heights[((y-1)%n)*n+x])*.6
                    norm=Vector((-dx,-dy,1)).normalized(); vals=[a*.5+.5 for a in norm]
                pixels.extend((*vals,1))
        im=bpy.data.images.new(name+'_'+channel,n,n,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels);im.update()
        im.filepath_raw=str(out/'materials'/f'{name}-{channel}.png');im.file_format='PNG';im.save();im.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;tex.extension='REPEAT'
        if channel=='normal':
            normal=nodes.new('ShaderNodeNormalMap'); links.new(tex.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs[0],bsdf.inputs['Normal'])
        else:links.new(tex.outputs['Color'],bsdf.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked']=True
    mat['texture_method']='Deterministic sampled grain/pores, image albedo + roughness + tangent normal'
    return mat


def material(name,color,rough,metal,out,kind='stone',wood=False):
    if pbr and not wood:
        try:
            return pbr.material(kind,name=name,color=color,roughness=rough,metallic=metal,
                                bump=.009,bake=True,resolution=512,cache_dir=out/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake fallback: {exc}')
    return pixel_material(name,color,rough,metal,out,wood)


def plank(name,left,right,bottom,height,mat,seed):
    # Closed subdivided cross sections with physically cut longitudinal channels.
    rng=random.Random(seed); phase=rng.random()*6
    verts=[];sections=22
    for i in range(sections+1):
        t=i/sections;x=left+(right-left)*t
        for j in range(10):
            q=j/9
            groove=.009*math.exp(-((q-.34-.025*math.sin(t*8+phase))/.065)**2)
            groove+=.007*math.exp(-((q-.73-.015*math.sin(t*11+phase))/.05)**2)
            verts.append((x,-.238+groove+.002*math.sin(t*23+q*8+phase),bottom+height*q))
        verts.extend([(x,.105,bottom+height),(x,.105,bottom)])
    count=12;faces=[tuple(reversed(range(count)))]
    for i in range(sections):
        for j in range(count):
            a=i*count+j;b=i*count+(j+1)%count
            faces.append((a,b,b+count,a+count))
    faces.append(tuple(range(sections*count,(sections+1)*count)))
    faces = [tuple(reversed(f)) for f in faces]
    return bevel(mesh(name,verts,faces,mat),.005,2)


def supports(wood,iron,brick):
    for x in (-1.08,1.08):
        box('Rear timber upright',(.18,.105,1.72),(x,.1675,1),wood,.014)
        for z in (.20,1.80):
            box('Blackened masonry mounting shoe',(.30,.08,.24),(x,.21,z),brick,.018)
            box('Iron strap collar',(.23,.03,.075),(x,.226,z),iron,.009)
    # Diagonal load path sits entirely within the specified depth.
    obj=box('Rear diagonal timber brace',(2.3,.09,.14),(0,0,0),wood,.01)
    obj.rotation_euler[1]=-.52
    obj.location=(0,.166,1)


def create(asset_id,mats):
    global ROOT,COLLECTION
    COLLECTION=bpy.data.collections.new(asset_id)
    bpy.context.scene.collection.children.link(COLLECTION)
    ROOT=bpy.data.objects.new(asset_id,None);COLLECTION.objects.link(ROOT)
    ROOT['asset_id']=asset_id;ROOT['nominal_dimensions']='X=3, Y=0.5, Z=2'
    ROOT['front_axis']='-Y'; ROOT['origin']='bottom-center'
    iron,wood,wood_light,brick=mats['iron'],mats['wood'],mats['wood_light'],mats['brick']
    if asset_id=='wood-platform':
        # Six staggered strakes, enclosed ends and open narrow caulking joints.
        for row in range(6):
            z=row/3+.006
            split=(-.42 if row%2 else .53)
            for k,(a,b) in enumerate([(-1.5,split-.007),(split+.007,1.5)]):
                plank(f'Hull strake {row+1} segment {k+1}',a,b,z,1/3-.012,
                      wood if (row+k)%3 else wood_light,row*7+k)
        for x in (-1.18,1.18):
            box('Blackened iron hull band',(.075,.017,1.88),(x,-.238,1),iron,.006)
            for z in (.17,.50,.83,1.17,1.50,1.83):
                ring('Flush ship nail',x,z,[(0,-.249),(.021,-.249),(.023,-.240),(0,-.240)],iron,10)
        box('Top end-grain cap',(3,.35,.055),(0,-.075,1.9725),wood_light,.012)
        box('Lower keel edge',(3,.35,.045),(0,-.075,.0225),wood,.009)
    else:
        panel('Exposed timber structural core',2.96,1.96,-.19,.112,.10,wood,.02)
        face=panel('Rounded painted plaster face',3,2,-.25,-.16,.12,mats[asset_id])
        # Countersunk bores are genuine subtraction, not dark discs over an intact face.
        for x in (-1.28,1.28):
            for z in (.22,1.78):
                bore(face,x,z,.107,iron)
                fastener(x,z,iron)
        # Thin edge-bound return bands preserve the source's highlighted lower/right border.
        box('Lower painted return',(2.72,.20,.048),(0,-.105,.045),mats[asset_id],.015)
        # Restrained irregular exposed substrate chips on the outer edge, as actual shallow wedges.
        rng=random.Random(291)
        for i in range(13):
            x=rng.uniform(-1.15,1.15);w=rng.uniform(.012,.038)
            z=.012+rng.uniform(0,.015)
            mesh('Small chipped paint edge',[(x-w,-.2501,z),(x+w,-.2501,z+.005),
                 (x+w*.3,-.2501,z+rng.uniform(.008,.021)),(x,-.242,z)],
                 [(0,1,2),(0,3,1),(1,3,2),(2,3,0)],wood_light)
    supports(wood,iron,brick)
    return ROOT,list(COLLECTION.objects)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve();(out/'models').mkdir(parents=True,exist_ok=True);(out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    mats={}
    for ident,col in [('platform-coral','CC7768'),('platform-cream','E2CE99'),('platform-blue','719EAD')]:
        mats[ident]=material(ident+'-painted-plaster',col,.76,0,out)
    mats['iron']=material('Blackened forged iron','343534',.56,.78,out,kind='worn_brass')
    mats['brick']=material('Soot darkened mounting brick','49423C',.94,0,out,kind='brick')
    mats['wood']=material('Weathered oak','826044',.83,0,out,wood=True)
    mats['wood_light']=material('Exposed oak fibers','AA845B',.89,0,out,wood=True)
    entries=[];roots=[]
    for ident in IDS:
        root,objects=create(ident,mats);roots.append(root)
        bpy.ops.object.select_all(action='DESELECT')
        for obj in objects:obj.select_set(True)
        bpy.context.view_layer.objects.active=root
        path=out/'models'/f'{ident}.glb'
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                 export_extras=True,export_apply=True,export_materials='EXPORT',export_yup=True)
        used=sorted({m.name for obj in objects if obj.type=='MESH' for m in obj.data.materials})
        deps=bpy.context.evaluated_depsgraph_get();triangles=0
        for obj in objects:
            if obj.type=='MESH':
                ev=obj.evaluated_get(deps);me=ev.to_mesh();me.calc_loop_triangles();triangles+=len(me.loop_triangles);ev.to_mesh_clear()
        entry={'asset_id':ident,'path':f'models/{ident}.glb','nominaldimensions':{'width':3,'height':2,'depth':.5},
               'materials':used,'triangles':triangles,
               'meshfeatures':['separate editable closed structural parts','beveled silhouette','rear timber uprights and diagonal brace','blackened masonry mounting shoes',
                               'subdivided carved planks, staggered joints, iron bands and nails' if ident=='wood-platform' else 'rounded plaster skin, true recessed corner bores, inset hex bolts and exposed edge chips'],
               'sourcebasis':{'catalog':'smb3-rom-assets/catalog','visual_sheet':'observed-metatile-00.png',
                              'evidence':'Colored large panel cells with corner fasteners and lower/right edge bands; rectangular 3x2 composition from user brief.',
                              'wood_context':'binary-assets.json context-10-0-10, Tile_Layout_TS10, PalSet_Airship; physical joinery is authored interpretation.'},
               'knownqualitylimitations':['Not rendered or visually verified during authoring.','Fine wood and plaster variation is synthesized image PBR, not scanned material.','Rear construction and dimensions are artistic reconstruction; no exact assembled ROM object mapping.']}
        if pbr and hasattr(pbr,'inspect_glb'):entry['export_inspection']=pbr.inspect_glb(path)
        entries.append(entry)
    # Exports above are at origin; only the inspection library is spaced apart.
    for i,root in enumerate(roots):root.location=((i%2)*3.8,(i//2)*1.8,0)
    bpy.ops.object.select_all(action='DESELECT')
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    style_path=SHARED/'design'/'style.json'
    style=json.loads(style_path.read_text()) if style_path.exists() else {'units':'Z up, -Y front; 1 unit = 16 NES pixels'}
    (out/'manifest.json').write_text(json.dumps({'assets':entries,'style_contract':style,'build_warnings':WARNINGS},indent=2))


if __name__=='__main__':
    main()
