"""Direct source-sprite Squirtle candidate: continuous remeshed skin, turtle shell, deforming rig."""
import bpy, math, json, hashlib, os
import numpy as np
from pathlib import Path
from mathutils import Vector, Matrix, Quaternion
ROOT=Path(__file__).resolve().parents[4]
MODELS=ROOT/'outputs/pokemon-remake/models'
REVIEW_ROOT=Path('/Volumes/Vault/dev/agarstra-model-work/starter-battle-models') if Path('/Volumes/Vault').is_dir() else ROOT/'work/pokemon/model-reviews'
OUT=Path(os.environ.get('AGARSTRA_MODEL_WORK',str(REVIEW_ROOT)))/'squirtle'
OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=30
skin_parts=[];attachments=[]
def textured(name,color,roughness,kind='skin'):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Roughness'].default_value=roughness
    p.inputs['Specular IOR Level'].default_value=.34
    if kind=='skin':p.inputs['Subsurface Weight'].default_value=.075
    n=512;rng=np.random.default_rng(17 if kind=='skin' else 71)
    noise=rng.random((n,n)).astype(np.float32)
    for i in range(8):noise=(noise+np.roll(noise,1,0)+np.roll(noise,-1,0)+np.roll(noise,1,1)+np.roll(noise,-1,1))/5
    noise=(noise-noise.mean())/(noise.std()+1e-6)
    yy,xx=np.mgrid[0:n,0:n];variation=(.008 if kind=='skin' else .012)*noise
    if kind=='shell':variation+=.008*np.sin(yy*.19+noise*2)
    values=np.empty((n,n,4),dtype=np.float32);values[:,:,:3]=np.clip(np.array(color)[None,None,:]*(1+variation[:,:,None]),0,1);values[:,:,3]=1
    image=bpy.data.images.new(name+' color',width=n,height=n);image.pixels.foreach_set(values.ravel());image.pack()
    tex=mat.node_tree.nodes.new('ShaderNodeTexImage');tex.image=image;mat.node_tree.links.new(tex.outputs['Color'],p.inputs['Base Color'])
    normal=np.zeros((n,n,4),dtype=np.float32);normal[:,:,0]=.5+(np.roll(noise,1,1)-np.roll(noise,-1,1))*.08;normal[:,:,1]=.5+(np.roll(noise,1,0)-np.roll(noise,-1,0))*.08;normal[:,:,2]=1;normal[:,:,3]=1
    ni=bpy.data.images.new(name+' micro normal',width=n,height=n);ni.colorspace_settings.name='Non-Color';ni.pixels.foreach_set(normal.ravel());ni.pack()
    nt=mat.node_tree.nodes.new('ShaderNodeTexImage');nt.image=ni;nm=mat.node_tree.nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.075 if kind=='skin' else .10;mat.node_tree.links.new(nt.outputs['Color'],nm.inputs['Color']);mat.node_tree.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    return mat
def solid(name,color,rough=.45):
    mat=bpy.data.materials.new(name);mat.diffuse_color=(*color,1);mat.use_nodes=True;p=mat.node_tree.nodes.get('Principled BSDF');p.inputs['Base Color'].default_value=(*color,1);p.inputs['Roughness'].default_value=rough;return mat
skin=textured('Blue freshwater turtle skin',(.095,.46,.57),.48)
cream=textured('Warm ivory plastron',(.73,.62,.39),.58,'shell')
brown=textured('Amber keratin scutes',(.31,.13,.055),.54,'shell')
seam=solid('Shell deep seams',(.10,.045,.02),.72);rim=solid('Shell pale growing rim',(.77,.67,.46),.59)
socket=solid('Soft dark eyelid edge',(.026,.10,.105),.6);white=solid('Warm wet sclera',(.85,.90,.83),.24)
iris=solid('Deep ruby iris',(.29,.035,.05),.22);pupil=solid('Black eye pupil',(.005,.008,.012),.18);glint=solid('Eye catchlights',(.97,.99,1),.12)
mouth=solid('Mouth crease',(.045,.10,.105),.7);belly_seam=solid('Belly plate creases',(.33,.24,.115),.78)
def ellipsoid(name,location,scale,mat=None,skinpart=False,segments=40,rings=24):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=location);o=bpy.context.object;o.name=name;o.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for face in o.data.polygons:face.use_smooth=True
    if mat:o.data.materials.append(mat)
    if skinpart:skin_parts.append(o)
    return o
