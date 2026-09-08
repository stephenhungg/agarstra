"""Local broad-crown revision of the existing generated branch scaffold."""
import bpy, math, random, json, hashlib, numpy as np
from pathlib import Path
from mathutils import Vector,kdtree
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/environment/tree-v2'
MODELS=ROOT/'outputs/pokemon-remake/models'
SOURCE=ROOT/'outputs/pokemon-remake/environment/tree/tree.blend'
rng=random.Random(894517)
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
old=bpy.data.objects['Pallet_Broadleaf_Tree']
old_foliage=bpy.data.objects['Pallet_Broadleaf_Foliage']
for obj in list(bpy.data.objects):
    if obj!=old:bpy.data.objects.remove(obj,do_unlink=True)
# Preserve continuous provider scaffold, widen its upper branches and shorten
# the exposed trunk relative to the source's compact rounded leaf crown.
vertices=[]
for vertex in old.data.vertices:
    p=old.matrix_world@vertex.co;p*=.76
    t=max(0,min(1,(p.z-.7)/1.6))
    p.x*=1+.32*t;p.y*=1+.62*t
    p.z=.82*p.z if p.z<1.35 else 1.107+(p.z-1.35)*.91
    vertices.append(p)
faces=[tuple(p.vertices) for p in old.data.polygons]
uvs=[]
uv_layer=old.data.uv_layers.active
for poly in old.data.polygons:uvs.append([tuple(uv_layer.data[i].uv) for i in poly.loop_indices])
base_vertex_count=len(vertices);base_triangles=sum(len(f)-2 for f in faces)

