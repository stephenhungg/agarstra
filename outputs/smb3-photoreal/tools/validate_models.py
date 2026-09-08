#!/usr/bin/env python3
"""Validate GLB exports without conflating valid files with photoreal visual quality.

Usage: python3 validate_models.py models/*.glb --out design/model-validation.json
Optional --spec job.json: familyId, requiredNodeNames, requiredSourceAssetIds.
Optional --review review.json: assetSHA256, approved, reviewer, checks.
--require-photoreal makes unreviewed/visually rejected candidates fail the command.
"""
import argparse,base64,hashlib,itertools,json,math,struct,sys
from pathlib import Path

class Invalid(Exception):pass

def finite(xs):return all(isinstance(v,(int,float)) and math.isfinite(v) for v in xs)
def identity():return [[1 if i==j else 0 for j in range(4)] for i in range(4)]
def mul(a,b):return [[sum(a[i][k]*b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]
def transform(m,p):return [sum(m[i][j]*([*p,1][j]) for j in range(4)) for i in range(3)]
def local(n):
 if 'matrix' in n:
  a=n['matrix']
  if len(a)!=16 or not finite(a):raise Invalid('Invalid node matrix')
  return [[a[j*4+i] for j in range(4)] for i in range(4)]
 t=n.get('translation',[0,0,0]);s=n.get('scale',[1,1,1]);q=n.get('rotation',[0,0,0,1])
 if len(t)!=3 or len(s)!=3 or len(q)!=4 or not finite(t+s+q):raise Invalid('Invalid TRS transform')
 x,y,z,w=q;length=math.sqrt(sum(v*v for v in q))
 if length<1e-12:raise Invalid('Zero-length quaternion')
 x,y,z,w=[v/length for v in q]
 r=[[1-2*y*y-2*z*z,2*x*y-2*z*w,2*x*z+2*y*w],[2*x*y+2*z*w,1-2*x*x-2*z*z,2*y*z-2*x*w],[2*x*z-2*y*w,2*y*z+2*x*w,1-2*x*x-2*y*y]]
 m=identity()
 for i in range(3):
  for j in range(3):m[i][j]=r[i][j]*s[j]
  m[i][3]=t[i]
 return m

def parse_glb(file):
 raw=file.read_bytes()
 if len(raw)<20:raise Invalid('GLB shorter than header and JSON chunk')
 magic,version,length=struct.unpack_from('<4sII',raw)
 if magic!=b'glTF' or version!=2:raise Invalid('Expected glTF 2.0 GLB')
 if length!=len(raw):raise Invalid('Declared GLB length differs from actual file')
 at=12;chunks=[]
 while at<len(raw):
  if at+8>len(raw):raise Invalid('Truncated chunk header')
  size,kind=struct.unpack_from('<II',raw,at);at+=8
  if size%4 or at+size>len(raw):raise Invalid('Invalid chunk alignment or length')
  chunks.append((kind,raw[at:at+size]));at+=size
 if not chunks or chunks[0][0]!=0x4e4f534a:raise Invalid('First GLB chunk must be JSON')
 doc=json.loads(chunks[0][1].rstrip(b'\0 \t\r\n'));blob=next((c for k,c in chunks if k==0x004e4942),b'')
 return raw,doc,blob

def view_bytes(doc,blob,index):
 try:v=doc.get('bufferViews',[])[index]
 except (IndexError,TypeError):raise Invalid('Invalid bufferView reference')
 if v.get('buffer',0)!=0:raise Invalid('External geometry buffers require separate validation')
 off=v.get('byteOffset',0);size=v['byteLength']
 if off<0 or size<0 or off+size>len(blob):raise Invalid('bufferView out of binary bounds')
 return blob[off:off+size]

def position_bounds(doc,blob,index):
 a=doc['accessors'][index]
 if a.get('type')!='VEC3' or a.get('componentType')!=5126:raise Invalid('POSITION must be float VEC3')
 count=a.get('count',0)
 if count<=0:raise Invalid('Empty POSITION accessor')
 values=None
 if 'bufferView' in a:
  v=doc['bufferViews'][a['bufferView']];b=view_bytes(doc,blob,a['bufferView']);stride=v.get('byteStride',12);off=a.get('byteOffset',0)
  if stride<12 or off+(count-1)*stride+12>len(b):raise Invalid('POSITION accessor exceeds bufferView')
  values=[list(struct.unpack_from('<fff',b,off+i*stride)) for i in range(count)]
 elif 'sparse' not in a:raise Invalid('POSITION has neither bufferView nor sparse values (compressed exports need a decoder)')
 else:
  if count>10000000:raise Invalid('Sparse position count exceeds validation allocation budget')
  values=[[0.,0.,0.] for _ in range(count)]
 if 'sparse' in a:
  sp=a['sparse'];ib=view_bytes(doc,blob,sp['indices']['bufferView']);vb=view_bytes(doc,blob,sp['values']['bufferView']);fmt={5121:'B',5123:'H',5125:'I'}.get(sp['indices']['componentType'])
  if not fmt:raise Invalid('Invalid sparse index type')
  sz=struct.calcsize(fmt)
  for i in range(sp['count']):
   ix=struct.unpack_from('<'+fmt,ib,sp['indices'].get('byteOffset',0)+i*sz)[0]
   if ix>=count:raise Invalid('Sparse accessor index out of bounds')
   values[ix]=list(struct.unpack_from('<fff',vb,sp['values'].get('byteOffset',0)+i*12))
 if not all(finite(v) for v in values):raise Invalid('Nonfinite vertex position')
 lo=[min(v[k] for v in values) for k in range(3)];hi=[max(v[k] for v in values) for k in range(3)]
 if 'min' in a and any(abs(a['min'][k]-lo[k])>max(1e-5,abs(lo[k])*1e-4) for k in range(3)):raise Invalid('POSITION min metadata disagrees with vertex bytes')
 if 'max' in a and any(abs(a['max'][k]-hi[k])>max(1e-5,abs(hi[k])*1e-4) for k in range(3)):raise Invalid('POSITION max metadata disagrees with vertex bytes')
 return lo,hi,count

def image_info(doc,blob,file,image):
 b=b'';where=''
 if 'bufferView' in image:b=view_bytes(doc,blob,image['bufferView']);where='embedded'
 elif image.get('uri','').startswith('data:'):b=base64.b64decode(image['uri'].split(',',1)[1]);where='data-uri'
 elif 'uri' in image:
  p=file.parent/image['uri'];where='external-file'
  if not p.is_file():return {'location':where,'available':False,'uri':image['uri']}
  b=p.read_bytes()
 result={'location':where,'available':bool(b),'bytes':len(b),'mimeType':image.get('mimeType'),'dimensions':None}
 if b.startswith(b'\x89PNG\r\n\x1a\n') and len(b)>=24:result['dimensions']=list(struct.unpack_from('>II',b,16));result['mimeType']='image/png'
 elif b.startswith(b'\xff\xd8'):result['mimeType']='image/jpeg'
 return result

def inspect(file,spec,review):
 result={'file':str(file.resolve()),'errors':[],'warnings':[],'structuralReady':False,'photorealReady':False}
 try:
  raw,d,blob=parse_glb(file);result['sha256']=hashlib.sha256(raw).hexdigest();result['bytes']=len(raw)
  nodes=d.get('nodes',[]);meshes=d.get('meshes',[]);materials=d.get('materials',[]);textures=d.get('textures',[]);images=d.get('images',[])
  for i in range(len(d.get('bufferViews',[]))):view_bytes(d,blob,i)
  for i,b in enumerate(d.get('buffers',[])):
   if i==0 and not b.get('uri') and b.get('byteLength',0)>len(blob):raise Invalid('Buffer byteLength exceeds binary chunk')
  bounds={};triangles=0;vertices=0;normalPrimitives=0;uvPrimitives=0;primitiveCount=0
  for mi,m in enumerate(meshes):
   boxes=[]
   for p in m.get('primitives',[]):
    primitiveCount+=1;a=p.get('attributes',{})
    if 'POSITION' not in a:raise Invalid('Mesh primitive has no POSITION')
    lo,hi,count=position_bounds(d,blob,a['POSITION']);vertices+=count;boxes.append((lo,hi))
    elements=d['accessors'][p['indices']]['count'] if 'indices' in p else count
    if 'indices' in p:
     ia=d['accessors'][p['indices']];fmt={5121:'B',5123:'H',5125:'I'}.get(ia.get('componentType'))
     if not fmt or ia.get('type')!='SCALAR' or 'bufferView' not in ia:raise Invalid('Unsupported or invalid index accessor')
     ib=view_bytes(d,blob,ia['bufferView']);off=ia.get('byteOffset',0);step=struct.calcsize(fmt)
     if off<0 or off+elements*step>len(ib):raise Invalid('Index accessor exceeds binary data')
     for ix in range(elements):
      if struct.unpack_from('<'+fmt,ib,off+ix*step)[0]>=count:raise Invalid('Triangle index references absent vertex')
    mode=p.get('mode',4)
    triangles+=elements//3 if mode==4 else max(0,elements-2) if mode in [5,6] else 0
    if mode==4 and elements%3:raise Invalid('Triangle element count is not divisible by3')
    if 'material' in p and not 0<=p['material']<len(materials):raise Invalid('Invalid material reference')
    normalPrimitives+='NORMAL' in a;uvPrimitives+='TEXCOORD_0' in a
   bounds[mi]=boxes
  if not meshes or not triangles:raise Invalid('No triangle mesh geometry')
  names=[n.get('name','') for n in nodes];dupes=[n for n in set(names) if n and names.count(n)>1]
  if dupes:result['warnings'].append('Duplicate node names: '+', '.join(dupes[:8]))
  if any(not n for n in names):result['warnings'].append('Some nodes are unnamed')
  required=spec.get('requiredNodeNames',[]);missing=[n for n in required if n not in names]
  if missing:raise Invalid('Missing required node names: '+', '.join(missing))
  visited=set();allPoints=[]
  def walk(ix,parent,active):
   if ix in active:raise Invalid('Cycle in node hierarchy')
   if not 0<=ix<len(nodes):raise Invalid('Invalid node index')
   n=nodes[ix];world=mul(parent,local(n));visited.add(ix)
   if 'mesh' in n:
    if n['mesh'] not in bounds:raise Invalid('Invalid mesh index')
    for lo,hi in bounds[n['mesh']]:
     for bits in itertools.product([0,1],repeat=3):allPoints.append(transform(world,[hi[i] if bits[i] else lo[i] for i in range(3)]))
   for ch in n.get('children',[]):walk(ch,world,active|{ix})
  scenes=d.get('scenes',[]);roots=scenes[d.get('scene',0)].get('nodes',[]) if scenes else [i for i in range(len(nodes)) if not any(i in n.get('children',[]) for n in nodes)]
  for ix in roots:walk(ix,identity(),set())
  if not allPoints:raise Invalid('Active scene contains no mesh nodes')
  lo=[min(p[i] for p in allPoints) for i in range(3)];hi=[max(p[i] for p in allPoints) for i in range(3)];size=[hi[i]-lo[i] for i in range(3)]
  if not finite(lo+hi) or max(size)<=1e-9:raise Invalid('Empty or nonfinite world bounds')
  imageReports=[image_info(d,blob,file,i) for i in images]
  if any(not i['available'] for i in imageReports):raise Invalid('Missing or empty texture image')
  for t in textures:
   if 'source' in t and not 0<=t['source']<len(images):raise Invalid('Texture references invalid image')
  pbrCount=0;usedTextureIndices=set();roughness=[];metalness=[]
  for m in materials:
   p=m.get('pbrMetallicRoughness',{});pbrCount+='pbrMetallicRoughness'in m;r=p.get('roughnessFactor',1);metal=p.get('metallicFactor',1)
   if not finite([r,metal]) or not 0<=r<=1 or not 0<=metal<=1:raise Invalid('Metallic/roughness factors outside0..1')
   roughness.append(r);metalness.append(metal)
   for q in [p.get('baseColorTexture'),p.get('metallicRoughnessTexture'),m.get('normalTexture'),m.get('occlusionTexture'),m.get('emissiveTexture')]:
    if q:
     ix=q['index']
     if not 0<=ix<len(textures):raise Invalid('Material texture reference invalid')
     usedTextureIndices.add(ix)
  if usedTextureIndices and uvPrimitives<primitiveCount:result['warnings'].append('Some textured-scene primitives lack TEXCOORD_0; inspect per-material usage')
  if not usedTextureIndices:result['warnings'].append('No material texture maps. Solid PBR can be valid, but surface detail needs visual review.')
  if normalPrimitives<primitiveCount:result['warnings'].append('Some primitives lack exported normals')
  metadata=[d.get('extras',{}),d.get('asset',{}).get('extras',{})]+[n.get('extras',{}) for n in nodes]
  familyIds={str(e.get('familyId')) for e in metadata if isinstance(e,dict)and e.get('familyId')}
  sourceIds=set()
  for e in metadata:
   if isinstance(e,dict):
    for k in ['sourceAssetIds','sourceIDs','sourceIds']:
     v=e.get(k,[]);sourceIds.update(v if isinstance(v,list) else [v])
  if spec.get('familyId') and spec['familyId'] not in familyIds:raise Invalid('Expected familyId not embedded in GLB extras')
  if set(spec.get('requiredSourceAssetIds',[]))-sourceIds:raise Invalid('Required source asset provenance IDs missing from GLB extras')
  proxyNames=[n for n in names+[m.get('name','') for m in meshes] if any(k in n.lower()for k in['pixelmesh','pixel_mesh','pixel-extr','voxel','chr_tile','source_pattern'])]
  planar=min(size)/max(size)<.01
  if planar:result['warnings'].append('Bounds are nearly planar; this may be a card or shallow source extrusion')
  if proxyNames:result['warnings'].append('Names indicate source/pixel/voxel proxy geometry; not photoreal evidence')
  checks=['silhouette','materialResponse','lighting','runtimeReadability','notPixelExtrusion']
  reviewValid=bool(review and review.get('assetSHA256')==result['sha256'] and review.get('approved') is True and review.get('reviewer') and all(review.get('checks',{}).get(k)is True for k in checks))
  result.update(structuralReady=True,geometry={'meshes':len(meshes),'primitives':primitiveCount,'triangles':triangles,'vertices':vertices,'worldBounds':{'min':lo,'max':hi,'size':size},'nearlyPlanar':planar,'proxyNameSignals':proxyNames},materials={'count':len(materials),'explicitMetalRoughPBR':pbrCount,'textureCount':len(textures),'usedTextureCount':len(usedTextureIndices),'images':imageReports,'roughnessRange':[min(roughness),max(roughness)]if roughness else None,'metallicRange':[min(metalness),max(metalness)]if metalness else None},nodes={'count':len(nodes),'names':names,'duplicateNames':dupes},provenance={'familyIds':sorted(familyIds),'sourceAssetIds':sorted(sourceIds)},readiness={'structuralExport':True,'volumetricCandidate':not planar,'materialCandidate':bool(materials and pbrCount),'hashMatchedVisualApproval':reviewValid,'photorealQualityAutomaticallyProvable':False},photorealReady=bool(reviewValid and not planar and not proxyNames and materials and pbrCount))
  if not reviewValid:result['warnings'].append('Photoreal readiness awaits hash-matched visual approval; mesh counts/material flags do not prove it.')
 except (Invalid,ValueError,KeyError,IndexError,TypeError,struct.error,OSError) as e:result['errors'].append(str(e))
 return result

def main():
 ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('models',nargs='+',type=Path);ap.add_argument('--out',type=Path);ap.add_argument('--spec',type=Path);ap.add_argument('--review',type=Path);ap.add_argument('--require-photoreal',action='store_true');args=ap.parse_args();spec=json.loads(args.spec.read_text())if args.spec else {};review=json.loads(args.review.read_text())if args.review else {}
 reports=[inspect(f,spec,review)for f in args.models];ok=all(r['photorealReady'] if args.require_photoreal else r['structuralReady'] for r in reports);report={'passed':ok,'gate':'photoreal-reviewed'if args.require_photoreal else'structural-export','models':reports}
 text=json.dumps(report,indent=2)
 if args.out:args.out.parent.mkdir(parents=True,exist_ok=True);args.out.write_text(text)
 print(text);return 0 if ok else 1
if __name__=='__main__':sys.exit(main())
