"""Editable SMB3 vegetation family. Run only through the central Blender queue."""
import argparse
import json
import math
import random
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
SOURCE = {
    'catalog': '/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-rom-assets/catalog',
    'visual_reference': 'observed-metatile-00.png',
    'semantic_reference': 'binary-asset-manifest.json',
    'bush_symbols': ['TILE1_LITTLE_BUSH', 'TILE1_BUSH_UL', 'TILE1_BUSH_UR', 'TILE1_BUSH_FUL', 'TILE1_BUSH_FUR'],
    'hill_symbols': ['TILE11_HILL_PEAK', 'TILE11_HILL_LSLOPE', 'TILE11_HILL_RSLOPE'],
    'interpretation': 'Rounded crowns, upright hill sides and overlapping bush lobes; depth and botanical detail are authored reinterpretations, not ROM geometry.'
}
WARNINGS = []


def fallback_material(name, color, roughness, cache):
    """Deterministic raster PBR maps, no external packages or procedural-only shaders."""
    n = 512
    rgb = [int(color[i:i+2], 16) / 255 for i in (0, 2, 4)]
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = []
        for y in range(n):
            v = y / n
            for x in range(n):
                u = x / n
                a = TAU * (13*u + 3*v)
                b = TAU * (7*v - 2*u)
                grain = math.sin(a)*math.sin(b)
                fine = math.sin(TAU*97*u)*math.cos(TAU*83*v)
                if channel == 'basecolor':
                    values = [c*(.86 + .12*grain + .035*fine) for c in rgb]
                elif channel == 'roughness':
                    values = [max(.1, min(1, roughness + .07*grain + .03*fine))]*3
                else:
                    dx = .14*math.cos(a)*math.sin(b) + .05*math.cos(TAU*97*u)
                    dy = .14*math.sin(a)*math.cos(b) + .05*math.sin(TAU*83*v)
                    normal = Vector((-dx, -dy, 1)).normalized()
                    values = [.5+.5*c for c in normal]
                pixels.extend((*values, 1))
        img = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        img.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        img.pixels.foreach_set(pixels)
        img.filepath_raw = str(cache / (name+'_'+channel+'.png'))
        img.file_format = 'PNG'
        img.save()
        img.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = img
        if channel == 'normal':
            normal = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            mat.node_tree.links.new(tex.outputs['Color'], normal.inputs['Color'])
            mat.node_tree.links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'Deterministic raster fallback'
    return mat


def material(kind, name, color, roughness, cache):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                bake=True, resolution=512, cache_dir=cache)
        except Exception as exc:
            WARNINGS.append(f'{name}: shared bake failed; raster fallback used: {exc}')
    return fallback_material(name, color, roughness, cache)


class Geometry:
    def __init__(self):
        self.vertices, self.faces, self.uvs, self.slots = [], [], [], []

    def vert(self, co, uv):
        self.vertices.append(tuple(co))
        self.uvs.append(uv)
        return len(self.vertices)-1

    def face(self, ids, slot=0):
        self.faces.append(tuple(ids))
        self.slots.append(slot)

    def object(self, name, root, materials):
        mesh = bpy.data.meshes.new(name)
        mesh.from_pydata(self.vertices, [], self.faces)
        mesh.update()
        uv = mesh.uv_layers.new(name='UVMap')
        for face, slot in zip(mesh.polygons, self.slots):
            face.material_index = slot
            face.use_smooth = True
            for loop in face.loop_indices:
                uv.data[loop].uv = self.uvs[mesh.loops[loop].vertex_index]
        obj = bpy.data.objects.new(name, mesh)
        root.users_collection[0].objects.link(obj)
        obj.parent = root
        obj['asset_id'] = root['asset_id']
        for mat in materials:
            mesh.materials.append(mat)
        return obj


def surface(t, angle, center, radii, power, phase):
    # Dome with restrained, multi-scale scalloping; no smooth balloon primitives.
    rx, ry, h = radii
    radial = max(0, 1-t**power)**.5
    ripple = 1 + .025*math.sin(9*angle+phase+5*t) + .018*math.cos(17*angle-11*t)
    x = rx*radial*math.cos(angle)*ripple
    y = ry*radial*math.sin(angle)*ripple
    z = h*t + .018*h*math.sin(7*angle+8*t)*math.sin(math.pi*t)
    return Vector((x+center[0], y+center[1], z+center[2]))


