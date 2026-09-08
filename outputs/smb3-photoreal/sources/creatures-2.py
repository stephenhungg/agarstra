"""Author two editable SMB3-inspired creatures. Run only through the central Blender queue."""
import argparse
import json
import math
import sys
from array import array
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

SHARED = Path('/Users/stephenhung/Documents/Codex/2026-09-08/o/outputs/smb3-photoreal/tools')
sys.path.insert(0, str(SHARED))
try:
    import pbr_common as pbr
except ImportError:
    pbr = None

TAU = 2 * math.pi
WARNINGS = []
SOURCE = {
    'buzzy-beetle': {'symbol': 'OBJ_BUZZYBEATLE', 'object_id': 112, 'label': 'ObjP70', 'rom_offset': 33303, 'source': 'PRG/prg004.asm:420'},
    'spiny': {'symbol': 'OBJ_SPINY', 'object_id': 113, 'label': 'ObjP71', 'rom_offset': 33317, 'source': 'PRG/prg004.asm:422'},
}
LIMITATIONS = [
    'Authored without executing Blender or inspecting renders; central queue must verify appearance and runtime export.',
    'Source descriptors are unresolved for reachable frame assembly and palette; silhouettes and colors follow the supplied family brief, not a claimed exact sprite reconstruction.',
    'Static separate anatomical meshes; foot pivots are provided, without armature or animation.',
    'Fine material detail uses repeated UV swatches, not unique hand-painted anatomical texture maps.',
]


