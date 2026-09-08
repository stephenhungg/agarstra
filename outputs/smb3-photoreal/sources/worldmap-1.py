"""World-map architecture; authored for Blender 4.5, run only by the build queue."""
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
IDS = ['map-castle', 'map-fortress', 'map-house']
TAU = math.tau
MATS = {}
NOTES = []


def image_material(name, color, roughness, out, kind='grain', metallic=0):
    """Deterministic texture synthesis, including actual tangent normal PNGs.
    Used for directional wood absent from helper recipes and missing-helper fallback.
    No procedural nodes remain in exported materials.
    """
    n = 512
    rng = random.Random(53)
    heights = []
    for y in range(n):
        for x in range(n):
            u, v = x/n, y/n
            warp = 2.5*math.sin(TAU*v*2) + .7*math.sin(TAU*v*7)
            if kind == 'wood':
                h = .5+.18*math.sin(TAU*u*38+warp)+.09*math.sin(TAU*u*91+warp*2)
            elif kind == 'cloth':
                h = .5+.13*math.sin(TAU*u*96)*math.sin(TAU*v*96)
            else:
                h = .5+.13*math.sin(TAU*(u*7+v*3))*.7+.09*math.sin(TAU*(v*29-u*17))
            heights.append(h+rng.uniform(-.085,.085))
    channels = {k: [] for k in ('basecolor','roughness','normal')}
    rgb = [int(color[i:i+2],16)/255 for i in (0,2,4)]
    for y in range(n):
        for x in range(n):
            h = heights[y*n+x]
            channels['basecolor'].extend([min(1,c*(.7+.45*h)) for c in rgb]+[1])
            r = min(1,max(.08,roughness+(h-.5)*.22))
            channels['roughness'].extend((r,r,r,1))
            dx = (heights[y*n+(x+1)%n]-heights[y*n+(x-1)%n])*.8
            dy = (heights[((y+1)%n)*n+x]-heights[((y-1)%n)*n+x])*.8
            normal = Vector((-dx,-dy,1)).normalized()
            channels['normal'].extend((normal.x*.5+.5,normal.y*.5+.5,normal.z*.5+.5,1))
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Metallic'].default_value = metallic
    for channel, values in channels.items():
        im = bpy.data.images.new(name+'_'+channel,width=n,height=n,alpha=False)
        im.colorspace_settings.name = 'sRGB' if channel=='basecolor' else 'Non-Color'
        im.pixels.foreach_set(values)
        im.filepath_raw = str(out / (name+'_'+channel+'.png'))
        im.file_format = 'PNG'
        im.save()
        im.pack()
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = im
        if channel == 'normal':
            nm = mat.node_tree.nodes.new('ShaderNodeNormalMap')
            mat.node_tree.links.new(tex.outputs['Color'],nm.inputs['Color'])
            mat.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])
        else:
            mat.node_tree.links.new(tex.outputs['Color'],bs.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['texture_method'] = 'deterministic image synthesis; tangent normal from height derivatives'
    return mat


def materials(out):
    recipes = {
        'limestone': ('stone','ABA594',.86,0),
        'basalt': ('stone','555963',.88,0),
        'mortar': ('stone','625C51',.96,0),
        'cream': ('stone','D9C7A1',.83,0),
        'roof': ('leather','A04432',.64,0),
        'blue_cloth': ('cloth','325F91',.9,0),
        'iron': ('stone','333A42',.43,.8),
    }
    for name,(kind,col,rough,metal) in recipes.items():
        if pbr:
            MATS[name] = pbr.material(kind,name=name,color=col,roughness=rough,metallic=metal,
                                      bake=True,resolution=512,cache_dir=out)
        else:
            MATS[name] = image_material(name,col,rough,out,kind,metal)
    MATS['oak'] = image_material('oak','775038',.78,out,'wood')


class Builder:
    """Batch disconnected editable components by material, with one bevel per batch."""
    def __init__(self, asset):
        self.asset = asset
        self.parts = {}
        self.root = bpy.data.objects.new(asset,None)
        bpy.context.collection.objects.link(self.root)
        self.root['asset_id'] = asset
        self.root['front'] = '-Y'
        self.root['units'] = '1 unit = 16 NES pixels'

    def mesh(self, key, verts, faces, smooth=False, bevel=.008):
        bucket = self.parts.setdefault((key,smooth,bevel), [[],[]])
        offset = len(bucket[0])
        bucket[0].extend(verts)
        bucket[1].extend(tuple(offset+i for i in face) for face in faces)

    def box(self, key, center, size, bevel=.008, angle=0):
        cx,cy,cz = center
        sx,sy,sz = (s/2 for s in size)
        verts=[]
        for x,y,z in [(-sx,-sy,-sz),(sx,-sy,-sz),(sx,sy,-sz),(-sx,sy,-sz),
                      (-sx,-sy,sz),(sx,-sy,sz),(sx,sy,sz),(-sx,sy,sz)]:
            verts.append((cx+x*math.cos(angle)-y*math.sin(angle),cy+x*math.sin(angle)+y*math.cos(angle),cz+z))
        self.mesh(key,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],False,bevel)

    def lathe(self,key,profile,center=(0,0,0),segments=32,smooth=True):
        verts=[]
        rings=[]
        for r,z in profile:
            if abs(r)<1e-7:
                rings.append([len(verts)]*segments)
                verts.append((center[0],center[1],center[2]+z))
            else:
                rings.append(list(range(len(verts),len(verts)+segments)))
                verts.extend((center[0]+r*math.cos(TAU*j/segments),
                              center[1]+r*math.sin(TAU*j/segments),center[2]+z)
                             for j in range(segments))
        faces=[]
        for first,second in zip(rings,rings[1:]):
            for j in range(segments):
                k=(j+1)%segments
                face=list(dict.fromkeys((first[j],first[k],second[k],second[j])))
                if len(face)>=3: faces.append(tuple(face))
        self.mesh(key,verts,faces,smooth,0)

    def beam(self,key,start,end,radius=.015):
        a,b=Vector(start),Vector(end)
        axis=(b-a).normalized()
        u=axis.cross(Vector((0,0,1)))
        if u.length<.01: u=axis.cross(Vector((0,1,0)))
        u.normalize(); v=axis.cross(u)
        verts=[tuple(p+radius*(u*math.cos(j*TAU/8)+v*math.sin(j*TAU/8))) for p in (a,b) for j in range(8)]
        faces=[tuple(reversed(range(8))),tuple(range(8,16))]
        faces += [(j,(j+1)%8,(j+1)%8+8,j+8) for j in range(8)]
        self.mesh(key,verts,faces,True,0)

    def finish(self):
        objects=[self.root]
        for idx,((key,smooth,bevel),(verts,faces)) in enumerate(self.parts.items()):
            data=bpy.data.meshes.new(f'{self.asset}_{key}_{idx}')
            data.from_pydata(verts,[],faces); data.update()
            ob=bpy.data.objects.new(data.name,data)
            bpy.context.collection.objects.link(ob)
            ob.parent=self.root
            ob['asset_id']=self.asset
            data.materials.append(MATS[key])
            uv=data.uv_layers.new(name='UVMap')
            for poly in data.polygons:
                poly.use_smooth=smooth
                normal=poly.normal
                dominant=max(range(3),key=lambda k:abs(normal[k]))
                axes=[i for i in range(3) if i!=dominant]
                for li in poly.loop_indices:
                    co=data.vertices[data.loops[li].vertex_index].co
                    uv.data[li].uv=(co[axes[0]],co[axes[1]])
            if bevel:
                mod=ob.modifiers.new('Worn arris edges','BEVEL')
                mod.width=bevel; mod.segments=1
            objects.append(ob)
        return objects


