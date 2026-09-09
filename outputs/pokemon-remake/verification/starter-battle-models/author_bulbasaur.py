"""Source-guided continuous quadruped with a bespoke deforming battle rig."""
import bpy,math,json,hashlib,random
from pathlib import Path
from mathutils import Vector,Matrix,Quaternion
ROOT=Path(__file__).resolve().parents[4]
MODELS=ROOT/'outputs/pokemon-remake/models'
OUT=Path('/Volumes/Vault/dev/agarstra-model-work/starter-battle-models/bulbasaur');OUT.mkdir(parents=True,exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene=bpy.context.scene;scene.render.fps=30

def material(name,color,rough=.6):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(*color,1);bs.inputs['Roughness'].default_value=rough;bs.inputs['Specular IOR Level'].default_value=.3
    return m
skinmat=material('Teal skin with source-derived dark patches',(.065,.38,.26),.65)
bulbmat=material('Leaf bulb, muted living green',(.15,.31,.038),.7)
white=material('Warm ivory sclera',(.78,.81,.64),.28)
iris=material('Crimson iris',(.47,.025,.027),.25)
pupil=material('Dark garnet pupil',(.025,.007,.009),.23)
shine=material('Corneal catchlight',(.95,.98,1),.15)
clawmat=material('Ivory claws',(.72,.73,.56),.5)
mouthmat=material('Mouth recess',(.055,.017,.024),.68)
inner=material('Inner ear',(.055,.25,.18),.78)
lidmat=material('Soft teal eyelid rim',(.067,.37,.25),.62)

def mesh(name,vs,fs,mat):
    d=bpy.data.meshes.new(name);d.from_pydata(vs,[],fs);d.update();o=bpy.data.objects.new(name,d);scene.collection.objects.link(o)
    if mat:d.materials.append(mat)
    for p in d.polygons:p.use_smooth=True
    return o

def loft(name,rings,axis='Y',segments=40,power=1,mat=skinmat):
    vs=[];fs=[]
    for center,r1,r2 in rings:
        for k in range(segments):
            a=k*math.tau/segments;c=math.copysign(abs(math.cos(a))**power,math.cos(a));s=math.copysign(abs(math.sin(a))**power,math.sin(a))
            off=Vector((c*r1,0,s*r2)) if axis=='Y' else Vector((c*r1,s*r2,0))
            vs.append(Vector(center)+off)
    for j in range(len(rings)-1):
        for k in range(segments):
            a=j*segments+k;b=j*segments+(k+1)%segments;fs.append((a,b,b+segments,a+segments))
    fs.append(tuple(range(segments-1,-1,-1)));fs.append(tuple((len(rings)-1)*segments+k for k in range(segments)))
    return mesh(name,vs,fs,mat)

body=loft('Continuous broad torso',[( (0,-.25,.43),.18,.19),((0,-.12,.44),.34,.27),((0,.17,.43),.40,.30),((0,.47,.42),.37,.28),((0,.64,.41),.26,.22),((0,.72,.42),.04,.07)],power=.9)
head=loft('Broad frog-like head',[( (0,-1.005,.49),.23,.11),((0,-.95,.54),.40,.225),((0,-.78,.59),.50,.31),((0,-.50,.61),.50,.31),((0,-.29,.58),.35,.27),((0,-.18,.57),.12,.12)],power=.78)
parts=[body,head]
for side,sign in [('L',1),('R',-1)]:
    for label,y in [('Front',-.17),('Rear',.51)]:
        x=sign*(.34 if label=='Front' else .32)
        parts.append(loft(f'{side}{label} shaped leg',[( (x,y-.035,.035),.15,.19),((x,y-.015,.10),.155,.18),((x*.98,y+.015,.23),.145,.15),((x*.9,y+.025,.38),.18,.17),((x*.85,y+.015,.50),.11,.10)],axis='Z',segments=28))
    parts.append(loft(f'{side} pointed ear',[( (sign*.365,-.50,.73),.15,.10),((sign*.405,-.50,.88),.12,.08),((sign*.42,-.51,1.02),.02,.018)],axis='Z',segments=24))
bpy.ops.object.select_all(action='DESELECT')
for o in parts:o.select_set(True)
bpy.context.view_layer.objects.active=body;bpy.ops.object.join();body.name='Bulbasaur continuous skin'
remesh=body.modifiers.new('Connected sculpt surface','REMESH');remesh.mode='VOXEL';remesh.voxel_size=.016;remesh.use_smooth_shade=True
bpy.ops.object.modifier_apply(modifier=remesh.name)
smoothmod=body.modifiers.new('Relax anatomical transitions','SMOOTH');smoothmod.factor=1.1;smoothmod.iterations=4;bpy.ops.object.modifier_apply(modifier=smoothmod.name)
sub=body.modifiers.new('Smooth organic silhouette','SUBSURF');sub.levels=1;bpy.ops.object.modifier_apply(modifier=sub.name)
texture=bpy.data.textures.new('Fine restrained skin pores',type='CLOUDS');texture.noise_scale=.045;texture.noise_depth=1
displace=body.modifiers.new('Fine skin surface','DISPLACE');displace.texture=texture;displace.strength=.0022;displace.texture_coords='GLOBAL';bpy.ops.object.modifier_apply(modifier=displace.name)
dec=body.modifiers.new('Battle mesh budget','DECIMATE');dec.ratio=min(1,26000/max(1,len(body.data.polygons)*2));bpy.ops.object.modifier_apply(modifier=dec.name)
for p in body.data.polygons:p.use_smooth=True

# Vertex colors remain embedded in GLB. Patches are on the actual surface,
# with hand-positioned irregular boundaries instead of separate floating decals.
patches=[((0,-.69,.88),(.14,.17,.12)),((-.34,-.82,.72),(.11,.12,.12)),((.29,-.63,.86),(.13,.14,.08)),((.47,-.42,.64),(.10,.16,.16)),((-.44,-.36,.49),(.11,.14,.12)),((.36,.18,.49),(.09,.17,.13)),((-.38,.35,.49),(.08,.13,.17)),((.35,-.17,.18),(.08,.12,.08)),((-.33,.5,.2),(.085,.12,.08)),((-.35,-.11,.40),(.085,.11,.07))]
colors=body.data.color_attributes.new(name='SkinPattern',type='FLOAT_COLOR',domain='POINT');body.data.color_attributes.active_color=colors
for v in body.data.vertices:
    p=v.co;spot=False
    for c,r in patches:
        dx,dy,dz=[(p[i]-c[i])/r[i] for i in range(3)]
        d=abs(dx)**1.4+abs(dy)**1.4+abs(dz)**1.4
        if d<1.15+.15*math.sin(23*p.x+31*p.z):spot=True;break
    value=.95+.05*math.sin(p.x*7+p.y*8)*math.sin(p.z*13)
    col=(.026,.17,.105) if spot else (.066,.39,.265)
    colors.data[v.index].color=(*(x*value for x in col),1)
node=skinmat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='SkinPattern';skinmat.node_tree.links.new(node.outputs['Color'],skinmat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])

