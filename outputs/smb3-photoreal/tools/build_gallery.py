#!/usr/bin/env python3
"""Regenerate local gallery/report from existing outputs; never starts Blender."""
import hashlib, html, json
from datetime import datetime, timezone
from pathlib import Path
OUT = Path(__file__).resolve().parents[1]
WORK = OUT.parents[1] / 'work/photoreal-swarm'
def read(p, default):
    return json.loads(p.read_text()) if p.exists() else default
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else None
def esc(s): return html.escape(str(s))
def link(p, label):
    return f'<a href="{esc(p.relative_to(OUT).as_posix())}">{esc(label)}</a>' if p.exists() else ''
def main():
    jobs = read(OUT/'design/jobs.json', [])
    authors = read(WORK/'status.json', {})
    extra = read(WORK/'extra-build-jobs.json', {})
    builds = read(WORK/'build-status.json', {})
    names = sorted({j['id'] for j in jobs} | set(extra) | set(builds))
    rows = []; cards = []; counts = dict(models=0, done=0, structural=0, audited=0, approved=0, previews=0)
    for name in names:
        folder = OUT/'families'/name
        models = sorted((folder/'models').glob('*.glb'))
        preview = folder/'preview.png'; review = read(folder/'visual-review.json', {})
        manifest = read(folder/'manifest.json', {})
        state = builds.get(name, {})
        audited = bool(review.get('previewSHA256') and sha(preview)==review['previewSHA256'] and models and {p.stem:sha(p) for p in models}=={m['id']:m['sha256'] for m in review.get('models',[])})
        structural = bool(state.get('structuralPassed') and models and {p.stem:sha(p) for p in models}==state.get('modelSHA256'))
        counts['models'] += len(models); counts['done'] += state.get('phase')=='done'; counts['structural'] += structural
        counts['audited'] += audited; counts['approved'] += audited and review.get('photorealApproved',False); counts['previews'] += preview.exists()
        quality = 'contact sheet audited · candidate' if audited else 'visual audit pending or stale · candidate'
        if audited and review.get('photorealApproved'): quality='photoreal approved by recorded reviewer'
        links = [link(folder/'library.blend','Blender library'), link(folder/'manifest.json','Manifest'), link(folder/'validation.json','GLB checks'), link(folder/'visual-review.json','Visual review'), link(OUT/'sources'/f'{name}.py','Authoring source')]
        picture = f'<a href="families/{esc(name)}/preview.png"><img loading="lazy" src="families/{esc(name)}/preview.png" alt="Rendered exported GLB contact sheet: {esc(name)}"></a>' if preview.exists() else '<div class="missing">Preview not built yet</div>'
        evidence=[]
        assets=manifest.get('assets',[]) if isinstance(manifest,dict) else manifest
        if isinstance(assets,list):
            for a in assets:
                if not isinstance(a,dict):continue
                basis=a.get('source_basis',a.get('sourcebasis',a.get('sourceBasis')))
                limits=a.get('known_quality_limitations',a.get('knownqualitylimitations',a.get('knownQualityLimitations')))
                evidence.append({'asset':a.get('asset_id',a.get('id',a.get('assetId'))),'source_basis':basis,'author_limitations':limits})
        note=review.get('notes','No recorded visual inspection.')
        if review and not audited: note='Review hashes do not match all current files. '+note
        cards.append(f'<article>{picture}<div class="body"><h2>{esc(name)}</h2><p class="badge">{esc(quality)}</p><p>{esc(note)}</p><p class="meta">{len(models)} GLBs · build {esc(state.get("phase","pending"))} · current structural evidence {"verified" if structural else "pending/stale"}</p><p class="links">{" · ".join(x for x in links if x)}</p><p class="assets">{" · ".join(link(p,p.stem) for p in models)}</p><details><summary>Source correspondence and author limitations</summary><p>Author statements below are provenance notes, not independent equivalence checks. Later visual review above may supersede author-time review status.</p><pre>{esc(json.dumps(evidence,indent=2))}</pre></details></div></article>')
        rows.append(f'| [{name}](families/{name}/manifest.json) | {len(models)} | {state.get("phase","pending")} | {"verified" if structural else "pending/stale"} | {"audited candidate" if audited else "pending/stale"} |')
    stamp=datetime.now(timezone.utc).isoformat(timespec='seconds')
    summary=f'{counts["models"]} GLBs · {counts["done"]}/{len(names)} families built · {counts["audited"]}/{len(names)} contact sheets audited · {counts["approved"]} families approved as photoreal'
    commands='''# Run from the original workspace root. Requires authenticated Codex CLI\n# at work/photoreal-swarm/runtime/node_modules/.bin/codex.\npython3 outputs/smb3-photoreal/tools/swarm.py author --workers 24\n\n# Build/render all authored families, including extra-build-jobs.json.\n# This queue has exactly two Blender slots; run only one queue process.\npython3 outputs/smb3-photoreal/tools/build_queue.py --max-wait 7200\n\n# Alternatively, rebuild/resume selected families after editing their build.py.\npython3 outputs/smb3-photoreal/tools/build_queue.py --families blocks-1 clouds --max-wait 1800\n\n# Refresh this gallery and report after builds or visual reviews.\npython3 outputs/smb3-photoreal/tools/build_gallery.py'''
    caveat='These are authored 3D interpretations of SMB3 silhouettes, with physical materials and baked textures. The ROM provides tiles, palettes, object identities and gameplay; it does not contain hidden realistic geometry. The wider catalog includes brief-driven concepts that are not verified source matches or integrated gameplay replacements. Contact-sheet inspection is separate from in-game readability, source-shape accuracy and photoreal approval. No 95% visual-fidelity claim is established.'
    OUT.joinpath('index.html').write_text(f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>SMB3 · authored asset library</title><style>
:root{{color-scheme:dark;font-family:system-ui,sans-serif;background:#141815;color:#e9eee7}}*{{box-sizing:border-box}}body{{margin:0}}header,main,footer{{max-width:1440px;margin:auto;padding:32px}}header{{padding-top:56px}}h1{{font-size:clamp(32px,5vw,64px);letter-spacing:-.04em;margin:12px 0}}p{{line-height:1.6}}header p{{max-width:980px}}a{{color:#b7dab4}}.eyebrow,.meta{{color:#a3afa2;font-size:13px}}.stats{{font-size:20px;color:#d8eabd}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:24px}}article{{background:#1d231e;border:1px solid #354035;border-radius:14px;overflow:hidden}}img{{width:100%;display:block;aspect-ratio:1.5;object-fit:contain;background:#171b18}}.body{{padding:22px}}h2{{margin:0;font-size:22px}}.badge{{font-size:12px;color:#ddc88f}}.links,.assets{{font-size:13px}}details{{font-size:13px;color:#bec9bc}}summary{{cursor:pointer}}pre{{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;line-height:1.55}}.missing{{height:220px;display:grid;place-items:center}}footer{{color:#a3afa2}}@media(max-width:420px){{header,main,footer{{padding:20px}}.grid{{grid-template-columns:1fr}}}}
</style><header><div class="eyebrow">ROM → semantic scene → authored Blender assets</div><h1>SMB3 asset workshop</h1><p class="stats">{esc(summary)}</p><p>{esc(caveat)}</p><p>{len(jobs)} CLI author jobs · {len(extra)} supplemental jobs · {counts['structural']} current structural checks · snapshot {esc(stamp)}</p><p><a href="animated/README.md">Animated character library</a> · <a href="animated/pose-contact-sheet.png">Animation poses</a> · <a href="README.md">Build report & reproduction</a> · <a href="visual-review.json">Recorded visual review</a> · <a href="design/style.json">Style contract</a> · <a href="../smb3-rom-assets/EXTRACTION.md">Original ROM extraction evidence</a></p></header><main class="grid">{''.join(cards)}</main><footer><h2>Reproduce and refresh</h2><pre>{esc(commands)}</pre><p>Build scripts currently use /Volumes/Blender/Blender.app/Contents/MacOS/Blender. Update the BLENDER constant if installed elsewhere. A matching SHA-256 for each preview and GLB is required before this page counts a recorded audit as current.</p></footer></html>''')
    OUT.joinpath('README.md').write_text(f'''# SMB3 authored asset library

{summary}.

Snapshot: {stamp}. Generated from `design/jobs.json`, author/build queue state, existing family files and per-family visual-review hashes. {len(jobs)} CLI author jobs and {len(extra)} supplemental jobs; {counts['previews']} previews exist; {counts['structural']} families have current structural evidence.

Open [the local gallery](index.html) to inspect actual Blender/Cycles renders, editable libraries, individual GLBs, manifests and source scripts. Assets remain quality candidates unless explicitly approved in a current recorded review.

{caveat}

## Evidence and remaining work

Visual audits are the recorded reviewer’s inspection of exported GLB contact sheets. This generator verifies that preview and model hashes still match; it does not perform a new visual review. Structural checks establish valid exported geometry/material data, not artistic quality. Per-family notes identify issues such as stylized/faceted forms and character proportions. Original author limitations are preserved in manifests, including statements written before central rendering.

Original pixels and their ROM provenance are documented separately in [ROM extraction](../smb3-rom-assets/EXTRACTION.md). Whole-object source correspondence and runtime coverage require the semantic adapter and in-game testing; broad catalog availability does not establish whole-game support. Next work is source silhouette review, animation/pose continuity, scene integration, and measured gameplay performance.

| Family | GLBs | Build | Structural evidence | Contact sheet |
| --- | ---: | --- | --- | --- |
{chr(10).join(rows)}

## Reproduce

The scripts use the original workspace layout (`outputs/` alongside `work/`). Authoring requires an authenticated Codex CLI at the path below and selects `gpt-6-astra`. Existing authored jobs resume without re-authoring. Author prompts/results are in `work/photoreal-swarm/jobs/`; exported source copies are in `sources/`.

```sh
{commands}
```

The two build commands are alternatives: never run two queue instances concurrently. The build queue itself permits two Blender processes. It resumes matching completed jobs and retries changed scripts; unchanged failed jobs are skipped until corrected. Blender is currently configured at `/Volumes/Blender/Blender.app/Contents/MacOS/Blender`; change the `BLENDER` constant in the queue if needed. `swarm.py build` is an older direct build route that does not provide the same validation/render pipeline; use `build_queue.py`.

The gallery generator writes only `index.html` and this README. Run it after the queue finishes or review files change. A pending/stale audit means the recorded hashes do not cover the current preview and all models, or no review exists.
''')
    print(json.dumps({'families':len(names),**counts,'gallery':str(OUT/'index.html')}))
if __name__=='__main__': main()