# Retain the generated UV detail but recolor its luminance to brown bark and
# reduce its repeated-tree texture budget to 2K.
old_mat=old.data.materials[0]
old_bs=next(n for n in old_mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
def linked_image(socket):
    seen=set();queue=[l.from_node for l in old_bs.inputs[socket].links]
    while queue:
        node=queue.pop()
        if node in seen:continue
        seen.add(node)
        if node.type=='TEX_IMAGE':return node.image
        for inp in node.inputs:queue.extend(l.from_node for l in inp.links)
    return None
source_color=linked_image('Base Color')
# Load byte-extracted embedded maps directly. A copied packed Image can lose its
# loaded pixel buffer and must not silently flatten the revised material.
color=bpy.data.images.load(str(OUT/'source-bark-base.png'),check_existing=False);color.name='Tree v2 brown bark 2K';color.scale(2048,2048)
pixels=np.empty(len(color.pixels),dtype=np.float32);color.pixels.foreach_get(pixels)
rgba=pixels.reshape(-1,4);lum=rgba[:,:3]@np.array([.2126,.7152,.0722],dtype=np.float32)
variation=np.clip(.6+lum*1.2,.6,1.55)
rgba[:,:3]=variation[:,None]*np.array([.29,.16,.075],dtype=np.float32);rgba[:,3]=1
color.pixels.foreach_set(pixels);color.pack()
bark=bpy.data.materials.new('Tree v2 brown bark');bark.use_nodes=True
bs=bark.node_tree.nodes.get('Principled BSDF');bs.inputs['Roughness'].default_value=.89;bs.inputs['Metallic'].default_value=0
node=bark.node_tree.nodes.new('ShaderNodeTexImage');node.image=color;bark.node_tree.links.new(node.outputs['Color'],bs.inputs['Base Color'])
source_normal=bpy.data.images.load(str(OUT/'source-bark-normal.png'),check_existing=False)
if source_normal:
    normal=source_normal;normal.name='Tree v2 bark normal 2K';normal.colorspace_settings.name='Non-Color';normal.scale(2048,2048);normal.pack()
    node=bark.node_tree.nodes.new('ShaderNodeTexImage');node.image=normal;nm=bark.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.55;bark.node_tree.links.new(node.outputs['Color'],nm.inputs['Color']);bark.node_tree.links.new(nm.outputs['Normal'],bs.inputs['Normal'])

def tube(anchor,points,radii,sides=5):
    """Tapered extension sharing its first vertex with its parent branch mesh."""
    previous=None;last_ring=None
    for ring_index,(point,radius) in enumerate(zip(points,radii)):
        direction=(points[min(ring_index+1,len(points)-1)]-(vertices[anchor] if ring_index==0 else points[ring_index-1])).normalized()
        side=direction.cross(Vector((0,0,1)))
        if side.length<.01:side=Vector((1,0,0))
        side.normalize();other=direction.cross(side)
        start=len(vertices)
        for k in range(sides):vertices.append(point+radius*(side*math.cos(k*math.tau/sides)+other*math.sin(k*math.tau/sides)))
        if previous is None:
            for k in range(sides):faces.append((anchor,start+(k+1)%sides,start+k));uvs.append([(0,0),((k+1)/sides,.2),(k/sides,.2)])
        else:
            for k in range(sides):faces.append((previous+k,previous+(k+1)%sides,start+(k+1)%sides,start+k));uvs.append([(k/sides,ring_index*.2),((k+1)/sides,ring_index*.2),((k+1)/sides,(ring_index+1)*.2),(k/sides,(ring_index+1)*.2)])
        previous=start;last_ring=list(range(start,start+sides))
    tip=len(vertices);vertices.append(points[-1].copy())
    for k in range(sides):faces.append((last_ring[k],last_ring[(k+1)%sides],tip));uvs.append([(k/sides,.8),((k+1)/sides,.8),(.5,1)])
    return tip,last_ring

leaf_vertices=[];leaf_faces=[];leaf_uvs=[];leaf_colors=[]
def leaf(base,direction,length,width,tint):
    d=direction.normalized();side=d.cross(Vector((0,0,1)))
    if side.length<.05:side=Vector((1,0,0))
    side.normalize();normal=side.cross(d).normalized();angle=rng.uniform(-.65,.65)
    side=side*math.cos(angle)+normal*math.sin(angle);normal=side.cross(d).normalized()
    start=len(leaf_vertices)
    points=[base,base+d*length*.30-side*width*.5,base+d*length*.72-side*width*.38+normal*length*.07,base+d*length+normal*length*.13,base+d*length*.72+side*width*.38+normal*length*.07,base+d*length*.30+side*width*.5,base+d*length*.49+normal*length*.09]
    leaf_vertices.extend(points);coords=[(.5,0),(0,.3),(.12,.72),(.5,1),(.88,.72),(1,.3),(.5,.49)]
    for k in range(6):leaf_faces.append((start+k,start+(k+1)%6,start+6));leaf_uvs.append([coords[k],coords[(k+1)%6],coords[6]]);leaf_colors.append(tint)

tree=kdtree.KDTree(base_vertex_count)
for i,p in enumerate(vertices[:base_vertex_count]):tree.insert(p,i)
tree.balance()
branch_count=60;sprig_count=0;leaf_count=0;targets=[]
for j in range(branch_count):
    # Fibonacci directions produce even coverage; randomized radii and heights
    # break regular bands while retaining a compact broadleaf envelope.
    z=-.55+1.5*(j+.5)/branch_count;theta=j*2.399963229728653
    radial=math.sqrt(max(0,1-z*z));radius=rng.uniform(.76,1)
    target=Vector((math.cos(theta)*radial*1.28*radius,math.sin(theta)*radial*1.22*radius,2.42+z*.92))
    desired=Vector((target.x*.43,target.y*.43,min(target.z-.32,2.58)))
    _,anchor,_=tree.find(desired);a=vertices[anchor]
    mid=a.lerp(target,.58)+Vector((0,0,.07))
    tip,ring=tube(anchor,[a.lerp(mid,.22),mid,target],[.041,.023,.011],6)
    targets.append(list(target))
    for s in range(8):
        # Every sprig attaches to an actual terminal branch vertex.
        sprig_anchor=tip if s==0 else ring[s%len(ring)]
        start=vertices[sprig_anchor]
        angle=s*math.tau/8+theta*.3
        direction=Vector((math.cos(angle),math.sin(angle),rng.uniform(-.35,.65))).normalized()
        end=start+direction*rng.uniform(.26,.42)
        sprig_tip,_=tube(sprig_anchor,[start.lerp(end,.2),end],[.0045,.0015],3);sprig_count+=1
        sideways=direction.cross(Vector((0,0,1))).normalized()
        for k in range(7):
            factor=.16+k*.115
            ld=(direction*.38+sideways*((-1 if k%2 else 1)*.85)+Vector((0,0,rng.uniform(-.2,.45)))).normalized()
            p=start.lerp(end,factor)
            intensity=rng.uniform(.82,1.19);tint=(intensity,rng.uniform(.92,1.08)*intensity,rng.uniform(.78,1.02)*intensity,1)
            leaf(p,ld,rng.uniform(.17,.245),rng.uniform(.092,.14),tint);leaf_count+=1
        leaf(end,direction,rng.uniform(.18,.25),.125,(1.08,1.07,.92,1));leaf_count+=1

# Procedural UV vein variation supplements curved geometry; explicitly authored,
# not a downloaded or photographic leaf scan. Opaque double-sided geometry.
N=512;y,x=np.mgrid[0:N,0:N].astype(np.float32);u=x/(N-1);v=y/(N-1)
edge=np.minimum(1,np.abs(u-.5)*2);mid=np.exp(-((u-.5)/.012)**2)
branches=np.exp(-((np.mod(v*8+np.abs(u-.5)*2,1)-.5)/.045)**2)
grain=np.random.default_rng(1244).normal(0,.018,(N,N)).astype(np.float32)
intensity=.91+.10*(1-edge)+.045*np.sin(v*math.pi)+grain-.1*branches+.08*mid
leaf_pixels=np.ones((N,N,4),dtype=np.float32);leaf_pixels[:,:,:3]=intensity[:,:,None]*np.array([.12,.24,.038],dtype=np.float32)
leaf_image=bpy.data.images.new('Tree v2 authored leaf veins',width=N,height=N,alpha=True);leaf_image.pixels.foreach_set(leaf_pixels.reshape(-1));leaf_image.pack()
leaf_mat=bpy.data.materials.new('Tree v2 broad leaves');leaf_mat.use_nodes=True;leaf_mat.use_backface_culling=False
lbs=leaf_mat.node_tree.nodes.get('Principled BSDF');lbs.inputs['Roughness'].default_value=.72
tex=leaf_mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=leaf_image
vc=leaf_mat.node_tree.nodes.new('ShaderNodeVertexColor');vc.layer_name='LeafTint'
mix=leaf_mat.node_tree.nodes.new('ShaderNodeMixRGB');mix.blend_type='MULTIPLY';mix.inputs[0].default_value=1
leaf_mat.node_tree.links.new(tex.outputs['Color'],mix.inputs[1]);leaf_mat.node_tree.links.new(vc.outputs['Color'],mix.inputs[2]);leaf_mat.node_tree.links.new(mix.outputs['Color'],lbs.inputs['Base Color'])

def make_mesh(name,points,polygons,uv_values,material,colors=None):
    data=bpy.data.meshes.new(name);data.from_pydata(points,[],polygons);data.update();data.materials.append(material)
    uv=data.uv_layers.new(name='UVMap')
    color=data.color_attributes.new(name='LeafTint',type='FLOAT_COLOR',domain='CORNER') if colors else None
    if color:data.color_attributes.active_color=color
    for p,values in zip(data.polygons,uv_values):
        p.use_smooth=True
        for loop,val in zip(p.loop_indices,values):
            uv.data[loop].uv=val
            if color:color.data[loop].color=colors[p.index]
    obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);return obj

