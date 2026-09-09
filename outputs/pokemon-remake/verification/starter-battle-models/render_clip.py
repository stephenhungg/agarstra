"""Render continuous motion from an actual-export inspection scene."""
import bpy,sys,math
from pathlib import Path
from mathutils import Vector
args=sys.argv[sys.argv.index('--')+1:]
source=Path(args[0]);clip=args[1];output=Path(args[2])
bpy.ops.wm.open_mainfile(filepath=str(source))
scene=bpy.context.scene;action=bpy.data.actions[clip]
rigs=[o for o in scene.objects if o.type=='ARMATURE']
for rig in rigs:
    for track in rig.animation_data.nla_tracks:track.mute=True
    rig.animation_data.action=action
    if action.slots:rig.animation_data.action_slot=action.slots[0]
span=scene.camera.data.ortho_scale/1.55
target=Vector((0,.18*span,.45*span))
scene.camera.location=target+Vector((1.2,-3,1.1))*span
scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.resolution_x=scene.render.resolution_y=480;scene.cycles.samples=8
scene.frame_start=round(action.frame_range[0]);scene.frame_end=round(action.frame_range[1])
scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.filepath=str(output)
bpy.ops.render.render(animation=True)
