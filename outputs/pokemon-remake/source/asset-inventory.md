# FireRed Source Asset Inventory

Source inventory for the exact-matching FireRed 1.0 source checkout. This is queue input, not a claim of full ROM graphic extraction or complete semantic object identification.

Source commit: c75f352304d529f6ba92d4f74b9cf8b5c3810788. The recomputed built-ROM SHA-256 matches the recorded user-ROM digest: 3d0c79f1627022e18765766f6cb5ea067f6b5bf7dca115552189ad65a5c3a8ac.

## Counts

| Source scope | Count | Meaning |
|---|---:|---|
| Graphics PNG files | 3048 | All graphics, including unused/version-specific inputs |
| Tileset PNG files | 106 | Base sheets and separate animation images |
| Creature directory families | 389 | Includes special/placeholder families; not a species count |
| Creature front PNG files | 421 | Pose/form storage sheets |
| Creature back PNG files | 419 | Pose/form storage sheets |
| Creature icon PNG files | 418 | Icon sheets, including variants |
| Footprint PNG files | 387 | Separate graphic role |
| Trainer front PNG files | 146 | Includes unused/Ruby-Sapphire remnants |
| Trainer back PNG files | 6 | Multi-frame throwing sheets |
| Object-event PNG files | 157 | People, creatures and miscellaneous props |
| Object graphics descriptors | 154 | Dimensions, palette, frame and animation links |
| Map JSON records | 425 | Static maps |
| Layout records | 365 | Shared/unreferenced layouts retained |
| Tileset families | 67 | Primary and secondary families |
| Tileset animation families | 7 | Separate frame-image groups |

## What Is Mapped

- Every cataloged PNG has a source path, dimensions and SHA-256.
- Creature front/back species tables retain visible-size coordinates, form directories and palette associations.
- Trainer and object graphics retain source symbols, explicit frame dimensions/indices, timing command sequences and animation table references.
- Object descriptors carry static map placement counts. Map records retain event coordinates, movement types, scripts and flags.
- Maps link to layouts and primary/secondary tilesets. Layout binary sizes are checked against declared dimensions; tilesets retain palettes, metatile/attribute counts and animation callbacks.

Direct compiled-INCBIN comparisons at matching-build ROM symbol offsets: **3169 match**, **0 mismatch**, **6 not compared**. This compares existing compiled bytes; it does not decode or extract assets.

## Important Boundaries

- This is a source inventory tied to a matching build, not full binary extraction, decoded ROM coverage, observed gameplay coverage, or finished 3D assets.
- Source PNG totals include unused, placeholder, Ruby/Sapphire-remnant and LeafGreen-specific art. Reachability in FireRed is not inferred from file existence.
- One PNG may hold one pose, many frames, many forms or raw tiles. Palette swaps and mirrored frames reuse graphics. File counts are not game-object counts.
- storage_cells_64x64 is sheet capacity, not an animation count. Explicit timing is recorded only where source AnimCmd sequences or tileset C functions supply it.
- Static map object_events omit scripted spawns and dynamic graphics substitutions. Trainer parties and encounter reachability are not analyzed.
- Maps can share layouts; primary and secondary tilesets and multiple layers compose scenery. An 8x8 tile or 16x16 metatile is not necessarily a whole tree, fence or building.
- The C parser records structures without full preprocessing. Conditional context is retained on direct INCBIN declarations; cross-table records may contain unused/version-conditional entries.
- Direct byte comparisons use existing compiled INCBIN inputs and matching-build symbol offsets. No bytes were extracted into new assets and no compression stream was decoded.

## Concrete Examples

| Family | Source evidence | Queue implication |
|---|---|---|
| Squirtle | [front PNG](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/graphics/pokemon/squirtle/front.png), [back PNG](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/graphics/pokemon/squirtle/back.png), each 64 × 64; icon 32 × 64 | Reference views belong to one family; sheet capacity does not establish animation. |
| Castform | [build concatenation](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/graphics_file_rules.mk:30) | Four form directories combine into compiled front/back/palette data. |
| Deoxys | [version guards](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/src/data/graphics/pokemon.h:2699) | Preserve FireRed/LeafGreen selection; do not queue every source version as active FireRed content. |
| Red movement | [frame table](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/src/data/object_events/object_event_pic_tables.h:1) | One descriptor combines multiple PNGs, frame indices and flipped reuse. |
| Pallet Town | [map](/Users/stephenhung/Documents/GitHub/agarstra/work/pokemon/source/pokefirered/data/maps/PalletTown/map.json) | Buildings and trees require tile-layer composite identification; static NPC events are separate. |

## Next Queue Use

Choose a source family plus an actual scene/state. Carry its relevant pose, form, palette and timing references into one production card. Identify whole environment composites before counting buildings, roofs, trees or fences. Prefer runtime-observed families; source presence alone does not prove reachable content.

Full record index: [asset-inventory.json](/Users/stephenhung/Documents/GitHub/agarstra/outputs/pokemon-remake/source/asset-inventory.json).

## Verification and Map Index

All catalog image paths exist and are unique. All 425 map records resolve to declared layouts; all 365 populated layout records match their binary width × height × 2 byte sizes. The 18 empty source layout slots are preserved separately. All 67 tile sheets resolve to source tileset headers, including the three declarations housed in src/graphics.c. All 154 object graphics descriptors resolve to explicit frame metadata. Source files were not modified.

The [numeric map index](/Users/stephenhung/Documents/GitHub/agarstra/outputs/pokemon-remake/source/all-map-index.json) maps all 425 group:number keys across 43 groups to source map names and exact layout dimensions. Every numeric pair was checked against generated C map constants; none is unresolved. Read byKey["3:0"] for Pallet Town (24 × 20 metatiles).