def masonry(b,center,size,key,courses=4,columns=4):
    x,y,z=center; w,d,h=size
    # Solid recessed masonry core supports separately articulated facing blocks.
    b.box('mortar',center,(w-.035,d-.035,h-.018))
    for row in range(courses):
        zz=z-h/2+(row+.5)*h/courses
        for side in (-1,1):
            count=columns+(row%2)
            for j in range(count):
                xx=x-w/2+(j+.5)*w/count
                b.box(key,(xx,y+side*(d/2-.045),zz),(w/count-.012,.09,h/courses-.013))
            count=max(2,round(columns*d/w))
            for j in range(count):
                yy=y-d/2+.10+(j+.5)*(d-.20)/count
                b.box(key,(x+side*(w/2-.045),yy,zz),(.09,(d-.20)/count-.012,h/courses-.013))


def battlements(b,x,y,w,d,z,key,count=4):
    b.box(key,(x,y,z-.065),(w+.07,d+.07,.13))
    for side in (-1,1):
        for j in range(count):
            xx=x-w/2+(j+.5)*w/count
            b.box(key,(xx,y+side*(d/2-.07),z+.11),(w/count*.53,.19,.23))
        for j in range(1,count-1):
            yy=y-d/2+(j+.5)*d/count
            b.box(key,(x+side*(w/2-.07),yy,z+.11),(.19,d/count*.52,.23))


