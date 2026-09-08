"""Export edited registered Blender objects to the runtime replacement GLB directory.
Run inside Blender: --background --python export_replacements.py -- --registry FILE --output DIR [--asset-id ID ...]
The .blend is read but never saved. Catalog translations are removed only during export.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import bpy
from mathutils import Vector


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-id', action='append', dest='asset_ids', help='Repeat for multiple registered asset IDs; default: all runtime 8x8 tiles.')
    parser.add_argument('--registry', type=Path, default=Path(__file__).resolve().parent.parent / 'blender' / 'replacement-registry.json')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else [])
    registry_path = args.registry.resolve()
    registry = json.loads(registry_path.read_text())
    entries = {entry['assetId']: entry for entry in registry['entries']}
    ids = list(dict.fromkeys(args.asset_ids)) if args.asset_ids else [key for key, entry in entries.items() if entry['width'] == 8 and entry['height'] == 8 and entry['source'].get('sourceIdentity')]
    unknown = [key for key in ids if key not in entries]
    if unknown:
        raise ValueError('Unregistered asset IDs: ' + ', '.join(unknown))
    if not ids:
        raise ValueError('No registered runtime assets selected.')
    blend_path = registry_path.parent / 'rom-source-assets.blend'
    if not bpy.data.filepath:
        bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    elif Path(bpy.data.filepath).resolve() != blend_path.resolve():
        raise ValueError(f'Loaded {bpy.data.filepath}; expected {blend_path}. Use its matching registry.')
    objects = {}
    for obj in bpy.data.objects:
        key = obj.get('asset_id')
        if key in entries:
            if key in objects:
                raise ValueError('Duplicate asset_id custom property: ' + key)
            objects[key] = obj
    missing = [key for key in ids if key not in objects]
    if missing:
        raise ValueError('Registered objects are missing from the .blend: ' + ', '.join(missing))
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    selected_before = list(bpy.context.selected_objects)
    active_before = bpy.context.view_layer.objects.active
    exported = []
    try:
        for key in ids:
            obj = objects[key]
            entry = entries[key]
            if entry.get('origin') != 'top-left':
                raise ValueError('Unsupported registered origin for ' + key)
            if Path(key).name != key or '/' in key or '\\' in key:
                raise ValueError('Asset ID is not a safe output filename: ' + key)
            members = [obj, *obj.children_recursive]
            matrix_before = obj.matrix_world.copy()
            visibility = [(item, item.hide_get(), item.hide_viewport, item.hide_render) for item in members]
            bpy.ops.object.select_all(action='DESELECT')
            try:
                # Preserve local geometry, scale, rotation, modifiers and top-left origin.
                # Only strip the catalog's world-space display translation.
                matrix = obj.matrix_world.copy()
                matrix.translation = Vector((0, 0, 0))
                obj.matrix_world = matrix
                for item, _, _, _ in visibility:
                    item.hide_viewport = False
                    item.hide_render = False
                    item.hide_set(False)
                    item.select_set(True)
                bpy.context.view_layer.objects.active = obj
                bpy.context.view_layer.update()
                temporary = output / ('.' + key + '.tmp.glb')
                result = bpy.ops.export_scene.gltf(filepath=str(temporary), export_format='GLB', use_selection=True, export_extras=True, export_materials='EXPORT', export_yup=True, export_apply=True)
                if 'FINISHED' not in result or not temporary.is_file():
                    raise RuntimeError('glTF export did not finish for ' + key)
                destination = output / (key + '.glb')
                os.replace(temporary, destination)
                exported.append({'assetId': key, 'file': destination.name, 'sha256': hashlib.sha256(destination.read_bytes()).hexdigest(), 'origin': 'top-left', 'unitsPerPixel': entry['unitsPerPixel'], 'sourceIdentity': entry['source'].get('sourceIdentity'), 'sourceRgbaSHA256': entry.get('sourceRgbaSHA256')})
                print('EXPORTED', key, str(destination), flush=True)
            finally:
                obj.matrix_world = matrix_before
                for item, hidden, viewport, render in visibility:
                    item.select_set(False)
                    item.hide_viewport = viewport
                    item.hide_render = render
                    item.hide_set(hidden)
    finally:
        for obj in selected_before:
            obj.select_set(True)
        bpy.context.view_layer.objects.active = active_before
        bpy.context.view_layer.update()
    report = {'schemaVersion': 1, 'blend': str(blend_path), 'registry': str(registry_path), 'romSHA256': registry['romSHA256'], 'count': len(exported), 'entries': exported, 'blendSaved': False}
    (output / 'replacement-export.json').write_text(json.dumps(report, indent=2))
    print('EXPORT_COMPLETE', len(exported), 'assets; .blend not saved', flush=True)


if __name__ == '__main__':
    main()
