"""Blender 4.5 helpers for source-inspired PBR assets.

Coordinates: Blender Z up, front -Y, right +X. glTF export converts to Y up/front +Z.
Materials are UV-based and repeatable. Cycles bakes base color, roughness and tangent
normal to PNGs; the returned material contains only glTF-compatible image nodes.

Example inside Blender:
    import pbr_common as pbr
    paint = pbr.material('yellow_enamel', resolution=512, cache_dir='./textures')
    block = pbr.bevel_cube('QuestionBlock', (1, .65, 1), (0, 0, .5), paint)
    pbr.export_glb('question.glb', [block])
    print(pbr.inspect_glb('question.glb'))

No scene reset, camera, normalization, or file overwrite outside requested output/cache.
Bake each family once and reuse its material. A shared on-disk cache supports workers.
"""
import bpy, math, json, hashlib, os, struct
from pathlib import Path
from mathutils import Vector

RECIPES = {
    'worn_brass': {'color':'B28A43','roughness':.38,'metallic':.86,'bump':.018,'scale':7},
    'yellow_enamel': {'color':'E9B12E','roughness':.30,'metallic':.18,'bump':.009,'scale':11,'coat':.35},
    'green_metal': {'color':'287C4A','roughness':.31,'metallic':.28,'bump':.010,'scale':10,'coat':.30},
    'brick': {'color':'A75C3D','roughness':.87,'metallic':0,'bump':.035,'scale':6},
    'stone': {'color':'A6A38D','roughness':.82,'metallic':0,'bump':.026,'scale':8},
    'soil': {'color':'604832','roughness':.98,'metallic':0,'bump':.046,'scale':7},
    'leaf': {'color':'487F33','roughness':.68,'metallic':0,'bump':.012,'scale':8},
    'cloth': {'color':'376A97','roughness':.88,'metallic':0,'bump':.014,'scale':8},
    'leather': {'color':'58382A','roughness':.62,'metallic':0,'bump':.018,'scale':12},
}
ALIASES = {'painted_green_metal':'green_metal','brass':'worn_brass','enamel':'yellow_enamel','foliage':'leaf','fabric':'cloth'}
_material_cache = {}

def _linear(hex_color):
    if isinstance(hex_color, (tuple,list)):
        rgb=hex_color[:3]
    else:
        text=hex_color.lstrip('#');rgb=[int(text[i:i+2],16)/255 for i in (0,2,4)]
    return tuple(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb)

def _socket(node, name, value):
    if name in node.inputs: node.inputs[name].default_value=value

