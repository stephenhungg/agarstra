#!/usr/bin/env python3
"""Portable, resumable supported-NES ROM to playable source reconstruction."""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
import os
import signal
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
import zlib

SKILL = Path(__file__).resolve().parents[1]

def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n'); temporary.replace(path)

def run(command, cwd, log, timeout=600, stdin=None):
    with Path(log).open('w') as stream:
        process = subprocess.Popen([str(x) for x in command], cwd=cwd, stdin=subprocess.PIPE,
                                   text=True, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            process.communicate(stdin, timeout=timeout)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try: process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL); process.communicate()
            raise RuntimeError(f'Command timed out; process group stopped. Inspect {log}')
    if process.returncode:
        raise RuntimeError(f'Command failed ({process.returncode}); inspect {log}: '+Path(log).read_text(errors='replace')[-1500:])

def png(path, assets):
    # Faithful extracted pixel references, not generated concept art.
    width=512;rows=max(1,(len(assets)+15)//16);height=rows*32
    image=bytearray(bytes([30,35,30,255])*(width*height))
    for index,a in enumerate(assets):
        for y in range(8):
            for x in range(8):
                color=bytes(a['rgba'][(y*8+x)*4:(y*8+x+1)*4])
                if not color[3]:continue
                for dy in range(3):
                    for dx in range(3):
                        offset=(((index//16)*32+y*3+dy)*width+(index%16)*32+x*3+dx)*4
                        image[offset:offset+4]=color
    def chunk(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    scan=b''.join(b'\0'+image[y*width*4:(y+1)*width*4] for y in range(height))
    Path(path).write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,6,0,0,0))+chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))

def tool_path(explicit, name, candidates=()):
    found=explicit or shutil.which(name) or next((str(p) for p in candidates if Path(p).is_file()),None)
    if not found:raise RuntimeError(f'{name} is required; pass --{name} /absolute/path')
    return str(Path(found).resolve())

def fingerprint(runtime):
    return {str(p.relative_to(runtime)):sha(p) for p in sorted(runtime.rglob('*')) if p.is_file() and not any(x in p.parts for x in ('node_modules','__pycache__','dist'))}

def process_job(job, runtime, catalog, blender, codex, author, iterations, timeout):
    receipt=job/'receipt.json'
    key={'catalog':sha(catalog),'builder':sha(runtime/'blender/build.py'),'ids':sha(job/'ids.json'),'author':author}
    if receipt.exists():
        old=json.loads(receipt.read_text())
        if old.get('inputs')==key and old.get('status')=='complete' and all((job/p).is_file() and sha(job/p)==h for p,h in old.get('files',{}).items()) and old.get('files'):
            return old
    shutil.copy2(runtime/'blender/build.py',job/'build.py')
    status={'inputs':key,'status':'running','iterations':[]};write(receipt,status)
    for attempt in range(iterations if author=='codex' else 1):
        if author=='codex':
            feedback=(job/'review.json').read_text() if (job/'review.json').exists() else 'First candidate: preserve source shape/palette. Make editable real geometry.'
            prompt=f'''Build these extracted NES assets in Blender. Work only in this job directory. Do not spawn more agents. The provided build.py is a runnable source-preserving relief baseline; inspect task.json and target.png and improve geometry where source evidence supports it. Preserve stable IDs, top-left origin, 1/16 unit per pixel, Blender Xright/Zup/front -Y. Do not invent whole-object semantics from individual tiles. This pass is source reconstruction, not photoreal approval. Keep CLI --catalog --out --ids and registry.json output compatible. Run no Blender; the orchestrator renders your source and returns actual output. Do not access secrets or change other directories. Previous actual feedback: {feedback}. Write working build.py now. Report limitations honestly.'''
            run([codex,'exec','--ephemeral','--skip-git-repo-check','--sandbox','workspace-write','-c','approval_policy="never"','-C',job,'--json','-o',job/'author-result.txt','-i',job/'target.png','-'],job,job/f'author-{attempt}.jsonl',timeout,prompt)
        import ast
        ast.parse((job/'build.py').read_text())
        out=job/f'candidate-{attempt}';out.mkdir(exist_ok=True)
        run([blender,'--background','--threads','2','--python-exit-code','1','--python',job/'build.py','--','--catalog',catalog,'--out',out,'--ids',job/'ids.json'],job,job/f'blender-{attempt}.log',timeout)
        registry=json.loads((out/'registry.json').read_text())
        expected=set(json.loads((job/'ids.json').read_text()));actual={e['id'] for e in registry['assets']}
        source_assets={a['id']:a for a in json.loads(catalog.read_text())}
        if actual!=expected:raise RuntimeError(f'{job.name}: missing/extra exported IDs')
        for entry in registry['assets']:
            if entry.get('width')!=8 or entry.get('height')!=8 or entry.get('source',{}).get('sourceIdentity')!=source_assets[entry['id']]['sourceAssetId']:raise RuntimeError('Worker changed source mapping')
            file=(out/entry['path']).resolve()
            if not file.is_relative_to(out.resolve()) or not file.is_file() or sha(file)!=entry['sha256']:raise RuntimeError('Invalid exported model path/hash')
            raw=file.read_bytes()
            if raw[:4]!=b'glTF' or len(raw)!=int.from_bytes(raw[8:12],'little'):raise RuntimeError('Invalid GLB export')
        review={'verdict':'not-reviewed','scope':'source-relief prototype; technical export only'}
        if author=='codex':
            schema={'type':'object','properties':{'verdict':{'type':'string','enum':['pass','revise']},'defects':{'type':'array','items':{'type':'string'}},'limitations':{'type':'array','items':{'type':'string'}}},'required':['verdict','defects','limitations'],'additionalProperties':False}
            write(job/'review-schema.json',schema)
            prompt='Independently inspect target.png (extracted source) and candidate render.png (actual Blender output). This is source-relief reconstruction, not photoreal character production. Compare palette, silhouette and whether every expected tile exists; different contact-sheet layout is okay. Reject empty/inverted/invisible exports or unrecognizable source appearance. Return pass or revise with localized defects. Never infer artistic shipping approval. Do not edit files.'
            run([codex,'exec','--ephemeral','--skip-git-repo-check','--sandbox','read-only','-c','approval_policy="never"','-C',job,'--output-schema',job/'review-schema.json','-o',job/'review.json','-i',job/'target.png','-i',out/'render.png','-'],job,job/f'reviewer-{attempt}.log',timeout,prompt)
            review=json.loads((job/'review.json').read_text())
        status['iterations'].append({'attempt':attempt,'review':review,'buildSHA256':sha(job/'build.py')});write(receipt,status)
        if author=='source' or review['verdict']=='pass':
            files={str(p.relative_to(job)):sha(p) for p in out.rglob('*') if p.is_file()}
            files['build.py']=sha(job/'build.py')
            status.update(status='complete',output=str(out.relative_to(job)),files=files,quality='source-reconstruction-prototype');write(receipt,status);return status
    status['status']='changes-required';write(receipt,status)
    raise RuntimeError(f'{job.name}: visual defects remain after {iterations} iterations; no player registry published')

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rom',required=True,type=Path);ap.add_argument('--out',required=True,type=Path)
    ap.add_argument('--frames',type=int,default=300);ap.add_argument('--inputs',type=Path)
    ap.add_argument('--workers',type=int,default=2);ap.add_argument('--blender');ap.add_argument('--codex')
    ap.add_argument('--author',choices=['codex','source'],default='codex')
    ap.add_argument('--iterations',type=int,default=3);ap.add_argument('--timeout',type=int,default=900)
    ap.add_argument('--max-assets',type=int,help='Explicit prototype subset; omitted means all observed opaque palette variants')
    ap.add_argument('--resume',action='store_true');ap.add_argument('--skip-install',action='store_true')
    args=ap.parse_args()
    if not 1<=args.workers<=4 or not 1<=args.iterations<=5 or args.timeout<1:ap.error('workers 1..4, iterations 1..5 and positive timeout required')
    if args.max_assets is not None and args.max_assets<1:ap.error('max-assets must be positive')
    root=args.out.resolve();rom=args.rom.resolve();runtime=root/'runtime'
    if root.exists() and not args.resume:ap.error('output already exists; use --resume to verify and reuse matching outputs')
    blender=tool_path(args.blender,'blender',['/Applications/Blender.app/Contents/MacOS/Blender','/Volumes/Blender/Blender.app/Contents/MacOS/Blender'])
    codex=tool_path(args.codex,'codex') if args.author=='codex' else None
    request={'romFileSHA256':sha(rom),'frames':args.frames,'inputs':sha(args.inputs) if args.inputs else None,'author':args.author,'workers':args.workers,'maxAssets':args.max_assets,'templates':fingerprint(SKILL/'runtime'),'orchestrator':sha(__file__),'blenderVersion':subprocess.check_output([blender,'--version'],text=True).splitlines()[0]}
    if (root/'run.json').exists() and json.loads((root/'run.json').read_text())['request']!=request:raise RuntimeError('Resume inputs or templates changed; choose a new output directory to preserve the old run')
    root.mkdir(parents=True,exist_ok=True)
    if not runtime.exists():shutil.copytree(SKILL/'runtime',runtime,ignore=shutil.ignore_patterns('node_modules','__pycache__','dist'))
    state={'request':request,'status':'extracting','quality':'prototype','romPath':str(rom)};write(root/'run.json',state)
    try:
        command=['node',runtime/'nes/extract.mjs','--rom',rom,'--out',root/'extracted','--frames',str(args.frames)]
        if args.inputs:command+=['--inputs',args.inputs.resolve()]
        run(command,root,root/'extract.log',args.timeout)
        source=json.loads((root/'extracted/source.json').read_text())
        if source['coverage']['recompositionMismatchFrames']:raise RuntimeError('Source recomposition failed; refusing reconstruction')
        catalog=root/'extracted/catalog.json';assets=json.loads(catalog.read_text());assets=[a for a in assets if any(a['rgba'][3::4])]
        if args.max_assets:assets=assets[:args.max_assets]
        if not assets:raise RuntimeError('Replay observed no visible assets; supply inputs/longer capture')
        jobs=[]
        for index in range(min(args.workers,len(assets))):
            job=root/'jobs'/str(index);job.mkdir(parents=True,exist_ok=True);subset=assets[index::args.workers]
            write(job/'ids.json',[a['id'] for a in subset]);write(job/'task.json',{'romSha256':source['romSha256'],'assets':subset,'scope':'source-preserving tile reconstruction','notImplemented':'semantic whole-object inference'})
            png(job/'target.png',subset);jobs.append(job)
        state['status']='building';write(root/'run.json',state)
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            futures={pool.submit(process_job,j,runtime,catalog,blender,codex,args.author,args.iterations,args.timeout):j for j in jobs}
            results=[]
            for future in as_completed(futures):
                result=future.result();results.append((futures[future],result));print(f'Completed asset job {futures[future].name}',flush=True)
        target=runtime/'player/public/assets';target.mkdir(parents=True,exist_ok=True)
        entries=[]
        release_id=hashlib.sha256(json.dumps([(str(job.name),result['files']) for job,result in sorted(results)],sort_keys=True).encode()).hexdigest()[:24]
        release=target/'releases'/release_id;release.parent.mkdir(exist_ok=True)
        staging=Path(tempfile.mkdtemp(prefix='.publishing-',dir=release.parent))
        try:
            for job,result in results:
                out=job/result['output'];registry=json.loads((out/'registry.json').read_text())
                for entry in registry['assets']:
                    destination=staging/entry['path'];destination.parent.mkdir(exist_ok=True,parents=True);shutil.copy2(out/entry['path'],destination)
                    entries.append({**entry,'path':f'releases/{release_id}/'+entry['path']})
            if len(entries)!=len({e['id'] for e in entries}):raise RuntimeError('Duplicate registry IDs')
            if release.exists():
                for entry in entries:
                    if sha(target/entry['path'])!=entry['sha256']:raise RuntimeError('Existing release was modified; use a new output directory')
            else:os.rename(staging,release)
            write(target/'source-registry.json',{'profile':'prototype','romSha256':source['romSha256'],'assets':entries,'quality':'source-relief reconstruction; not whole-object remake'})
        finally:
            if staging.exists():shutil.rmtree(staging)
        write(target/'replay.json',{'events':json.loads((root/'extracted/replay.json').read_text())['events'],'frames':args.frames})
        state.update(status='installing',source=source,exportedAssets=len(entries));write(root/'run.json',state)
        if not args.skip_install:run(['npm','install','--no-audit','--no-fund'],runtime/'player',root/'install.log',args.timeout)
        run(['npm','run','build'],runtime/'player',root/'build.log',args.timeout)
        state.update(status='playable-prototype',launch=f'npm --prefix "{runtime / "player"}" run dev',limitations=source['limitations']+['Models are source-relief candidates, not automatically inferred whole characters.','Choose your original ROM in the player; no ROM is copied into the web build.'])
        write(root/'run.json',state);print(json.dumps({k:v for k,v in state.items() if k!='request'},indent=2))
    except Exception as error:
        state.update(status='failed',error=str(error));write(root/'run.json',state);raise

if __name__=='__main__':
    try:main()
    except Exception as error:print(f'Remake stopped: {error}',file=sys.stderr);sys.exit(1)
