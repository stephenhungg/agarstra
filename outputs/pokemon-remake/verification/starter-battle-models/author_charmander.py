"""Author source-timed battle reactions on the preserved, attributed creator skin."""
import bpy, math, json, hashlib
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion

ROOT=Path(__file__).resolve().parents[4]
MODELS=ROOT/'outputs/pokemon-remake/models'
OUT=Path('/Volumes/Vault/dev/agarstra-model-work/starter-battle-models/charmander')
OUT.mkdir(parents=True,exist_ok=True)
SOURCE=MODELS/'charmander-existing-v2.blend'
bpy.ops.wm.open_mainfile(filepath=str(SOURCE))
scene=bpy.context.scene;scene.render.fps=30;scene.frame_set(0)
rig=next(o for o in scene.objects if o.type=='ARMATURE')
meshes=[o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers)]
idle=rig.animation_data.action
base={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
for t in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(t)
rig.animation_data.action=None

def reset():
    for p in rig.pose.bones:p.matrix_basis=base[p.name];p.rotation_mode='QUATERNION'
    bpy.context.view_layer.update()

def rotate(name,axis,degrees):
    bone=rig.pose.bones['Charmander_'+name]
    world=rig.matrix_world@bone.matrix;pivot=world.translation
    rotation=Quaternion(Vector(axis),math.radians(degrees))
    bone.matrix=rig.matrix_world.inverted()@Matrix.Translation(pivot)@rotation.to_matrix().to_4x4()@Matrix.Translation(-pivot)@world
    bpy.context.view_layer.update()

def aim(name,child,direction):
    a=rig.pose.bones['Charmander_'+name];b=rig.pose.bones['Charmander_'+child]
    old=(rig.matrix_world@b.head)-(rig.matrix_world@a.head)
    q=old.normalized().rotation_difference(Vector(direction).normalized())
    world=rig.matrix_world@a.matrix;pivot=world.translation
    a.matrix=rig.matrix_world.inverted()@Matrix.Translation(pivot)@q.to_matrix().to_4x4()@Matrix.Translation(-pivot)@world
    bpy.context.view_layer.update()

def smooth(t):
    t=max(0,min(1,t));return t*t*(3-2*t)

def envelope(t,keys):
    for (ta,a),(tb,b) in zip(keys,keys[1:]):
        if t<=tb:return a+(b-a)*smooth((t-ta)/(tb-ta))
    return keys[-1][1]

def vecmix(a,b,t):return Vector(a).lerp(Vector(b),t)

def sample(kind,t):
    reset()
    if kind=='attack':
        wind=envelope(t,[(0,0),(.25,1),(.47,0),(1,0)])
        strike=envelope(t,[(0,0),(.27,0),(.43,1),(.65,.8),(1,0)])
        rotate('Spine2',(0,0,1),-9*wind+11*strike)
        rotate('Chest',(1,0,0),-3*wind+7*strike)
        rotate('Head',(0,0,1),5*wind-7*strike)
        upper=vecmix((-.55,-.1,-.83),(-.83,.20,.52),wind)
        upper=upper.lerp(Vector((.16,-.96,-.22)),strike)
        lower=vecmix((-.5,-.82,.28),(-.18,-.30,.94),wind)
        lower=lower.lerp(Vector((.65,-.55,-.50)),strike)
        aim('RArm1','RArm2',upper);aim('RArm2','RArmPalm',lower)
        rotate('RArmPalm',(0,0,1),-18*strike)
        rotate('LArm1',(1,0,0),-8*wind+8*strike)
        rotate('Tail2',(0,0,1),6*wind-7*strike)
        rotate('Tail3',(0,0,1),4*wind-5*strike)
        rotate('Jaw',(1,0,0),7*strike)
    elif kind=='growl':
        e=envelope(t,[(0,0),(.3,1),(.65,.8),(1,0)])
        rotate('Spine2',(1,0,0),-4*e)
        rotate('Head',(1,0,0),-9*e)
        rotate('Jaw',(1,0,0),20*e)
        rotate('Chest',(0,0,1),1.5*e*math.sin(t*math.pi*8))
        for side,sign in [('L',1),('R',-1)]:rotate(side+'Arm1',(0,1,0),-7*sign*e)
    elif kind=='hit':
        e=envelope(t,[(0,0),(.2,1),(.4,.7),(1,0)])
        rotate('Spine2',(1,0,0),-12*e)
        rotate('Chest',(0,0,1),-5*e)
        rotate('Head',(1,0,0),8*e)
        for side in ['L','R']:
            rotate(side+'Arm1',(1,0,0),-10*e)
            rotate(side+'Arm2',(1,0,0),8*e)
        rotate('Tail2',(0,0,1),7*e)
    elif kind=='faint':
        e=smooth(t/.75)
        rotate('Spine1',(1,0,0),12*e)
        rotate('Spine2',(1,0,0),22*e)
        rotate('Chest',(1,0,0),10*e)
        rotate('Head',(1,0,0),16*e)
        for side,sign in [('L',1),('R',-1)]:
            aim(side+'Arm1',side+'Arm2',vecmix((.55*sign,-.1,-.83),(.35*sign,-.05,-.93),e))
            aim(side+'Arm2',side+'ArmPalm',vecmix((.5*sign,-.82,.28),(.12*sign,-.15,-.98),e))
        rotate('Tail3',(1,0,0),-8*e)
        rotate('Tail4',(1,0,0),-10*e)

actions=[idle]
durations={'attack':30,'growl':36,'hit':18,'faint':42}
for name,last in durations.items():
    action=bpy.data.actions.new(name);rig.animation_data.action=action
    for frame in range(last+1):
        scene.frame_set(frame);sample(name,frame/last)
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name)
            p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name)
            p.keyframe_insert('scale',frame=frame,group=p.name)
    actions.append(action)
rig.animation_data.action=None
for action in actions:
    track=rig.animation_data.nla_tracks.new();track.name=action.name
    strip=track.strips.new(action.name,0,action)
    strip.action_frame_start=action.frame_range[0];strip.action_frame_end=action.frame_range[1];track.mute=True
reset();scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in [rig,*meshes]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=MODELS/'charmander-battle-v3.glb'
bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_force_sampling=True)
rig.animation_data.action=idle
if len(idle.slots):rig.animation_data.action_slot=idle.slots[0]
scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0
bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/'charmander-battle-v3.blend'))
report={'source':str(SOURCE),'sourceSHA256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'clips':{'idle':{'duration':3,'loop':True},'attack':{'duration':1,'impactSeconds':.43,'motion':'right shoulder/elbow/wrist scratch with spine twist and tail counterbalance'},'growl':{'duration':1.2,'motion':'jaw/head/chest display'},'hit':{'duration':.6,'motion':'spine/head recoil and arm reaction'},'faint':{'duration':1.4,'motion':'exhausted articulated slump, clamped end pose'}},'up':'+Y','forward':'+Z','rootTravel':0,'status':'candidate pending actual GLB inspection','limitations':['Faint is a grounded exhausted slump, not a full collapse.','Original coarse scales, horns and solid emissive tail tip retained.','Asset keeps original CC BY-NC 4.0 attribution.']}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report))
