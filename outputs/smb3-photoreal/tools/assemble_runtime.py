#!/usr/bin/env python3
"""Publish evidence-accepted releases atomically; candidate preview is explicit."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import uuid

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/smb3-photoreal'
APP = ROOT / 'outputs/smb3-demo'
sys.path.insert(0, str(ROOT / 'outputs/skills/rom-remake/scripts'))
from evidence_gate import GateError, digest, document, gate, require
from validate_models import inspect, parse_glb


def runtime_snapshot():
    return subprocess.check_output(['node', str(APP / 'scripts/runtime-context.mjs')], cwd=APP)


def embedded_glb(file):
    raw, doc, _ = parse_glb(file)
    for item in doc.get('buffers', []) + doc.get('images', []):
        require('uri' not in item, 'release GLB must embed all buffers and images')
    result = inspect(file, {}, {})
    require(result['structuralReady'], f'{file.name}: structural validation failed: {result["errors"]}')
    return raw, doc


def validate_animation(candidate, root, raw, doc, asset_id):
    """Preserve the prototype animator's source, final-byte, bounds and clip checks."""
    if not doc.get('animations'):
        return
    artifacts = candidate['artifacts']
    require({'animation_manifest', 'animation_source'} <= set(artifacts),
            'animated asset requires pinned animation_manifest and animation_source artifacts')
    manifest = json.loads((root / artifacts['animation_manifest']['path']).read_bytes())
    rows = [a for a in manifest.get('assets', []) if a.get('asset_id') == asset_id]
    require(len(rows) == 1, 'animation manifest must identify this asset exactly once')
    animation = rows[0]
    require(animation.get('sha256') == digest(raw), 'animated final checksum mismatch')
    require(animation.get('sourceSHA256') == artifacts['animation_source']['sha256'], 'stale animated source')
    error = animation.get('bindBoundsMaxError')
    require(type(error) in (float, int) and 0 <= error < 1e-4, 'animated bind bounds changed')
    clips = [a.get('name') for a in doc['animations']]
    require(all(isinstance(c, str) and c for c in clips) and len(clips) == len(set(clips)), 'invalid animation clips')
    require(set(clips) == {a['name'] for a in animation.get('clips', [])}, 'animation clips missing')


def accepted_entries(plan_path, stage, prefix, expected_runtime):
    plan, _ = document(plan_path)
    require(isinstance(plan.get('entries'), list), 'plan.entries must be a list (empty explicitly revokes all assets)')
    entries, seen = [], set()
    for index, selection in enumerate(plan['entries']):
        require(isinstance(selection, dict) and isinstance(selection.get('bundle'), str), 'plan entry requires bundle')
        bundle = (Path(plan_path).parent / selection['bundle']).resolve()
        candidate, candidate_bytes = document(bundle / 'candidate/manifest.json')
        acceptance, _ = document(bundle / 'acceptance.json')
        record = gate(bundle / 'candidate/manifest.json', bundle / 'contract.json',
                      bundle / 'reviews/technical/report.json', bundle / 'reviews/visual/report.json', profile='production')
        require(record == acceptance, 'acceptance record does not match revalidated bundle')
        require(digest(candidate_bytes) == record['candidate_sha256'], 'candidate changed during assembly')
        mapping = candidate.get('runtime_entry')
        require(isinstance(mapping, dict), 'candidate requires review-pinned runtime_entry mapping')
        asset_id = mapping.get('id')
        require(isinstance(asset_id, str) and asset_id.strip() and asset_id not in seen, 'missing or duplicate runtime asset ID')
        seen.add(asset_id)
        artifact = selection.get('artifact', 'glb')
        require(mapping.get('artifact') == artifact and artifact in candidate['artifacts'], 'artifact does not match reviewed runtime mapping')
        require(not {'path', 'sha256', 'bundle'} & set(mapping), 'runtime_entry cannot override generated paths or checksums')
        require(candidate['context']['runtime']['sha256'] == digest(expected_runtime), 'review belongs to a different runtime build')
        relative = f'accepted/{index}'
        destination = stage / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        # Republish from exact checked bytes, not shutil copies racing with review reads.
        copied = gate(bundle / 'candidate/manifest.json', bundle / 'contract.json',
                      bundle / 'reviews/technical/report.json', bundle / 'reviews/visual/report.json',
                      profile='production', output=destination)
        require(copied == record, 'bundle changed during assembly')
        model = destination / 'candidate' / candidate['artifacts'][artifact]['path']
        raw, doc = embedded_glb(model)
        validate_animation(candidate, destination / 'candidate', raw, doc, asset_id)
        entries.append({**mapping, 'path': f'{prefix}/{relative}/candidate/{candidate["artifacts"][artifact]["path"]}',
                        'bundle': f'{prefix}/{relative}', 'sha256': digest(raw),
                        'quality': 'production-evidence-accepted'})
    return entries


