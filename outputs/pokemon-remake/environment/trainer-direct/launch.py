from pathlib import Path
import json,subprocess,datetime,os
out=Path(__file__).parent.resolve(); manifest=json.loads((out/'manifest.json').read_text()); marker=out/'submission.json'
if marker.exists():raise SystemExit('Existing submission record; refusing to create a second job. Inspect saved process/job first.')
args=['/Users/stephenhung/.nvm/versions/node/v22.21.1/bin/higgsfield','generate','create','image_to_3d']
for key,value in manifest['params'].items():args.extend(['--'+key,str(value).lower() if isinstance(value,bool) else str(value)])
args.extend(['--wait','--wait-timeout','30m','--wait-interval','10s','--json'])
record={'startedUTC':datetime.datetime.now(datetime.timezone.utc).isoformat(),'status':'starting','commandArgs':args,'preparedPNGSHA256':manifest['preparedPNGSHA256']};marker.write_text(json.dumps(record,indent=2))
with (out/'job-result.json').open('w') as stdout,(out/'job-stderr.log').open('w') as stderr:
 proc=subprocess.Popen(args,stdout=stdout,stderr=stderr);record.update(pid=proc.pid,status='running');marker.write_text(json.dumps(record,indent=2));print(json.dumps({'pid':proc.pid,'record':str(marker)}),flush=True);code=proc.wait()
record.update(exitCode=code,status='cli-exited',finishedUTC=datetime.datetime.now(datetime.timezone.utc).isoformat());marker.write_text(json.dumps(record,indent=2));print(json.dumps(record),flush=True)
