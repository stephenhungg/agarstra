import bpy,math,json,hashlib
from pathlib import Path
from mathutils import Vector
root=Path('/Users/stephenhung/Documents/GitHub/agarstra');out=root/'outputs/pokemon-remake/verification/trainer-direct';source=root/'outputs/pokemon-remake/models/trainer-direct-v1.glb';target=root/'outputs/pokemon-remake/models/trainer-direct-v2.glb'
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(source));scene=bpy.context.scene;scene.render.fps=30;rig=next(o for o in scene.objects if o.type=='ARMATURE');mesh=next(o for o in scene.objects if o.type=='MESH' and any(m.type=='ARMATURE' for m in o.modifiers));scene.frame_set(1);bpy.context.view_layer.update()
# glTF imports supplied bone-display lengths 100x their actual child-joint spacing.
# Repair leg display/IK lengths from measured children, keeping joint origins/roll.
bpy.context.view_layer.objects.active=rig;rig.select_set(True);oldRest={n:rig.data.bones[n].matrix_local.copy() for n in ['LeftUpLeg','LeftLeg','RightUpLeg','RightLeg']};lengthRepairs=[]
bpy.ops.object.mode_set(mode='EDIT')
for side in ['Left','Right']:
 for parent,child in [(side+'UpLeg',side+'Leg'),(side+'Leg',side+'Foot')]:
  bone=rig.data.edit_bones[parent];old=bone.length;bone.length=(rig.data.edit_bones[child].head-bone.head).length;lengthRepairs.append({'bone':parent,'oldLength':old,'newLength':bone.length})
bpy.ops.object.mode_set(mode='OBJECT');scene.frame_set(1);bpy.context.view_layer.update();restMatrixError=max(abs(rig.data.bones[n].matrix_local[r][c]-oldRest[n][r][c]) for n in oldRest for r in range(4) for c in range(4));print('REST_MATRIX_CHANGE',restMatrixError,flush=True);assert restMatrixError<.002
idle=rig.animation_data.action;idle.name='idle';baseline={p.name:p.matrix_basis.copy() for p in rig.pose.bones};world={p.name:rig.matrix_world@p.matrix for p in rig.pose.bones};feet={};calibration=[]
# Measured sole-to-ankle offsets from the actual evaluated skin and foot vertex groups.
evalobj=mesh.evaluated_get(bpy.context.evaluated_depsgraph_get());em=evalobj.to_mesh();coords=[evalobj.matrix_world@v.co for v in em.vertices];evalobj.to_mesh_clear()
for side in ['Left','Right']:
 names=[side+'Foot',side+'ToeBase'];indices={mesh.vertex_groups[n].index for n in names if n in mesh.vertex_groups};ids=[v.index for v in mesh.data.vertices if sum(g.weight for g in v.groups if g.group in indices)>.55];assert ids
 sole=min(coords[i].z for i in ids);ankle=world[side+'Foot'].translation.copy();feet[side]={'ankle':ankle,'sole':sole,'soleToAnkle':ankle.z-sole,'vertexIndices':ids}
for track in rig.animation_data.nla_tracks:track.mute=True
rig.animation_data.action=None
for p in rig.pose.bones:p.matrix_basis=baseline[p.name];p.rotation_mode='QUATERNION'
bpy.context.view_layer.update();empties=[];constraints=[]
def empty(name,matrix=None,location=None):
 o=bpy.data.objects.new(name,None);scene.collection.objects.link(o)
 if matrix is not None:o.matrix_world=matrix
 if location is not None:o.location=location
 empties.append(o);return o
for side in ['Left','Right']:
 hip=world[side+'UpLeg'].translation;knee=world[side+'Leg'].translation;ankle=feet[side]['ankle'];line=(ankle-hip).normalized();poleDirection=knee-(hip+line*(knee-hip).dot(line));assert poleDirection.length>.0001;poleDirection.normalize();pole=empty(side+'KneePole',location=knee+poleDirection*.6);targetEmpty=empty(side+'AnkleTarget',location=ankle);ik=rig.pose.bones[side+'Leg'].constraints.new('IK');ik.target=targetEmpty;ik.pole_target=pole;ik.chain_count=2;ik.use_stretch=False
 # Fit pole angle to the original evaluated knee rather than assuming a bone roll.
 best=(1e9,0)
 for i in range(72):
  angle=-math.pi+i*2*math.pi/72;ik.pole_angle=angle;bpy.context.view_layer.update();actual=(rig.matrix_world@rig.pose.bones[side+'Leg'].matrix).translation;error=(actual-knee).length
  if error<best[0]:best=(error,angle)
 for delta in [(-.08+j*.01) for j in range(17)]:
  angle=best[1]+delta;ik.pole_angle=angle;bpy.context.view_layer.update();error=((rig.matrix_world@rig.pose.bones[side+'Leg'].matrix).translation-knee).length
  if error<best[0]:best=(error,angle)
 ik.pole_angle=best[1];footOrient=empty(side+'FootOrientation',matrix=world[side+'Foot'].copy());copy=rig.pose.bones[side+'Foot'].constraints.new('COPY_ROTATION');copy.target=footOrient;copy.target_space='WORLD';copy.owner_space='WORLD';constraints.extend([ik,copy]);feet[side].update(target=targetEmpty,pole=pole);calibration.append({'side':side,'poleAngleRadians':best[1],'baselineKneeError':best[0],'baselineHip':list(hip),'baselineKnee':list(knee),'baselineAnkle':list(ankle),'soleZ':feet[side]['sole'],'soleToAnkle':feet[side]['soleToAnkle'],'poleDirection':list(poleDirection)})