def fallback_material(name, color, roughness, cache):
    """Deterministic raster PBR fallback: actual image maps, no procedural-only export."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    rgb = tuple(int(color[i:i+2], 16) / 255 for i in (0, 2, 4))
    n = 512
    # Periodic multiscale pore field. Central differences encode tangent-space normals.
    heights = []
    for y in range(n):
        v = y / n
        for x in range(n):
            u = x / n
            h = .42 * math.sin(TAU*(23*u+7*v))*math.cos(TAU*(13*v-5*u))
            h += .16*math.sin(TAU*(89*u+31*v))*.8*math.cos(TAU*(71*v-17*u))
            h += .22*math.sin(TAU*(3*u+2*v))*math.cos(TAU*(5*v-u))
            heights.append(h)
    for channel in ('basecolor', 'roughness', 'normal'):
        pixels = array('f')
        for y in range(n):
            for x in range(n):
                h = heights[y*n+x]
                if channel == 'basecolor':
                    values = tuple(max(0, min(1, c*(.94+.10*h))) for c in rgb)
                elif channel == 'roughness':
                    r = max(.05, min(.98, roughness + .09*h))
                    values = (r, r, r)
                else:
                    dx = heights[y*n+(x+1)%n] - heights[y*n+(x-1)%n]
                    dy = heights[((y+1)%n)*n+x] - heights[((y-1)%n)*n+x]
                    normal = Vector((-dx*.28, -dy*.28, 1)).normalized()
                    values = tuple(.5+.5*c for c in normal)
                pixels.extend((*values, 1))
        image = bpy.data.images.new(name+'_'+channel, width=n, height=n, alpha=False)
        image.colorspace_settings.name = 'sRGB' if channel == 'basecolor' else 'Non-Color'
        image.pixels.foreach_set(pixels)
        image.filepath_raw = str(cache/(name+'_'+channel+'.png'))
        image.file_format = 'PNG'
        image.save()
        image.pack()
        node = nodes.new('ShaderNodeTexImage')
        node.image = image
        if channel == 'normal':
            normal = nodes.new('ShaderNodeNormalMap')
            links.new(node.outputs['Color'], normal.inputs['Color'])
            links.new(normal.outputs['Normal'], bsdf.inputs['Normal'])
        else:
            links.new(node.outputs['Color'], bsdf.inputs['Base Color' if channel == 'basecolor' else 'Roughness'])
    mat['pbr_baked'] = True
    mat['texture_method'] = 'deterministic raster fallback'
    return mat


def material(name, kind, color, roughness, cache, bump=.009, coat=0):
    if pbr:
        try:
            return pbr.material(kind, name=name, color=color, roughness=roughness,
                                metallic=0, bump=bump, coat=coat, bake=True,
                                resolution=512, cache_dir=cache)
        except Exception as exc:
            WARNINGS.append(name+': shared bake failed; raster fallback used: '+str(exc))
    return fallback_material(name, color, roughness, cache)


class Creature:
    def __init__(self, asset_id):
        self.asset_id = asset_id
        self.collection = bpy.data.collections.new(asset_id)
        bpy.context.scene.collection.children.link(self.collection)
        self.root = bpy.data.objects.new(asset_id+'_ROOT', None)
        self.collection.objects.link(self.root)
        self.root['asset_id'] = asset_id
        self.root['coordinate_contract'] = 'Z up; front -Y; root bottom-center; block=1'
        self.objects = [self.root]

    def mesh(self, name, vertices, faces, uvs, mat):
        data = bpy.data.meshes.new(self.asset_id+'_'+name)
        data.from_pydata(vertices, [], faces)
        data.update()
        # Consistent outward winding also for the cap triangles and curved sweeps.
        bm = bmesh.new()
        bm.from_mesh(data)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(data)
        bm.free()
        layer = data.uv_layers.new(name='UVMap')
        for poly in data.polygons:
            puv = [uvs[data.loops[i].vertex_index] for i in poly.loop_indices]
            seam = max(p[0] for p in puv)-min(p[0] for p in puv) > .5
            for li, uv in zip(poly.loop_indices, puv):
                layer.data[li].uv = (uv[0]+(1 if seam and uv[0]<.5 else 0), uv[1])
            poly.use_smooth = True
        data.materials.append(mat)
        obj = bpy.data.objects.new(self.asset_id+'_'+name, data)
        self.collection.objects.link(obj)
        obj.parent = self.root
        obj['asset_id'] = self.asset_id
        self.objects.append(obj)
        return obj

    def rings(self, name, rows, mat, cap=True):
        n = len(rows[0])
        verts = [tuple(v) for row in rows for v in row]
        uv = [(j/n, i/(len(rows)-1)) for i in range(len(rows)) for j in range(n)]
        faces = []
        for i in range(len(rows)-1):
            for j in range(n):
                a, b = i*n+j, i*n+(j+1)%n
                faces.append((a, b, b+n, a+n))
        if cap:
            for row, flip in ((0, True), (len(rows)-1, False)):
                center = sum((Vector(v) for v in rows[row]), Vector())/n
                c = len(verts)
                verts.append(tuple(center)); uv.append((.5, row/(len(rows)-1)))
                for j in range(n):
                    f = (c, row*n+j, row*n+(j+1)%n)
                    faces.append(tuple(reversed(f)) if flip else f)
        return self.mesh(name, verts, faces, uv, mat)

    def organic(self, name, center, size, mat, n=32, rings=16, shaping=0):
        rows = []
        for i in range(rings+1):
            t = .015 + (math.pi-.03)*i/rings
            row = []
            for j in range(n):
                a = TAU*j/n
                ripple = 1+shaping*math.sin(3*a)*math.sin(t)**2
                x = size[0]*math.sin(t)*math.cos(a)*ripple
                y = size[1]*math.sin(t)*math.sin(a)*ripple
                z = size[2]*math.cos(t)
                row.append((center[0]+x, center[1]+y, center[2]+z))
            rows.append(row)
        return self.rings(name, rows, mat)

    def sweep(self, name, centers, radii, mat, n=12, ellipticity=1):
        rows=[]
        for i, center in enumerate(centers):
            c=Vector(center)
            tangent=Vector(centers[min(i+1,len(centers)-1)])-Vector(centers[max(0,i-1)])
            tangent.normalize()
            ref=Vector((0,0,1)) if abs(tangent.z)<.9 else Vector((0,1,0))
            a=tangent.cross(ref).normalized()
            b=tangent.cross(a).normalized()
            rows.append([c+radii[i]*(math.cos(TAU*j/n)*a+ellipticity*math.sin(TAU*j/n)*b) for j in range(n)])
        return self.rings(name,rows,mat)

    def pivot(self, name, location, objects):
        pivot = bpy.data.objects.new(self.asset_id+'_'+name, None)
        self.collection.objects.link(pivot)
        pivot.parent=self.root
        pivot.location=location
        pivot.empty_display_size=.06
        self.objects.append(pivot)
        for obj in objects:
            obj.parent=pivot
            # Mesh coordinates were authored in root space.
            obj.location=-Vector(location)
        return pivot

    def normalize(self, height):
        bpy.context.view_layer.update()
        points=[o.matrix_world @ Vector(c) for o in self.objects if o.type=='MESH' for c in o.bound_box]
        low=Vector(tuple(min(p[k] for p in points) for k in range(3)))
        high=Vector(tuple(max(p[k] for p in points) for k in range(3)))
        offset=Vector(((low.x+high.x)/2,(low.y+high.y)/2,low.z))
        scale=height/(high.z-low.z)
        # Scale local geometry and translations, keeping root identity for downstream tools.
        for obj in self.objects:
            if obj.type=='MESH':
                for vertex in obj.data.vertices: vertex.co *= scale
            if obj != self.root:
                obj.location *= scale
                if obj.parent == self.root: obj.location -= offset*scale
        bpy.context.view_layer.update()
        return [round((high[k]-low[k])*scale,5) for k in range(3)]


def shell(c, spiny, m):
    """One thick closed shell surface; seam channels are physically recessed."""
    rx, ry = .565, .61
    base, rise = .35, (.45 if spiny else .62)
    rows=[]
    for i in range(37):
        t=.016+(math.pi/2-.016)*i/36
        row=[]
        for j in range(96):
            a=TAU*j/96
            x=rx*math.sin(t)*math.cos(a)
            y=ry*math.sin(t)*math.sin(a)
            # Beetle elytra center line; spiny has radial and concentric scute channels.
            if spiny:
                angular=math.exp(-(math.sin(4*a)/.085)**2)*math.sin(t)**2
                belt=math.exp(-((t-.88)/.033)**2)
                groove=.012*max(angular,belt)
            else:
                groove=.014*math.exp(-(x/.016)**2)*math.sin(t)**.5
            grain=.002*math.sin(17*a+3*t)*math.sin(t*13)*math.sin(t)**2
            row.append((x,y,base+rise*math.cos(t)-groove+grain))
        rows.append(row)
    # Rolled-in lower shell makes an enclosed, editable carapace, not an open dome.
    rows.extend([[(r*rx*math.cos(TAU*j/96), r*ry*math.sin(TAU*j/96), z) for j in range(96)] for r,z in ((.995,base-.035),(.91,base-.065),(.15,base-.065))])
    c.rings('carapace_recessed_scutes' if spiny else 'carapace_split_elytra',rows,m['shell'])
    # Continuous oval lip, modeled as a mesh sweep, with cream keratin for Spiny.
    centers=[(rx*math.cos(TAU*j/96),ry*math.sin(TAU*j/96),base-.006) for j in range(97)]
    c.sweep('rolled_shell_lip',centers,[.034]*97,m['horn'] if spiny else m['rim'],n=10)
    if not spiny:
        # Fine perimeter growth striae sit close to the dome without changing silhouette.
        for k in range(2):
            t=1.34+k*.095
            centers=[(rx*math.sin(t)*math.cos(TAU*j/80),ry*math.sin(t)*math.sin(TAU*j/80),base+rise*math.cos(t)+.002) for j in range(81)]
            c.sweep('shell_growth_line_%02d'%k,centers,[.0045]*81,m['rim'],n=6)
    else:
        # Conical curved keratin spines, flared basal collars, outward splay.
        positions=[(0,0)]
        positions += [(.53, TAU*j/5+.25) for j in range(5)]
        positions += [(.98, TAU*j/7) for j in range(7)]
        for k,(t,a) in enumerate(positions):
            basep=Vector((rx*math.sin(t)*math.cos(a),ry*math.sin(t)*math.sin(a),base+rise*math.cos(t)-.012))
            normal=Vector((.7*math.sin(t)*math.cos(a),.7*math.sin(t)*math.sin(a),math.cos(t))).normalized()
            length=.275 if k==0 else (.245 if t<.8 else .205)
            centers=[basep+normal*length*s+Vector((0,.024*s*s,0)) for s in (0,.07,.2,.4,.64,.83,.985,1)]
            radii=[.09,.086,.07,.052,.031,.015,.003,.001]
            c.sweep('keratin_spine_%02d'%k,centers,radii,m['horn'],n=16)
            c.sweep('spine_socket_%02d'%k,[basep-normal*.008,basep+normal*.012,basep+normal*.029],[.099,.098,.081],m['rim'],n=16)


def anatomy(c, spiny, m):
    c.organic('belly_continuous', (0,.015,.255),(.45,.49,.16),m['skin'],shaping=.014)
    # Four low leathery limbs; individual toes and nail tips read from side and front.
    for side in (-1,1):
        for front in (True,False):
            y=-.34 if front else .32
            code=('L' if side<0 else 'R')+('_front' if front else '_rear')
            parts=[]
            parts.append(c.sweep('bent_leg_'+code,[(side*.30,y,.29),(side*.40,y-.025,.22),(side*.46,y-.065,.145),(side*.46,y-.10,.10)],[.115,.12,.10,.095],m['skin'],n=20))
            parts.append(c.organic('padded_foot_'+code,(side*.455,y-.105,.087),(.14,.20,.085),m['skin'],n=28,rings=12,shaping=.027))
            for toe in range(3):
                x=side*.455+(toe-1)*.073
                parts.append(c.sweep('toe_'+code+'_'+str(toe),[(x,y-.18,.088),(x,y-.245,.065),(x,y-.29,.059)],[.043,.041,.018],m['skin'],n=10))
                if spiny:
                    parts.append(c.sweep('claw_'+code+'_'+str(toe),[(x,y-.267,.066),(x,y-.306,.060),(x,y-.329,.05)],[.025,.016,.001],m['horn'],n=10))
            c.pivot('foot_pivot_'+code,(side*.37,y,.24),parts)
    # Head stays tucked under the front brow of the carapace.
    c.organic('head_tucked', (0,-.50,.275),(.305,.245,.185),m['skin'],n=40,rings=20,shaping=.013)
    c.organic('muzzle', (0,-.697,.205),(.235,.098,.087),m['skin'],n=32,rings=12)
    # Mouth recessed behind the fleshy lower lip.
    mouth=[(-.18+i*.36/18,-.771-.009*math.sin(math.pi*i/18),.187-.014*math.sin(math.pi*i/18)) for i in range(19)]
    c.sweep('mouth_crease',mouth,[.006]*19,m['dark'],n=8)
    lower=[(x,y+.006,z-.013) for x,y,z in mouth]
    c.sweep('lower_lip',lower,[.013]*19,m['skin'],n=10)
    for side in (-1,1):
        x=side*.142
        c.organic('eye_socket_'+str(side),(x,-.687,.352),(.107,.052,.127),m['rim'],n=28,rings=14)
        c.organic('eye_white_'+str(side),(x,-.720,.353),(.080,.035,.101),m['eye'],n=28,rings=14)
        c.organic('pupil_'+str(side),(x-side*.012,-.750,.342),(.033,.016,.063),m['dark'],n=24,rings=12)
        # Thick angry orbital ridge descends toward inner corner; no floating eyebrow.
        brow=[]
        for j in range(13):
            t=j/12
            brow.append((side*(.06+.18*t),-.735+.042*t,.395+.06*t-.012*t*t))
        c.sweep('scowling_orbital_ridge_'+str(side),brow,[.024+.009*math.sin(math.pi*j/12) for j in range(13)],m['skin'],n=12)
        c.organic('nostril_'+str(side),(side*.09,-.788,.23),(.017,.008,.011),m['dark'],n=16,rings=8)
    if spiny:
        c.sweep('small_tail',[(0,.43,.25),(0,.59,.23),(0,.71,.18)],[.085,.056,.004],m['skin'],n=16)


def inspect_glb(path):
    import struct
    raw=path.read_bytes()
    magic, version, total=struct.unpack_from('<III',raw,0)
    assert magic==0x46546C67 and version==2 and total==len(raw)
    length, chunk=struct.unpack_from('<II',raw,12)
    assert chunk==0x4E4F534A
    doc=json.loads(raw[20:20+length])
    assert not doc.get('cameras'), 'Cameras must not be exported'
    assert all('bufferView' in im for im in doc.get('images',[])), 'Images must be embedded'
    for mat in doc.get('materials',[]):
        p=mat.get('pbrMetallicRoughness',{})
        assert 'baseColorTexture' in p and 'metallicRoughnessTexture' in p and 'normalTexture' in mat, 'Missing transferable PBR map'
    return {'meshes':len(doc.get('meshes',[])), 'embedded_images':len(doc.get('images',[])), 'bytes':len(raw)}


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',required=True,type=Path)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=args.out.resolve()
    (out/'models').mkdir(parents=True,exist_ok=True)
    cache=out/'materials';cache.mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    bpy.context.scene.unit_settings.system='METRIC'
    bpy.context.scene.unit_settings.scale_length=1
    common={
        'horn':material('Ivory_striated_keratin','leather','D8C6A0',.43,cache,.008),
        'eye':material('Warm_sclera','leather','E3DDCB',.27,cache,.001),
        'dark':material('Obsidian_eyes_and_creases','leather','15100D',.24,cache,.001),
    }
    entries=[];creatures=[]
    for asset_id,spiny,height in [('buzzy-beetle',False,1.0),('spiny',True,1.1)]:
        m=dict(common)
        m['shell']=material('Spiny_oxblood_shell' if spiny else 'Buzzy_midnight_navy_shell','leather','A92C24' if spiny else '142C4A',.36 if spiny else .29,cache,.006,.18)
        m['skin']=material('Spiny_ochre_hide' if spiny else 'Buzzy_ochre_hide','leather','A97436' if spiny else '967039',.67,cache,.012)
        m['rim']=material('Spiny_dark_scute_sockets' if spiny else 'Buzzy_shell_edge','leather','703024' if spiny else '101E2B',.47,cache,.006)
        c=Creature(asset_id)
        shell(c,spiny,m);anatomy(c,spiny,m)
        dims=c.normalize(height)
        triangles=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in c.objects if o.type=='MESH')
        path=out/'models'/(asset_id+'.glb')
        bpy.ops.object.select_all(action='DESELECT')
        for o in c.objects:o.select_set(True)
        bpy.context.view_layer.objects.active=c.root
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
            export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO',export_yup=True)
        report=inspect_glb(path)
        mats=sorted({slot.material.name for o in c.objects if o.type=='MESH' for slot in o.material_slots})
        entries.append({'asset_id':asset_id,'path':'models/'+asset_id+'.glb','nominaldimensions':dims,
            'nominal_dimensions':{'x':dims[0],'y':dims[1],'z':dims[2],'unit':'block'},
            'materials':mats,'triangles':triangles,'meshfeatures':[
                'Closed sculpted shell with recessed seam channels and rolled lip',
                'Flared keratin spines and sockets' if spiny else 'Split elytra and growth striae',
                'Tucked head, muzzle, mouth crease, nostrils, inset eyes and scowling orbital ridges',
                'Four bent limbs, padded feet, modeled toes, named foot pivots',
                'UV base color, roughness and tangent normal textures, packed and embedded'],
            'sourcebasis':{'catalog':'smb3-rom-assets/catalog/binary-assets.json:objectDescriptors',**SOURCE[asset_id],
                'resolution':'unresolved','silhouette_basis':'User family brief plus semantic ROM descriptor; original PNG frame not claimed verified'},
            'knownqualitylimitations':LIMITATIONS,'export_validation':report})
        creatures.append(c)
    # Exports above remain centered; inspection library uses spaced root translations.
    for i,c in enumerate(creatures):c.root.location.x=(i-.5)*2.2
    bpy.ops.object.select_all(action='DESELECT')
    for c in creatures:c.root.select_set(True)
    bpy.context.view_layer.objects.active=creatures[0].root
    for image in bpy.data.images:
        if image.source=='FILE' and not image.packed_file:
            image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    manifest={'schema_version':1,'assets':entries,'warnings':WARNINGS,'library':'library.blend',
              'coordinates':'Blender Z-up, front -Y; GLB Y-up; each exported root is bottom-center',
              'style_contract':'smb3-photoreal/design/style.json','render_review':'pending central queue'}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps({'status':'built','assets':[e['asset_id'] for e in entries],'warnings':WARNINGS}))


if __name__=='__main__':
    main()