# Continuous radial bulb mesh with real longitudinal grooves and a pointed tip.
vs=[];fs=[];segments=72
profile=[(.65,.19),(.70,.31),(.82,.395),(1.00,.42),(1.16,.34),(1.29,.23),(1.40,.055),(1.43,.008)]
for j,(z,r) in enumerate(profile):
    for k in range(segments):
        a=math.tau*k/segments;rr=r*(1+.12*math.cos(6*a+.25*j));vs.append((rr*math.cos(a)+.04*(z-.65),.25+rr*math.sin(a),z))
for j in range(len(profile)-1):
    for k in range(segments):fs.append((j*segments+k,j*segments+(k+1)%segments,(j+1)*segments+(k+1)%segments,(j+1)*segments+k))
fs.append(tuple(range(segments-1,-1,-1)));fs.append(tuple((len(profile)-1)*segments+k for k in range(segments)))
bulb=mesh('Ribbed closed plant bulb',vs,fs,bulbmat)
bpy.context.view_layer.objects.active=bulb;bulb.select_set(True)
sub=bulb.modifiers.new('Soft leaf lobe contours','SUBSURF');sub.levels=2;bpy.ops.object.modifier_apply(modifier=sub.name)
leafcolors=bulb.data.color_attributes.new(name='LeafVeins',type='FLOAT_COLOR',domain='POINT');bulb.data.color_attributes.active_color=leafcolors
for v in bulb.data.vertices:
    p=v.co;a=math.atan2(p.y-.25,p.x);vein=.82+.14*math.cos(6*a+.5*p.z)+.04*math.cos(a*54+4*p.z)
    leafcolors.data[v.index].color=(.20*vein,.36*vein,.050*vein,1)
