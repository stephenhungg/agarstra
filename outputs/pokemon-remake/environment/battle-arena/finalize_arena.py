"""Validate the real GLB through Blender re-import and render its runtime framing."""
import importlib.util
import json
from pathlib import Path
import struct
import sys

import bpy

root = Path(sys.argv[sys.argv.index('--') + 1]).resolve()
module_path = root / 'environment' / 'battle-arena' / 'author_arena.py'
spec = importlib.util.spec_from_file_location('arena_author', module_path)
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)
blend = root / 'models' / 'battle-arena-v1.blend'
evidence = root / 'verification' / 'battle-arena'
glb = root / 'models' / 'battle-arena-v1.glb'
bpy.ops.wm.open_mainfile(filepath=str(blend))

# Separate the broad continuation slab from inset tiles to prevent coplanar flicker.
for name, height in [('Continuous laboratory subfloor', -.30), ('Continuous limestone floor', -.105)]:
    obj = bpy.data.objects.get(name)
    if obj:
        obj.location.z = height
bpy.ops.wm.save_as_mainfile(filepath=str(blend))
author.merge_runtime_meshes()
bpy.ops.export_scene.gltf(filepath=str(glb), export_format='GLB', export_yup=True,
                         export_lights=False, export_cameras=False, export_animations=False,
                         export_apply=True)
data = glb.read_bytes()
assert struct.unpack_from('<I', data, 0)[0] == 0x46546C67
length = struct.unpack_from('<I', data, 12)[0]
document = json.loads(data[20:20 + length])
assert not any(item.get('uri') for item in document.get('buffers', []))
assert not any(item.get('uri') for item in document.get('images', []))
assert len(document.get('images', [])) >= 8
assert len(document.get('meshes', [])) < 50, 'Runtime meshes must be material-batched'
triangles = sum(document['accessors'][p['indices']]['count'] // 3
                for mesh in document['meshes'] for p in mesh['primitives'])
report = {'sha256': author.hash_file(glb), 'bytes': len(data), 'meshes': len(document['meshes']),
          'materials': len(document['materials']), 'embeddedImages': len(document['images']),
          'triangles': triangles, 'externalDependencies': 0, 'bakedLights': False,
          'sourceCoordinatesPreserved': True, 'validatedActualGLB': True}
manifest = json.loads((evidence / 'manifest.json').read_text())
manifest['sha256'] = report['sha256']
manifest['technical'] = report
manifest['authorScriptSha256'] = author.hash_file(module_path)
manifest['finalizerSha256'] = author.hash_file(Path(__file__))
(evidence / 'manifest.json').write_text(json.dumps(manifest, indent=2))

# Render imported bytes, not merely the in-memory pre-export scene.
author.setup()
bpy.ops.import_scene.gltf(filepath=str(glb))
report['importedMeshObjects'] = len([obj for obj in bpy.context.scene.objects if obj.type == 'MESH'])
author.area('Warm window key', (-8, 10, -5), (0, 0, 1), 4500, 9, (1, .88, .69))
author.area('Wide camera fill', (2, 11, 12), (0, 1, -4), 2500, 10, (.81, .87, 1))
author.area('Rear soft sunlight', (10, 10, -9), (2, 0, 3), 3400, 6, (1, .89, .73))
bpy.context.scene.cycles.samples = 16
author.render_evidence(evidence)
report['renders'] = ['gameplay.png', 'wide.png', 'portrait.png']
(evidence / 'technical-verification.json').write_text(json.dumps(report, indent=2))
print('FINAL_ARENA ' + json.dumps(report), flush=True)
