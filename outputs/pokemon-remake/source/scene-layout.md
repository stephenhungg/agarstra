# Pallet Town semantic layout

Coordinates use source map tile centers: world x = tile x and world z = tile y. Source/scene-layout.json derives its tile values and event positions from the exact matching build in source-maps.json. House and lab footprints were identified from the source metatile image and checked against the warp events. House bounds are inclusive x5–9/z3–7 and x14–18/z3–7; doors are x6,z7 and x15,z7. Lab bounds are x13–19/z9–13, door x16,z13.

Tree anchors are inferred from every second row's boundary-tree metatiles; they are scenery placements, not collision data. Ground path classification is a draft subset of Pallet-specific tile IDs. Edge blending, garden flowers and exact terrain appearance remain unimplemented. Source collision arrays are preserved but not executed by the renderer: the ROM owns collisions.

The v1 cottage door was on the wrong side of its facade. V2 fixes the facade arrangement; verification/cottage-v2/door-anchor.json records its measured local anchor. Runtime placement uses that anchor with a uniform scale, and both final world door coordinates match the original warp events. No gameplay collision is shifted. This addresses doorway placement, not full architectural or terrain fidelity.
