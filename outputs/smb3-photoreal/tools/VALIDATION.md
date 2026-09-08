# Model and Family Validation

## Family manifest

`build_families.py` regenerates `../design/families.json` from the delivered source catalogs. It contains 36 production planning groups, including broad unresolved domains. This is not a claim that the game has 36 distinct visual assets or that 8,192 patterns imply 8,192 model jobs.

Each family carries source records, exact visual IDs and context pointers, palette/context alias counts, rendering requirements, estimated shared geometry reuse, and uncertainty. Paths are relative to the photoreal project root. Label-based grouping is a proposed production organization, not a runtime replacement mapping. Opening priority based on equal RGBA hashes means visual-content overlap only; shared/blank graphics can have different identities. Unclassified observed sprites and source-unnamed definitions stay unresolved.

## Structural checks

```sh
python3 tools/validate_models.py models/example.glb --out design/example-validation.json
```

The script reads GLB binary data directly using the Python standard library; Blender is not required. It checks GLB chunk structure, buffer bounds, actual position accessor data and bounds, triangle index ranges, node hierarchy/transforms, required names/provenance, material factors, texture/image references, embedded PNG dimensions, and active-scene bounds. Compression requiring an external decoder is reported as unsupported rather than silently accepted.

It reports geometry, materials, texture detail, naming/provenance, and readiness separately. High triangle counts, many materials, or baked textures alone do not demonstrate photoreal quality. Proxy-name signals and nearly planar bounds are diagnostics.

Optional job spec:

```json
{
  "familyId": "pipes",
  "requiredNodeNames": ["PipeRoot"],
  "requiredSourceAssetIds": ["actual-source-id"]
}
```

Pass with `--spec job.json`. Embed `familyId` and `sourceAssetIds` in a glTF node's `extras` or the document/asset `extras`; these are preserved from Blender custom properties when exported appropriately.

## Visual readiness

An export is structurally ready when its machine checks pass. Photoreal readiness remains false until a real rendered review is recorded against that exact file hash. The review can be performed by a person or an agent inspecting the actual rendered output; it must not be fabricated from metadata alone.

```json
{
  "assetSHA256": "exact-sha256-from-validator",
  "approved": true,
  "reviewer": "identifier-of-actual-reviewer",
  "checks": {
    "silhouette": true,
    "materialResponse": true,
    "lighting": true,
    "runtimeReadability": true,
    "notPixelExtrusion": true
  }
}
```

Pass with `--review review.json --require-photoreal` when the worker must meet the visual gate. Missing/stale review, a planar card, or explicit pixel/voxel proxy geometry does not pass this gate. The current validator is primarily for volumetric prop/character jobs, not background image assets.

## Checks exercised

`test_validate_models.py` uses the local `models/pbr-smoke.glb` fixture to check a real baked export, file truncation, geometry buffer overrun, missing textures, required names/provenance, stale visual approval, and a flattened-card case. All seven checks passed. The fixture's structural result is saved in `design/validator-pbr-smoke.json`; it is not a visual approval of a production model.
