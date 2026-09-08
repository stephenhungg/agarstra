"""Run with Blender --background --python this_file. Paths resolve from this file."""
import bpy,json,struct,hashlib,math,os
from pathlib import Path
from mathutils import Quaternion,Vector
OUT=Path(__file__).resolve().parent; BASE=OUT.parent.parent
src=Path(os.environ.get('TRAINER_SOURCE_GLB',str(BASE/'models/trainer-direct-v2.glb'))); dst=BASE/'models/trainer-direct-v3.glb'
b=src.read_bytes(); assert hashlib.sha256(b).hexdigest()=='fd14343ce1c070bdd3bd51c6c01b8c871bf26f81f7206c57466bb33270c1fe74', 'Expected verified v2 source'; jl=struct.unpack_from('<I',b,12)[0];doc=json.loads(b[20:20+jl]);data=bytearray(b[28+jl:]);original=bytes(data)
nodes=doc['nodes'];parents={c:i for i,n in enumerate(nodes)for c in n.get('children',[])};byname={n['name']:i for i,n in enumerate(nodes)if 'name'in n};counts={'SCALAR':1,'VEC3':3,'VEC4':4,'MAT4':16}
def arr(idx,buf=data):
 a=doc['accessors'][idx];v=doc['bufferViews'][a['bufferView']];n=counts[a['type']];return [struct.unpack_from('<'+'f'*n,buf,v.get('byteOffset',0)+a.get('byteOffset',0)+i*v.get('byteStride',n*4))for i in range(a['count'])]
def quat(q):return Quaternion((q[3],q[0],q[1],q[2]))
def sample(anim,t,buf):
 st=[{'rotation':n.get('rotation',[0,0,0,1]),'translation':n.get('translation',[0,0,0]),'scale':n.get('scale',[1,1,1])}for n in nodes]
 for ch in anim['channels']:
  s=anim['samplers'][ch['sampler']];ts=[x[0]for x in arr(s['input'],buf)];vs=arr(s['output'],buf);i=next((i for i in range(len(ts)-1)if ts[i+1]>=t),len(ts)-1);u=max(0,min(1,(t-ts[i])/(ts[i+1]-ts[i])))if i<len(ts)-1 else 0
  if ch['target']['path']=='rotation':q=quat(vs[i]).slerp(quat(vs[min(i+1,len(vs)-1)]),u);val=[q.x,q.y,q.z,q.w]
  else:val=[x+(y-x)*u for x,y in zip(vs[i],vs[min(i+1,len(vs)-1)])]
  st[ch['target']['node']][ch['target']['path']]=val
 return st
def world(st,i):
 n=st[i];q=quat(n['rotation']);p=Vector(n['translation']);sc=Vector(n['scale'])
 if i in parents:
  pq,pp,ps=world(st,parents[i]);return pq@q,pp+pq@Vector([p[j]*ps[j]for j in range(3)]),Vector([sc[j]*ps[j]for j in range(3)])
 return q,p,sc
# Dense arm-only walk samples provide a modest counter-swing; all existing times remain untouched.
walk=next(a for a in doc['animations']if a['name']=='walk')
def append_accessor(values,kind):
 n=counts[kind];offset=len(data);data.extend(struct.pack('<'+'f'*(len(values)*n),*(v for row in values for v in row)));vi=len(doc['bufferViews']);doc['bufferViews'].append({'buffer':0,'byteOffset':offset,'byteLength':len(values)*n*4});ai=len(doc['accessors']);doc['accessors'].append({'bufferView':vi,'componentType':5126,'count':len(values),'type':kind,'min':[min(row[j]for row in values)for j in range(n)],'max':[max(row[j]for row in values)for j in range(n)]});return ai
times=[(k/30,)for k in range(31)];ti=append_accessor(times,'SCALAR')
for name in ['LeftArm','RightArm','LeftForeArm','RightForeArm']:
 ch=next(c for c in walk['channels']if c['target']=={'node':byname[name],'path':'rotation'});s=walk['samplers'][ch['sampler']];vals=[sample(walk,t[0],data)[byname[name]]['rotation']for t in times];s['input']=ti;s['output']=append_accessor(vals,'VEC4')
changed=[]
for anim in doc['animations']:
 for name,child in [('LeftArm','LeftForeArm'),('RightArm','RightForeArm'),('LeftForeArm','LeftHand'),('RightForeArm','RightHand')]:
  idx=byname[name];side=1 if name.startswith('Left')else -1
  ch=next(c for c in anim['channels']if c['target']=={'node':idx,'path':'rotation'});s=anim['samplers'][ch['sampler']];ts=arr(s['input']);acc=doc['accessors'][s['output']];bv=doc['bufferViews'][acc['bufferView']];offset=bv.get('byteOffset',0)+acc.get('byteOffset',0);prev=None
  for k,(t,)in enumerate(ts):
   st=sample(anim,t,data);q,p,_=world(st,idx);_,cp,_=world(st,byname[child]);pq,_,_=world(st,parents[idx]);swing=math.sin(2*math.pi*t)*side if anim['name']=='walk'else .025*math.sin(2*math.pi*t/4.0333333)
   # Model left has positive X. Maintain a small gap to vest and a softly bent elbow.
   target=Vector((side*(.23 if name.endswith('Arm')and not name.endswith('ForeArm')else .08),-1,(.08 if not name.endswith('ForeArm')else .38)+swing*.22)).normalized()
   nq=pq.inverted()@((cp-p).normalized().rotation_difference(target)@q);nq.normalize()
   if prev and prev.dot(nq)<0:nq.negate()
   prev=nq;struct.pack_into('<4f',data,offset+k*bv.get('byteStride',16),nq.x,nq.y,nq.z,nq.w)
  values=arr(s['output'])
  for key,fn in [('min',min),('max',max)]:
   if key in acc:acc[key]=[fn(row[j]for row in values)for j in range(4)]
  changed.append({'clip':anim['name'],'node':name,'samples':len(ts),'outputAccessor':s['output']})
doc['buffers'][0]['byteLength']=len(data)
j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);data+=b'\0'*((-len(data))%4);dst.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(data))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(data),0x004e4942)+data)
allowed=set()
for c in changed:
 a=doc['accessors'][c['outputAccessor']];v=doc['bufferViews'][a['bufferView']];o=v.get('byteOffset',0)+a.get('byteOffset',0)
 for k in range(a['count']):allowed.update(range(o+k*v.get('byteStride',16),o+k*v.get('byteStride',16)+16))
assert all(a==z or i in allowed for i,(a,z)in enumerate(zip(original,data)))
report={'sourceSHA256':hashlib.sha256(b).hexdigest(),'candidateSHA256':hashlib.sha256(dst.read_bytes()).hexdigest(),'changed':changed,'allOtherBinaryBytesUnchanged':True,'status':'candidate-pending-visual-review'}
(OUT/'report.json').write_text(json.dumps(report,indent=2))
bpy.ops.wm.read_factory_settings(use_empty=True);bpy.context.scene.render.fps=30;bpy.ops.import_scene.gltf(filepath=str(dst));bpy.ops.wm.save_as_mainfile(filepath=str(BASE/'models/trainer-direct-v3.blend'))
print(json.dumps(report))