def tube(name,points,radii,mat=None,skinpart=False,sides=14):
    vertices=[];faces=[]
    for i,p in enumerate(points):
        p=Vector(p);direction=Vector(points[min(i+1,len(points)-1)])-Vector(points[max(0,i-1)]);direction.normalize();axis=direction.cross(Vector((0,0,1)))
        if axis.length<.1:axis=direction.cross(Vector((1,0,0)))
        axis.normalize();other=direction.cross(axis).normalized()
        for j in range(sides):vertices.append(p+(axis*math.cos(j*math.tau/sides)+other*math.sin(j*math.tau/sides))*radii[i])
    for i in range(len(points)-1):
        for j in range(sides):faces.append((i*sides+j,i*sides+(j+1)%sides,(i+1)*sides+(j+1)%sides,(i+1)*sides+j))
    faces.extend([tuple(reversed(range(sides))),tuple((len(points)-1)*sides+j for j in range(sides))])
    m=bpy.data.meshes.new(name);m.from_pydata(vertices,[],faces);m.update();o=bpy.data.objects.new(name,m);scene.collection.objects.link(o)
    for p in m.polygons:p.use_smooth=True
    if mat:m.materials.append(mat)
    if skinpart:skin_parts.append(o)
    return o
ellipsoid('Body',(0,0,.93),(.48,.34,.58),skinpart=True)
ellipsoid('Neck',(0,-.025,1.38),(.235,.245,.28),skinpart=True)
ellipsoid('Rounded broad turtle head',(0,-.10,1.77),(.565,.47,.48),skinpart=True,segments=56,rings=36)
ellipsoid('Soft muzzle',(0,-.425,1.535),(.38,.23,.205),skinpart=True)
for side in [-1,1]:
    ellipsoid('Cheek',(.34*side,-.30,1.55),(.23,.23,.20),skinpart=True)
    tube('Arm',[(.35*side,-.015,1.09),(.49*side,-.09,.99),(.62*side,-.17,.86),(.69*side,-.235,.74)],[.19,.18,.155,.15],skinpart=True)
    ellipsoid('Webbed hand',(.69*side,-.24,.73),(.175,.165,.15),skinpart=True)
    for finger in [-1,0,1]:ellipsoid('Rounded finger',((.69+finger*.09)*side,-.335,.71+abs(finger)*.014),(.069,.104,.079),skinpart=True,segments=24,rings=16)
    ellipsoid('Haunch',(.28*side,.005,.48),(.225,.26,.30),skinpart=True)
    ellipsoid('Ankle',(.335*side,-.06,.25),(.19,.22,.23),skinpart=True)
    ellipsoid('Broad foot',(.335*side,-.19,.145),(.235,.29,.14),skinpart=True)
    for toe in [-1,0,1]:ellipsoid('Soft toe',((.335+toe*.13)*side,-.39,.12),(.082,.135,.105),skinpart=True,segments=24,rings=16)
tail_points=[(0,.22,.49),(.12,.45,.40),(.32,.66,.36),(.54,.81,.43),(.68,.80,.60),(.68,.67,.78),(.52,.59,.87),(.36,.65,.83),(.32,.77,.69),(.42,.81,.62),(.50,.75,.68)]
tail_controls=tail_points[:];control_radii=[.18,.175,.17,.165,.16,.15,.14,.13,.115,.09,.045];smooth_tail=[];smooth_radii=[]
for i in range(len(tail_controls)-1):
    p0=Vector(tail_controls[max(0,i-1)]);p1=Vector(tail_controls[i]);p2=Vector(tail_controls[i+1]);p3=Vector(tail_controls[min(len(tail_controls)-1,i+2)])
    for j in range(8):
        t=j/8;smooth_tail.append(.5*((2*p1)+(-p0+p2)*t+(2*p0-5*p1+4*p2-p3)*t*t+(-p0+3*p1-3*p2+p3)*t*t*t));smooth_radii.append(control_radii[i]*(1-t)+control_radii[i+1]*t)
