"""Reimport the actual tree GLB and render it at the runtime's 3.8 height."""
import bpy,json,hashlib,struct
from pathlib import Path
from mathutils import Vector
ROOT=Path('/Users/stephenhung/Documents/GitHub/agarstra')
OUT=ROOT/'outputs/pokemon-remake/verification/tree-v2'
GLB=ROOT/'outputs/pokemon-remake/models/tree-v2.glb'
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=str(GLB))
assets=[o for o in bpy.context.scene.objects if o.type=='MESH']
points=[o.matrix_world@v.co for o in assets for v in o.data.vertices]
lo=Vector([min(p[i] for p in points) for i in range(3)])
hi=Vector([max(p[i] for p in points) for i in range(3)])
assert abs(hi.z-lo.z-3.8)<1e-5
blob=GLB.read_bytes();length=struct.unpack_from('<I',blob,12)[0];g=json.loads(blob[20:20+length])
report={'status':'candidate; pending image review','glbSHA256':hashlib.sha256(blob).hexdigest(),'bytes':len(blob),'meshCount':len(assets),'materialCount':len(g['materials']),'triangles':sum(len(p.vertices)-2 for o in assets for p in o.data.polygons),'boundsBlender':{'min':list(lo),'max':list(hi)},'dimensions':list(hi-lo),'gltfUp':'+Y','origin':'grounded trunk root at origin; canopy is intentionally asymmetric','images':[{'name':im.name,'size':list(im.size),'packed':bool(im.packed_file)} for im in bpy.data.images if im.name not in ['Render Result','Viewer Node']],'gltfMaterials':g['materials'],'externalResources':[x.get('uri') for x in g.get('images',[])+g.get('buffers',[]) if x.get('uri') and not x['uri'].startswith('data:')],'actualExportReimported':True}
assert not report['externalResources'] and report['materialCount']==2 and report['triangles']<55000
(OUT/'export-inspection.json').write_text(json.dumps(report,indent=2))
scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.render.resolution_x=scene.render.resolution_y=1100;scene.render.resolution_percentage=100
scene.world=bpy.data.worlds.new('Neutral daylight');scene.world.use_nodes=True
scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.65,.72,.8,1);scene.world.node_tree.nodes['Background'].inputs[1].default_value=.45
for name,loc,power,size in [('Key',(-4,-6,9),1800,6),('Fill',(4,3,7),900,5)]:
    d=bpy.data.lights.new(name,'AREA');d.energy=power;d.size=size;o=bpy.data.objects.new(name,d);scene.collection.objects.link(o);o.location=loc;o.rotation_euler=(Vector((0,0,1.9))-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.012));floor=bpy.context.object;floor.name='Review floor';mat=bpy.data.materials.new('Neutral ground');mat.diffuse_color=(.25,.28,.24,1);floor.data.materials.append(mat)
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO';camera.data.ortho_scale=5.55;scene.view_settings.view_transform='AgX'
for name,position,target in [('front',(8,-11,7),(0,0,1.9)),('back',(-8,11,7),(0,0,1.9)),('gameplay',(8,-11,13),(0,0,1.75))]:
    camera.location=position;camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
bpy.context.preferences.filepaths.save_version=0;bpy.ops.file.pack_all();bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'actual-export-review.blend'))
# A fixed-height comparison is diagnostic only, not an assembled-town approval.
for o in assets:o.location.x+=2.1
before=set(bpy.data.objects)
bpy.ops.import_scene.gltf(filepath=str(ROOT/'outputs/pokemon-remake/environment/tree/tree.glb'))
v1=[o for o in bpy.data.objects if o not in before and o.type=='MESH']
for o in v1:
    world=o.matrix_world.copy();o.parent=None;o.matrix_world=world
    o.scale*=.76;o.location.x-=2.1
camera.data.ortho_scale=10.4;camera.location=(1,-16,10);camera.rotation_euler=(Vector((0,0,1.8))-camera.location).to_track_quat('-Z','Y').to_euler()
scene.render.filepath=str(OUT/'comparison-v1-left-v2-right.png');bpy.ops.render.render(write_still=True)
print('EXPORT_VERIFIED',json.dumps({k:v for k,v in report.items() if k!='gltfMaterials'}))
