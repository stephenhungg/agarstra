#!/usr/bin/env python3
"""Bounded headless Codex authoring queue and separate Blender build queue."""
import argparse, concurrent.futures, json, os, pathlib, subprocess, time, threading, signal
ROOT=pathlib.Path(__file__).resolve().parents[3]
OUT=ROOT/'outputs/smb3-photoreal'; WORK=ROOT/'work/photoreal-swarm'
CODEX=WORK/'runtime/node_modules/.bin/codex'; BLENDER=pathlib.Path('/Volumes/Blender/Blender.app/Contents/MacOS/Blender')
FAMILIES=[
 ('blocks', ['question-block','used-block','brick-block','stone-block','ice-block'], 'Source-recognizable golden question block with inset embossed question mark, countersunk corner bolts, weathered enamel and bevels; worn used block with inset panels; real masonry brick block with recessed mortar; granular fortress stone and frosted ice variants. No pixel extrusions.'),
 ('pipes', ['pipe-green','pipe-red','pipe-gold','pipe-elbow','pipe-short'], 'Hollow cast enamel metal pipes: thick rolled rim, real dark interior geometry, flanged segment joints, subtle casting imperfections and scratches. Each rooted at floor; pipe-green should be 2 units diameter and 3 high. Real cylinder and torus tessellation, not block approximations.'),
 ('terrain', ['ground-grass','ground-soil','ground-sand','ground-snow','ground-stone','ground-wood'], 'Modular terrain segments with layers, soil clods, stones, dense small grass blades at top, natural dry sand ripples, compacted snow, rough fortress masonry, aged wood planks. 4 units wide, 1 high, depth2; root floor. Continuous tileable edges where possible. PBR surfaces must survive glTF.'),
 ('vegetation', ['hill-green','hill-tall','bush','fern','vine','mushroom-tree'], 'Reinterpret actual SMB3 rounded hill/bush silhouettes with organic layered vegetation, rounded topiary-like dense foliage and real irregular leaf geometry and underlying earthy rock, avoiding smooth shiny green balloons. Leaf planes may be leaves but model cannot be a single billboard. Hill width4 height3; bush width2 height1. Preserve lushgreen readable shape.'),
 ('architecture', ['platform-coral','platform-cream','platform-blue','wood-platform','castle-wall','castle-door','airship-hull'], 'Source raised rectangular colored platforms become thick painted plaster/wood architectural panels with rounded corners, recessed corner bolts and rear supports; platforms width3 height2 depth.5. Weathered wood airship plank hull and blackened castle brick. Layered materials, bevels, mechanical construction detail.'),
 ('items', ['coin','super-mushroom','one-up','super-leaf','star','fire-flower','music-block','pow-block'], 'Detailed source-recognizable collectibles: machined gold coin with milled edges embossed numeral1, organic spotted mushroom red or green, veined warm leaf, bevelled fivepoint luminous star, flower with organic petals, smooth ivory note block with raised note mark, darkblue POWblock. Real materials and readable silhouettes; coin diameter1 thickness.14.'),
 ('creatures', ['goomba','koopa-green','koopa-red','buzzy-beetle','spiny'], 'Detailed organic/armored creatures following SMB3 source silhouettes: Goomba ochre mushroom cap broad scowling eyes and short brown shoes, turtleKoopa shell scutes and cream belly, darkblue rounded beetle shell, redspikedspiny shell. Sculpted continuous surfaces, eyelids/brows, proper skin/leather/shell roughness; no simple toyblob. Static meshes plus named foot pivots ifeasy. Rootbottomcenter, goomba height1 andkoopa1.5.'),
 ('mechanisms', ['cannon','bullet-bill','hammer','firebar','spike-trap','chain-chomp'], 'Weathered blackcast-iron cannon with bore and ironbands, recognizable BulletBill with stern eyes and riveted body, heavy steelhammer withwoodenhandle, articulatedfirebarchain, worn metalspiketrap, glossy blackChomp metalcreature withhollowjaw individualteeth and chainlinks. Model mechanicalconnections and realedgewear.'),
 ('aquatic', ['cheep-cheep','blooper','piranha-plant','dry-bones','boo'], 'Detailed source-recognizable fish redscales whitebelly expressiveeyes fins, squidmantle andtentacles, spottedredPiranhaPlant withhollowmouth teeth greenstem leaves, skeletalKoopa bones shell, spectral roundBoo withlargeopenmouth tongue. Distinct materials and continuous geometry; noflatpixeltileupsampling. Avoid claiming anatomicalphotorealism fromproceduralproxies.'),
 ('worldmap', ['map-castle','map-fortress','map-house','map-bridge','map-lock','map-boat'], 'Detailed architectural worldmapicons: smallcastle withstonemasonry battlements blueflags, fortress, mushroomroofhouse, woodropebridge, ironpadlock, smallwoodboat. Recognizable silhouette; realtimber/granularstone/cloth/metal materials. Meshheight1to3, bottomcenter. Make standalone assets readable fromside andthreequarter.'),
 ('set-dressing', ['rock-cluster','grass-clump','reeds','wood-crate','wood-fence','metal-gate'], 'Grounded environmentdressing withroughstoneclusters, grassclumps with variedblades, wetlandreeds, weatheredcrateplanks nails joins, woodfencegrain andironhinges, wroughtirongate. Highvalue naturalmaterial detail; mutedrelative tohero andinteractivegoldblocks. Efficient gameplayLODs.'),
 ('character-kit', ['mario-body','mario-cap','mario-boot','mario-glove','raccoon-tail','hammer-suit-shell'], 'Author source-recognizable Mario clothing/accessory kit with actual stitching seamgeometry, capwhiteMbadge, bootsole weltlaces ifappropriate, paddedleathergloves, fur-liketaperedstripedtail, darkprotectiveshell. Mainmario-body detailedcompactplumber shape recognizablemustache eyes browsredcap redshirtblueoverallsbrassbuttons, anatomicallyconnectedroundedforms. This is a reviewedfallback; generatedhero mayreplaceit. Rootbottomcenter height1.5. No armsout Tposeforfinalstaticbody; handsat sidesapart slightly.')
]
FAMILIES=[(name+'-'+str(i+1), ids[:(len(ids)+1)//2] if i==0 else ids[(len(ids)+1)//2:], brief) for name,ids,brief in FAMILIES for i in range(2)]
LOCK=threading.Lock(); state={}; RETRIES=2; TIMEOUT=1500
def update(key,**fields):
 with LOCK:
  state.setdefault(key,{}).update(fields)
  tmp=WORK/'status.tmp';tmp.write_text(json.dumps(state,indent=2));tmp.replace(WORK/'status.json')
def prompt(name,ids,brief):
 return f'''You are one isolated asset-family author in an explicitly user-authorized parallel Codex/Blender asset build. Work only inside your current working directory. Do not spawn agents or Codex processes, use cloud generation, contact other people, edit shared files, or run Blender. A central build queue runs Blender with a concurrency limit.\n\nTask: Write build.py that creates these independent detailed editable Blender4.5 assets and exports one GLB per asset: {json.dumps(ids)}. Family brief: {brief}\n\nRead the shared style contract at {OUT/'design/style.json'} and shared helper API at {OUT/'tools/pbr_common.py'} plus its neighboring README ifpresent. Use a sys.path insert to import that module. Ifnotyetavailable, write self-contained material/geometry fallbacks with the same convention; do not wait. Existing original ROM asset reference JSON andPNG catalogs are under {ROOT/'outputs/smb3-rom-assets/catalog'}, use relevantsourceevidence for silhouettes; do notscanhugeentireJSONintooutput.\n\nCoordinatecontract: BlenderZup, facefront toward -Y, Xright. GLTFexport willbeYup. Eachmeshasset at origin bottom-center; oneblock=1unit=16NESpixels. Exporteachwithits own root and stableasset_id. No stagefloor/camera/lights in GLB.\n\nScript CLI: Blender --background --python build.py -- --out DIRECTORY. Write DIRECTORY/models/<id>.glb and DIRECTORY/library.blend containing allauthoredassets laidoutforinspection. Write DIRECTORY/manifest.json listing assetid,path,nominaldimensions,materials,meshfeatures,sourcebasis,knownqualitylimitations. Savepackedtextures inblend andembeddedinGLB. Make script robust to Blender4.5 API; use mesh/ring-based modeling ratherthan hugeoperatorloops. Build recognizable detailedgeometry with bevels, joins, carveddetails, subdivisions andsurfacevariation. Do not pass off a singlecube, spriteplane, or simpleclusterofspheres asfinishedphotorealmodel.\n\nPBRquality: Realistic albedo/roughness/normal detail MUST transfer toglTF. Blender-only proceduralshadernodes withoutbakedtextures do notmeetthisrequirement. Prefer shared pbr_common material(bake=True,resolution=512,cache_dir=out/materials) whenavailable. For initialauthoring create reproduciblegeometry with PBRparameters; centralqueuecanfixunsupportedhelpers. Bound ~8k triangles/prop, 20kcreature; notstrictifdetailsjustifyit. Use a smallnumberof meaningfulmaterialslots; reusematerials.\n\nYou only author code plus README.md and job.json (status=authored, listassets, howtorun,limitations); rootwillrun/render/inspect. Check Python syntax with ast.parse/py_compile. Do not report visualquality orrenderspassed withoutactuallyseeingthem. Do not useimagegenerationtools to fake aBlender render. Eachobject needsreal3Dgeometry. Avoid license/download/auth flows. No externalruntime dependencies beyondBlender stdlib plusread-only pbr_common.\n\nImplement now, finishwithinonefocusedturn. Noquestions.''' 
def author(job):
 name,ids,brief=job;cwd=WORK/'jobs'/name;
 if state.get(name,{}).get('phase') in ('authored','building','built') and (cwd/'build.py').exists():return name,True
 cwd.mkdir(parents=True,exist_ok=True);p=prompt(name,ids,brief);(cwd/'prompt.txt').write_text(p)
 update(name,phase='authoring',assets=ids,started=time.time())
 cmd=[str(CODEX),'exec','--ephemeral','--skip-git-repo-check','--sandbox','workspace-write','--model','gpt-6-astra','-c','agents.enabled=false','-c','approval_policy="never"','-C',str(cwd),'--json','-o',str(cwd/'result.txt'),'-']
 for attempt in range(RETRIES+1):
  suffix='' if attempt==0 else f'.retry-{attempt}'
  log_path=cwd/f'events{suffix}.jsonl';err_path=cwd/f'stderr{suffix}.log'
  update(name,phase='authoring',attempt=attempt+1)
  with log_path.open('w') as log,err_path.open('w') as err:
   try:
    process=subprocess.Popen(cmd,stdin=subprocess.PIPE,stdout=log,stderr=err,text=True,start_new_session=True)
    update(name,pid=process.pid)
    process.communicate(p,timeout=TIMEOUT);code=process.returncode
   except subprocess.TimeoutExpired:
    os.killpg(process.pid,signal.SIGTERM)
    try:process.communicate(timeout=5)
    except subprocess.TimeoutExpired:
     os.killpg(process.pid,signal.SIGKILL);process.communicate()
    code=124
   except OSError as error:
    err.write(str(error));code=127
  ok=code==0 and (cwd/'build.py').is_file()
  if ok:
   try:
    import ast
    ast.parse((cwd/'build.py').read_text())
   except (SyntaxError,OSError):ok=False
  message=err_path.read_text(errors='replace')[-8000:].lower()
  transient=code==124 or any(x in message for x in ('rate limit','429','overloaded','temporarily unavailable','connection reset'))
  if ok or not transient or attempt==RETRIES:
   update(name,phase='authored' if ok else 'failed',exitCode=code,ended=time.time(),pid=None)
   return name,ok
  delay=min(120,15*2**attempt);update(name,phase='retry-wait',exitCode=code,retryAfterSeconds=delay,pid=None)
  time.sleep(delay)

def build(name):
 cwd=WORK/'jobs'/name;target=OUT/'families'/name;target.mkdir(parents=True,exist_ok=True);update(name,phase='building',buildStarted=time.time())
 with (cwd/'blender.log').open('w') as log:
  r=subprocess.run([str(BLENDER),'--background','--threads','4','--python-exit-code','1','--python',str(cwd/'build.py'),'--','--out',str(target)],stdout=log,stderr=subprocess.STDOUT,timeout=1800)
 files=list((target/'models').glob('*.glb'));update(name,phase='built' if r.returncode==0 and files else 'build-failed',buildExitCode=r.returncode,models=len(files),buildEnded=time.time())
 return name,r.returncode,len(files)
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('mode',choices=['author','build']);ap.add_argument('--workers',type=int,default=24);ap.add_argument('--families',nargs='*');ap.add_argument('--retries',type=int,default=2);ap.add_argument('--timeout',type=int,default=1500);a=ap.parse_args();WORK.mkdir(parents=True,exist_ok=True)
 if a.workers<1 or a.timeout<1 or a.retries<0:ap.error('workers/timeout must be positive and retries nonnegative')
 RETRIES=a.retries;TIMEOUT=a.timeout
 if (WORK/'status.json').exists():state=json.loads((WORK/'status.json').read_text())
 selected=[j for j in FAMILIES if not a.families or j[0] in a.families]
 (OUT/'design/jobs.json').write_text(json.dumps([{'id':n,'assets':ids,'brief':b}for n,ids,b in FAMILIES],indent=2))
 failed=False
 with concurrent.futures.ThreadPoolExecutor(max_workers=min(a.workers,24 if a.mode=='author' else 2)) as pool:
  futures=[pool.submit(author,j) if a.mode=='author' else pool.submit(build,j[0]) for j in selected]
  for f in concurrent.futures.as_completed(futures):
   try:
    result=f.result();print(json.dumps(result),flush=True)
    failed=failed or (not result[1] if a.mode=='author' else result[1]!=0)
   except Exception as e:failed=True;print(json.dumps({'error':str(e)}),flush=True)
 raise SystemExit(1 if failed else 0)
