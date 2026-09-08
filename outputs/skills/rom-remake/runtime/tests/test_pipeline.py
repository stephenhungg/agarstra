"""Mechanical orchestration tests, never evidence of artistic acceptance."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('remake',Path(__file__).resolve().parents[2]/'scripts/remake.py')
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)

class PipelineTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
 def test_fingerprint_ignores_installed_and_generated_dependencies(self):
  (self.root/'source.py').write_text('source')
  for folder in ['node_modules','__pycache__','dist']:
   (self.root/folder).mkdir();(self.root/folder/'artifact').write_text('generated')
  self.assertEqual(list(m.fingerprint(self.root)),['source.py'])
 def test_faithful_reference_png(self):
  out=self.root/'target.png';m.png(out,[{'rgba':[255,0,0,255]*64}]);self.assertEqual(out.read_bytes()[:8],b'\x89PNG\r\n\x1a\n')
 def test_atomic_state_write(self):
  out=self.root/'run.json';m.write(out,{'status':'building'});m.write(out,{'status':'complete'})
  self.assertEqual(json.loads(out.read_text()),{'status':'complete'});self.assertFalse(out.with_suffix('.json.tmp').exists())
 def test_worker_cache_requires_matching_artifact_bytes(self):
  runtime=self.root/'runtime';(runtime/'blender').mkdir(parents=True);(runtime/'blender/build.py').write_text('pass')
  job=self.root/'job';job.mkdir();(job/'ids.json').write_text('[]');catalog=self.root/'catalog.json';catalog.write_text('[]')
  (job/'build.py').write_text('pass');(job/'model.glb').write_bytes(b'original')
  key={'catalog':m.sha(catalog),'builder':m.sha(runtime/'blender/build.py'),'ids':m.sha(job/'ids.json'),'author':'source'}
  receipt={'inputs':key,'status':'complete','files':{'model.glb':m.sha(job/'model.glb'),'build.py':m.sha(job/'build.py')}};m.write(job/'receipt.json',receipt)
  with patch.object(m,'run',side_effect=RuntimeError('rebuild invoked')):
   self.assertEqual(m.process_job(job,runtime,catalog,'blender',None,'source',1,10),receipt)
   (job/'model.glb').write_bytes(b'changed')
   with self.assertRaisesRegex(RuntimeError,'rebuild invoked'):m.process_job(job,runtime,catalog,'blender',None,'source',1,10)

if __name__=='__main__':unittest.main()
