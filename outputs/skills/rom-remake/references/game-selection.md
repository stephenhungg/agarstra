# Choosing a Demonstration Game

This is a suitability assessment, not a conversion benchmark. Historical research snapshot: September 8, 2026. Recheck tool capabilities and current adapter directories before using any implementation-status statements below. These are optional candidate hypotheses, not the default target of this skill. Do not treat these examples as a requirement to abandon the user's selected game.

For the existing NES-oriented pipeline, **Battle City is the preferred candidate to investigate**. Its tank combat, headquarters defense and terrain built from brick walls, barriers and rivers provide a constrained mechanical/environment asset vocabulary. These features are documented by [Nintendo](https://www.nintendo.co.jp/wii/vc/vc_bc/vc_bc_01.html) and [Bandai Namco](https://nc.bn-ent.net/title-lineup/title.php?tit=battle-city).

The expected advantage is artistic: rigid tank bodies, tread motion and repeated masonry should need less organic deformation work than Mario and his enemies. Metal, masonry and water also give clear material references. A controlled elevated camera could make a convincing miniature battlefield. These are proposed creative/engineering choices, not measured results. Four-direction movement should preserve source behavior; add cosmetic recoil or effects only when they do not misrepresent collision or timing. Damaged terrain needs correct partial-cell state and gameplay readability; cosmetic debris must not imply new collisions.

**Excitebike** is a plausible second candidate: motorcycles and repeated track obstacles offer reuse, but riders, landing poses and crashes still need articulated motion. See [Nintendo's NES description](https://www.nintendo.com/en-gb/Games/NES/Excitebike-751574.html). Do not conflate the NES version with its arcade or later 3D versions.

SMB3 remains feasible, but it places more demands on expressive character forms, organic scenery and animation-state coverage. Selecting a mechanically simpler game reduces art complexity; it does not eliminate extraction, semantic mapping, visual review or integration work.

Before committing to a new title:

1. Identify an authorized local ROM and exact revision; inspect mapper/emulator compatibility.
2. Reproduce one scene and recover actor position, direction, animation state, projectiles, terrain changes and end-of-stage/retry behavior relevant to it.
3. Demonstrate source correspondence without a custom model, then export one representative model and inspect it at intended gameplay size.
4. Estimate effort from those probes. Do not extrapolate from SMB3 adapter coverage to another ROM.

The current SMB3 RAM addresses, source definitions and renderer assumptions are game-specific. No Battle City or Excitebike adapter or completed model set has been built by this skill.

## Pokémon as a More Recognizable Demonstration

For a Pokémon-focused prototype, investigate the original GBA **FireRed** version and one small outdoor map leading to a single battle. The [pret FireRed/LeafGreen decompilation](https://github.com/pret/pokefirered) supplies structured source context; [pret's Red/Blue disassembly](https://github.com/pret/pokered) is an alternative for an explicitly 8-bit Game Boy target. Verify the exact ROM revision against the chosen project's build targets and hashes. These are reverse-engineering resources, not evidence that our own adapter already exists.

The proposed demo advantage is recognizable scenery, reusable environmental assets, a controlled battle camera and discrete turn-based events. A single trainer and two reviewed creatures can establish a bounded battle slice. Show one actual encounter and command resolved by the original simulation, with the remodeled view depicting the same result. Use an appropriate saved state for that slice rather than promising a complete new-game progression.

The art risk remains substantial: close-up creature models, facial identity and animation will be scrutinized. Do not reuse the failed organic-model method or assume a smaller asset count guarantees quality. Validate the hero creature in the battle camera before building the town or additional species.

This changes platform: JSNES cannot run Game Boy or GBA ROMs. An appropriate emulator core, integration interface and new state adapter are required. [mGBA documents GBA and Game Boy support](https://mgba.io/faq.html), but this historical comparison did not establish a working mGBA bridge. Inspect current Pokémon work and probe evidence before claiming absence or completion. Prototype state extraction for map position, actors, encounter transitions, battle participants, actions, HP and menus before committing to full production. Preserve ROM mechanics while scheduling cosmetic animations around its actual battle events.