centerY=sum(f['ankle'].y for f in feet.values())/2;snapshots=[];targetSamples=[]
for frame in range(31):
 phase=frame/30
 for p in rig.pose.bones:p.matrix_basis=baseline[p.name]
 hipWorld=world['Hips'].copy();hipWorld.translation.z+=-.025+.009*(1-math.cos(4*math.pi*phase));rig.pose.bones['Hips'].matrix=rig.matrix_world.inverted()@hipWorld
 targets={}
 for side,offset in [('Left',0),('Right',.5)]:
  t=(phase+offset)%1
  if t<.5:y=-.16+.64*t;lift=0
  else:u=(t-.5)*2;y=.16-.32*u;lift=.085*math.sin(math.pi*u)**2
  pos=feet[side]['ankle'].copy();pos.y=centerY+y;pos.z=feet[side]['soleToAnkle']+lift;feet[side]['target'].location=pos;targets[side]=list(pos)
 bpy.context.view_layer.update();evaluated=rig.evaluated_get(bpy.context.evaluated_depsgraph_get());snapshots.append({p.name:p.matrix.copy() for p in evaluated.pose.bones});targetSamples.append({'frame':frame,'targets':targets})
for p in rig.pose.bones:
 for constraint in list(p.constraints):p.constraints.remove(constraint)
for o in empties:bpy.data.objects.remove(o,do_unlink=True)
walk=bpy.data.actions.new('walk');rig.animation_data.action=walk
for frame,snapshot in enumerate(snapshots):
 scene.frame_set(frame)
 for p in rig.pose.bones:
  p.matrix=snapshot[p.name];bpy.context.view_layer.update();p.keyframe_insert('location',frame=frame,group=p.name);p.keyframe_insert('rotation_quaternion',frame=frame,group=p.name);p.keyframe_insert('scale',frame=frame,group=p.name)
scene.frame_start=0;scene.frame_end=121
# Export the two explicit NLA tracks, keeping the original idle action separate.
for t in list(rig.animation_data.nla_tracks):rig.animation_data.nla_tracks.remove(t)
for action in [idle,walk]:
 track=rig.animation_data.nla_tracks.new();track.name=action.name;strip=track.strips.new(action.name,int(action.frame_range[0]),action);strip.action_frame_start=action.frame_range[0];strip.action_frame_end=action.frame_range[1];track.mute=True
rig.animation_data.action=None
bpy.ops.object.select_all(action='DESELECT');rig.select_set(True);mesh.select_set(True);bpy.context.view_layer.objects.active=rig
bpy.ops.export_scene.gltf(filepath=str(target),export_format='GLB',use_selection=True,export_animations=True,export_animation_mode='NLA_TRACKS',export_frame_range=False,export_force_sampling=True,export_nla_strips_merged_animation_name='Animation')
# Save editable authoring source with the walk active for inspection.
rig.animation_data.action=walk;scene.frame_set(0);bpy.ops.wm.save_as_mainfile(filepath=str(root/'outputs/pokemon-remake/models/trainer-direct-v2.blend'))
report={'sourceSHA256':hashlib.sha256(source.read_bytes()).hexdigest(),'candidateSHA256':hashlib.sha256(target.read_bytes()).hexdigest(),'method':'two-bone ankle-target IK, knee pole fit against actual source pose, world-space foot orientation, baked local transforms','clip':'walk','durationSeconds':1,'frames':31,'inPlace':True,'nominalDistancePerCycle':.64,'footLift':.085,'strideHalfExtent':.16,'lengthRepairs':lengthRepairs,'maxRestMatrixChange':restMatrixError,'calibration':calibration,'targets':targetSamples,'limitations':['source battle upper-body pose retained','walk is locally authored, not generated or extracted from ROM','candidate skin and foot contact require fresh GLB reimport review']};(out/'walk-authoring.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