def core(g, center, radii, power, phase, segments=40, rings=14, earthy=False):
    rows=[]
    for k in range(rings):
        t = k/rings
        row=[]
        for j in range(segments+1):
            row.append(g.vert(surface(t, TAU*j/segments, center, radii, power, phase), (j/segments*3,t*3)))
        rows.append(row)
    for k in range(rings-1):
        for j in range(segments):
            g.face((rows[k][j],rows[k][j+1],rows[k+1][j+1],rows[k+1][j]), 0 if earthy or k == 0 else 1)
    top=g.vert((center[0],center[1],center[2]+radii[2]),(.5,3))
    for j in range(segments):
        g.face((rows[-1][j], rows[-1][j+1], top),0 if earthy else 1)
    g.face(tuple(reversed(rows[0][:-1])),0)


def leaf(g, pos, normal, length, width, rng, slot):
    # Small rounded botanical blade: elliptical curled rim and lifted central vein.
    reference = Vector((0,0,1)) if abs(normal.z)<.92 else Vector((1,0,0))
    side = normal.cross(reference).normalized()
    along = side.cross(normal).normalized()
    spin = rng.uniform(-math.pi,math.pi)
    side, along = side*math.cos(spin)+along*math.sin(spin), -side*math.sin(spin)+along*math.cos(spin)
    center=g.vert(pos+along*(.20*length)+normal*(.065*length),(.5,.5))
    rim=[]
    for j in range(10):
        a=TAU*j/10
        x=.5*math.cos(a);t=.5+.5*math.sin(a)
        curl=.025*math.cos(a)**2+.07*(t-.35)**2
        point=pos+side*(x*width)+along*((t-.30)*length)+normal*(curl*length)
        rim.append(g.vert(point,(x+.5,t)))
    for j in range(10):g.face((center,rim[(j+1)%10],rim[j]),slot)


def foliage(g, center, radii, power, phase, count, rng, size):
    for i in range(count):
        t = .035 + .94*(i+.5)/count
        angle = i*2.399963229728653 + rng.uniform(-.2,.2)
        pos=surface(t,angle,center,radii,power,phase)
        dt=surface(min(.999,t+.001),angle,center,radii,power,phase)-pos
        da=surface(t,angle+.001,center,radii,power,phase)-pos
        normal=da.cross(dt).normalized()
        pos += normal*rng.uniform(.008,.045)*size
        leaf(g,pos,normal,rng.uniform(.88,1.16)*size,rng.uniform(.48,.66)*size,rng, rng.choices([0,1,2],[5,3,2])[0])


def normalize(objects, dimensions):
    vertices=[v.co for ob in objects for v in ob.data.vertices]
    lo=[min(v[i] for v in vertices) for i in range(3)]
    hi=[max(v[i] for v in vertices) for i in range(3)]
    middle=((lo[0]+hi[0])/2,(lo[1]+hi[1])/2,lo[2])
    for ob in objects:
        for vertex in ob.data.vertices:
            vertex.co=Vector([(vertex.co[i]-middle[i])*dimensions[i]/(hi[i]-lo[i]) for i in range(3)])
        ob.data.update()


def build_asset(asset_id, dimensions, mats, seed):
    rng=random.Random(seed)
    collection=bpy.data.collections.new(asset_id)
    bpy.context.scene.collection.children.link(collection)
    root=bpy.data.objects.new(asset_id,None)
    collection.objects.link(root)
    root['asset_id']=asset_id
    root['nominal_dimensions']=list(dimensions)
    root['front']='-Y'
    cores, leaves, stones = Geometry(), Geometry(), Geometry()
    if asset_id=='bush':
        lobes=[((-.57,0,.07),(.54,.38,.66),2.2,1250),((0,.025,.065),(.62,.43,.90),2.4,1600),((.61,.02,.065),(.47,.36,.62),2.1,1100)]
        size=.065
    else:
        lobes=[((0,0,.09),(1.88,.89,2.75), 4.8 if asset_id=='hill-tall' else 2.05,4600)]
        size=.14
    for index,(center,radii,power,count) in enumerate(lobes):
        phase=seed+index
        core(cores,center,radii,power,phase,segments=32 if asset_id=='bush' else 48,rings=10 if asset_id=='bush' else 14)
        foliage(leaves,center,radii,power,phase,count,rng,size)
    width,depth,height=dimensions
    # Irregular exposed basal rocks tucked under the foliage, not a stage floor.
    for j in range(9):
        a=j*TAU/9
        center=(width*.38*math.cos(a),depth*.34*math.sin(a),0)
        radii=(width*rng.uniform(.055,.09),depth*.12,height*rng.uniform(.04,.075))
        core(stones,center,radii,2.2,j*2.1,segments=9,rings=3,earthy=True)
    objects=[cores.object(asset_id+'_earthen_foliage_core',root,[mats['soil'],mats['deep']]),
             leaves.object(asset_id+'_individual_folded_leaves',root,[mats['leaf'],mats['deep'],mats['young']]),
             stones.object(asset_id+'_basal_weathered_rock',root,[mats['stone']])]
    normalize(objects,dimensions)
    triangles=sum(sum(len(p.vertices)-2 for p in ob.data.polygons) for ob in objects)
    return root,objects,triangles


