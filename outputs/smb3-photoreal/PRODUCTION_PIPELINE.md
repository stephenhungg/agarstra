# Production asset enforcement

Implemented September 8, 2026. Production assembly, both runtime GLB loaders/reload paths, and packaging now consume the same evidence contract. The current 73 model candidates are **not** thereby approved: the 25 family reviews decline photoreal approval and there are no real production acceptance bundles yet.

## Boundaries

- Production is the default for assembly, build, and packaging. Legacy `phase: done`, structural checks, a filename, or `acceptance.json` alone do not grant admission.
- Prototype is an explicit build profile, visibly labeled and packaged separately. A URL query cannot downgrade a production build.
- The Python assembler reruns the evidence gate, verifies actual embedded GLB structure, preserves animated-source/bounds/clip checks, and invokes the same JavaScript verifier used by the consumers before publication.
- A release lives under `public/assets/releases/<revision>/`. The registry pointer changes atomically only after the complete release passes. Older release files remain available to readers. Failed releases never partially overwrite active model files.
- Both renderers verify complete evidence chains and parse the exact verified GLB bytes without a second model URL fetch. External/data URI dependencies are prohibited for production GLBs.
- Reload stages both renderers before committing, rejects failed/superseded attempts, and replaces complete maps. Removed IDs are revoked; failure retains the previous release and is shown in the UI.
- Packaging checks public assets before building, then the new build and staged app. It rejects stale source/build/profile/evidence, strips unreferenced models, preserves pinned source/evidence models, checks staged bytes and signing, and restores the old app if publication fails.

## Prepare a real reviewed candidate

Use the schema in `../skills/rom-remake/references/evidence-gate.md`. Collect actual target, camera, replay, technical captures, and independent visual inspection. Never generate positive review records to pass the checker.

Create the runtime context before reviewing:

```sh
node outputs/smb3-demo/scripts/runtime-context.mjs > /path/to/candidate/runtime.json
```

The exact output bytes must be the candidate's `context.runtime` payload. It includes content hashes for all runtime source files, the dependency lockfile, Vite config, Electron/preload, HTML, and the context builder. Build embeds the same fingerprint and exports `runtime-build.json`; changed source invalidates old reviews. Camera, replay, target and their relevant dependencies must also be explicit pinned context entries. This is content binding, not proof that a reviewer performed a meaningful comparison.

The candidate manifest additionally requires a **review-pinned** mapping:

```json
"runtime_entry": {
  "id": "actual-supported-runtime-id",
  "artifact": "glb",
  "family": "actual-family"
}
```

For source-tile replacements, include `width`, `height`, and `source.sourceIdentity` in that same pinned mapping. Do not include generated `path`, `bundle`, or `sha256` fields. Consumers reject unreviewed metadata/remapping.

An animated asset also requires pinned `animation_manifest` and `animation_source` artifacts. The manifest must identify its final GLB hash, original source hash, bind-bounds error below `1e-4`, and actual clip names. Review the final animated GLB, not only the static original.

Publish an isolated accepted bundle with the skill's `evidence_gate.py --profile production --output ...` after real reviews. Then select bundles in a release plan:

```json
{
  "schema": 1,
  "entries": [
    {"bundle": "accepted/actual-reviewed-bundle", "artifact": "glb"}
  ]
}
```

Bundle paths resolve relative to the plan. An explicit empty `entries` list revokes all replacements in that registry; it does not mean a scene has passed visual acceptance.

## Assemble and deliver

From the repository root:

```sh
python3 outputs/smb3-photoreal/tools/assemble_runtime.py --plan /path/to/photo-release.json
python3 outputs/smb3-photoreal/tools/assemble_runtime.py --plan /path/to/source-release.json --registry source-registry.json
npm --prefix outputs/smb3-demo run package:check
npm --prefix outputs/smb3-demo run package
```

Both registries must be explicit production registries, even if one has an intentionally empty replacement scope. Production packaging is currently expected to reject the legacy candidate registries. The existing app is not touched by this rejection.

Candidate preview stays available:

```sh
python3 outputs/smb3-photoreal/tools/assemble_runtime.py --profile prototype
npm --prefix outputs/smb3-demo run start:prototype
npm --prefix outputs/smb3-demo run package:prototype
```

Prototype assembly publishes `photoreal-prototype-registry.json`, never the production pointer. `--include-rendering` is allowed only with the explicit prototype profile. The packaged preview is `outputs/SMB3 Asset Lab Prototype.app`. Production output remains `outputs/SMB3 Asset Lab.app`.

## Verification

```sh
python3 -m unittest discover -s outputs/skills/rom-remake/scripts -p test_evidence_gate.py
python3 -m unittest discover -s outputs/smb3-photoreal/tools -p 'test_*runtime.py'
python3 -m unittest discover -s outputs/smb3-photoreal/tools -p test_consumer_chain.py
npm --prefix outputs/smb3-demo test
node outputs/smb3-demo/tests/runtime-reload-test.mjs
```

Tests use temporary, explicitly synthetic accepted fixtures. Cross-language tests pass two independent bundles from Python assembly through the real JavaScript verifier, then mutate evidence, GLBs, identities, and runtime context to prove rejection. Renderer tests cover exact-byte parsing, revocation, failure preservation, and superseded reloads. They prove enforcement behavior, not artistic quality.

## Remaining production work

Automated target-driven author/render/critique/revision is not implemented by this consumer boundary. Real asset and scene acceptance, deformation-quality characters, and broader scene/form/action coverage remain incomplete. Image-to-3D and Unreal are also not implemented. Review records are attestations protected by ordinary repository/storage permissions, not cryptographic signatures or proof of observation. Do not call the full high-fidelity pipeline complete because its gates now work.
