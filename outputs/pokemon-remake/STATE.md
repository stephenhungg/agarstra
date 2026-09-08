# Pokémon FireRed remake — active, incomplete

## Proven source and simulation
- User ROM: English FireRed revision 0, SHA1 `41cb23d8dccc8ebd7c649cd8fbb58eeace6e2fdc`.
- Matching pret source rebuilt byte-for-byte; 54,248 ELF symbols exported.
- Original mGBA WASM core owns gameplay. Pallet Town and first-battle/first-attack checkpoints have input-only replay evidence. Inventory: 3,154 source PNGs, 425 maps, 3,169 matching compiled INCBIN ranges, zero mismatches; not semantic or 3D completion.

## Implemented presentation
- Town: cottage v2, tree, laboratory v1, PBR grass/path surfaces and source-clock grass/water motion. All building door anchors match source warps.
- Player house 1F/2F and Oak lab: source-aligned 3D interiors and source actors. Human characters remain markers.
- Dialog: actual printer progress, native text and cropped-window alternatives.
- Battle: original sprite cutouts, position/visibility/affine/palette observation, HP/levels, native actions/moves/PP, source tutorial dialog. Independent effects/background layers remain incomplete; party/bag retain original pixels.
- Source panel optional; 3D is the default. Unsupported maps explicitly state missing coverage.

## Verification
Integrated Electron smoke passed 23 checks after fixing an extra checkpoint redraw frame in the exact replay setup. Evidence: verification/workbench/results.json plus town/dialog/interior/battle/moves/after-turn captures. Re-run after further edits. Battle separately passed 13 source checks and three WebGL checkpoints. Dialog has 13 source and six browser fixtures. Interior source/renderer evidence is under verification/interiors/.

## Art — changes required
Cottage v2: soft glossy roof and baked glazing. Laboratory v1: open-looking blue vent top, soft roof/masonry, inferred rear. Tree: narrow tufted crown, weak bark/leaf materials. Ground: too dry/brown, sparse blades, no detailed water depth or garden flowers. Interiors: candidate forms/materials. No approved photoreal scene or 95% claim.

An existing creator-offered Charmander FBX was imported into Blender and exported to models/charmander-existing-v1.glb: 60 bones, original clip, restored textures. Actual GLB skin was verified, with a maximum sampled four-weight export error of 0.00393 units (0.66% of rest height). The clip appears to be a rig demonstration; frame 51 stretches the neck. Battle animation is not approved and the model remains unintegrated. See verification/charmander-existing/REVIEW.md. CC BY-NC 4.0 and creator credits are preserved in verification/charmander-existing/export.json.

The prior creature reference generation rejections remain recorded in design/production.json. No alternate-provider generation retry was used. Existing model reuse is separately sourced.

## Workflow and next dependency
Preferred geometry path: extracted sprites → directly authored/inferred Blender mesh → materials → rig → GLB → runtime inspection and revision. Intermediate generated imagery is optional; it previously introduced source-identity drift. Do not label inferred geometry as extracted geometry.

Next: build approved character geometry and source-event motion; replace trainer markers; refine actual environment defects; then expand battle effects and maps. Full objective remains active. Preserve unrelated root Next.js work.

## Run
`npm start --prefix outputs/pokemon-remake/app` or Launch Workbench.command.
`npm run smoke --prefix outputs/pokemon-remake/app` rebuilds and exercises the real Electron/core integration.

Latest rebuilt workbench is running in Electron session 6773. Final integration smoke passed 23 checks; short local sample advanced 124 original frames over 2.08 seconds, median render interval 8.4 ms, p95 9.9 ms at 2880×1678. This is not full-game performance coverage.