smooth_tail.append(Vector(tail_controls[-1]));smooth_radii.append(control_radii[-1])
tube('Curled tail',smooth_tail,smooth_radii,skinpart=True,sides=20)
bpy.ops.object.select_all(action='DESELECT')
for o in skin_parts:o.select_set(True)
bpy.context.view_layer.objects.active=skin_parts[0];bpy.ops.object.join();body=bpy.context.object;body.name='Squirtle continuous organic skin'
remesh=body.modifiers.new('Connected organic surface','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.018;remesh.use_smooth_shade=True;bpy.ops.object.modifier_apply(modifier=remesh.name)
smooth=body.modifiers.new('Soft tissue surface','SMOOTH');smooth.factor=.8;smooth.iterations=5;bpy.ops.object.modifier_apply(modifier=smooth.name)
decimate=body.modifiers.new('Runtime skin density','DECIMATE');decimate.ratio=.65;bpy.ops.object.modifier_apply(modifier=decimate.name)
body.data.materials.append(skin)
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15,island_margin=.01);bpy.ops.object.mode_set(mode='OBJECT')
for face in body.data.polygons:face.use_smooth=True
# Separate keratin plates are physically distinct surfaces fitted into the body.
plastron=ellipsoid('Segmented cream plastron',(0,-.265,.96),(.426,.157,.493),cream);attachments.append((plastron,'Spine'))
for z in [.72,.95,1.18]:
    points=[]
    for i in range(31):
        x=-.365+i*.73/30; zz=z+.035*(x/.365)**2; t=1-(x/.426)**2-((zz-.96)/.493)**2
        if t>.025:points.append((x,-.265-.158*math.sqrt(t)-.002,zz))
    o=tube('Plastron growth seam',points,[.006]*len(points),belly_seam,sides=8);attachments.append((o,'Spine'))
back=ellipsoid('Dark shell foundation',(0,.205,.95),(.548,.35,.648),seam);attachments.append((back,'Spine'))
# A contiguous domed field of low-relief hexagonal scutes with narrow seams.
for row in range(-3,4):
    for col in range(-3,4):
        cx=col*.30+(row%2)*.15;cz=.95+row*.26
        if (cx/.52)**2+((cz-.95)/.61)**2>.97:continue
        points=[]
        for i in range(6):
            x=cx+.166*math.cos(math.pi/6+i*math.tau/6);z=cz+.166*math.sin(math.pi/6+i*math.tau/6);r=math.sqrt((x/.543)**2+((z-.95)/.642)**2)
            if r>.978:x/=(r/.978);z=.95+(z-.95)/(r/.978)
            y=.205+.35*math.sqrt(max(.002,1-(x/.548)**2-((z-.95)/.648)**2))+.012
            points.append((x,y,z))
        center=Vector((cx,.205+.35*math.sqrt(max(.001,1-(cx/.548)**2-((cz-.95)/.648)**2))+.025,cz));verts=[center,*points];faces=[(0,i+1,(i+1)%6+1) for i in range(6)]
        mesh=bpy.data.meshes.new('Rounded scute');mesh.from_pydata(verts,[],faces);mesh.update();o=bpy.data.objects.new('Amber hexagonal shell scute',mesh);scene.collection.objects.link(o);mesh.materials.append(brown)
        for f in mesh.polygons:f.use_smooth=True
        solidify=o.modifiers.new('Plate thickness','SOLIDIFY');solidify.thickness=.008
        bevel=o.modifiers.new('Worn plate edges','BEVEL');bevel.width=.014;bevel.segments=3
        bpy.context.view_layer.objects.active=o
        for mod in list(o.modifiers):bpy.ops.object.modifier_apply(modifier=mod.name)
        attachments.append((o,'Spine'))
points=[(.55*math.cos(i*math.tau/96),.20,.95+.65*math.sin(i*math.tau/96)) for i in range(97)]
attachments.append((tube('Pale continuous shell rim',points,[.046]*len(points),rim, sides=12),'Spine'))
for side in [-1,1]:
    for name,loc,scale,mat in [
      ('Sculpted eyelid',(.315*side,-.466,1.805),(.194,.057,.246),socket),
      ('Eye white',(.315*side,-.493,1.805),(.167,.043,.219),white),
      ('Ruby iris',(.323*side,-.529,1.80),(.106,.026,.183),iris),
      ('Deep oval pupil',(.323*side,-.552,1.805),(.047,.013,.139),pupil),
      ('Main eye reflection',(.294*side,-.565,1.885),(.034,.009,.047),glint),
      ('Secondary eye reflection',(.348*side,-.565,1.741),(.013,.007,.020),glint),
      ('Nostril',(.108*side,-.645,1.60),(.019,.008,.011),mouth)]:attachments.append((ellipsoid(name,loc,scale,mat,segments=32,rings=20),'Head'))
