"""Add editable, in-place rigid-part animations to the authored character GLBs.

Run with Blender 4.5:
  blender -b -t 4 --python-exit-code 1 --python animate_characters.py -- --root PROJECT

The source models/materials remain intact. No skinning or motion capture is implied.
Each clip is a named NLA track shared across its moving parts, exported to glTF.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Vector

FPS = 30
TAU = math.tau
SOURCES = {
    'mario-body': 'character-kit-1',
    'goomba': 'creatures-1',
    'koopa-green': 'creatures-1',
    'koopa-red': 'creatures-1',
    'piranha-plant': 'aquatic-1',
}
CLIPS = {
    'mario-body': [('idle', 60, True), ('walk', 24, True), ('run', 18, True),
                   ('jump-rise', 6, False), ('jump-fall', 6, False), ('death', 12, False)],
    'goomba': [('idle', 60, True), ('walk', 24, True), ('squash', 6, False)],
    'koopa-green': [('idle', 60, True), ('walk', 30, True), ('shell', 8, False)],
    'koopa-red': [('idle', 60, True), ('walk', 30, True), ('shell', 8, False)],
    'piranha-plant': [('idle', 60, True), ('bite', 24, True)],
}


def bounds(objects):
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ Vector(c) for o in objects if o.type == 'MESH' for c in o.bound_box]
    return Vector(tuple(min(p[k] for p in pts) for k in range(3))), Vector(tuple(max(p[k] for p in pts) for k in range(3)))


def preserve_parent(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world


def pivot(name, parent, position):
    obj = bpy.data.objects.new('ANIM_' + name, None)
    bpy.context.collection.objects.link(obj)
    obj.parent = parent
    obj.location = position
    obj.rotation_mode = 'XYZ'
    obj.empty_display_type = 'PLAIN_AXES'
    obj.empty_display_size = .09
    bpy.context.view_layer.update()
    return obj


def merge_children(joint):
    """Merge rigid parts by material, preserving UVs and the joint hierarchy."""
    buckets = {}
    for obj in list(joint.children):
        if obj.type == 'MESH':
            key = tuple(m.name for m in obj.data.materials)
            buckets.setdefault(key, []).append(obj)
    for i, parts in enumerate(buckets.values()):
        if len(parts) < 2:
            continue
        names = [p.name for p in parts]
        bpy.ops.object.select_all(action='DESELECT')
        for part in parts:
            part.select_set(True)
        bpy.context.view_layer.objects.active = parts[0]
        bpy.ops.object.join()
        obj = bpy.context.object
        obj.name = joint.name + '_material_' + str(i)
        obj['source_parts'] = names


def rig_model(asset, root, meshes):
    lo, hi = bounds(meshes)
    h = hi.z - lo.z
    body = pivot('body', root, (0, 0, 0))
    joints = {'body': body}
    if asset == 'mario-body':
        for s, side in [(-1, 'left'), (1, 'right')]:
            joints[side + '_leg'] = pivot(side + '_leg', body, (s * h * .077, 0, h * .345))
            joints[side + '_arm'] = pivot(side + '_arm', body, (s * h * .115, 0, h * .615))
        joints['head'] = pivot('head', body, (0, 0, h * .67))
        for obj in meshes:
            name = obj.name
            low, high = bounds([obj])
            side = 'left' if (low.x + high.x) < 0 else 'right'
            if name.startswith(('Denim_trouser', 'Trouser_', 'Worn_boot')):
                target = joints[side + '_leg']
            elif name.startswith(('Shirt_relaxed_sleeve', 'Glove_')):
                target = joints[side + '_arm']
            elif name.startswith(('Head_', 'Ear', 'Eye_', 'Blue_', 'Pupil', 'Expressive_', 'Bulbous_', 'Sideburn', 'Moustache_', 'Six_lobed', 'Smile_', 'Worn_cap')):
                target = joints['head']
            else:
                target = body
            preserve_parent(obj, target)
    elif asset == 'goomba':
        for s, side in [(-1, 'left'), (1, 'right')]:
            feet = [o for o in meshes if o.name.startswith('Goomba_foot_' + str(s))]
            low, high = bounds(feet)
            joints[side + '_leg'] = pivot(side + '_leg', body, ((low.x + high.x) / 2, (low.y + high.y) / 2, high.z * .7))
        for obj in meshes:
            side = 'left' if '_-1' in obj.name else 'right'
            preserve_parent(obj, joints[side + '_leg'] if 'Goomba_foot_' in obj.name else body)
    elif asset.startswith('koopa'):
        for s, side in [(-1, 'left'), (1, 'right')]:
            joints[side + '_leg'] = pivot(side + '_leg', body, (s * h * .13, 0, h * .25))
            joints[side + '_arm'] = pivot(side + '_arm', body, (s * h * .145, -h * .014, h * .56))
        joints['head'] = pivot('head', body, (0, -h * .06, h * .59))
        for obj in meshes:
            name = obj.name
            side = 'left' if '_-1' in name else 'right'
            if name.startswith(('Koopa_leg_', 'Koopa_foot_')):
                target = joints[side + '_leg']
            elif name.startswith(('Koopa_arm_', 'Koopa_hand_', 'Koopa_finger_')):
                target = joints[side + '_arm']
            elif name.startswith(('Koopa_neck', 'Koopa_cranium', 'Koopa_muzzle', 'Koopa_eye', 'Koopa_pupil', 'Koopa_upper_', 'Koopa_nostril', 'Koopa_mouth')):
                target = joints['head']
            else:
                target = body
            preserve_parent(obj, target)
    else:
        # The existing head has a circular mouth, not separate anatomical jaws.
        # Preserve that mesh and animate a compressing snap plus head/leaf motion.
        # This is explicitly a rigid shape approximation, not a weighted jaw rig.
        joints['head'] = pivot('head', body, (0, 0, h * .69))
        for s, side in [(-1, 'left'), (1, 'right')]:
            joints[side + '_leaf'] = pivot(side + '_leaf', body, (0, 0, h * (.18 + s * .02)))
        for obj in meshes:
            if obj.name.startswith('Leaf_'):
                target = joints['left_leaf' if 'Leaf_-1' in obj.name else 'right_leaf']
            else:
                target = body if obj.name.startswith('Curved_green_stem') else joints['head']
            preserve_parent(obj, target)
    for obj in list(root.children_recursive):
        if obj.type == 'EMPTY' and obj not in joints.values() and not obj.children:
            bpy.data.objects.remove(obj, do_unlink=True)
    for joint in joints.values():
        merge_children(joint)
    bind = {name: (o.location.copy(), o.rotation_euler.copy(), o.scale.copy()) for name, o in joints.items()}
    return {'asset': asset, 'root': root, 'joints': joints, 'bind': bind, 'height': h, 'bounds': [list(lo), list(hi)]}


def reset(rig):
    for name, obj in rig['joints'].items():
        loc, rot, scale = rig['bind'][name]
        obj.location = loc
        obj.rotation_euler = rot
        obj.scale = scale


def pose(rig, clip, t):
    reset(rig)
    j = rig['joints']; h = rig['height']; asset = rig['asset']
    wave = math.sin(TAU * t)
    ease = t * t * (3 - 2 * t)
    if clip == 'idle':
        j['body'].scale.z = 1 + .008 * math.sin(TAU * t)
        if 'head' in j:
            j['head'].rotation_euler.z = .018 * math.sin(TAU * t)
    elif clip in ('walk', 'run'):
        strength = .64 if clip == 'run' else (.48 if asset == 'mario-body' else .38)
        for side, sign in [('left', 1), ('right', -1)]:
            j[side + '_leg'].rotation_euler.x = wave * strength * sign
            if side + '_arm' in j:
                j[side + '_arm'].rotation_euler.x = -wave * strength * sign * 1.25
        j['body'].rotation_euler.y = .045 * wave
        if 'head' in j:
            j['head'].rotation_euler.y = -.035 * wave
        # Plant each rigid shoe at or above its source bind floor.
        bpy.context.view_layer.update()
        for side, sign in [('left', 1), ('right', -1)]:
            limb = j[side + '_leg']
            low, _ = bounds(list(limb.children_recursive))
            lift = max(0, wave * sign) * h * (.025 if clip == 'run' else .012)
            limb.location.z += max(0, -low.z) + lift
    elif clip in ('jump-rise', 'jump-fall'):
        rising = clip == 'jump-rise'
        angles = {'left_leg': -.62 if rising else -.24,
                  'right_leg': .35 if rising else .22,
                  'left_arm': -1.10 if rising else -.52,
                  'right_arm': -.75 if rising else -.36}
        for name, angle in angles.items():
            j[name].rotation_euler.x = angle * ease
        j['head'].rotation_euler.x = (-.08 if rising else .08) * ease
    elif clip == 'death':
        for name in ('left_arm', 'right_arm'):
            j[name].rotation_euler.x = -.95 * ease
            j[name].rotation_euler.y = (-.48 if name.startswith('left') else .48) * ease
        j['left_leg'].rotation_euler.x = -.25 * ease
        j['right_leg'].rotation_euler.x = .22 * ease
        j['head'].rotation_euler.x = -.18 * ease
    elif clip == 'squash':
        j['body'].scale = (1 + .24 * ease, 1 + .19 * ease, 1 - .78 * ease)
    elif clip == 'shell':
        j['head'].scale = (1 - .999 * ease,) * 3
        j['head'].location.z -= h * .25 * ease
        for name in ('left_leg', 'right_leg', 'left_arm', 'right_arm'):
            j[name].scale = (1 - .999 * ease,) * 3
            j[name].location.z = rig['bind'][name][0].z + (h * .40 - rig['bind'][name][0].z) * ease
        j['body'].location.z = -h * .14 * ease
        j['body'].scale.z = 1 - .22 * ease
    elif clip == 'bite':
        snap = max(0, math.sin(TAU * t)) ** 4
        j['head'].scale.z = 1 - .38 * snap
        j['head'].rotation_euler.x = -.22 * snap
        j['head'].location.y -= h * .035 * snap
        j['left_leaf'].rotation_euler.y = -.10 * math.sin(TAU * t)
        j['right_leaf'].rotation_euler.y = .10 * math.sin(TAU * t)


def author_clips(rig):
    for clip, frames, loop in CLIPS[rig['asset']]:
        for obj in rig['joints'].values():
            obj.animation_data_create()
            for track in obj.animation_data.nla_tracks:
                track.mute = True
            action = bpy.data.actions.new(rig['asset'] + '__' + clip + '__' + obj.name)
            obj.animation_data.action = action
        for frame in range(frames + 1):
            # Pose calculations operate on explicit transforms. No NLA evaluation
            # may overwrite these between bound checks and key insertion.
            pose(rig, clip, frame / frames)
            for obj in rig['joints'].values():
                for prop in ('location', 'rotation_euler', 'scale'):
                    obj.keyframe_insert(prop, frame=frame + 1)
        for obj in rig['joints'].values():
            action = obj.animation_data.action
            action['clip'] = clip
            action['loop'] = loop
            # Linear sampling avoids extrapolated overshoot at planted contacts.
            for layer in action.layers:
                for strip in layer.strips:
                    for bag in strip.channelbags:
                        for curve in bag.fcurves:
                            for key in curve.keyframe_points:
                                key.interpolation = 'LINEAR'
            track = obj.animation_data.nla_tracks.new()
            track.name = clip
            track.strips.new(clip, 1, action)
            track.mute = True
            obj.animation_data.action = None
        reset(rig)
    for obj in rig['joints'].values():
        # Exporter discovers these same-name tracks and combines their channels.
        for track in obj.animation_data.nla_tracks:
            track.mute = False
    reset(rig)


def glb_json(path):
    raw = path.read_bytes()
    length = struct.unpack_from('<I', raw, 12)[0]
    return json.loads(raw[20:20 + length])


def export(rig, path):
    objs = [rig['root']] + list(rig['root'].children_recursive)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objs:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = rig['root']
    # Tracks are unmuted for discovery; setting frame zero keeps the bind pose.
    bpy.context.scene.frame_set(0)
    reset(rig)
    bpy.ops.export_scene.gltf(filepath=str(path), export_format='GLB', use_selection=True,
        export_extras=True, export_materials='EXPORT', export_image_format='AUTO',
        export_yup=True, export_animations=True, export_animation_mode='NLA_TRACKS',
        export_force_sampling=True, export_frame_range=False, export_anim_slide_to_zero=True)
    data = glb_json(path)
    names = {a['name'] for a in data.get('animations', [])}
    expected = {c[0] for c in CLIPS[rig['asset']]}
    assert names == expected, (rig['asset'], names, expected)
    assert all('uri' not in im for im in data.get('images', [])), 'External image reference'
    for obj in rig['joints'].values():
        for track in obj.animation_data.nla_tracks:
            track.mute = True
    reset(rig)
    lo, hi = bounds([o for o in rig['root'].children_recursive if o.type == 'MESH'])
    error = max(abs(actual - expected) for a, b in zip([list(lo), list(hi)], rig['bounds']) for actual, expected in zip(a, b))
    assert error < .0001, ('Bind bounds changed', error)
    return {'asset_id': rig['asset'], 'path': 'models/' + path.name,
        'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size,
        'bindBoundsBlender': rig['bounds'], 'bindBoundsMaxError': error,
        'movingParts': list(rig['joints']), 'meshCount': len(data.get('meshes', [])),
        'materialCount': len(data.get('materials', [])), 'embeddedImages': len(data.get('images', [])),
        'clips': [{'name': a['name'], 'channels': len(a['channels']),
            'duration': max(data['accessors'][s['input']]['max'][0] for s in a['samplers']),
            'loop': dict((name, loop) for name, frames, loop in CLIPS[rig['asset']])[a['name']]}
            for a in data['animations']],
        'limitations': ['Rigid part transforms; no skinned deformation or facial rig'] +
            (['Bite uses head compression; original model has no separate jaw mesh'] if rig['asset'] == 'piranha-plant' else [])}


def contact_sheet(rigs, out, samples):
    # Snapshot evaluated authored poses without touching exported files.
    stages = []
    cols = 4
    for row, rig in enumerate(rigs):
        states = [('idle', 0), ('walk', .25), ('walk', .75),
                  ('jump-rise', 1) if rig['asset'] == 'mario-body' else
                  ('squash', 1) if rig['asset'] == 'goomba' else
                  ('shell', 1) if rig['asset'].startswith('koopa') else ('bite', .25)]
        if rig['asset'] == 'piranha-plant':
            states = [('idle', 0), ('bite', .125), ('bite', .25), ('bite', .75)]
        for col, (clip, t) in enumerate(states):
            pose(rig, clip, t)
            bpy.context.view_layer.update()
            offset = Vector(((col - 1.5) * 2.50, (2 - row) * 3.65, 0))
            scale = 1.65 / rig['height']
            for source in list(rig['root'].children_recursive):
                if source.type != 'MESH':
                    continue
                obj = bpy.data.objects.new('Proof_' + source.name, source.data.copy())
                bpy.context.collection.objects.link(obj)
                obj.matrix_world = source.matrix_world.copy()
                obj.location = obj.location * scale + offset
                obj.scale *= scale
                stages.append(obj)
            font = bpy.data.curves.new('Pose label', 'FONT')
            font.body = f"{rig['asset']} / {clip}"
            font.align_x = 'CENTER'; font.size = .115
            obj = bpy.data.objects.new(font.name, font)
            bpy.context.collection.objects.link(obj)
            obj.location = offset + Vector((0, -.72, .025))
            obj.rotation_euler = (math.pi / 2, 0, 0)
            ink = bpy.data.materials.get('Proof ink') or bpy.data.materials.new('Proof ink')
            ink.use_nodes = True
            ink.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.012, .025, .022, 1)
            font.materials.append(ink)
            stages.append(obj)
        reset(rig)
        for obj in [rig['root']] + list(rig['root'].children_recursive):
            obj.hide_render = True
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.035))
    mat = bpy.data.materials.new('Proof floor'); mat.diffuse_color = (.25, .30, .28, 1)
    bpy.context.object.data.materials.append(mat)
    center = Vector((0, 0, .65))
    bpy.ops.object.camera_add(location=(1.3, -19, 19))
    cam = bpy.context.object
    cam.rotation_euler = (center - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.data.type = 'ORTHO'
    bpy.context.scene.camera = cam
    bpy.context.view_layer.update()
    inv = cam.matrix_world.inverted()
    points = [inv @ (o.matrix_world @ Vector(c)) for o in stages for c in o.bound_box]
    lx, hx = min(v.x for v in points), max(v.x for v in points)
    ly, hy = min(v.y for v in points), max(v.y for v in points)
    cam.location += cam.rotation_euler.to_matrix() @ Vector(((lx + hx) / 2, (ly + hy) / 2, 0))
    # AUTO sensor fitting switches axis for a portrait render.
    aspect = 1600 / 1800
    cam.data.ortho_scale = max(hx - lx, hy - ly, (hy - ly) * aspect, (hx - lx) / aspect) * 1.10
    for pos, power, color in [((-6, -9, 12), 2400, (1, .88, .72)), ((8, 1, 10), 1800, (.73, .85, 1)), ((0, 8, 12), 2200, (1, 1, .9))]:
        bpy.ops.object.light_add(type='AREA', location=pos)
        light = bpy.context.object; light.data.energy = power; light.data.shape = 'DISK'; light.data.size = 6; light.data.color = color
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'; scene.cycles.samples = samples; scene.cycles.use_denoising = True
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 4
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.25, .29, .31, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .4
    scene.render.resolution_x = 1600; scene.render.resolution_y = 1800; scene.render.resolution_percentage = 100
    scene.render.filepath = str(out / 'pose-contact-sheet.png')
    bpy.ops.render.render(write_still=True)


def main():
    p = argparse.ArgumentParser(); p.add_argument('--root', type=Path, required=True)
    p.add_argument('--assets', nargs='*', default=list(SOURCES)); p.add_argument('--samples', type=int, default=24)
    p.add_argument('--no-render', action='store_true')
    p.add_argument('--render-only', action='store_true')
    a = p.parse_args(sys.argv[sys.argv.index('--') + 1:])
    base = a.root.resolve() / 'outputs/smb3-photoreal'
    out = base / 'animated'; (out / 'models').mkdir(parents=True, exist_ok=True)
    if a.render_only:
        bpy.ops.wm.open_mainfile(filepath=str(out / 'animated-library.blend'))
        manifest = json.loads((out / 'manifest.json').read_text())
        rigs = []
        for entry in manifest['assets']:
            root = bpy.data.objects[entry['asset_id']]
            root.location = (0, 0, 0)
            joints = {o.name.removeprefix('ANIM_').split('.')[0]: o for o in root.children_recursive if o.type == 'EMPTY' and o.name.startswith('ANIM_')}
            for obj in joints.values():
                for track in obj.animation_data.nla_tracks:
                    track.mute = True
            bind = {name: (o.location.copy(), o.rotation_euler.copy(), o.scale.copy()) for name, o in joints.items()}
            rigs.append({'asset': entry['asset_id'], 'root': root, 'joints': joints, 'bind': bind, 'height': entry['bindBoundsBlender'][1][2] - entry['bindBoundsBlender'][0][2]})
        contact_sheet(rigs, out, a.samples)
        return
    bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
    bpy.context.scene.render.fps = FPS; bpy.context.scene.frame_start = 1; bpy.context.scene.frame_end = 61
    rigs, entries = [], []
    for asset in a.assets:
        src = base / 'families' / SOURCES[asset] / 'models' / (asset + '.glb')
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(src))
        objs = sorted(set(bpy.data.objects) - before, key=lambda obj: obj.name)
        root = next(o for o in objs if o.parent not in objs)
        meshes = [o for o in objs if o.type == 'MESH']
        rig = rig_model(asset, root, meshes)
        author_clips(rig)
        entry = export(rig, out / 'models' / (asset + '.glb'))
        entry['sourcePath'] = str(src.relative_to(a.root.resolve()))
        entry['sourceSHA256'] = hashlib.sha256(src.read_bytes()).hexdigest()
        entries.append(entry); rigs.append(rig)
        print('ANIMATED_ASSET_READY ' + json.dumps(entry), flush=True)
        (out / 'manifest.json').write_text(json.dumps({'fps': FPS, 'method': 'In-place rigid part NLA clips', 'assets': entries}, indent=2))
    for i, rig in enumerate(rigs):
        rig['root'].location.x = i * 2.5
        preview = 'bite' if rig['asset'] == 'piranha-plant' else 'walk'
        for obj in rig['joints'].values():
            for track in obj.animation_data.nla_tracks:
                track.mute = track.name != preview
                # A two-second inspection loop; the underlying action retains
                # its exact authored duration and the GLBs are already exported.
                if track.name == preview:
                    for strip in track.strips:
                        strip.repeat = 60 / (strip.action_frame_end - strip.action_frame_start)
    for image in bpy.data.images:
        if image.source == 'FILE' and not image.packed_file:
            image.pack()
    bpy.ops.wm.save_as_mainfile(filepath=str(out / 'animated-library.blend'))
    for rig in rigs:
        rig['root'].location.x = 0
        for obj in rig['joints'].values():
            for track in obj.animation_data.nla_tracks:
                track.mute = True
    if not a.no_render:
        contact_sheet(rigs, out, a.samples)
    (out / 'README.md').write_text('''# Character Animation Library

These are real named glTF animation clips and matching editable Blender NLA tracks.
The authored source meshes, UVs, and embedded material maps are retained; rigid parts
are grouped by material under transform pivots. The original family models are unchanged.

Clips are in-place. Runtime position, collision, facing, state selection and timing must
come from the ROM. Loop idle/walk/run/bite; clamp one-shot pose clips at their final frame.
The manifest records durations, source hashes, bounds, and channel counts.

Open `animated-library.blend` and press Play: walking and biting tracks are enabled
and repeated over the inspection timeline. To inspect another clip, mute the current
track and unmute the same new track name on each of that character's pivots.

This is rigid part animation, not skinning, mocap, or a facial animation rig.
The Piranha bite compresses the existing continuous head; it has no separate jaw mesh.
`pose-contact-sheet.png` shows evaluated authored poses for visual inspection.

Rebuild from the project root:

```sh
/Volumes/Blender/Blender.app/Contents/MacOS/Blender -b -t 4 --python-exit-code 1 --python outputs/smb3-photoreal/tools/animate_characters.py -- --root "$PWD"
```
''')


if __name__ == '__main__':
    main()
