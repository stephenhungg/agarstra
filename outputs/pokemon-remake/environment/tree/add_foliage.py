import bpy, math, random, json
from mathutils import Vector
from pathlib import Path
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/environment/tree'
bpy.ops.wm.open_mainfile(filepath=str(OUT/'tree.blend'))
rng=random.Random(18394)
trunk=bpy.data.objects['Pallet_Broadleaf_Tree']
points=[v.co.copy() for v in trunk.data.vertices if v.co.z>2.15 and (v.co.x*v.co.x+v.co.y*v.co.y)**0.5>0.35]
verts=[]; faces=[]; material_ids=[]
greens=[(0.070,0.145,0.023,1),(0.095,0.18,0.03,1),(0.135,0.215,0.045,1),(0.055,0.12,0.018,1),(0.18,0.245,0.06,1),(0.08,0.17,0.025,1)]
def leaf(base,direction,length,width,idx):
    d=direction.normalized()
    # Individual curved leaf blades: six triangles, central raised vein.
    side=d.cross(Vector((0,0,1)))
    if side.length<0.01: side=Vector((1,0,0))
    side.normalize()
    normal=side.cross(d).normalized()
    angle=rng.uniform(-0.8,0.8)
    side=side*math.cos(angle)+normal*math.sin(angle)
    normal=side.cross(d).normalized()
    start=len(verts)
    verts.extend([base,base+d*length*.30-side*width*.43,base+d*length*.70-side*width*.36+normal*length*.055,base+d*length+normal*length*.08,base+d*length*.70+side*width*.36+normal*length*.055,base+d*length*.30+side*width*.43,base+d*length*.49+normal*length*.08])
    for i in range(6):
        faces.append((start+i,start+(i+1)%6,start+6));material_ids.append(idx)
def twig(a,b,radius=.005):
    d=(b-a).normalized(); side=d.cross(Vector((0,0,1)))
    if side.length<.01: side=Vector((1,0,0))
    side.normalize(); other=d.cross(side)
    start=len(verts)
    for p,r in [(a,radius),(b,radius*.45)]:
        for k in range(3):
            ang=k*math.tau/3; verts.append(p+(side*math.cos(ang)+other*math.sin(ang))*r)
    for k in range(3):
        a0=start+k;a1=start+(k+1)%3;b0=start+3+k;b1=start+3+(k+1)%3
        faces.extend([(a0,a1,b1),(a0,b1,b0)]);material_ids.extend([6,6])

for j in range(900):
    anchor=rng.choice(points)
    outward=Vector((anchor.x,anchor.y,.5)).normalized()
    direction=(outward*.5+Vector((rng.uniform(-1,1),rng.uniform(-1,1),rng.uniform(-.1,.9)))).normalized()
    length=rng.uniform(.25,.55)
    end=anchor+direction*length
    twig(anchor,end)
    side=direction.cross(Vector((0,0,1))).normalized()
    for k in range(7):
        t=.22+k*.105
        leaf_direction=(direction*.5+side*((-1 if k%2 else 1)*.85)+Vector((0,0,rng.uniform(-.3,.4)))).normalized()
        base=anchor+direction*(length*t)
        leaf(base,leaf_direction,rng.uniform(.10,.18),rng.uniform(.055,.09),rng.randrange(6))
    leaf(end,direction,rng.uniform(.12,.19),.08,rng.randrange(6))
mesh=bpy.data.meshes.new('Authored_individual_leaf_sprays')
mesh.from_pydata(verts,[],faces);mesh.update()
foliage=bpy.data.objects.new('Pallet_Broadleaf_Foliage',mesh)
bpy.context.collection.objects.link(foliage)
for i,color in enumerate(greens+[(.12,.075,.028,1)]):
    mat=bpy.data.materials.new(f'Leaf_green_{i}' if i<6 else 'Young_twigs')
    mat.use_nodes=True
    bs=mat.node_tree.nodes.get('Principled BSDF')
    bs.inputs['Base Color'].default_value=color
    bs.inputs['Roughness'].default_value=.66 if i<6 else .85
    mat.diffuse_color=color
    mat.use_backface_culling=False
    mesh.materials.append(mat)
for poly,idx in zip(mesh.polygons,material_ids): poly.material_index=idx
for poly in mesh.polygons: poly.use_smooth=True

# Reduce only generated bark topology for the repeated runtime candidate.
bpy.context.view_layer.objects.active=trunk
mod=trunk.modifiers.new('Repeated_tree_bark_budget','DECIMATE');mod.ratio=.26
bpy.ops.object.modifier_apply(modifier=mod.name)
all_assets=[trunk,foliage]
height=max(v.co.z for o in all_assets for v in o.data.vertices)
factor=5/height
for o in all_assets:
    for v in o.data.vertices: v.co*=factor
bpy.ops.object.select_all(action='DESELECT')
for o in all_assets:o.select_set(True)
bpy.context.view_layer.objects.active=trunk
bpy.ops.export_scene.gltf(filepath=str(OUT/'tree.glb'),export_format='GLB',use_selection=True,export_animations=False)
stats=json.loads((OUT/'mesh-inspection.json').read_text())
stats['generated_scaffold_triangles_before_decimation']=stats['triangles']
stats['triangles']=sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in all_assets)
stats['vertices']=sum(len(o.data.vertices) for o in all_assets)
stats['meshes']=2
stats['authored_leaves']=7200
stats['authored_sprays']=900
stats['correction']='Provider omitted foliage; deterministic local Blender modeling adds curved individual leaf blades and twigs to provider branch scaffold.'
pts=[v.co for o in all_assets for v in o.data.vertices]
stats['bbox_min_xyz_blender']=[min(p[i] for p in pts) for i in range(3)]
stats['bbox_max_xyz_blender']=[max(p[i] for p in pts) for i in range(3)]
stats['dimensions_m']=[stats['bbox_max_xyz_blender'][i]-stats['bbox_min_xyz_blender'][i] for i in range(3)]
(OUT/'mesh-inspection.json').write_text(json.dumps(stats,indent=2))
scene=bpy.context.scene
cam=scene.camera
for name,position,target in [('front',(8,-11,7),(0,0,2.5)),('back',(-8,11,7),(0,0,2.5)),('gameplay',(8,-11,13),(0,0,2.3))]:
    cam.location=position
    cam.rotation_euler=(Vector(target)-cam.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(OUT/f'tree-review-{name}.png')
    bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tree.blend'))