points=[]
for i in range(41):
    x=-.285+i*.57/40;u=x/.285;points.append((x,-.585-.070*(1-u*u),1.48+.06*u*u))
attachments.append((tube('Gentle turtle smile',points,[.009]*len(points),mouth,sides=8),'Head'))
# Skeleton uses deforming limbs and a continuous weighted body, no detached bobbing pieces.
bpy.ops.object.armature_add();rig=bpy.context.object;rig.name='Squirtle_Rig';bpy.ops.object.mode_set(mode='EDIT');rig.data.edit_bones.remove(rig.data.edit_bones[0])
bones={}
def bone(name,head,tail,parent=None,deform=True):
    b=rig.data.edit_bones.new(name);b.head=head;b.tail=tail;b.use_deform=deform
    if parent:b.parent=rig.data.edit_bones[parent]
    bones[name]=(Vector(head),Vector(tail));return b
bone('Root',(0,0,.05),(0,0,.35),deform=False)
bone('Spine',(0,0,.45),(0,-.01,1.34),'Root');bone('Neck',(0,-.025,1.34),(0,-.075,1.52),'Spine');bone('Head',(0,-.075,1.52),(0,-.09,2.12),'Neck')
for label,side in [('L',1),('R',-1)]:
    bone(label+'UpperArm',(.36*side,-.02,1.07),(.58*side,-.145,.89),'Spine');bone(label+'Forearm',(.58*side,-.145,.89),(.69*side,-.235,.74),label+'UpperArm');bone(label+'Hand',(.69*side,-.235,.74),(.69*side,-.36,.7),label+'Forearm')
    bone(label+'Thigh',(.28*side,0,.58),(.335*side,-.03,.31),'Root');bone(label+'Foot',(.335*side,-.03,.31),(.335*side,-.32,.12),label+'Thigh')
for i,(a,b) in enumerate(zip(tail_points[::2],tail_points[2::2])):bone('Tail'+str(i),a,b,'Spine' if i==0 else 'Tail'+str(i-1))
bpy.ops.object.mode_set(mode='OBJECT')
deform=[n for n in bones if n!='Root']
for name in deform:body.vertex_groups.new(name=name)
def segment_distance(p,a,b):
    d=b-a;t=max(0,min(1,(p-a).dot(d)/d.length_squared));return (p-a-t*d).length
for v in body.data.vertices:
    p=body.matrix_world@v.co;dist=[]
    if p.z>1.30:
        t=max(0,min(1,(p.z-1.30)/.22))
        if abs(p.x)>.25 or p.y<-.25:t=max(t,max(0,min(1,(p.z-1.28)/.12)))
        h=t*t*(3-2*t)
        for name,weight in [('Head',h),('Neck',(1-h)*.75),('Spine',(1-h)*.25)]:
            if weight>0:body.vertex_groups[name].add([v.index],weight,'REPLACE')
        continue
    for name in deform:
        # Tail weights remain on the posterior curl, not a neighboring calf.
        if name.startswith('Tail') and p.y<.26:continue
        if p.y>.48 and p.z<1.2 and not name.startswith('Tail'):continue
        if p.z>1.47 and name not in ['Head','Neck','Spine']:continue
        dist.append((segment_distance(p,*bones[name]),name))
    dist.sort();nearest=dist[:3];weights=[1/(d+.045)**5 for d,n in nearest];total=sum(weights)
    for (d,name),weight in zip(nearest,weights):body.vertex_groups[name].add([v.index],weight/total,'REPLACE')
mod=body.modifiers.new('Organic skin deformation','ARMATURE');mod.object=rig;body.parent=rig
for o,name in attachments:
    vg=o.vertex_groups.new(name=name);vg.add(list(range(len(o.data.vertices))),1,'REPLACE');mod=o.modifiers.new('Bound anatomical part','ARMATURE');mod.object=rig;o.parent=rig
all_meshes=[body,*[o for o,n in attachments]]
rig.animation_data_create()
def reset():
    for p in rig.pose.bones:p.matrix_basis=Matrix.Identity(4);p.rotation_mode='QUATERNION'
    bpy.context.view_layer.update()
