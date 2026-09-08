"""Editable SMB3 block family. Run only through the central Blender queue."""
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

WARNINGS = []
ASSETS = ['question-block', 'used-block', 'brick-block']


def activate(obj):
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj


def mesh(name, verts, faces, mat=None, bevel=0):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    ob = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(ob)
    if mat:
        data.materials.append(mat)
    # Face-local planar UVs in world-scale units: no procedural-only materials.
    uv = data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        normal = poly.normal
        axis = max(range(3), key=lambda i: abs(normal[i]))
        axes = [i for i in range(3) if i != axis]
        for li in poly.loop_indices:
            co = data.vertices[data.loops[li].vertex_index].co
            uv.data[li].uv = (co[axes[0]], co[axes[1]])
    if bevel:
        mod = ob.modifiers.new('Machined edge radius', 'BEVEL')
        mod.width = bevel
        mod.segments = 3
    return ob


def box(name, size, center, mat, bevel=.012):
    x, y, z = (v / 2 for v in size)
    verts = [(a*x+center[0], b*y+center[1], c*z+center[2])
             for a,b,c in [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),
                           (-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    return mesh(name, verts, [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),
                               (3,0,4,7),(4,5,6,7)], mat, bevel)


def fallback_material(name, color, roughness, metallic, cache):
    """Deterministic raster PBR fallback, including tangent-space normal texture."""
    import hashlib
    rng = random.Random(int(hashlib.sha256(name.encode()).hexdigest()[:8], 16))
    n = 512
    heights = [rng.random() for _ in range(n*n)]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Metallic'].default_value = metallic
    rgb = [int(color[i:i+2],16)/255 for i in (0,2,4)]
    for channel in ['basecolor', 'roughness', 'normal']:
        image = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        pixels = []
        for y in range(n):
            for x in range(n):
                h = heights[y*n+x]
                broad = math.sin(x*.073)*math.sin(y*.059)*.08
                if channel == 'basecolor':
                    v = [.78*c + c*(h*.25+broad) for c in rgb]
                elif channel == 'roughness':
                    v = [min(1,max(.05,roughness+(h-.5)*.18+broad))]*3
                else:
                    dx = (heights[y*n+(x+1)%n]-h)*.28
                    dy = (heights[((y+1)%n)*n+x]-h)*.28
                    normal = Vector((-dx,-dy,1)).normalized()
                    v = [t*.5+.5 for t in normal]
                pixels.extend(v+[1])
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(cache / (name+'_'+channel+'.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = image
        if channel == 'normal':
            norm = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            mat.node_tree.links.new(node.outputs['Color'], norm.inputs['Color'])
            mat.node_tree.links.new(norm.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            mat.node_tree.links.new(node.outputs['Color'], bsdf.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    return mat


def material(kind, name, color, roughness, metallic=0):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=metallic, bake=True, resolution=512, cache_dir=CACHE)
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed; raster fallback: {exc}')
    return fallback_material(name, color, roughness, metallic, CACHE)


def root(asset_id):
    ob = bpy.data.objects.new(asset_id, None)
    bpy.context.collection.objects.link(ob)
    ob['asset_id'] = asset_id
    ob['units'] = '1 unit = 16 NES pixels'
    return ob


def attach(ob, parent, angle=0):
    ob.parent = parent
    ob.rotation_euler.z = angle
    return ob


def ring(name, profile, x, z, mat, parent, angle):
    # Profile (radius, depth) revolves around face normal, front = -Y.
    count = 20
    verts = [(x+r*math.cos(i*2*math.pi/count), depth,
              z+r*math.sin(i*2*math.pi/count)) for r,depth in profile for i in range(count)]
    faces = []
    for j in range(len(profile)-1):
        for i in range(count):
            a=j*count+i; b=j*count+(i+1)%count
            faces.append((a,a+count,b+count,b))
    ob = attach(mesh(name, verts, faces, mat), parent, angle)
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def frame(parent, angle, metal):
    loops=[]
    for half,y in [(.5,-.5),(.433,-.5),(.416,-.477),(.416,-.46),(.5,-.46)]:
        loops.extend([(-half,y,.5-half),(half,y,.5-half),(half,y,.5+half),(-half,y,.5+half)])
    faces=[]
    for j in range(5):
        for i in range(4):
            k=(i+1)%4; nxt=(j+1)%5
            faces.append((j*4+i,j*4+k,nxt*4+k,nxt*4+i))
    attach(mesh('Cast perimeter with recessed reveal',loops,faces,metal,.005),parent,angle)


def question(parent, angle, brass, dark):
    # Smooth typographic hook, solid rectangular ribbon, not a pixel extrusion.
    curves = [((-.19,.66),(-.20,.88),(.22,.88),(.22,.69)),
              ((.22,.69),(.22,.59),(.04,.59),(.04,.49)),
              ((.04,.49),(.04,.47),(.04,.44),(.04,.42))]
    points=[]
    for ci, controls in enumerate(curves):
        for k in range(13):
            if ci and k==0: continue
            t=k/12; u=1-t
            points.append(tuple(u**3*controls[0][i]+3*u*u*t*controls[1][i]+3*u*t*t*controls[2][i]+t**3*controls[3][i] for i in range(2)))
    for width,back,front,mat,label in [(.133,-.479,-.481,dark,'Hook recessed shadow'),(.106,-.479,-.496,brass,'Embossed question hook')]:
        verts=[]
        for i,(x,z) in enumerate(points):
            prev=Vector(points[max(0,i-1)]); nxt=Vector(points[min(len(points)-1,i+1)])
            tangent=(nxt-prev).normalized(); nx,nz=-tangent.y,tangent.x
            for y in (back,front):
                for s in (-1,1): verts.append((x+s*nx*width/2,y,z+s*nz*width/2))
        faces=[(0,2,3,1)]
        for i in range(len(points)-1):
            a=i*4;b=a+4
            faces += [(a,b,b+1,a+1),(a+2,a+3,b+3,b+2),(a,a+2,b+2,b),(a+1,b+1,b+3,a+3)]
        a=(len(points)-1)*4;faces.append((a,a+1,a+3,a+2))
        attach(mesh(label,verts,faces,mat,.004),parent,angle)
    attach(box('Question dot',(.11,.017,.105),(.04,-.487,.282),brass,.014),parent,angle)


def metal_block(asset_id, used=False):
    parent=root(asset_id)
    coat=M['used'] if used else M['enamel']
    attach(box('Solid cast chassis',(.94,.94,1),(0,0,.5),M['brass'],.025),parent)
    for side in range(4):
        angle=side*math.pi/2
        frame(parent,angle,coat)
        attach(box('Inset face plate',(.836,.025,.836),(0,-.463,.5),coat,.013),parent,angle)
        for x in (-.365,.365):
            for z in (.135,.865):
                # Annular conical seat descends beneath a flush split screw head.
                ring('Countersunk seat',[(.034,-.477),(.024,-.482),(.019,-.473),(.034,-.477)],x,z,M['dark'],parent,angle)
                ring('Beveled screw head',[(0,-.476),(.019,-.476),(.024,-.479),(.024,-.483),(0,-.483)],x,z,M['brass'],parent,angle)
                attach(box('Screwdriver slot',(.031,.0015,.004),(x,-.484,z),M['dark'],.001),parent,angle)
        if not used:
            question(parent,angle,M['brass'],M['dark'])
        else:
            # Second stepped interior panel and cast ribs communicate spent state.
            attach(box('Inner panel dark reveal',(.64,.008,.64),(0,-.48,.5),M['dark'],.018),parent,angle)
            attach(box('Worn blank panel',(.612,.009,.612),(0,-.484,.5),coat,.018),parent,angle)
        rng=random.Random(81+side)
        for i in range(7):
            x=rng.uniform(-.33,.33); z=rng.choice([.088,.911])+rng.uniform(-.008,.008)
            ob=box('Small exposed enamel chip',(.018+rng.random()*.033,.002,.004+rng.random()*.006),(x,-.501,z),M['brass'],.001)
            attach(ob,parent,angle)
    return parent


def masonry(asset_id, variant='masonry'):
    parent=root(asset_id)
    parent['variant']=variant
    mortar=M['mortar'] if variant!='ice' else M['frost']
    attach(box('Recessed continuous joint core',(.952,.952,.956),(0,0,.5),mortar,.012),parent)
    palette={'masonry':[M['brick'],M['brick2']], 'stone':[M['stone']], 'ice':[M['ice']]}[variant]
    rng=random.Random(133)
    # Full-depth bonded units, including top and underside. No facade planes.
    for row in range(3):
        limits=[-.5,0,.5] if row%2==0 else [-.5,-.25,.25,.5]
        for col,(left,right) in enumerate(zip(limits,limits[1:])):
            for course in range(2):
                gap=.018
                ob=box(f'{variant} course {row+1} unit {col+1}-{course+1}',
                    (right-left-gap,.5-gap,1/3-gap),
                    ((left+right)/2,-.25+course*.5,(row+.5)/3),
                    palette[(row+col+course)%len(palette)],.012 if variant!='ice' else .022)
                # Mild asymmetric arrises; retain the 1-unit tile envelope.
                if variant!='ice':
                    for v in ob.data.vertices:
                        for axis in range(3): v.co[axis]+=rng.uniform(-.003,.003)
                attach(ob,parent)
    if variant=='ice':
        # Fine embedded fracture ribbons: opaque frost geometry inside outer seams.
        for side in range(4):
            for i in range(3):
                x=-.3+i*.29
                verts=[(x,-.492,.18),(x+.026,-.492,.19),(x+.09,-.492,.51),
                       (x+.065,-.492,.54),(x+.12,-.492,.77)]
                ob=mesh('Frost fracture',verts,[(0,1,2,3),(3,2,4)],M['frost'])
                solid=ob.modifiers.new('Fracture thickness','SOLIDIFY');solid.thickness=.001
                attach(ob,parent,side*math.pi/2)
    return parent


def ground(parent):
    bpy.context.view_layer.update()
    bottom=min((ob.matrix_world @ Vector(c)).z for ob in parent.children_recursive
               if ob.type=='MESH' for c in ob.bound_box)
    for ob in parent.children:
        ob.location.z -= bottom
    bpy.context.view_layer.update()


def export(parent, path):
    activate(parent)
    for ob in parent.children_recursive: ob.select_set(True)
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                             export_apply=True,export_extras=True,export_yup=True,
                             export_materials='EXPORT',export_image_format='AUTO')


def main():
    global CACHE,M
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    parser.add_argument('--brick-variant',choices=['masonry','stone','ice'],default='masonry')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=Path(args.out).resolve();out.mkdir(parents=True,exist_ok=True)
    (out/'models').mkdir(exist_ok=True)
    CACHE=out/'materials';CACHE.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    M={}
    recipes=[('enamel','yellow_enamel','DCAA32',.34,.18),('used','yellow_enamel','94703B',.63,.12),
             ('brass','worn_brass','C19648',.43,.78),('dark','stone','473B2A',.83,0),
             ('brick','brick','A76143',.88,0),('brick2','brick','965037',.9,0),
             ('mortar','stone','9D9786',.96,0),('stone','stone','77796F',.89,0),
             ('ice','stone','A9D6E3',.27,0),('frost','stone','D3E7E9',.75,0)]
    for name,kind,color,rough,metal in recipes:
        M[name]=material(kind,'blocks_'+name,color,rough,metal)
    ice_bsdf=next(n for n in M['ice'].node_tree.nodes if n.type=='BSDF_PRINCIPLED')
    ice_bsdf.inputs['Transmission Weight'].default_value=.38
    ice_bsdf.inputs['IOR'].default_value=1.31
    roots=[metal_block('question-block'),metal_block('used-block',True),masonry('brick-block',args.brick_variant)]
    entries=[]
    for parent in roots:
        ground(parent)
        asset_id=parent['asset_id'];path=out/'models'/f'{asset_id}.glb'
        bpy.context.view_layer.update()
        export(parent,path)
        corners=[ob.matrix_world@Vector(c) for ob in parent.children_recursive if ob.type=='MESH' for c in ob.bound_box]
        dims=[round(max(v[i] for v in corners)-min(v[i] for v in corners),5) for i in range(3)]
        entries.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb','nominal_dimensions':[1,1,1],
            'measured_dimensions':dims,'materials':sorted({m.name for ob in parent.children_recursive if ob.type=='MESH' for m in ob.data.materials}),
            'mesh_features': ['Beveled editable cast frame','Inset panels','Conical screw seats','Embossed smooth question hook' if asset_id=='question-block' else 'Blank stepped panels'] if asset_id!='brick-block' else ['Separate full-depth bonded masonry units','Recessed mortar','Irregular beveled arrises',args.brick_variant],
            'source_basis':{'catalog':'observed-metatile-00.png','question_reference':'observed-metatile-2a3e8b18f2562fd1892d','used_reference':'observed-metatile-2bfb0a8c6f4893db93ca','notes':'Golden square and corner marks observed; depth, material wear and bonded masonry are authored interpretation. Stone and ice are brief-driven variants, not verified ROM identities.'},
            'known_quality_limitations':['Not rendered or visually verified by author; central queue must inspect.','Raster microdetail is repeated; no unique hand-painted wear map.','Fastener slots use inset dark inserts, not boolean-cut screw heads.']})
    for i,parent in enumerate(roots): parent.location.x=i*1.6
    for i,variant in enumerate(['stone','ice']):
        parent=masonry('brick-block--'+variant+'-study',variant)
        ground(parent)
        parent.location=(i*1.6,-1.6,0)
        parent['library_only']=True
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file: image.pack()
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=1
    scene['style_contract']= (SHARED/'design/style.json').read_text() if (SHARED/'design/style.json').exists() else 'Z up, front -Y; one unit blocks; grounded PBR'
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':entries,'library_variants':['stone','ice'],
        'warnings':WARNINGS,'validation':'Authored only; Blender execution and visual review delegated to central queue.'},indent=2))

if __name__=='__main__':
    main()