def _procedural(kind, recipe, name):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;n=mat.node_tree.nodes;links=mat.node_tree.links;n.clear()
    output=n.new('ShaderNodeOutputMaterial');bsdf=n.new('ShaderNodeBsdfPrincipled');links.new(bsdf.outputs['BSDF'],output.inputs['Surface'])
    _socket(bsdf,'Metallic',recipe['metallic']);_socket(bsdf,'Roughness',recipe['roughness']);_socket(bsdf,'Coat Weight',recipe.get('coat',0));_socket(bsdf,'Coat Roughness',.24)
    uv=n.new('ShaderNodeTexCoord');coarse=n.new('ShaderNodeTexNoise');coarse.inputs['Scale'].default_value=recipe['scale'];coarse.inputs['Detail'].default_value=4;coarse.inputs['Roughness'].default_value=.72;links.new(uv.outputs['UV'],coarse.inputs['Vector'])
    fine=n.new('ShaderNodeTexNoise');fine.inputs['Scale'].default_value=180 if kind=='cloth' else 110;fine.inputs['Detail'].default_value=3;links.new(uv.outputs['UV'],fine.inputs['Vector'])
    ramp=n.new('ShaderNodeValToRGB');base=_linear(recipe['color']);ramp.color_ramp.elements[0].position=.2;ramp.color_ramp.elements[0].color=tuple(v*.70 for v in base)+(1,);ramp.color_ramp.elements[1].position=.83;ramp.color_ramp.elements[1].color=tuple(min(1,v*1.17) for v in base)+(1,);links.new(coarse.outputs['Fac'],ramp.inputs['Fac']);links.new(ramp.outputs['Color'],bsdf.inputs['Base Color'])
    rough=n.new('ShaderNodeMapRange');rough.inputs['From Min'].default_value=.15;rough.inputs['From Max'].default_value=.85;rough.inputs['To Min'].default_value=max(.12,recipe['roughness']-.12);rough.inputs['To Max'].default_value=min(1,recipe['roughness']+.12);links.new(fine.outputs['Fac'],rough.inputs['Value']);links.new(rough.outputs['Result'],bsdf.inputs['Roughness'])
    height=fine.outputs['Fac']
    if kind=='cloth':
        waves=[]
        for direction in ('X','Y'):
            wave=n.new('ShaderNodeTexWave');wave.wave_type='BANDS';wave.bands_direction=direction;wave.inputs['Scale'].default_value=70;wave.inputs['Distortion'].default_value=2;links.new(uv.outputs['UV'],wave.inputs['Vector']);waves.append(wave)
        mul=n.new('ShaderNodeMath');mul.operation='MULTIPLY';links.new(waves[0].outputs['Fac'],mul.inputs[0]);links.new(waves[1].outputs['Fac'],mul.inputs[1]);height=mul.outputs[0]
    bump=n.new('ShaderNodeBump');bump.inputs['Strength'].default_value=.45;bump.inputs['Distance'].default_value=recipe['bump'];links.new(height,bump.inputs['Height']);links.new(bump.outputs['Normal'],bsdf.inputs['Normal'])
    mat.diffuse_color=(*base,1);return mat

def _image_material(name, recipe, paths):
    mat=bpy.data.materials.new(name);mat.use_nodes=True;nodes=mat.node_tree.nodes;links=mat.node_tree.links;nodes.clear();bsdf=nodes.new('ShaderNodeBsdfPrincipled');out=nodes.new('ShaderNodeOutputMaterial');links.new(bsdf.outputs['BSDF'],out.inputs['Surface'])
    _socket(bsdf,'Metallic',recipe['metallic']);_socket(bsdf,'Coat Weight',recipe.get('coat',0));_socket(bsdf,'Coat Roughness',.24)
    for channel,path in paths.items():
        image=bpy.data.images.load(str(path),check_existing=True);image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color';image.pack();texture=nodes.new('ShaderNodeTexImage');texture.image=image;texture.label=channel;texture.extension='REPEAT'
        if channel=='normal':
            normal=nodes.new('ShaderNodeNormalMap');links.new(texture.outputs['Color'],normal.inputs['Color']);links.new(normal.outputs['Normal'],bsdf.inputs['Normal'])
        else:links.new(texture.outputs['Color'],bsdf.inputs['Base Color' if channel=='basecolor' else 'Roughness'])
    mat['pbr_baked']=True;mat['texture_files']=json.dumps({k:str(v) for k,v in paths.items()});return mat

