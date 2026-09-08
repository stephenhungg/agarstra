#!/usr/bin/env python3
"""Independent resumable two-slot Blender build/render queue. Never writes authorstatus."""
import argparse,concurrent.futures,hashlib,json,os,subprocess,threading,time
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=OUT.parents[1];WORK=ROOT/'work/photoreal-swarm';STATUS=WORK/'build-status.json';AUTHOR=WORK/'status.json';BLENDER='/Volumes/Blender/Blender.app/Contents/MacOS/Blender';LOCK=threading.Lock();state={}
def update(name,**data):
 with LOCK:
  state.setdefault(name,{}).update(data);tmp=STATUS.with_suffix('.tmp');tmp.write_text(json.dumps(state,indent=2));os.replace(tmp,STATUS)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def run(cmd,log,timeout=1800):
 with log.open('w')as f:r=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,timeout=timeout)
 return r.returncode

def build(name,author):
 job=WORK/'jobs'/name;target=OUT/'families'/name;target.mkdir(parents=True,exist_ok=True);script=job/'build.py';expected=author.get('assets',[]);sourcehash=sha(script);old=dict(state.get(name,{}))
 update(name,phase='building',started=time.time(),sourceSHA256=sourcehash,expectedAssets=expected,attempts=old.get('attempts',0)+1)
 models=list((target/'models').glob('*.glb'));canResume=(target/'manifest.json').exists() and all((target/'models'/f'{x}.glb').exists()for x in expected) and models and (not old.get('sourceSHA256')or old.get('sourceSHA256')==sourcehash)
 try:
  if not canResume:
   code=run([BLENDER,'--background','--threads','4','--python-exit-code','1','--python',str(script),'--','--out',str(target)],target/'build.log')
   if code:raise RuntimeError(f'Blender build exit{code}; see build.log')
  models=sorted((target/'models').glob('*.glb'));missing=[x for x in expected if not(target/'models'/f'{x}.glb').exists()]
  if missing or not models:raise RuntimeError('Missing expected models: '+','.join(missing))
  update(name,phase='validating',models=len(models),modelPaths=[str(p)for p in models],resumed=bool(canResume))
  code=run(['python3',str(OUT/'tools/validate_models.py'),*[str(p)for p in models],'--out',str(target/'validation.json')],target/'validation.log',300)
  validation=json.loads((target/'validation.json').read_text())
  if code:raise RuntimeError('Structural GLB validation failed; see validation.json')
  textureless=[Path(r['file']).stem for r in validation['models']if not r.get('materials',{}).get('usedTextureCount')]
  update(name,phase='rendering',structuralPassed=True,texturelessAssets=textureless)
  renderHash=sha(OUT/'tools/render_family.py')
  if not(target/'preview.png').exists()or not canResume or old.get('renderHelperSHA256')!=renderHash:
   code=run([BLENDER,'--background','--threads','4','--python-exit-code','1','--python',str(OUT/'tools/render_family.py'),'--','--family',str(target)],target/'render.log',1200)
   if code:raise RuntimeError(f'Contact sheet render exit{code}; see render.log')
  update(name,phase='done',ended=time.time(),preview=str(target/'preview.png'),visualReview='pending actual inspection',renderHelperSHA256=renderHash,modelSHA256={p.stem:sha(p)for p in models})
  print(json.dumps({'job':name,'phase':'done','models':len(models),'textureless':textureless}),flush=True)
 except Exception as e:
  update(name,phase='failed',ended=time.time(),error=str(e));print(json.dumps({'job':name,'phase':'failed','error':str(e)}),flush=True)

def main():
 global state
 ap=argparse.ArgumentParser();ap.add_argument('--poll',type=float,default=3);ap.add_argument('--max-wait',type=float,default=3600);ap.add_argument('--families',nargs='*');args=ap.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if STATUS.exists():state=json.loads(STATUS.read_text())
 started=time.time();priority={'blocks':0,'character-kit':1,'terrain':2,'architecture':3,'pipes':4,'vegetation':5,'creatures':6,'items':7};running={}
 with concurrent.futures.ThreadPoolExecutor(max_workers=2)as pool:
  while time.time()-started<args.max_wait:
   try:author=json.loads(AUTHOR.read_text())
   except (FileNotFoundError,json.JSONDecodeError):time.sleep(args.poll);continue
   supplement=WORK/'extra-build-jobs.json'
   if supplement.exists():author.update(json.loads(supplement.read_text()))
   if args.families:author={k:v for k,v in author.items()if k in args.families}
   for f in list(running):
    if f.done():f.result();del running[f]
   candidates=[]
   for name,a in author.items():
    if a.get('phase')!='authored' or name in running.values():continue
    current=state.get(name,{});script=WORK/'jobs'/name/'build.py'
    if not script.exists():continue
    changed=current.get('sourceSHA256')!=sha(script)
    if current.get('phase')=='done' and not changed and current.get('renderHelperSHA256')==sha(OUT/'tools/render_family.py'):continue
    if current.get('phase')=='failed' and not changed:continue
    candidates.append((priority.get(name.rsplit('-',1)[0],9),name))
   for _,name in sorted(candidates)[:max(0,2-len(running))]:running[pool.submit(build,name,author[name])]=name
   authorFinished=author and all(a.get('phase')in ['authored','failed']for a in author.values())
   remaining=any(a.get('phase')=='authored' and state.get(n,{}).get('phase')not in ['done','failed']for n,a in author.items())
   if authorFinished and not remaining and not running:break
   time.sleep(args.poll)
 print(json.dumps({'queueFinished':True,'done':sum(v.get('phase')=='done'for v in state.values()),'failed':sum(v.get('phase')=='failed'for v in state.values())}),flush=True)
if __name__=='__main__':main()
