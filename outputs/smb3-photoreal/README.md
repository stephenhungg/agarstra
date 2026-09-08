# SMB3 authored asset library

73 GLBs · 25/25 families built · 25/25 contact sheets audited · 0 families approved as photoreal.

Snapshot: 2026-09-08T21:56:05+00:00. Generated from `design/jobs.json`, author/build queue state, existing family files and per-family visual-review hashes. 24 CLI author jobs and 1 supplemental jobs; 25 previews exist; 25 families have current structural evidence.

Open [the local gallery](index.html) to inspect actual Blender/Cycles renders, editable libraries, individual GLBs, manifests and source scripts. Assets remain quality candidates unless explicitly approved in a current recorded review.

These are authored 3D interpretations of SMB3 silhouettes, with physical materials and baked textures. The ROM provides tiles, palettes, object identities and gameplay; it does not contain hidden realistic geometry. The wider catalog includes brief-driven concepts that are not verified source matches or integrated gameplay replacements. Contact-sheet inspection is separate from in-game readability, source-shape accuracy and photoreal approval. No 95% visual-fidelity claim is established.

## Evidence and remaining work

Visual audits are the recorded reviewer’s inspection of exported GLB contact sheets. This generator verifies that preview and model hashes still match; it does not perform a new visual review. Structural checks establish valid exported geometry/material data, not artistic quality. Per-family notes identify issues such as stylized/faceted forms and character proportions. Original author limitations are preserved in manifests, including statements written before central rendering.

Original pixels and their ROM provenance are documented separately in [ROM extraction](../smb3-rom-assets/EXTRACTION.md). Whole-object source correspondence and runtime coverage require the semantic adapter and in-game testing; broad catalog availability does not establish whole-game support. Next work is source silhouette review, animation/pose continuity, scene integration, and measured gameplay performance.

| Family | GLBs | Build | Structural evidence | Contact sheet |
| --- | ---: | --- | --- | --- |
| [aquatic-1](families/aquatic-1/manifest.json) | 3 | done | verified | audited candidate |
| [aquatic-2](families/aquatic-2/manifest.json) | 2 | done | verified | audited candidate |
| [architecture-1](families/architecture-1/manifest.json) | 4 | done | verified | audited candidate |
| [architecture-2](families/architecture-2/manifest.json) | 3 | done | verified | audited candidate |
| [blocks-1](families/blocks-1/manifest.json) | 3 | done | verified | audited candidate |
| [blocks-2](families/blocks-2/manifest.json) | 2 | done | verified | audited candidate |
| [character-kit-1](families/character-kit-1/manifest.json) | 3 | done | verified | audited candidate |
| [character-kit-2](families/character-kit-2/manifest.json) | 3 | done | verified | audited candidate |
| [clouds](families/clouds/manifest.json) | 2 | done | verified | audited candidate |
| [creatures-1](families/creatures-1/manifest.json) | 3 | done | verified | audited candidate |
| [creatures-2](families/creatures-2/manifest.json) | 2 | done | verified | audited candidate |
| [items-1](families/items-1/manifest.json) | 4 | done | verified | audited candidate |
| [items-2](families/items-2/manifest.json) | 4 | done | verified | audited candidate |
| [mechanisms-1](families/mechanisms-1/manifest.json) | 3 | done | verified | audited candidate |
| [mechanisms-2](families/mechanisms-2/manifest.json) | 3 | done | verified | audited candidate |
| [pipes-1](families/pipes-1/manifest.json) | 3 | done | verified | audited candidate |
| [pipes-2](families/pipes-2/manifest.json) | 2 | done | verified | audited candidate |
| [set-dressing-1](families/set-dressing-1/manifest.json) | 3 | done | verified | audited candidate |
| [set-dressing-2](families/set-dressing-2/manifest.json) | 3 | done | verified | audited candidate |
| [terrain-1](families/terrain-1/manifest.json) | 3 | done | verified | audited candidate |
| [terrain-2](families/terrain-2/manifest.json) | 3 | done | verified | audited candidate |
| [vegetation-1](families/vegetation-1/manifest.json) | 3 | done | verified | audited candidate |
| [vegetation-2](families/vegetation-2/manifest.json) | 3 | done | verified | audited candidate |
| [worldmap-1](families/worldmap-1/manifest.json) | 3 | done | verified | audited candidate |
| [worldmap-2](families/worldmap-2/manifest.json) | 3 | done | verified | audited candidate |

## Reproduce

The scripts use the original workspace layout (`outputs/` alongside `work/`). Authoring requires an authenticated Codex CLI at the path below and selects `gpt-6-astra`. Existing authored jobs resume without re-authoring. Author prompts/results are in `work/photoreal-swarm/jobs/`; exported source copies are in `sources/`.

```sh
# Run from the original workspace root. Requires authenticated Codex CLI
# at work/photoreal-swarm/runtime/node_modules/.bin/codex.
python3 outputs/smb3-photoreal/tools/swarm.py author --workers 24

# Build/render all authored families, including extra-build-jobs.json.
# This queue has exactly two Blender slots; run only one queue process.
python3 outputs/smb3-photoreal/tools/build_queue.py --max-wait 7200

# Alternatively, rebuild/resume selected families after editing their build.py.
python3 outputs/smb3-photoreal/tools/build_queue.py --families blocks-1 clouds --max-wait 1800

# Refresh this gallery and report after builds or visual reviews.
python3 outputs/smb3-photoreal/tools/build_gallery.py
```

The two build commands are alternatives: never run two queue instances concurrently. The build queue itself permits two Blender processes. It resumes matching completed jobs and retries changed scripts; unchanged failed jobs are skipped until corrected. Blender is currently configured at `/Volumes/Blender/Blender.app/Contents/MacOS/Blender`; change the `BLENDER` constant in the queue if needed. `swarm.py build` is an older direct build route that does not provide the same validation/render pipeline; use `build_queue.py`.

The gallery generator writes only `index.html` and this README. Run it after the queue finishes or review files change. A pending/stale audit means the recorded hashes do not cover the current preview and all models, or no review exists.
