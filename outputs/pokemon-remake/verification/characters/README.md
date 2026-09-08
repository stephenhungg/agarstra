# Source character rendering verification

The isolated Electron harness loads the actual BPRE English rev0 ROM and original-input checkpoints. It uses the new character module on a coordinate grid, with the actual 240×160 source framebuffer inset. It does not launch or replace the workbench, change the shared checkout, write progress, or mutate RAM.

Run from the worktree root:

```sh
/Users/stephenhung/Documents/GitHub/agarstra/outputs/pokemon-remake/app/node_modules/.bin/electron outputs/pokemon-remake/verification/characters/browser.cjs
```

`CHARACTER_REFERENCE_ROOT` can point to another full checkout containing the ROM, original checkpoints, Three.js dependency and hydrated mGBA WASM. Code comes from this worktree; Git LFS pointer binaries are read from the reference checkout. Output stays here. The browser gets a temporary profile and a randomly assigned local HTTP port.

## Verified scope

- Five source checkpoint scenes: Pallet Town, upstairs bedroom, downstairs house, Oak's lab, and sign dialogue.
- Every non-hidden active ObjectEvent is rendered with matching ID, graphics ID, facing and exact fractional world/visual-offset coordinates. Unsupported source actors fail these checks.
- Twenty-four original Down-input frames move the downstairs player and change the decoded sprite pixel hash. Per-frame reports are independent snapshots.
- Original-input replays traverse bedroom → house, house → town, and town → lab. Character lifetimes clear during non-overworld phases. Final source memory from serialized offset `0x800` onward exactly matches the supplied checkpoint for all three replays.
- Source snapshot reads remain unchanged by presentation. No core RAM writes or invented NPC movement occur.
- Pallet Town includes active actor ID 2, graphics ID 27, with source `offScreen: true`; it remains rendered in the wider view.

`browser-results.json` records reports, all movement samples, transition boundaries, errors/warnings and the SHA256 of the tested character renderer.

## Visual inspection

`town.png`, `lab.png`, `movement.png` and `dialog.png` were inspected directly. Source sprite orientation is upright; Red, Mom, Oak and GREEN retain their source identity and facing. The town's originally culled NPC remains visible. Sign and Oak dialogue come from the original simulation. Nearest sampling preserves the source pixel art; bottom-centered source sprites sit near the ground grid anchor.

This is a source-sprite fallback acceptance for these scenes, not a 3D or photoreal character acceptance. The grid deliberately excludes buildings/furniture, so it does not verify world occlusion, scene integration, the main gameplay camera, model arms, or lab table grounding. Adjacent north/south billboards can overlap in the independent perspective. The emulator header/IO bytes before `0x800` are not claimed byte-identical. The local unpackaged Electron harness emits its normal missing-CSP development warning.

## Synthetic presentation lifecycle checks

A separate bounded `CHARACTER_LIFECYCLE_ONLY=1` run passed six checks: script-hide retirement and texture disposal, graphics-ID slot replacement, player-model substitution, total hide/disposal, restoration, and byte-identical native state before/after. These deliberately clone and vary observed JavaScript state; they are **synthetic renderer assertions**, not source gameplay coverage and never write RAM. Results are stored as `lifecycle` in `browser-results.json`, which also binds `decoderSHA256`. The lifecycle-only run requires the earlier full report and checks its renderer hash before supplementing it.