def rotate(name,axis,degrees):
    p=rig.pose.bones[name];world=rig.matrix_world@p.matrix;pivot=world.translation;rot=Quaternion(Vector(axis),math.radians(degrees));p.matrix=rig.matrix_world.inverted()@Matrix.Translation(pivot)@rot.to_matrix().to_4x4()@Matrix.Translation(-pivot)@world;bpy.context.view_layer.update()
def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
def env(t,keys):
    for (a,x),(b,y) in zip(keys,keys[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return keys[-1][1]
def sample(kind,t):
    reset()
    if kind=='idle':
        breath=math.sin(t*math.tau);rig.pose.bones['Spine'].scale=(1+breath*.006,1+breath*.012,1+breath*.006)
        rotate('Head',(0,0,1),2*math.sin(t*math.tau));rotate('Tail0',(0,0,1),4*math.sin(t*math.tau))
        for side,sign in [('L',1),('R',-1)]:rotate(side+'UpperArm',(0,1,0),sign*breath*2)
    elif kind=='attack':
        wind=env(t,[(0,0),(.25,1),(.46,0),(1,0)]);strike=env(t,[(0,0),(.27,0),(.45,1),(.63,.65),(1,0)])
        rotate('Spine',(1,0,0),-11*wind+22*strike);rotate('Head',(1,0,0),5*wind+13*strike)
        for side in ['L','R']:rotate(side+'UpperArm',(1,0,0),-10*wind+35*strike);rotate(side+'Forearm',(1,0,0),12*strike)
        rotate('Tail0',(1,0,0),-8*strike)
    elif kind=='hit':
        e=env(t,[(0,0),(.18,1),(.40,.65),(1,0)]);rotate('Spine',(1,0,0),-18*e);rotate('Head',(1,0,0),12*e)
        for side in ['L','R']:rotate(side+'Forearm',(1,0,0),-20*e)
    elif kind=='faint':
        e=smooth(t/.8);rotate('Spine',(1,0,0),43*e);rotate('Neck',(1,0,0),12*e);rotate('Head',(1,0,0),17*e)
        for side in ['L','R']:rotate(side+'UpperArm',(1,0,0),-20*e);rotate(side+'Forearm',(1,0,0),-15*e)
        rotate('Tail0',(1,0,0),18*e)
    elif kind=='tailWhip':
        e=env(t,[(0,0),(.2,1),(.78,1),(1,0)]);wave=math.sin((t-.2)*math.tau*2)*e
        rotate('Spine',(0,0,1),65*e);rotate('Head',(0,0,1),-35*e)
        for i in range(5):rotate('Tail'+str(i),(0,0,1),(12+4*i)*wave)
actions=[]
for kind,last in [('idle',90),('attack',30),('hit',18),('faint',42),('tailWhip',42)]:
    action=bpy.data.actions.new(kind);rig.animation_data.action=action
    for frame in range(last+1):
        scene.frame_set(frame);sample(kind,frame/last)
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name);p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('scale',frame=frame,group=p.name)
    actions.append(action)
rig.animation_data.action=None
for action in actions:
    track=rig.animation_data.nla_tracks.new();track.name=action.name;strip=track.strips.new(action.name,0,action);strip.action_frame_start=action.frame_range[0];strip.action_frame_end=action.frame_range[1];track.mute=True
reset();scene.frame_set(0)
bpy.ops.object.select_all(action='DESELECT')
for o in [rig,*all_meshes]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
path=MODELS/'squirtle-battle-v1.glb'
bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_force_sampling=True)
rig.animation_data.action=actions[0]
if actions[0].slots:rig.animation_data.action_slot=actions[0].slots[0]
scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/'squirtle-battle-v1.blend'))
report={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'source':str(ROOT/'outputs/pokemon-remake/environment/starter-battle/squirtle-source-front.png'),'method':'Direct Blender geometry inferred from source sprite. Continuous voxel-remeshed skin, explicit fitted plastron/scutes, smooth limb and tail skinning, PBR texture maps.','clips':{a.name:float(a.frame_range[1])/30 for a in actions},'bones':len(rig.data.bones),'skinVertices':len(body.data.vertices),'status':'candidate requires actual GLB rendering and visual review','up':'+Y','front':'+Z','rootMotion':False,'limitations':['Stylized source-faithful turtle proportions; not photoreal approved.','Faint is an articulated slump, not a full body collapse.']}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