def bake_material(procedural, recipe, cache_dir, key, resolution=512):
    """Bake a UV-plane swatch in actual Cycles. Cache writes are atomic across workers."""
    cache_dir=Path(cache_dir).resolve();cache_dir.mkdir(parents=True,exist_ok=True);paths={kind:cache_dir/f'{key}-{kind}.png' for kind in ('basecolor','roughness','normal')}
    if all(path.exists() for path in paths.values()):return paths
    scene=bpy.context.scene;old_engine=scene.render.engine;old_samples=scene.cycles.samples;old_device=scene.cycles.device;old_bake={k:getattr(scene.render.bake,k) for k in ('use_pass_direct','use_pass_indirect','use_pass_color','margin','use_selected_to_active','normal_space')};active=bpy.context.view_layer.objects.active;selected=list(bpy.context.selected_objects);objects=[]
    for obj in selected:obj.select_set(False)
    try:
        bpy.ops.mesh.primitive_plane_add(size=1,location=(0,0,-10000));plane=bpy.context.object;objects.append(plane);plane.data.materials.append(procedural);scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=8
        scene.render.bake.use_pass_direct=False;scene.render.bake.use_pass_indirect=False;scene.render.bake.use_pass_color=True;scene.render.bake.margin=8;scene.render.bake.use_selected_to_active=False
        for channel,path in paths.items():
            if path.exists():continue
            image=bpy.data.images.new(f'Bake_{key}_{channel}',width=resolution,height=resolution,alpha=False,float_buffer=False);image.colorspace_settings.name='sRGB' if channel=='basecolor' else 'Non-Color';node=procedural.node_tree.nodes.new('ShaderNodeTexImage');node.image=image;procedural.node_tree.nodes.active=node
            if channel=='normal':scene.render.bake.normal_space='TANGENT'
            bsdf=next(n for n in procedural.node_tree.nodes if n.type=='BSDF_PRINCIPLED');old_metallic=bsdf.inputs['Metallic'].default_value
            if channel=='basecolor':bsdf.inputs['Metallic'].default_value=0
            try:bpy.ops.object.bake(type={'basecolor':'DIFFUSE','roughness':'ROUGHNESS','normal':'NORMAL'}[channel])
            finally:bsdf.inputs['Metallic'].default_value=old_metallic
            temp=path.with_name(f'.{path.stem}-{os.getpid()}.png');image.filepath_raw=str(temp);image.file_format='PNG';image.save();os.replace(temp,path);procedural.node_tree.nodes.remove(node);bpy.data.images.remove(image)
    finally:
        for obj in objects:
            mesh=obj.data;bpy.data.objects.remove(obj,do_unlink=True);bpy.data.meshes.remove(mesh)
        scene.render.engine=old_engine;scene.cycles.samples=old_samples;scene.cycles.device=old_device
        for field,value in old_bake.items():setattr(scene.render.bake,field,value)
        for obj in selected:
            if obj.name in bpy.context.view_layer.objects:obj.select_set(True)
        if active and active.name in bpy.context.view_layer.objects:bpy.context.view_layer.objects.active=active
    return paths

def material(kind, *, name=None, color=None, bake=True, resolution=512, cache_dir=None, **overrides):
    """Reusable material family. Optional color hex + roughness/metallic/bump/scale overrides."""
    kind=ALIASES.get(kind,kind)
    if kind not in RECIPES:raise ValueError(f'Unknown material {kind}; choose {list(RECIPES)}')
    recipe={**RECIPES[kind],**overrides}
    if color is not None:recipe['color']=color
    key=kind+'-'+hashlib.sha256(json.dumps({'recipe':recipe,'resolution':resolution,'version':1},sort_keys=True).encode()).hexdigest()[:12]
    cache_key=(key,bake)
    if cache_key in _material_cache:
        try:
            cached=_material_cache[cache_key]
            if cached.name in bpy.data.materials:return cached
        except ReferenceError:pass
        del _material_cache[cache_key]
    procedural=_procedural(kind,recipe,(name or key)+'_procedural')
    if bake:
        cache_dir=cache_dir or Path(__file__).resolve().parents[1]/'textures'
        paths=bake_material(procedural,recipe,cache_dir,key,resolution);mat=_image_material(name or key,recipe,paths);bpy.data.materials.remove(procedural)
    else:mat=procedural
    mat['pbr_family']=kind;mat['pbr_recipe']=json.dumps(recipe);_material_cache[cache_key]=mat;return mat

def _activate(obj):
    for selected in bpy.context.selected_objects:selected.select_set(False)
    obj.select_set(True);bpy.context.view_layer.objects.active=obj

def uv_smart(obj, angle=66, margin=.025):
    _activate(obj);bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=math.radians(angle),island_margin=margin);bpy.ops.object.mode_set(mode='OBJECT');return obj

def bevel_cube(name,size=(1,1,1),location=(0,0,0),material=None,bevel=.04,segments=3):
    bpy.ops.mesh.primitive_cube_add(size=1,location=location);obj=bpy.context.object;obj.name=name;obj.dimensions=size;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:obj.data.materials.append(material)
    if bevel:
        mod=obj.modifiers.new('Rounded physical edges','BEVEL');mod.width=min(bevel,min(size)*.24);mod.segments=segments;mod.affect='EDGES';bpy.ops.object.modifier_apply(modifier=mod.name)
    uv_smart(obj);return obj

