"""Reopen saved Blender library and recover front-face source pixels for every object."""
import bpy,json,sys,argparse,hashlib
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('--catalog',required=True);p.add_argument('--report',required=True);a=p.parse_args(sys.argv[sys.argv.index('--')+1:]);data=json.loads(Path(a.catalog).read_text());counts={};pixels=0;polygons=0
assert len(bpy.data.objects)==len(data['assets'])
for src in data['assets']:
 obj=bpy.data.objects.get(src['id']);assert obj is not None and obj.type=='MESH',src['id'];assert obj['source_rgba_sha256']==hashlib.sha256(bytes(src['rgba'])).hexdigest();assert json.loads(obj['source_provenance'])['id']==src['id']
 kind=src['kind'];counts[kind]=counts.get(kind,0)+1;w,h=src['width'],src['height'];out=bytearray(w*h*4)
 for poly in obj.data.polygons:
  coords=[obj.data.vertices[i].co for i in poly.vertices]
  if not all(abs(v.y+.0375)<.000001 for v in coords):continue
  x0=round(min(v.x for v in coords)*16);x1=round(max(v.x for v in coords)*16);y0=round(-max(v.z for v in coords)*16);y1=round(-min(v.z for v in coords)*16)
  rgb=list(obj.data.materials[poly.material_index]['source_srgb_bytes']);assert 0<=x0<x1<=w and 0<=y0<y1<=h
  for y in range(y0,y1):
   for x in range(x0,x1):i=(y*w+x)*4;assert out[i+3]==0;out[i:i+4]=bytes(rgb+[255])
 for i in range(w*h):
  at=i*4;expected=src['rgba'][at:at+4];actual=list(out[at:at+4]);assert (expected==actual if expected[3] else actual[3]==0),(src['id'],i,actual,expected)
 if kind=='binary-player-template-preview':assert 'UNVERIFIED' in obj['reachability']
 pixels+=w*h;polygons+=len(obj.data.polygons)
report={'passed':True,'method':'Reopened .blend; reconstructed RGBA from actual front-face mesh polygons/materials; compared every source pixel','counts':counts,'objects':len(bpy.data.objects),'sourcePixelsCompared':pixels,'mismatches':0,'polygons':polygons,'blend':bpy.data.filepath}
Path(a.report).write_text(json.dumps(report,indent=2));print('REOPEN_VERIFICATION',json.dumps(report))