node=bulbmat.node_tree.nodes.new('ShaderNodeVertexColor');node.layer_name='LeafVeins';bulbmat.node_tree.links.new(node.outputs['Color'],bulbmat.node_tree.nodes.get('Principled BSDF').inputs['Base Color'])

attachments=[]
def ellipsoid(name,location,scale,mat,bone='Head',rotation=(0,0,0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32,ring_count=20,location=location)
    o=bpy.context.object;o.name=name;o.scale=scale;o.rotation_euler=rotation
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    o.data.materials.append(mat)
    for p in o.data.polygons:p.use_smooth=True
    attachments.append((o,bone));return o
for side,sign in [('L',1),('R',-1)]:
    # Eyes are anatomical layered curved inserts, with a tilted outer silhouette.
    x=sign*.255;y=-.949;z=.635
    rot=(0,sign*math.radians(-10),0)
    ellipsoid(side+' almond sclera',(x,y,z),(.115,.032,.142),white,rotation=rot)
    ellipsoid(side+' red iris',(x-sign*.014,y-.029,z),(.067,.015,.112),iris,rotation=rot)
    ellipsoid(side+' vertical pupil',(x-sign*.017,y-.043,z),(.032,.008,.086),pupil,rotation=rot)
    ellipsoid(side+' eye glint',(x-sign*.03,y-.05,z+.049),(.018,.005,.025),shine,rotation=rot)
    ellipsoid(side+' nostril',(sign*.071,-1.003,.513),(.018,.007,.011),mouthmat)
    ellipsoid(side+' ear inset',(sign*.406,-.581,.865),(.06,.012,.085),inner,rotation=(0,sign*math.radians(8),0))
    for label,y in [('Front',-.17),('Rear',.51)]:
        x=sign*(.34 if label=='Front' else .32)
        for k in [-1,0,1]:
            claw=loft(f'{side}{label} toe{k}',[((x+k*.075,y-.155,.077),.025,.03),((x+k*.079,y-.222,.058),.021,.021),((x+k*.082,y-.25,.037),.002,.003)],axis='Y',segments=16,mat=clawmat)
            attachments.append((claw,f'{side}{label}Foot'))

def curve_mesh(name,coords,radius,mat,bone='Head'):
    data=bpy.data.curves.new(name,'CURVE');data.dimensions='3D';data.resolution_u=20;data.bevel_depth=radius;data.bevel_resolution=3
    s=data.splines.new('BEZIER');s.bezier_points.add(len(coords)-1)
    for p,c in zip(s.bezier_points,coords):p.co=c;p.handle_left_type='AUTO';p.handle_right_type='AUTO'
    o=bpy.data.objects.new(name,data);scene.collection.objects.link(o);o.data.materials.append(mat)
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH');attachments.append((o,bone));return o
curve_mesh('Gently curved broad mouth',[(-.31,-.977,.416),(-.18,-1.012,.385),(0,-1.021,.38),(.18,-1.012,.385),(.31,-.977,.416)],.008,mouthmat)
for sign in [-1,1]:
    x=sign*.255
    curve_mesh('Upper organic eyelid',[(x-.11,-.977,.625),(x-.074,-.972,.741),(x+.005,-.968,.783),(x+.077,-.972,.729),(x+.11,-.977,.625)],.012,lidmat)
for sign in [-1,1]:
    fang=loft('Small upper fang',[((sign*.215,-1.005,.414),.014,.012),((sign*.22,-1.009,.37),.003,.004)],axis='Z',segments=14,mat=clawmat);attachments.append((fang,'Head'))

# Custom quadruped skeleton. Four independently articulated legs, body chain,
# head and plant bulb. No humanoid template or body-only rigid animation.
data=bpy.data.armatures.new('Bulbasaur quadruped skeleton');rig=bpy.data.objects.new('BulbasaurRig',data);scene.collection.objects.link(rig)
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);bpy.context.view_layer.objects.active=rig;bpy.ops.object.mode_set(mode='EDIT')
bones={}
def bone(name,head,tail,parent=None,deform=True):
    b=data.edit_bones.new(name);b.head=head;b.tail=tail;b.use_deform=deform
    if parent:b.parent=bones[parent]
    bones[name]=b
