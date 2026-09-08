# Save / Load Progress Verification

All **18 checks pass** in `progress-store-results.json`. The test uses the actual `runtime-core/checkpoints/pallet-town.state` and a temporary fixture directory that is removed after the run. It does not touch `work/pokemon/player-progress.json` or the root's `work/pokemon/verification-save.json` smoke-test file.

Verified behavior:

- Exact 397,312-byte file roundtrip, including matching timestamp and SHA-256.
- Missing save returns null; completed save leaves no `.tmp` file.
- Invalid length or state magic is rejected before overwriting the prior valid save.
- Corrupted checksum, changed payload, truncated state, invalid magic, wrong ROM envelope, unsupported version and invalid JSON are rejected.
- A separately initialized fresh mGBA `GbaAdapter` loads the saved bytes into exactly the same observed state as a separate core loading the original checkpoint: frame 11979, PalletTown group 3 / map 0, player (6, 8), facing down, no active battle.
- The adapter rejects a mismatched embedded ROM identity. The first redraw advances to frame 11980 while preserving map and player position.

From repository root:

```sh
node outputs/pokemon-remake/verification/playability/check-progress-store.mjs
```

The JSON result binds the tested store and checkpoint hashes. Store checks validate the envelope, size, magic and checksum; the adapter separately checks embedded ROM identity. These checks do not claim semantic validation of every possible corrupted emulator field or crash/fault-injection testing of filesystem atomicity. Exact byte equality applies to file storage; native restore/redraw may update emulator bookkeeping and advances one frame when drawing.

Electron button, keyboard, pause/focus behavior and packaged-app tests are owned by the root integration test. No app/shared runtime files were edited by this verification worker.