bpy.data.objects.remove(old,do_unlink=True)
wood=make_mesh('Tree_v2_connected_branch_scaffold',vertices,faces,uvs,bark)
foliage=make_mesh('Tree_v2_broadleaf_crown',leaf_vertices,leaf_faces,leaf_uvs,leaf_mat,leaf_colors)
assets=[wood,foliage];points=[v.co for o in assets for v in o.data.vertices]
height=max(p.z for p in points)-min(p.z for p in points);ground=min(p.z for p in points);factor=3.8/height
for obj in assets:
    for v in obj.data.vertices:v.co=(v.co-Vector((0,0,ground)))*factor
all_points=[v.co for o in assets for v in o.data.vertices]
bounds={'min':[min(p[i] for p in all_points) for i in range(3)],'max':[max(p[i] for p in all_points) for i in range(3)]}
triangles=sum(len(p.vertices)-2 for o in assets for p in o.data.polygons)
assert triangles<55000
bpy.ops.object.select_all(action='DESELECT')
for o in assets:o.select_set(True)
bpy.context.view_layer.objects.active=wood
glb=MODELS/'tree-v2.glb';bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=False,export_all_vertex_colors=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/'tree-v2.blend'))
report={'status':'candidate awaiting actual export review','seed':894517,'sourceBlend':str(SOURCE.relative_to(ROOT)),'sourceGLBSHA256':hashlib.sha256((SOURCE.parent/'tree.glb').read_bytes()).hexdigest(),'glbSHA256':hashlib.sha256(glb.read_bytes()).hexdigest(),'triangles':triangles,'29InstanceTriangles':triangles*29,'previous29InstanceTriangles':61526*29,'meshCount':2,'materials':2,'nominalHeight':3.8,'boundsBlender':bounds,'leafCount':leaf_count,'newBranchExtensions':branch_count,'newSprigs':sprig_count,'branchScaffoldBaseVertices':base_vertex_count,'branchScaffoldBaseTriangles':base_triangles,'branchAttachmentMethod':'Every extension shares an existing scaffold vertex; sprigs share terminal extension vertices. No detached leaf-cloud helper objects.','textureMethod':'Generated-source bark luminance remapped to brown and reduced to 2K; locally authored 512px leaf veins with per-leaf tint. Not photographic scans.','limitations':['Static tree; no wind.','Opaque leaves do not reproduce physical transmission.','Generated scaffold shape and locally authored foliage still require visual review.','A scene with 29 real runtime instances must be measured by integration owner.']}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))
