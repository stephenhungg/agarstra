"""Author a restrained, attributed battle idle from the existing creator rig."""
import bpy, json, math, hashlib, numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/verification/charmander-v2'
MODELS=ROOT/'outputs/pokemon-remake/models'
bpy.ops.wm.open_mainfile(filepath=str(MODELS/'charmander-existing-v1.blend'))
scene=bpy.context.scene
scene.frame_set(1)
rig=next(o for o in scene.objects if o.type=='ARMATURE')
mesh=next(o for o in scene.objects if o.type=='MESH')
initial={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
rig.animation_data_clear()
for action in list(bpy.data.actions): bpy.data.actions.remove(action)
for p in rig.pose.bones:
    p.rotation_mode='QUATERNION'
    p.matrix_basis=initial[p.name]
bpy.context.view_layer.update()

def world_rotate(name, rotation):
    bone=rig.pose.bones['Charmander_'+name]
    world=rig.matrix_world@bone.matrix
    pivot=world.translation
    rotated=Matrix.Translation(pivot)@rotation.to_matrix().to_4x4()@Matrix.Translation(-pivot)@world
    bone.matrix=rig.matrix_world.inverted()@rotated
    bpy.context.view_layer.update()

def aim_child(name, child, desired):
    a=rig.pose.bones['Charmander_'+name]
    b=rig.pose.bones['Charmander_'+child]
    direction=(rig.matrix_world@b.head)-(rig.matrix_world@a.head)
    world_rotate(name,direction.normalized().rotation_difference(Vector(desired).normalized()))

# Directions derived from inspected world-space joint heads, not assumed local axes.
for side, sign in [('L',1),('R',-1)]:
    aim_child(side+'Arm1',side+'Arm2',(.55*sign,-.1,-.83))
    aim_child(side+'Arm2',side+'ArmPalm',(.5*sign,-.82,.28))
base={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
stance={p.name:list(rig.matrix_world@p.head) for p in rig.pose.bones if any(x in p.name for x in ['Arm1','Arm2','ArmPalm','LegAnkle'])}

# Keep original base color; reduce relief and remap the original roughness values.
mat=mesh.data.materials[0]
mat.name='Charmander skin - restrained v2'
bs=next(n for n in mat.node_tree.nodes if n.type=='BSDF_PRINCIPLED')
rough_source=next(n for n in mat.node_tree.nodes if n.type=='TEX_IMAGE' and n.image and 'Roughness' in n.image.name)
pixels=np.empty(len(rough_source.image.pixels),dtype=np.float32)
rough_source.image.pixels.foreach_get(pixels)
rgba=pixels.reshape((-1,4));rough=.62+.24*rgba[:,0]
rgba[:,:3]=rough[:,None];rgba[:,3]=1
rough_image=bpy.data.images.new('Charmander v2 restrained roughness',width=rough_source.image.size[0],height=rough_source.image.size[1],alpha=True)
rough_image.colorspace_settings.name='Non-Color'
rough_image.pixels.foreach_set(pixels);rough_image.pack();rough_source.image=rough_image
for n in mat.node_tree.nodes:
    if n.type=='NORMAL_MAP':n.inputs['Strength'].default_value=.18
bs.inputs['Specular IOR Level'].default_value=.32

# The distal region is at the last tail joint, well separated from body/limbs.
# Keep the original skin and geometry; assign only fully distal triangles.
tip=rig.pose.bones['Charmander_Tail5']
tip_origin=rig.matrix_world@tip.head
tip_axis=(rig.matrix_world@tip.matrix).to_3x3().col[0].normalized()
flame=bpy.data.materials.new('Charmander terminal tail - emissive candidate')
flame.use_nodes=True
fbs=flame.node_tree.nodes.get('Principled BSDF')
fbs.inputs['Base Color'].default_value=(1,.12,.007,1)
fbs.inputs['Roughness'].default_value=.6
fbs.inputs['Emission Color'].default_value=(1,.24,.012,1)
fbs.inputs['Emission Strength'].default_value=2.4
mesh.data.materials.append(flame)
world_vertices=[mesh.matrix_world@v.co for v in mesh.data.vertices]
tip_indices={i for i,p in enumerate(world_vertices) if p.y>.46 and p.z>.295 and (p-tip_origin).dot(tip_axis)>.012}
flame_faces=[]
for polygon in mesh.data.polygons:
    if all(i in tip_indices for i in polygon.vertices):
        polygon.material_index=1;flame_faces.append(polygon.index)
assert 10<len(flame_faces)<800, ('Unexpected terminal tail selection',len(flame_faces))

# Author only a new, three-second idle. Original rig-demo action has been removed.
scene.render.fps=30
scene.frame_start=0;scene.frame_end=90
for frame in range(91):
    scene.frame_set(frame)
    for p in rig.pose.bones:p.matrix_basis=base[p.name]
    bpy.context.view_layer.update()
    wave=math.sin(2*math.pi*frame/90)
    sway=math.sin(2*math.pi*frame/90+.4)-math.sin(.4)
    world_rotate('Spine2',Quaternion(Vector((1,0,0)),math.radians(.4*wave)))
    world_rotate('Chest',Quaternion(Vector((1,0,0)),math.radians(.3*wave)))
    world_rotate('Head',Quaternion(Vector((1,0,0)),math.radians(-.45*wave)))
    world_rotate('Head',Quaternion(Vector((0,0,1)),math.radians(.3*sway)))
    for side, sign in [('L',1),('R',-1)]:
        world_rotate(side+'Arm1',Quaternion(Vector((0,1,0)),math.radians(sign*.6*wave)))
        world_rotate(side+'Arm2',Quaternion(Vector((1,0,0)),math.radians(.25*wave)))
    for p in rig.pose.bones:
        p.keyframe_insert('location',frame=frame,group=p.name)
        p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name)
        p.keyframe_insert('scale',frame=frame,group=p.name)
rig.animation_data.action.name='idle'
# Baking each source frame ensures exactly reproducible interpolation/export.
scene.frame_set(0)
for o in scene.objects:o.select_set(o in [mesh,rig])
bpy.context.view_layer.objects.active=rig
glb=MODELS/'charmander-existing-v2.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_frame_range=True,export_force_sampling=True)
bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/'charmander-existing-v2.blend'))

