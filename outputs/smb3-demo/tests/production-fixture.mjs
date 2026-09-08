// Synthetic mechanical gate evidence. Never represents an actual visual approval.
import {sha256} from '../src/production-gate.js';
const encode = value => new TextEncoder().encode(JSON.stringify(value));
export async function productionFixture(runtimeBytes = encode({schema:1,fixture:'synthetic runtime'}), runtimeEntry = {id:'ground-grass',artifact:'glb'}) {
  const files = new Map(), base='accepted/test';
  const put = (path,bytes) => files.set(`${base}/${path}`,bytes);
  const pin = async (path,bytes,prefix='candidate') => {put(`${prefix}/${path}`,bytes);return {path,sha256:await sha256(bytes)};};
  const json = JSON.stringify({asset:{version:'2.0'},scene:0,scenes:[{nodes:[0]}],nodes:[{mesh:0}],meshes:[{primitives:[{attributes:{POSITION:0}}]}],buffers:[{byteLength:36}],bufferViews:[{buffer:0,byteOffset:0,byteLength:36}],accessors:[{bufferView:0,componentType:5126,count:3,type:'VEC3',min:[0,0,0],max:[1,1,0]}]});
  const payload = new TextEncoder().encode(json.padEnd(Math.ceil(json.length/4)*4,' '));
  const binary = new Float32Array([0,0,0,1,0,0,0,1,0]);
  const glb = new Uint8Array(28+payload.length+binary.byteLength), view=new DataView(glb.buffer);
  view.setUint32(0,0x46546c67,true);view.setUint32(4,2,true);view.setUint32(8,glb.length,true);view.setUint32(12,payload.length,true);view.setUint32(16,0x4e4f534a,true);glb.set(payload,20);
  view.setUint32(20+payload.length,binary.byteLength,true);view.setUint32(24+payload.length,0x004e4942,true);glb.set(new Uint8Array(binary.buffer),28+payload.length);
  const context={}; for(const id of ['target','runtime','camera','replay']) context[id]=await pin(`${id}.json`,id==='runtime'?runtimeBytes:encode({fixture:id}));
  const artifact=await pin('model.glb',glb);
  const candidate={schema:1,id:'synthetic-v1',author:'fixture-author',source_ids:['synthetic-source'],runtime_entry:runtimeEntry,artifacts:{glb:artifact},context};
  const contract={schema:1,required_artifacts:['glb'],required_context:['target','runtime','camera','replay'],technical_checks:['parse'],visual_checks:['compare']};
  put('candidate/manifest.json',encode(candidate));put('contract.json',encode(contract));
  const candidateHash=await sha256(encode(candidate)),contractHash=await sha256(encode(contract));
  for(const kind of ['technical','visual']) {
    const evidence=await pin('capture.txt',encode({synthetic:true}),`reviews/${kind}`);
    put(`reviews/${kind}/report.json`,encode({schema:1,candidate_sha256:candidateHash,contract_sha256:contractHash,reviewer:'fixture-reviewer',inspected:true,verdict:'pass',blockers:[],evidence:{capture:evidence},checks:{[kind==='technical'?'parse':'compare']:{status:'pass',reason:'Synthetic fixture only',evidence:['capture']}}}));
  }
  const acceptance={schema:1,candidate_id:candidate.id,profile:'production',status:'production-evidence-accepted',candidate_sha256:candidateHash,contract_sha256:contractHash,artistic_quality_evaluated_by_checker:false,files:{}};
  for(const [path,bytes] of files)acceptance.files[path.slice(base.length+1)]=await sha256(bytes);
  put('acceptance.json',encode(acceptance));
  const runtimeHash=await sha256(runtimeBytes);
  const registry={schemaVersion:2,profile:'production',runtime_sha256:runtimeHash,entries:[{...candidate.runtime_entry,bundle:base,path:`${base}/candidate/model.glb`,sha256:artifact.sha256}]};
  return {files,registry,runtimeHash,readBytes:async path=>{if(!files.has(path))throw new Error(`Missing ${path}`);return files.get(path);},encode};
}
