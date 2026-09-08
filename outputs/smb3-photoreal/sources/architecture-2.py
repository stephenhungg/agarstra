"""Editable architectural modules. Execute only in the central Blender 4.5 queue."""
import argparse
import json
import math
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

IDS = ['castle-wall', 'castle-door', 'airship-hull']
WARNINGS = []
ROOT = None
COLLECTION = None
MATS = {}
OUT = None


def texture_material(name, color, roughness, metallic=0, wood=False):
    """Deterministic tileable image PBR; no procedural nodes remain at export."""
    size = 512
    heights = []
    for y in range(size):
        v = y / size
        for x in range(size):
            u = x / size
            if wood:
                warp = .012 * math.sin(2*math.pi*u*3) + .006*math.sin(2*math.pi*u*7)
                grain = math.sin(2*math.pi*(v*67 + warp*28))
                pores = max(0, math.sin(2*math.pi*(v*139 + warp*40)))**18
                h = .5 + .19*grain + .12*math.sin(2*math.pi*(v*17+warp*12)) - .2*pores
            else:
                h = .5 + .15*math.sin(2*math.pi*(u*43+v*31))*math.sin(2*math.pi*(u*19-v*53))
            h += .04*math.sin(2*math.pi*(u*179+v*113))
            heights.append(h)
    buffers = {k: array('f') for k in ('basecolor', 'roughness', 'normal')}
    for y in range(size):
        for x in range(size):
            i=y*size+x
            h=heights[i]
            dx=(heights[y*size+(x+1)%size]-heights[y*size+(x-1)%size])*.48
            dy=(heights[((y+1)%size)*size+x]-heights[((y-1)%size)*size+x])*.48
            n=Vector((-dx,-dy,1)).normalized()
            buffers['normal'].extend((n.x*.5+.5,n.y*.5+.5,n.z*.5+.5,1))
            r=max(.1,min(.98,roughness+(h-.5)*.2))
            buffers['roughness'].extend((r,r,r,1))
            tint=.72+.46*h
            buffers['basecolor'].extend((*[min(.98,c*tint) for c in color],1))
    mat=bpy.data.materials.new(name)
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    links=mat.node_tree.links
    shader=nodes.get('Principled BSDF')
    shader.inputs['Metallic'].default_value=metallic
    shader.inputs['Roughness'].default_value=roughness
    for channel,pixels in buffers.items():
        im=bpy.data.images.new(name+'_'+channel,width=size,height=size,alpha=False)
        im.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color'
        im.pixels.foreach_set(pixels)
        im.filepath_raw=str(OUT/'materials'/f'{name}-{channel}.png')
        im.file_format='PNG'
        im.save()
        im.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=im;tex.extension='REPEAT'
        if channel=='normal':
            normal=nodes.new('ShaderNodeNormalMap')
            links.new(tex.outputs['Color'],normal.inputs['Color'])
            links.new(normal.outputs['Normal'],shader.inputs['Normal'])
        else:
            links.new(tex.outputs['Color'],shader.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked']=True
    mat['texture_method']='deterministic image synthesis; directional timber grain' if wood else 'deterministic image synthesis fallback'
    return mat


def material(name, kind, color, roughness, metallic=0):
    if pbr:
        try:
            return pbr.material(kind,name=name,color=color,roughness=roughness,
                                metallic=metallic,bake=True,resolution=512,cache_dir=OUT/'materials')
        except Exception as exc:
            WARNINGS.append(f'{name}: shared helper failed; image fallback used: {exc}')
    rgb=tuple(int(color[i:i+2],16)/255 for i in (0,2,4))
    return texture_material(name,rgb,roughness,metallic)


def mesh(name, vertices, faces, mat, bevel=0, uv_mode='world'):
    data=bpy.data.meshes.new(name)
    data.from_pydata(vertices,[],faces);data.update()
    obj=bpy.data.objects.new(name,data);COLLECTION.objects.link(obj)
    obj.parent=ROOT
    obj['asset_id']=ROOT['asset_id']
    data.materials.append(mat)
    uv=data.uv_layers.new(name='UVMap')
    for poly in data.polygons:
        axis=max(range(3),key=lambda i:abs(poly.normal[i]))
        for li in poly.loop_indices:
            co=data.vertices[data.loops[li].vertex_index].co
            if axis==1: a,b=co.x,co.z
            elif axis==2: a,b=co.x,co.y
            else: a,b=co.y,co.z
            if uv_mode=='vertical':a,b=b,a
            uv.data[li].uv=(a,b)
    if bevel:
        mod=obj.modifiers.new('Editable edge wear bevel','BEVEL')
        mod.width=bevel;mod.segments=2
        mod.limit_method='ANGLE'
    return obj


def box(name, center, size, mat, bevel=.012, uv_mode='world'):
    x,y,z=center;w,d,h=[s/2 for s in size]
    vertices=[(x+a*w,y+b*d,z+c*h) for a,b,c in
              [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]]
    faces=[(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
    return mesh(name,vertices,faces,mat,bevel,uv_mode)


def prism(name, outline, front, back, mat, bevel=.008):
    # outline counterclockwise in XZ yields front normals toward -Y.
    n=len(outline)
    verts=[(x,y,z) for y in (front,back) for x,z in outline]
    faces=[tuple(range(n)),tuple(range(2*n-1,n-1,-1))]
    faces += [(i+n,(i+1)%n+n,(i+1)%n,i) for i in range(n)]
    return mesh(name,verts,faces,mat,bevel)


def ring(name,x,z,profile,mat,segments=16):
    # Closed radius/Y profile is an actual annulus, not a painted bolt recess.
    vertices=[(x+r*math.cos(j*2*math.pi/segments),y,z+r*math.sin(j*2*math.pi/segments))
              for r,y in profile for j in range(segments)]
    faces=[]
    for row in range(len(profile)):
        nxt=(row+1)%len(profile)
        for j in range(segments):
            k=(j+1)%segments
            faces.append((row*segments+j,row*segments+k,nxt*segments+k,nxt*segments+j))
    return mesh(name,vertices,faces,mat)


def bolt(x,z,y=-.23, radius=.037):
    ring('Countersunk washer',x,z,[(radius*1.6,y+.026),(radius*1.6,y),
         (radius*1.14,y),(radius*.98,y+.02)],MATS['iron'])
    outline=[(x+radius*math.cos(i*math.pi/3),z+radius*math.sin(i*math.pi/3)) for i in range(6)]
    prism('Recessed hex head',outline,y+.013,y+.035,MATS['brass'],.002)
    box('Forged head slot',(x,y+.010,z),(radius*1.15,.004,.006),MATS['dark'],.001)


def support():
    for x in (-1.1,1.1):
        box('Rear timber upright',(x,.185,1),(.16,.13,1.84),MATS['wood_dark'],.018,'vertical')
    box('Rear cross rail',(0,.185,.47),(2.6,.13,.14),MATS['wood_dark'])
    box('Rear cross rail',(0,.185,1.54),(2.6,.13,.14),MATS['wood_dark'])
    for x in (-1.28,1.28):
        for z in (.22,1.78):
            box('Corner mounting plate',(x,-.195,z),(.22,.055,.22),MATS['iron'],.025)
            bolt(x,z)


def castle_wall():
    box('Mortared panel core',(0,0,1),(3,.29,2),MATS['mortar'],.045)
    for row in range(6):
        z=.17+row*.327
        bounds=[-1.46]
        bounds += ([-.98,-.25,.48,1.21] if row%2 else [-.73,0,.73])
        bounds += [1.46]
        for j,(a,b) in enumerate(zip(bounds,bounds[1:])):
            h=.303 + .004*math.sin(row*7+j*3)
            obj=box(f'Blackened brick course {row+1} stone {j+1}',((a+b)/2,-.163,z),
                    (b-a-.024,.145,h),MATS['brick' if (j+row)%3 else 'brick_alt'],.019)
            obj['construction']='individually editable staggered masonry; mortar beds retained'
    support()


def castle_door():
    # Flat topped double door follows TILE2_ENDDOOR quadrants, with a broad frame.
    box('Upper lintel',(0,-.005,1.85),(3,.42,.30),MATS['brick'],.04)
    for x in (-1.34,1.34):
        box('Stone jamb',(x,-.005,.85),(.32,.42,1.7),MATS['brick'],.03)
        for z in (.38,.8,1.22):
            box('Jamb mortar seam',(x,-.219,z),(.306,.008,.013),MATS['mortar'],.002)
    box('Threshold',(0,.005,.06),(2.4,.41,.12),MATS['brick_alt'],.02)
    for side in (-1,1):
        leaf=bpy.data.objects.new('Left leaf pivot' if side<0 else 'Right leaf pivot',None)
        COLLECTION.objects.link(leaf);leaf.parent=ROOT
        leaf.location=(side*1.15,0,.12)
        before=set(COLLECTION.objects)
        for j in range(5):
            x=side*(.135+j*.223)
            box('Vertical oak door board',(x,-.025,.9),(.214,.25,1.56),MATS['wood_dark'],.013,'vertical')
            # A second, inset field produces real raised-panel construction.
        for z in (.30,1.46):
            box('Forged hinge strap',(side*.585,-.177,z),(1.10,.043,.105),MATS['iron'],.014)
            for x in (.2,.58,1.02):bolt(side*x,z,-.208,.025)
        box('Door bottom weather rail',(side*.586,-.165,.16),(1.12,.06,.075),MATS['wood'])
        box('Lock escutcheon',(side*.16,-.18,.87),(.12,.045,.22),MATS['iron'],.024)
        ring('Pull handle',side*.16,.83,[(.067,-.22),(.067,-.255),(.046,-.255),(.046,-.22)],MATS['brass'],20)
        for obj in set(COLLECTION.objects)-before:
            obj.parent=leaf
            obj.location=-leaf.location
    for x in (-1.33,1.33):
        for z in (.23,1.78):bolt(x,z,-.239)
    for x in (-1.32,1.32):
        box('Rear frame reinforcement',(x,.215,.95),(.13,.07,1.8),MATS['wood_dark'],.012,'vertical')


def airship_hull():
    # Side-on modular hull bay, not an entire vessel; lower chine narrows slightly.
    def width(z):return 1.21+.29*min(1,z/.67)
    for row in range(7):
        low=row*2/7+.009;high=(row+1)*2/7-.009
        w0=width(low);w1=width(high)
        cuts=[-1, -.22 if row%2 else .3,1]
        for j,(a,b) in enumerate(zip(cuts,cuts[1:])):
            outline=[(a*w0+.006,low),(b*w0-.006,low),(b*w1-.006,high),(a*w1+.006,high)]
            prism(f'Hull strake {row+1} scarf section {j+1}',outline,-.20-.007*(row%2),.11,
                  MATS['wood' if (row+j)%3 else 'wood_dark'],.012)
        for x in (-.97,.95):bolt(x,(low+high)/2,-.229,.023)
    box('Upper gunwale',(0,-.025,1.935),(3,.45,.13),MATS['wood_dark'],.028)
    box('Lower keel rail',(0,-.035,.06),(2.42,.40,.12),MATS['wood_dark'],.025)
    for x in (-1.06,1.06):
        box('Rear hull rib',(x,.177,1.08),(.15,.146,1.73),MATS['wood_dark'],.022,'vertical')
    # Front metal bands wrap the timber bay, with recessed bolts at both ends.
    for x in (-1.24,1.24):
        box('Iron hull strap',(x,-.222,1.29),(.092,.036,1.25),MATS['iron'],.014)
        for z in (.74,1.82):bolt(x,z,-.248,.027)
    # Shallow carved timber checks: V-profile incisions represented by separate dark inset splinters.
    for i in range(12):
        x=-.8+(i%4)*.49;z=.43+(i//4)*.57
        prism('Split grain inset',[(x,z),(x+.23,z+.008),(x+.33,z+.002),(x+.04,z-.004)],
              -.209,-.201,MATS['dark'],0)


def descendants(root):
    return [root]+list(root.children_recursive)


def stats(root):
    bpy.context.view_layer.update()
    dg=bpy.context.evaluated_depsgraph_get()
    points=[];tris=0
    for obj in descendants(root):
        if obj.type!='MESH':continue
        evaluated=obj.evaluated_get(dg)
        points.extend(evaluated.matrix_world @ Vector(corner) for corner in evaluated.bound_box)
        data=evaluated.to_mesh();data.calc_loop_triangles();tris+=len(data.loop_triangles)
        evaluated.to_mesh_clear()
    dims=[round(max(p[i] for p in points)-min(p[i] for p in points),4) for i in range(3)]
    return dims,tris


def verify_glb(path):
    import struct
    raw=path.read_bytes()
    assert raw[:4]==b'glTF'
    length=struct.unpack_from('<I',raw,12)[0]
    doc=json.loads(raw[20:20+length])
    assert all('bufferView' in im for im in doc.get('images',[])), 'External texture found'
    assert not doc.get('cameras'), 'Unexpected camera'
    for mat in doc.get('materials',[]):
        assert 'normalTexture' in mat, f'Missing normal texture: {mat.get("name")}'
        p=mat['pbrMetallicRoughness']
        assert 'baseColorTexture' in p and 'metallicRoughnessTexture' in p
    return {'embedded_images':len(doc.get('images',[])), 'material_texture_checks':'passed'}


def main():
    global ROOT,COLLECTION,MATS,OUT
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    OUT=Path(args.out).resolve()
    (OUT/'models').mkdir(parents=True,exist_ok=True)
    (OUT/'materials').mkdir(parents=True,exist_ok=True)
    for obj in list(bpy.data.objects):bpy.data.objects.remove(obj,do_unlink=True)
    MATS={
        'brick':material('Soot black fired masonry','brick','33353A',.88),
        'brick_alt':material('Ash worn brick edges','brick','45464A',.85),
        'mortar':material('Recessed lime mortar','stone','777267',.94),
        'iron':material('Blackened forged iron','stone','34332F',.51,.78),
        'brass':material('Aged fastener metal','worn_brass','897044',.48,.82),
        'dark':material('Timber crevice','stone','21190F',.96),
        'wood':texture_material('Weathered honey oak',(.46,.29,.135),.78,wood=True),
        'wood_dark':texture_material('Dark aged structural oak',(.29,.165,.072),.84,wood=True),
    }
    basis={
        'castle-wall':['Tile_Layout_TS2-156 / TILE2_SOLIDBRICK: Solid Bowser castle style brick'],
        'castle-door':['Tile_Layout_TS2-151..154 / TILE2_ENDDOOR_UL, UR, LL, LR: rectangular final door quadrants'],
        'airship-hull':['Tile_Layout_TS10-226..229 / TILE10_WOODH: horizontal logs',
                        'Tile_Layout_TS10-249..254 / WOODBOTTOM, LEDGE, REARTIP',
                        'context-10-0-10 / PalSet_Airship'],
    }
    features={
        'castle-wall':['staggered individual beveled black bricks','recessed lime mortar beds','corner countersunk hex fasteners','rear timber framing'],
        'castle-door':['rectangular lintel and jambs','two independently pivoted plank leaves','forged straps and recessed fasteners','open ring handles','threshold and rear reinforcement'],
        'airship-hull':['seven separate thick hull strakes','staggered butt joints','tapered lower chine','gunwale and keel','iron bands and recessed hex bolts','rear timber ribs','grain checks'],
    }
    records=[];roots=[]
    for aid,builder in zip(IDS,(castle_wall,castle_door,airship_hull)):
        COLLECTION=bpy.data.collections.new(aid)
        bpy.context.scene.collection.children.link(COLLECTION)
        ROOT=bpy.data.objects.new(aid,None);COLLECTION.objects.link(ROOT)
        ROOT['asset_id']=aid;ROOT['front_axis']='-Y';ROOT['unit']='1 block = 16 NES pixels'
        builder();roots.append(ROOT)
        dims,tris=stats(ROOT)
        path=OUT/'models'/f'{aid}.glb'
        bpy.ops.object.select_all(action='DESELECT')
        for obj in descendants(ROOT):obj.select_set(True)
        bpy.context.view_layer.objects.active=ROOT
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_extras=True,export_apply=True,export_yup=True,
                                  export_materials='EXPORT',export_image_format='AUTO')
        check=verify_glb(path)
        records.append({'asset_id':aid,'path':f'models/{aid}.glb',
            'nominaldimensions':{'width':3,'height':2,'depth':.5},'actual_dimensions_xyz':dims,
            'triangles_evaluated':tris,'materials':sorted({slot.material.name for o in descendants(ROOT)
              if o.type=='MESH' for slot in o.material_slots if slot.material}),
            'meshfeatures':features[aid], 'sourcebasis':basis[aid],
            'knownqualitylimitations':['Source-inspired reinterpretation, not a pixel-exact reconstruction.',
              'Rendered appearance requires central queue inspection.',
              'Hardware may project slightly beyond nominal depth; actual dimensions recorded.',
              'Synthesized repeating timber grain; no photographic texture scans.'], 'export_checks':check})
    for i,root in enumerate(roots):root.location.x=(i-1)*4.3
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file:im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'library.blend'))
    contract=SHARED/'design'/'style.json'
    style=json.loads(contract.read_text()) if contract.exists() else {'units':'Z up, front -Y, bottom-center'}
    (OUT/'manifest.json').write_text(json.dumps({'assets':records,'warnings':WARNINGS,
       'coordinate_contract':'Blender Z up / -Y front; glTF Y up; individual exports bottom-center origin',
       'library_layout':'Roots spaced 4.3 units along X for inspection; GLBs exported before layout',
       'style_contract':style},indent=2)+'\n')


if __name__=='__main__':main()