def prototype_entries(stage, prefix, include_rendering=False):
    status = json.loads((ROOT / 'work/photoreal-swarm/build-status.json').read_bytes())
    manifest_path = OUT / 'animated/manifest.json'
    animated = {a['asset_id']: a for a in json.loads(manifest_path.read_bytes()).get('assets', [])} if manifest_path.exists() else {}
    entries, seen = [], set()
    for family, job in sorted(status.items()):
        if job.get('phase') != 'done' and not (include_rendering and job.get('structuralPassed')):
            continue
        for original in sorted((OUT / 'families' / family / 'models').glob('*.glb')):
            asset_id = original.stem
            require(asset_id not in seen, 'duplicate asset ID')
            seen.add(asset_id)
            file = original
            animation = animated.get(asset_id)
            if animation:
                require(animation['sourceSHA256'] == digest(original.read_bytes()), f'stale animated source: {asset_id}')
                file = OUT / 'animated' / animation['path']
            raw, doc = embedded_glb(file)
            if animation:
                require(animation['sha256'] == digest(raw), f'animated checksum mismatch: {asset_id}')
                require(0 <= animation['bindBoundsMaxError'] < 1e-4, f'animated bind bounds changed: {asset_id}')
                require(bool(doc.get('animations')) and {c['name'] for c in doc['animations']} == {c['name'] for c in animation['clips']}, 'animation clips missing')
            target = stage / 'models' / f'{asset_id}.glb'
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(raw)
            entry = {'id': asset_id, 'path': f'{prefix}/models/{asset_id}.glb', 'family': family,
                     'sha256': digest(raw), 'bytes': len(raw), 'sourceManifest': f'families/{family}/manifest.json',
                     'quality': 'prototype-only; visual acceptance not granted'}
            if animation:
                entry.update(sourceSHA256=animation['sourceSHA256'], animationManifest='animated/manifest.json', clips=[c['name'] for c in doc['animations']])
            entries.append(entry)
    return entries


def verify_staged_registry(stage, prefix, expected_runtime):
    script = """
import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
const [modulePath,stage,prefix,hash] = process.argv.slice(1);
const {verifyRegistry} = await import(pathToFileURL(modulePath));
const registry = JSON.parse(fs.readFileSync(path.join(stage,'registry.json')));
await verifyRegistry(registry, async name => {
  if (!name.startsWith(prefix+'/')) throw new Error('Staged path outside release');
  const file = path.resolve(stage,name.slice(prefix.length+1));
  if (!file.startsWith(path.resolve(stage)+path.sep)) throw new Error('Staged path escape');
  return fs.readFileSync(file);
}, {profile:'production',expectedRuntimeHash:hash});
"""
    subprocess.run(['node', '--input-type=module', '-e', script,
                    str(APP / 'src/production-gate.js'), str(stage), prefix, digest(expected_runtime)],
                   check=True, capture_output=True, text=True)


def assemble(*, profile='production', plan=None, assets=None, registry='photoreal-registry.json', include_rendering=False, runtime=None):
    require(profile in ('production', 'prototype'), 'invalid release profile')
    require(not include_rendering or profile == 'prototype', '--include-rendering requires explicit --profile prototype')
    require(profile != 'production' or plan is not None, 'production assembly requires --plan with accepted bundles; legacy candidates are not approved')
    require(profile != 'prototype' or registry == 'photoreal-registry.json', 'prototype assembly supports the photoreal preview registry only')
    require(registry in ('photoreal-registry.json', 'source-registry.json'), 'unsupported registry name')
    snapshot = runtime if runtime is not None else runtime_snapshot()
    assets = Path(assets or APP / 'public/assets')
    assets.mkdir(parents=True, exist_ok=True)
    releases = assets / 'releases'
    releases.mkdir(exist_ok=True)
    release_id = uuid.uuid4().hex
    prefix = f'releases/{release_id}'
    stage = Path(tempfile.mkdtemp(prefix='.assembling-', dir=releases))
    published = releases / release_id
    pointer_tmp = assets / f'.registry-{release_id}.tmp'
    pointer = assets / ('photoreal-prototype-registry.json' if profile == 'prototype' else registry)
    try:
        entries = accepted_entries(plan, stage, prefix, snapshot) if profile == 'production' else prototype_entries(stage, prefix, include_rendering)
        data = {'schemaVersion': 2, 'profile': profile, 'runtime_sha256': digest(snapshot), 'entries': entries}
        (stage / 'registry.json').write_text(json.dumps(data, indent=2) + '\n')
        if profile == 'production':
            verify_staged_registry(stage, prefix, snapshot)
        # The active pointer is the only commit point. Older releases stay available to readers.
        os.rename(stage, published)
        pointer_tmp.write_bytes((published / 'registry.json').read_bytes())
        os.replace(pointer_tmp, pointer)
        return {'registry': str(pointer), 'profile': profile, 'models': len(entries), 'release': release_id}
    finally:
        if stage.exists():
            shutil.rmtree(stage)
        pointer_tmp.unlink(missing_ok=True)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--profile', choices=['production', 'prototype'], default='production')
    ap.add_argument('--plan', type=Path)
    ap.add_argument('--assets', type=Path, help='asset root; defaults to app public/assets')
    ap.add_argument('--registry', choices=['photoreal-registry.json', 'source-registry.json'], default='photoreal-registry.json')
    ap.add_argument('--include-rendering', action='store_true')
    args = ap.parse_args()
    try:
        print(json.dumps(assemble(**vars(args)), indent=2))
    except (GateError, OSError, ValueError, TypeError, KeyError, subprocess.CalledProcessError) as error:
        detail = error.stderr.strip() if isinstance(error, subprocess.CalledProcessError) and error.stderr else str(error)
        print(f'assembly rejected: {detail}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