bone('Root',(0,0,0),(0,0,.15),deform=False)
bone('Pelvis',(0,.48,.36),(0,.18,.44),'Root')
bone('Spine',(0,.18,.44),(0,-.15,.47),'Pelvis')
bone('Head',(0,-.20,.55),(0,-.75,.59),'Spine')
bone('Bulb',(0,.25,.7),(0,.25,1.23),'Spine')
for side,sign in [('L',1),('R',-1)]:
    for label,y in [('Front',-.17),('Rear',.51)]:
        x=sign*(.34 if label=='Front' else .32);parent='Spine' if label=='Front' else 'Pelvis'
        bone(side+label+'Upper',(x*.85,y+.025,.43),(x,y+.015,.23),parent)
        bone(side+label+'Lower',(x,y+.015,.23),(x,y-.015,.08),side+label+'Upper')
        bone(side+label+'Foot',(x,y-.015,.08),(x,y-.20,.05),side+label+'Lower')
bpy.ops.object.mode_set(mode='OBJECT')

# Surface region-aware smooth weights. Head/body ownership is blended through
# neck; legs blend smoothly into torso and through knees/ankles, with fixed feet.
def assign(obj,pervertex):
    names=set(k for row in pervertex for k in row)
    groups={n:obj.vertex_groups.new(name=n) for n in names}
    for v,w in zip(obj.data.vertices,pervertex):
        top=sorted(w.items(),key=lambda item:item[1],reverse=True)[:4];total=sum(v for _,v in top)
        for name,value in top:
            if value>1e-6:groups[name].add([v.index],value/total,'REPLACE')
    modifier=obj.modifiers.new('Organic battle deformation','ARMATURE');modifier.object=rig;obj.parent=rig

def smooth(t):t=max(0,min(1,t));return t*t*(3-2*t)
skinweights=[]
for v in body.data.vertices:
    p=v.co;headweight=smooth((-.16-p.y)/.23)*smooth((p.z-.18)/.10);w={'Head':headweight}
    legweight=(1-headweight)*smooth((.40-p.z)/.14)*smooth((abs(p.x)-.16)/.09)
    torso=1-headweight-legweight
    rear=smooth((p.y-.1)/.4);w['Pelvis']=torso*rear;w['Spine']=torso*(1-rear)
    if legweight>0:
        side='L' if p.x>0 else 'R';label='Rear' if p.y>.2 else 'Front';foot=smooth((.145-p.z)/.07);lower=smooth((.30-p.z)/.14)*(1-foot)
        w[side+label+'Upper']=legweight*(1-foot-lower);w[side+label+'Lower']=legweight*lower;w[side+label+'Foot']=legweight*foot
    skinweights.append(w)
assign(body,skinweights);assign(bulb,[{'Bulb':1} for _ in bulb.data.vertices])
for o,n in attachments:assign(o,[{n:1} for _ in o.data.vertices])
assets=[body,bulb,*[o for o,_ in attachments]]