def evaluated_positions():
    obj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());data=obj.to_mesh()
    pos=[obj.matrix_world@v.co for v in data.vertices];obj.to_mesh_clear();return pos
samples={}
for frame in [0,15,30,45,60,75,90]:
    scene.frame_set(frame);samples[frame]=evaluated_positions()
np.savez(OUT/'authored-samples.npz',**{str(k):np.array([list(c) for c in v]) for k,v in samples.items()})
feet=[i for i,p in enumerate(samples[0]) if p.z<.04]
report={'status':'candidate pending actual GLB reimport review','source':'Existing Milos Cerny / Guilherme Lauck creator asset, CC BY-NC 4.0','v1Preserved':True,'glbSHA256':hashlib.sha256(glb.read_bytes()).hexdigest(),'authoredClip':'idle','durationSeconds':3,'frameRange':[0,90],'fps':30,'rootTravel':0,'stanceJointHeadsBlender':stance,'footVertexCount':len(feet),'maxAuthoredFootTravel':max((p[i]-samples[0][i]).length for p in samples.values() for i in feet),'loopClosureMaxVertexError':max((a-b).length for a,b in zip(samples[0],samples[90])),'normalStrength':.18,'roughnessRemap':[.62,.86],'terminalTailMaterial':{'selectedFaces':len(flame_faces),'selectedVertices':len(tip_indices),'rule':'All face vertices: Blender Y > .46, Z > .295, projection from Tail5 origin along its inspected longitudinal local X axis > .012.','originBlender':list(tip_origin),'axisBlender':list(tip_axis),'emissionStrength':2.4,'limitation':'Localized emission on existing solid terminal geometry; not a translucent animated flame simulation.'}}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