def sphere(name,scale=(.5,.5,.5),location=(0,0,0),material=None,segments=32,rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,radius=1,location=location);obj=bpy.context.object;obj.name=name;obj.scale=scale;bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    if material:obj.data.materials.append(material)
    for p in obj.data.polygons:p.use_smooth=True
    return obj

def mesh(name,vertices,faces,material=None,location=(0,0,0),smooth=False,auto_uv=True):
    data=bpy.data.meshes.new(name);data.from_pydata(vertices,[],faces);data.update();obj=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(obj);obj.location=location
    if material:data.materials.append(material)
    for p in data.polygons:p.use_smooth=smooth
    if auto_uv:uv_smart(obj)
    return obj

def lathe(name,profile,location=(0,0,0),material=None,segments=64):
    """Revolve [(radius,z), ...] about Blender Z. Close profile explicitly for a sealed shape."""
    verts=[(r*math.cos(j*2*math.pi/segments),r*math.sin(j*2*math.pi/segments),z) for r,z in profile for j in range(segments)];faces=[]
    for row in range(len(profile)-1):
        for j in range(segments):k=(j+1)%segments;faces.append((row*segments+j,row*segments+k,(row+1)*segments+k,(row+1)*segments+j))
    return mesh(name,verts,faces,material,location,smooth=True,auto_uv=True)

def tube(name,radius=.5,depth=1,location=(0,0,0),material=None,thickness=.08,segments=64):
    inner=max(.001,radius-thickness);z=depth/2
    return lathe(name,[(inner,-z),(radius,-z),(radius,z),(inner,z),(inner,-z)],location,material,segments)

def leaf(name,length=1,width=.4,location=(0,0,0),material=None,curve=.10,segments=12):
    verts=[]
    for i in range(segments+1):
        t=i/segments;w=width*.5*math.sin(math.pi*t)**.85
        for side in (-1,0,1):verts.append((side*w,-curve*math.sin(math.pi*t)*(1-.35*abs(side)),t*length))
    faces=[]
    for i in range(segments):
        for j in range(2):a=i*3+j;faces.append((a,a+1,a+4,a+3))
    obj=mesh(name,verts,faces,material,location,smooth=True);mod=obj.modifiers.new('Leaf thickness','SOLIDIFY');mod.thickness=.006;return obj

def export_glb(path,objects, *, extras=None):
    path=Path(path).resolve();path.parent.mkdir(parents=True,exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    for obj in objects:
        obj.select_set(True)
        if extras:
            for k,v in extras.items():obj[k]=v if isinstance(v,(str,int,float,bool)) else json.dumps(v)
    if objects:bpy.context.view_layer.objects.active=objects[0]
    bpy.ops.export_scene.gltf(filepath=str(path),export_format='GLB',use_selection=True,export_extras=True,export_apply=True,export_materials='EXPORT',export_image_format='AUTO')
    return inspect_glb(path)

def inspect_glb(path):
    raw=Path(path).read_bytes();magic,version,total=struct.unpack_from('<III',raw,0);assert magic==0x46546C67 and version==2 and total==len(raw);length,kind=struct.unpack_from('<II',raw,12);assert kind==0x4E4F534A;doc=json.loads(raw[20:20+length]);materials=doc.get('materials',[])
    return {'path':str(Path(path).resolve()),'bytes':len(raw),'meshes':len(doc.get('meshes',[])),'materials':len(materials),'images':len(doc.get('images',[])),'embeddedImages':sum('bufferView' in i for i in doc.get('images',[])),'baseColorTextureMaterials':sum('baseColorTexture' in m.get('pbrMetallicRoughness',{}) for m in materials),'roughnessTextureMaterials':sum('metallicRoughnessTexture' in m.get('pbrMetallicRoughness',{}) for m in materials),'normalTextureMaterials':sum('normalTexture' in m for m in materials),'externalImageURIs':[i['uri'] for i in doc.get('images',[]) if 'uri' in i]}
