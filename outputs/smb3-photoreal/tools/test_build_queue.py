"""Regression checks for source-aware queue resume without launching Blender."""
import importlib.util,json,tempfile,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('build_queue',Path(__file__).with_name('build_queue.py'))
q=importlib.util.module_from_spec(spec);spec.loader.exec_module(q)
class ResumeTests(unittest.TestCase):
 def scenario(self,changed):
  with tempfile.TemporaryDirectory()as directory:
   root=Path(directory);q.OUT=root/'out';q.WORK=root/'work';q.STATUS=q.WORK/'status.json'
   job=q.WORK/'jobs/test';target=q.OUT/'families/test';job.mkdir(parents=True);(target/'models').mkdir(parents=True);(q.OUT/'tools').mkdir()
   script=job/'build.py';script.write_text('old source');oldhash=q.sha(script)
   if changed:script.write_text('changed source')
   (target/'models/model.glb').write_bytes(b'existing glb');(target/'manifest.json').write_text('{}');(target/'preview.png').write_bytes(b'preview');(q.OUT/'tools/render_family.py').write_text('render')
   q.state={'test':{'sourceSHA256':oldhash,'renderHelperSHA256':q.sha(q.OUT/'tools/render_family.py'),'phase':'done'}}
   calls=[]
   def fake_run(cmd,log,timeout=1800):
    calls.append(cmd)
    if 'validate_models.py' in ' '.join(cmd):(target/'validation.json').write_text(json.dumps({'models':[{'file':str(target/'models/model.glb'),'materials':{'usedTextureCount':3}}]}))
    return 0
   q.run=fake_run;q.build('test',{'assets':['model']})
   built=any(str(script)in cmd for cmd in calls)
   self.assertEqual(built,changed)
   self.assertEqual(q.state['test']['resumed'],not changed)
   self.assertEqual(q.state['test']['phase'],'done')
 def test_changed_script_forces_build_even_after_status_mutation(self):self.scenario(True)
 def test_unchanged_script_resumes_existing_manifest(self):self.scenario(False)
if __name__=='__main__':unittest.main()