def export(path, root, objects):
    bpy.ops.object.select_all(action='DESELECT')
    for ob in [root]+objects:
        ob.select_set(True)
    bpy.context.view_layer.objects.active=root
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                             export_extras=True,export_apply=True,export_materials='EXPORT',
                             export_image_format='AUTO',export_yup=True)


def add_botanical_veins(mats, cache):
    # Explicit UV-space midrib and branching vein normal map, embedded in every GLB.
    n=256
    heights=[]
    for y in range(n):
        v=y/(n-1)
        for x in range(n):
            u=x/(n-1);off=abs(u-.5)
            mid=.0018*math.exp(-(off/.012)**2)
            dist=min(abs(v-(k*.15+off*.62)) for k in range(1,7))
            branches=.00055*math.exp(-(dist/.008)**2)*max(0,1-off*2)
            heights.append(mid+branches)
    pixels=[]
    for y in range(n):
        for x in range(n):
            dx=(heights[y*n+min(n-1,x+1)]-heights[y*n+max(0,x-1)])*n*.5
            dy=(heights[min(n-1,y+1)*n+x]-heights[max(0,y-1)*n+x])*n*.5
            normal=Vector((-dx,-dy,1)).normalized()
            pixels.extend((normal.x*.5+.5,normal.y*.5+.5,normal.z*.5+.5,1))
    img=bpy.data.images.new('Botanical_mid_and_branch_veins',width=n,height=n,alpha=False)
    img.colorspace_settings.name='Non-Color';img.pixels.foreach_set(pixels)
    img.filepath_raw=str(cache/'botanical-veins-normal.png');img.file_format='PNG';img.save();img.pack()
    for key in ('leaf','deep','young'):
        nodes=mats[key].node_tree.nodes;links=mats[key].node_tree.links
        tex=nodes.new('ShaderNodeTexImage');tex.image=img
        normal=nodes.new('ShaderNodeNormalMap');normal.inputs['Strength'].default_value=.65
        links.new(tex.outputs['Color'],normal.inputs['Color'])
        links.new(normal.outputs['Normal'],nodes.get('Principled BSDF').inputs['Normal'])


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=args.out.resolve()
    (out/'models').mkdir(parents=True,exist_ok=True)
    cache=out/'materials'
    cache.mkdir(parents=True,exist_ok=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob,do_unlink=True)
    mats={}
    for key,kind,color,rough in [('leaf','leaf','3D6B32',.77),('deep','leaf','345D2D',.86),
                                ('young','leaf','477638',.74),('soil','soil','554732',.96),
                                ('stone','stone','77715B',.9)]:
        mats[key]=material(kind,'vegetation_'+key,color,rough,cache)
        # Opaque botanical sheets remain visible from either side; no alpha cards.
        mats[key].use_backface_culling=False
    add_botanical_veins(mats,cache)
    records=[]
    for index,(asset_id,dims) in enumerate([('hill-green',(4,1.9,3)),('hill-tall',(4,1.9,3)),('bush',(2,.95,1))]):
        root,objects,triangles=build_asset(asset_id,dims,mats,407+index*73)
        path=out/'models'/f'{asset_id}.glb'
        export(path,root,objects)
        used=sorted({mat.name for ob in objects for mat in ob.data.materials})
        records.append({'asset_id':asset_id,'path':f'models/{asset_id}.glb',
                        'nominal_dimensions':{'x':dims[0],'y':dims[1],'z':dims[2]},'triangles':triangles,
                        'materials':used,'mesh_features':['Irregular closed ring-mesh cores','Dense curved 10-triangle elliptical leaves with lifted central ridge','Three botanical leaf age colors','Separate weathered basal rocks','Explicit UVs and embedded albedo, roughness and tangent normal maps'],
                        'source_basis':SOURCE,'known_quality_limitations':['Authored procedural interpretation; central render review pending','Leaf sheets are opaque two-sided surfaces without physical thickness','Both hills obey 4 by 3 requested silhouette bounds; tall variant has steeper shoulders','No wind rig; overlapping bush cores remain independently editable'],
                        'glb_inspection':pbr.inspect_glb(path) if pbr else {'status':'exported; shared inspector unavailable'}})
        # Exports are at origin; only the inspection library gets a layout offset.
        root.location.x=index*5.3
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'family':'vegetation-1','coordinate_system':'Blender Z up; front -Y; GLB Y up','assets':records,'warnings':WARNINGS},indent=2)+'\n')


if __name__=='__main__':
    main()
