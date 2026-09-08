"""Negative export and readiness-gate checks using the local PBR smoke fixture."""
import importlib.util,json,struct,tempfile,unittest,hashlib
from pathlib import Path
spec=importlib.util.spec_from_file_location('validator',Path(__file__).with_name('validate_models.py'));v=importlib.util.module_from_spec(spec);spec.loader.exec_module(v)
FIXTURE=Path(__file__).resolve().parents[1]/'models/pbr-smoke.glb'
def write_glb(path,doc,blob):
 j=json.dumps(doc,separators=(',',':')).encode();j+=b' '*((-len(j))%4);b=blob+b'\0'*((-len(blob))%4);data=struct.pack('<4sII',b'glTF',2,12+8+len(j)+8+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b;path.write_bytes(data)
class ValidationTests(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.path=Path(self.tmp.name)/'fixture.glb';self.raw,self.doc,self.blob=v.parse_glb(FIXTURE)
 def tearDown(self):self.tmp.cleanup()
 def test_real_baked_export_is_structural_not_automatically_photoreal(self):
  r=v.inspect(FIXTURE,{},{});self.assertTrue(r['structuralReady']);self.assertFalse(r['photorealReady']);self.assertEqual(r['materials']['usedTextureCount'],3)
 def test_truncated_file_is_rejected(self):
  self.path.write_bytes(self.raw[:-7]);self.assertFalse(v.inspect(self.path,{},{})['structuralReady'])
 def test_out_of_bounds_geometry_is_rejected(self):
  p=self.doc['meshes'][0]['primitives'][0];self.doc['accessors'][p['attributes']['POSITION']]['count']=10**7;write_glb(self.path,self.doc,self.blob);self.assertFalse(v.inspect(self.path,{},{})['structuralReady'])
 def test_missing_external_image_is_rejected(self):
  self.doc['images'][0]={'uri':'missing-image.png'};write_glb(self.path,self.doc,self.blob);self.assertFalse(v.inspect(self.path,{},{})['structuralReady'])
 def test_required_nodes_and_provenance_are_enforced(self):
  self.assertFalse(v.inspect(FIXTURE,{'requiredNodeNames':['nonexistent']},{})['structuralReady']);self.assertFalse(v.inspect(FIXTURE,{'familyId':'pipes'},{})['structuralReady'])
 def test_stale_visual_review_does_not_approve(self):
  review={'assetSHA256':'stale','approved':True,'reviewer':'test-only','checks':{k:True for k in ['silhouette','materialResponse','lighting','runtimeReadability','notPixelExtrusion']}};self.assertFalse(v.inspect(FIXTURE,{},review)['photorealReady'])
 def test_flattened_card_not_photoreal_ready_even_with_review(self):
  self.doc['nodes'][0]['scale']=[1,1,0];write_glb(self.path,self.doc,self.blob);review={'assetSHA256':hashlib.sha256(self.path.read_bytes()).hexdigest(),'approved':True,'reviewer':'test-only','checks':{k:True for k in ['silhouette','materialResponse','lighting','runtimeReadability','notPixelExtrusion']}};r=v.inspect(self.path,{},review);self.assertTrue(r['structuralReady']);self.assertTrue(r['geometry']['nearlyPlanar']);self.assertFalse(r['photorealReady'])
if __name__=='__main__':unittest.main()
