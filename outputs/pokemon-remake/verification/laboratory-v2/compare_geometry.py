import bpy,json
from pathlib import Path
from mathutils.kdtree import KDTree
BASE=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent

def read(name):
 bpy.ops.wm.read_factory_settings(use_empty=True);bpy.ops.import_scene.gltf(filepath=str(BASE/f'models/{name}.glb'))
 return {o.name:[o.matrix_world@v.co for v in o.data.vertices] for o in bpy.context.scene.objects if o.type=='MESH'}
a=read('laboratory-v1');b=read('laboratory-v2');ap=[v for vs in a.values()for v in vs];bp=[v for name,vs in b.items()if 'ClosedRedVentCap' not in name for v in vs];tree=KDTree(len(bp))
for i,v in enumerate(bp):tree.insert(v,i)
tree.balance();deviations=[tree.find(v)[2] for v in ap]
report={'v1Vertices':len(ap),'v2BaseVertices':len(bp),'maximumOriginalVertexDisplacement':max(deviations),'allOriginalVerticesPreservedWithin1e-6':max(deviations)<1e-6,'baseObjectsV2':list(b),'v1Bounds':[[min(p[i]for p in ap)for i in range(3)],[max(p[i]for p in ap)for i in range(3)]],'v2Bounds':[[min(p[i]for vs in b.values()for p in vs)for i in range(3)],[max(p[i]for vs in b.values()for p in vs)for i in range(3)]]}
(OUT/'geometry-comparison.json').write_text(json.dumps(report,indent=2)+'\n');assert report['allOriginalVerticesPreservedWithin1e-6'];print('GEOMETRY',json.dumps(report))
