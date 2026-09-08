# Evidence gate helper

Use `scripts/evidence_gate.py` to reject missing, stale, malformed, or failed evidence before creating an isolated accepted asset bundle. Python 3.9+ and the standard library are sufficient. Check-only works cross-platform; atomic publication supports macOS and Linux with `renameat2`. Unsupported publication platforms fail closed.

This checker does **not** inspect images, decide artistic merit, run Blender, generate reviews, authenticate reviewer identities, validate ROM provenance claims, or install anything into the live game. Its production status means the supplied review evidence satisfies the pinned contract. Actual visual inspection and truthful reviewer attestations remain necessary. A game loader must separately enforce the accepted bundle boundary; this helper does not retrofit that enforcement into an existing prototype.

## Invoke

Run from the skill directory; all arguments can use absolute paths:

```sh
python3 scripts/evidence_gate.py \
  --candidate /path/to/candidate/manifest.json \
  --contract /path/to/contract.json \
  --technical /path/to/technical/report.json \
  --visual /path/to/visual/report.json \
  --profile production \
  --output /path/to/new-accepted-bundle
```

Omit `--output` for check-only. The output parent must already exist and the output directory must **not** exist. An existing directory, including an empty one, is never replaced. The helper does not write into a live assets directory. Exit code 0 means the evidence gate passed; exit code 1 includes a rejection reason. `--profile` is mandatory. Prototype checks may omit visual review, but their record always says `prototype-only`. A provided visual review is fully checked even for prototype runs.

## Schema 1

All documents are JSON objects with integer `"schema": 1`. Duplicate keys are rejected. Hashes are lowercase SHA-256 of exact file bytes, including JSON whitespace. Finish the contract and candidate manifest **before** reviewing them; any edit requires fresh review pins. No automatic pin refresh or approval migration is provided.

Candidate manifest:

- `id`: nonempty candidate/revision identifier.
- `author`: nonempty asset author identity.
- `source_ids`: nonempty unique list of provenance IDs that resolve in the project's source inventory. This checker verifies presence, not the inventory's truth.
- `artifacts`: nonempty map of logical IDs to `{ "path": "relative/file.glb", "sha256": "64 lowercase hex digits" }`.
- `context`: same map format for the inputs that can change review meaning.

Paths in both maps are relative to the candidate manifest's parent. Use forward slashes and ordinary relative paths. Absolute paths, `.`/`..` components, backslashes, and symlinks escaping the document root are rejected. Every listed file, including non-required extras, is read and hash-checked. List separate texture files and other dependencies individually; a GLB hash cannot pin a separately loaded external texture.

The contract defines four nonempty arrays of unique nonempty IDs:

```json
{
  "schema": 1,
  "required_artifacts": ["glb", "blender_source"],
  "required_context": ["target", "runtime", "camera", "replay"],
  "technical_checks": ["glb-load", "rig-deformation", "runtime-replay"],
  "visual_checks": ["silhouette", "materials", "animation", "runtime-composition"]
}
```

This example is a starting contract, not universal acceptance criteria. Choose checks and quantitative budgets for the actual asset and requested production scope; add text/rubrics to the contract as needed. Their bytes are pinned by each review. The checker requires all four arrays even for prototype checks, keeping the intended visual criteria explicit before production review. In production, `required_context` must include the exact IDs `target`, `runtime`, `camera`, and `replay`:

- `target`: the approved visual reference/brief, including its acceptance criteria.
- `runtime`: a reproducible description of renderer build, lighting, material settings, and dependencies, with content pins for inputs.
- `camera`: exact framing and capture settings used for comparison.
- `replay`: deterministic state/input trace identifying the reviewed poses/actions/scenes.

A hash of a descriptive file does not recursively validate files mentioned in its contents. List those dependencies in `context` as additional entries when their changes must invalidate review. Likewise, the checker cannot tell whether `target` contains a meaningful reference or an empty image; the reviewer must inspect the actual content.

Each technical/visual report has:

```json
{
  "schema": 1,
  "candidate_sha256": "64 lowercase hex digits of the candidate manifest",
  "contract_sha256": "64 lowercase hex digits of the contract",
  "reviewer": "reviewer identity",
  "inspected": true,
  "verdict": "pass",
  "blockers": [],
  "evidence": {
    "runtime-capture": {
      "path": "captures/runtime.png",
      "sha256": "64 lowercase hex digits of the evidence file"
    }
  },
  "checks": {
    "silhouette": {
      "status": "pass",
      "reason": "specific comparison against the contract criterion",
      "evidence": ["runtime-capture"]
    }
  }
}
```

The strings describing hashes above are schema explanations, not runnable hashes. Populate reports only after performing the relevant inspection. Report evidence paths are relative to that report's parent, under the same containment rules. Every required check must be present. Every supplied check, including extras, must pass, have a nonempty reason, and cite at least one existing pinned evidence key. Any blocker, non-pass verdict, uninspected attestation, failed extra check, missing/stale file, or stale manifest/contract pin rejects the candidate. Production visual reviewer identity must differ from the candidate author after whitespace trimming and case folding; this is an accountability check, not cryptographic identity verification.

## Accepted bundle and invalidation

The bundle is assembled from the exact bytes that were checked, in a temporary sibling directory, then published with an atomic, kernel-enforced no-replace rename. Concurrent helper processes cannot overwrite an accepted destination. Failure before publication removes the staging directory and leaves any destination untouched. This guarantees atomic visibility, not crash-durable archival storage.

Layout:

```text
accepted-bundle/
  acceptance.json
  contract.json
  candidate/
    manifest.json
    [artifact/context paths preserved]
  reviews/
    technical/
      report.json
      [evidence paths preserved]
    visual/
      report.json
      [evidence paths preserved; omitted if no visual review]
```

Reserved names `candidate/manifest.json` and each review's `report.json` cannot also be payload files. File/directory path collisions reject publication. `acceptance.json` records the profile, candidate and contract hashes, every copied file hash, and `artistic_quality_evaluated_by_checker: false`. Its status is either `prototype-only` or `production-evidence-accepted`.

An accepted bundle is self-contained for rerunning this checker with its copied manifest, contract and reports. It is not signed or immutable: changing a review and its evidence can produce a different accepted bundle. Protect accepted storage through the project's normal review and permissions controls. Consumers must revalidate exact bytes and the production profile before loading; do not trust a filename or `acceptance.json` alone. A context, artifact, evidence, manifest or contract change invalidates the corresponding existing review chain. Obtain fresh actual review instead of merely replacing hashes.

## Verify the helper

```sh
python3 -m unittest discover -s scripts -p 'test_evidence_gate.py' -v
```

Tests use explicitly synthetic text fixtures. They exercise mechanical acceptance/rejection, isolation, portability of a copied bundle, stale pins, failed/missing checks, author self-review, unsafe paths, and no-overwrite publication. They do not demonstrate real asset quality or a completed game pipeline.