# World-space joint rotations avoid assumptions about bone roll or local axes.
base={p.name:p.matrix_basis.copy() for p in rig.pose.bones}
foot_world={p.name:p.matrix.copy() for p in rig.pose.bones if p.name.endswith('Foot')}
def rotate(name,axis,degrees):
    p=rig.pose.bones[name];world=rig.matrix_world@p.matrix;origin=world.translation
    p.matrix=rig.matrix_world.inverted()@Matrix.Translation(origin)@Quaternion(Vector(axis),math.radians(degrees)).to_matrix().to_4x4()@Matrix.Translation(-origin)@world;bpy.context.view_layer.update()
def envelope(t,points):
    for (a,x),(b,y) in zip(points,points[1:]):
        if t<=b:return x+(y-x)*smooth((t-a)/(b-a))
    return points[-1][1]
actions=[]
for name,last in [('idle',90),('attack',33),('hit',18),('faint',42),('growl',36)]:
    rig.animation_data_create();action=bpy.data.actions.new(name);rig.animation_data.action=action
    for frame in range(last+1):
        scene.frame_set(frame)
        for p in rig.pose.bones:p.matrix_basis=base[p.name];p.rotation_mode='QUATERNION'
        bpy.context.view_layer.update();t=frame/last
        if name=='idle':
            e=math.sin(t*math.tau);rotate('Spine',(1,0,0),.65*e);rotate('Head',(1,0,0),-.8*e);rotate('Bulb',(0,1,0),1.2*e)
        elif name=='attack':
            wind=envelope(t,[(0,0),(.28,1),(.50,0),(1,0)]);strike=envelope(t,[(0,0),(.29,0),(.45,1),(.66,.8),(1,0)])
            rotate('Spine',(1,0,0),-5*wind+8*strike);rotate('Head',(1,0,0),-8*wind+11*strike);rotate('Bulb',(1,0,0),5*wind-9*strike)
            for side in ['L','R']:
                rotate(side+'FrontUpper',(1,0,0),8*wind-13*strike);rotate(side+'FrontLower',(1,0,0),-12*wind+15*strike)
                rotate(side+'RearUpper',(1,0,0),-4*wind+6*strike);rotate(side+'RearLower',(1,0,0),4*wind-6*strike)
        elif name=='hit':
            e=envelope(t,[(0,0),(.22,1),(.45,.5),(1,0)]);rotate('Spine',(1,0,0),-9*e);rotate('Head',(0,0,1),-9*e);rotate('Bulb',(0,1,0),8*e)
        elif name=='faint':
            e=smooth(t/.8);rotate('Spine',(1,0,0),6*e);rotate('Head',(1,0,0),12*e);rotate('Bulb',(1,0,0),4*e)
            for side in ['L','R']:rotate(side+'FrontUpper',(1,0,0),-8*e);rotate(side+'FrontLower',(1,0,0),10*e)
        elif name=='growl':
            e=envelope(t,[(0,0),(.3,1),(.7,.8),(1,0)]);rotate('Head',(1,0,0),-10*e);rotate('Head',(0,0,1),2*e*math.sin(t*math.pi*8));rotate('Bulb',(0,1,0),4*e*math.sin(t*math.pi*4));rotate('Spine',(1,0,0),-3*e)
        # Bake foot world transforms after each body/leg pose to keep contacts.
        for foot_name,matrix in foot_world.items():rig.pose.bones[foot_name].matrix=matrix
        bpy.context.view_layer.update()
        for p in rig.pose.bones:
            p.keyframe_insert('location',frame=frame,group=p.name);p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('scale',frame=frame,group=p.name)
    actions.append(action)
rig.animation_data.action=None
for action in actions:
    track=rig.animation_data.nla_tracks.new();track.name=action.name;strip=track.strips.new(action.name,0,action);strip.action_frame_start=0;strip.action_frame_end=action.frame_range[1];track.mute=True
for p in rig.pose.bones:p.matrix_basis=base[p.name]
scene.frame_set(0);bpy.context.view_layer.update()
ground_points=[];dg=bpy.context.evaluated_depsgraph_get()
for obj in assets:
    evaluated=obj.evaluated_get(dg);em=evaluated.to_mesh();ground_points.extend((evaluated.matrix_world@v.co).z for v in em.vertices);evaluated.to_mesh_clear()