def doorway(b,x,y,z,width,height,trim='limestone'):
    r=width/2; spring=z+height-r
    # Real arched plank outline and projecting stone voussoirs; closed building.
    for j in range(7):
        xx=-r+(j+.5)*width/7
        top=spring+math.sqrt(max(0,r*r-xx*xx))
        b.box('oak',(x+xx,y,(z+top)/2),(width/7-.008,.055,top-z),.004)
    for side in (-1,1):
        for j in range(3):
            b.box(trim,(x+side*(r+.055),y-.007,z+(j+.5)*(height-r)/3),(.105,.13,(height-r)/3-.008))
    for j in range(11):
        a=j*math.pi/11+.015; c=(j+1)*math.pi/11-.015
        verts=[(x+rr*math.cos(t),yy,spring+rr*math.sin(t)) for yy in (y-.075,y+.07) for rr,t in ((r,a),(r+.115,a),(r+.115,c),(r,c))]
        b.mesh(trim,verts,[(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],False,.005)
    for zz in (z+.19,spring-.08):
        b.box('iron',(x,y-.04,zz),(width*.87,.025,.045),.003)
        for side in (-1,1):
            b.box('iron',(x+side*width*.34,y-.06,zz),(.026,.016,.026),.003)
    b.beam('iron',(x+.06,y-.075,z+.3),(x+.06,y-.075,z+.40),.02)


def flag(b,x,y,z):
    b.beam('iron',(x,y,z-.1),(x,y,z+.62),.014)
    verts=[]
    for i in range(13):
        u=i/12
        for j in range(4):
            v=j/3
            verts.append((x+u*.39,y+.055*math.sin(u*8-v*.8)*u,z+.55-v*.22-u*.045))
    faces=[(i*4+j,(i+1)*4+j,(i+1)*4+j+1,i*4+j+1) for i in range(12) for j in range(3)]
    # Two explicit surfaces with sealed rim, glTF-safe thickness.
    nv=len(verts); verts += [(a,bb+.004,c) for a,bb,c in verts]
    faces += [tuple(nv+k for k in reversed(f)) for f in list(faces)]
    boundary=list(range(0,49,4))+[49,50,51]+list(range(47,2,-4))+[2,1]
    faces += [(a,bb,bb+nv,a+nv) for a,bb in zip(boundary,boundary[1:]+boundary[:1])]
    b.mesh('blue_cloth',verts,faces,True,0)


def castle():
    b=Builder('map-castle')
    b.box('limestone',(0,0,.065),(2.24,1.63,.13),.025)
    masonry(b,(0,.12,.82),(1.2,1.18,1.42),'limestone',4,3)
    battlements(b,0,.12,1.22,1.2,1.56,'limestone',4)
    for x in (-.78,.78):
        masonry(b,(x,-.13,.95),(.66,1.1,1.68),'limestone',5,2)
        battlements(b,x,-.13,.72,1.12,1.82,'limestone',3)
        flag(b,x,-.03,1.96)
        b.box('iron',(x,-.691,1.19),(.08,.018,.27),.018)
    masonry(b,(0,.3,1.93),(.63,.62,.74),'limestone',3,2)
    battlements(b,0,.3,.67,.66,2.33,'limestone',3)
    doorway(b,0,-.502,.13,.46,.85)
    b.box('limestone',(0,-.67,.07),(.72,.47,.14),.016)
    return b.finish()


def fortress():
    b=Builder('map-fortress')
    b.box('basalt',(0,0,.09),(2.2,1.65,.18),.025)
    masonry(b,(0,0,.73),(1.91,1.4,1.17),'basalt',4,5)
    battlements(b,0,0,2,1.47,1.34,'basalt',6)
    for x in (-.83,.83):
        # Broad sloped buttress feet distinguish the squat stronghold.
        b.box('basalt',(x,-.70,.45),(.28,.34,.66),.023)
        b.box('basalt',(x,-.72,.16),(.38,.4,.23),.02)
    masonry(b,(0,.32,1.5),(.93,.65,.51),'basalt',2,3)
    battlements(b,0,.32,1,.71,1.78,'basalt',4)
    doorway(b,0,-.728,.18,.61,.91,'basalt')
    for x in (-.56,.56):
        b.box('iron',(x,-.713,.98),(.085,.024,.22),.013)
    for y in (-.35,.2):
        b.box('iron',(.963,y,.98),(.018,.09,.22),.012)
    # Portcullis hangs above the upper third of the closed oak portal.
    for x in (-.20,-.10,0,.10,.20):
        b.beam('iron',(x,-.796,.72),(x,-.796,.95),.011)
    b.beam('iron',(-.25,-.796,.83),(.25,-.796,.83),.015)
    return b.finish()


def house():
    b=Builder('map-house')
    b.lathe('limestone',[(0,0),(.62,0),(.65,.10),(.59,.19),(0,.19)],segments=32)
    b.lathe('cream',[(0,.12),(.51,.12),(.56,.44),(.48,1.15),(0,1.15)],segments=40)
    b.lathe('oak',[(.49,1.02),(.56,1.02),(.57,1.13),(.48,1.13),(.49,1.02)],segments=40)
    # Mushroom roof is a closed elliptical cap, with downturned lip and radial gills.
    profile=[(0,1.02),(.5,1.02),(.87,1.08),(1.01,1.17),(1.03,1.25)]
    for i in range(1,17):
        t=(math.pi/2)*i/16
        profile.append((1.03*math.cos(t),1.25+.77*math.sin(t)))
    b.lathe('roof',profile,segments=64)
    b.lathe('cream',[(.51,1.02),(.88,1.08),(1.015,1.17),(.99,1.19),(.85,1.12),(.51,1.06),(.51,1.02)],segments=48)
    for j in range(32):
        a=TAU*j/32
        b.beam('cream',(.54*math.cos(a),.54*math.sin(a),1.055),(.94*math.cos(a),.94*math.sin(a),1.14),.008)
    # Raised pale patches follow the ellipsoid, rather than floating planar discs.
    for theta,phi,size in [(1.02,-1.55,.18),(.65,-.65,.16),(.78,-2.7,.15),(.48,1.2,.16),(1.13,.8,.13),(1.12,2.7,.14),(.22,-1,.13)]:
        center=Vector((math.sin(theta)*math.cos(phi),math.sin(theta)*math.sin(phi),math.cos(theta)))
        u=Vector((-math.sin(phi),math.cos(phi),0)); v=center.cross(u)
        verts=[]
        for rr in (size*.65,size):
            for j in range(20):
                q=(center+rr*(u*math.cos(TAU*j/20)+v*math.sin(TAU*j/20))).normalized()
                verts.append((q.x*1.035,q.y*1.035,1.25+q.z*.775))
        verts.append((center.x*1.035,center.y*1.035,1.25+center.z*.775))
        faces=[(40,j,(j+1)%20) for j in range(20)]
        faces += [(j,(j+1)%20,20+(j+1)%20,20+j) for j in range(20)]
        b.mesh('cream',verts,faces,True,0)
    doorway(b,0,-.544,.16,.35,.68,'oak')
    b.box('oak',(0,-.65,.095),(.5,.34,.09),.012)
    # Side window: physical frame, dark inset, mullions and timber sill.
    b.box('iron',(.525,.02,.66),(.025,.29,.30),.025)
    for yy in (-.155,.195):
        b.box('oak',(.54,yy,.66),(.055,.045,.39),.009)
    for zz in (.47,.85):
        b.box('oak',(.54,.02,zz),(.06,.39,.055),.009)
    b.box('oak',(.555,.02,.66),(.035,.018,.31),.004)
    b.box('oak',(.555,.02,.66),(.035,.31,.02),.004)
    b.box('oak',(.57,.02,.44),(.17,.43,.07),.008)
    return b.finish()


def bounds(objects):
    bpy.context.view_layer.update()
    deps=bpy.context.evaluated_depsgraph_get()
    points=[ob.matrix_world @ Vector(co) for obj in objects if obj.type=='MESH'
            for ob in [obj.evaluated_get(deps)] for co in ob.bound_box]
    lo=[min(v[k] for v in points) for k in range(3)]
    hi=[max(v[k] for v in points) for k in range(3)]
    return lo,hi


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    out=args.out.resolve(); (out/'models').mkdir(parents=True,exist_ok=True)
    (out/'materials').mkdir(exist_ok=True)
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    materials(out/'materials')
    entries=[]
    features=[
        ['Stepped central keep','Two crenellated towers','Individual bevelled masonry blocks','Arched oak gate with voussoirs','Two volumetric rippled blue flags','Iron arrow slits'],
        ['Squat rectangular stronghold','Heavy battlements','Raised rear keep','Buttresses','Closed arched oak gate','Partial iron portcullis','Masonry courses'],
        ['Broad spotted ellipsoidal mushroom cap','Rolled cream eaves and radial gills','Tapered plaster stem','Arched plank door','Iron straps','Framed side window','Timber cornice']]
    source='ROM catalog worldmap-metatiles-00.png: spotted mushroom-house silhouettes in row 5; crenellated gate/building silhouettes in lower architectural rows. WORLDMAP.md and worldmap-assets.json inspected. Architectural depth, joinery and PBR surfaces are authored interpretations; no ROM textures embedded.'
    for idx,make in enumerate((castle,fortress,house)):
        objects=make(); root=objects[0]
        lo,hi=bounds(objects)
        shift=Vector((-(lo[0]+hi[0])/2,-(lo[1]+hi[1])/2,-lo[2]))
        for ob in objects[1:]: ob.location+=shift
        bpy.context.view_layer.update()
        path=out/'models'/f'{root.name}.glb'
        bpy.ops.object.select_all(action='DESELECT')
        for ob in objects: ob.select_set(True)
        bpy.context.view_layer.objects.active=root
        bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,
                                  export_apply=True,export_extras=True,export_yup=True,export_materials='EXPORT')
        deps=bpy.context.evaluated_depsgraph_get()
        triangles=0
        for ob in objects[1:]:
            evaluated=ob.evaluated_get(deps); mesh=evaluated.to_mesh()
            mesh.calc_loop_triangles(); triangles+=len(mesh.loop_triangles)
            evaluated.to_mesh_clear()
        entries.append({'asset_id':root.name,'path':f'models/{root.name}.glb',
                        'nominaldimensions':[round(hi[k]-lo[k],4) for k in range(3)],
                        'dimension_axes':'Blender XYZ; GLB Y-up',
                        'materials':sorted({slot.material.name for ob in objects[1:] for slot in ob.material_slots}),
                        'meshfeatures':features[idx],'triangles':triangles,'sourcebasis':source,
                        'knownqualitylimitations':['Unrendered authoring; central visual QA required.',
                        'Closed miniature buildings; no accessible interiors.',
                        'Surface textures are baked or synthesized, not scanned.',
                        'Windows and arrow slits use dark inset geometry, not cut-through openings.']})
        root.location.x=idx*3.5
    for im in bpy.data.images:
        if im.source=='FILE' and not im.packed_file: im.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'library.blend'))
    (out/'manifest.json').write_text(json.dumps({'assets':entries,'authoring_status':'authored',
        'style_contract':str(SHARED/'design/style.json'),'pbr_helper_used':bool(pbr)},indent=2)+'\n')


if __name__=='__main__':
    main()