rig.location.z-=min(ground_points);bpy.context.view_layer.update()

# Bake restrained pores and roughness into actual GLB texture maps. Procedural
# preview nodes alone would disappear in the browser renderer.
bpy.ops.object.select_all(action='DESELECT');body.select_set(True);bpy.context.view_layer.objects.active=body
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(65),island_margin=.012);bpy.ops.object.mode_set(mode='OBJECT')
scene.render.engine='CYCLES';scene.cycles.samples=8;scene.render.bake.margin=12
nodes=skinmat.node_tree.nodes;links=skinmat.node_tree.links;bs=nodes.get('Principled BSDF')
coords=nodes.new('ShaderNodeTexCoord');noise=nodes.new('ShaderNodeTexNoise');noise.inputs['Scale'].default_value=155;noise.inputs['Detail'].default_value=2;noise.inputs['Roughness'].default_value=.55
links.new(coords.outputs['Generated'],noise.inputs['Vector'])
bump=nodes.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.25;bump.inputs['Distance'].default_value=.012;links.new(noise.outputs['Fac'],bump.inputs['Height']);links.new(bump.outputs['Normal'],bs.inputs['Normal'])
normal=bpy.data.images.new('Bulbasaur baked fine skin normal',width=1024,height=1024);normal.colorspace_settings.name='Non-Color'
target=nodes.new('ShaderNodeTexImage');target.image=normal;nodes.active=target
bpy.ops.object.bake(type='NORMAL');normal.pack();links.remove(bs.inputs['Normal'].links[0]);nm=nodes.new('ShaderNodeNormalMap');nm.inputs['Strength'].default_value=.45;links.new(target.outputs['Color'],nm.inputs['Color']);links.new(nm.outputs['Normal'],bs.inputs['Normal'])
mapping=nodes.new('ShaderNodeMapRange');mapping.inputs['From Min'].default_value=0;mapping.inputs['From Max'].default_value=1;mapping.inputs['To Min'].default_value=.51;mapping.inputs['To Max'].default_value=.76;links.new(noise.outputs['Fac'],mapping.inputs['Value']);links.new(mapping.outputs['Result'],bs.inputs['Roughness'])
rough=bpy.data.images.new('Bulbasaur baked skin roughness',width=1024,height=1024);rough.colorspace_settings.name='Non-Color';roughnode=nodes.new('ShaderNodeTexImage');roughnode.image=rough;nodes.active=roughnode
bpy.ops.object.bake(type='ROUGHNESS');rough.pack();links.remove(bs.inputs['Roughness'].links[0]);links.new(roughnode.outputs['Color'],bs.inputs['Roughness'])
bpy.ops.object.select_all(action='DESELECT')
for o in [rig,*assets]:o.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=MODELS/'bulbasaur-battle-v1.glb';bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_force_sampling=True,export_all_vertex_colors=True)
rig.animation_data.action=actions[0]
if actions[0].slots:rig.animation_data.action_slot=actions[0].slots[0]
scene.frame_set(0);bpy.context.preferences.filepaths.save_version=0;bpy.ops.wm.save_as_mainfile(filepath=str(MODELS/'bulbasaur-battle-v1.blend'))
report={'status':'source-guided candidate pending reference comparison and GLB reimport','sha256':hashlib.sha256(glb.read_bytes()).hexdigest(),'source':'environment/starter-battle/bulbasaur-source-front.png','method':'Tailored continuous loft surfaces, voxel union, anatomical skin weight blending, custom four-leg deform skeleton, geometric bulb grooves and embedded vertex color patches','rigBones':len(rig.data.bones),'triangles':sum(sum(len(p.vertices)-2 for p in o.data.polygons) for o in assets),'clips':[{'name':a.name,'seconds':a.frame_range[1]/30} for a in actions],'limitations':['Stylized PBR geometry, not a photoreal reconstruction.','Growl is head/neck/body display without a jaw-open morph.','No production acceptance until imported motion and source identity are inspected.']}
(OUT/'authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
