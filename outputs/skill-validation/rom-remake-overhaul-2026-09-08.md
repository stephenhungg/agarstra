# ROM Remake Skill Overhaul — Verification

September 8, 2026. Scope: the reusable skill and bundled evidence helper. No Blender jobs, game-asset changes, runtime migration, external generation, or package publication were performed.

## Changes

- Replaced the entrypoint with deliverable-based routing: skill/audit work, prototype delivery, high-fidelity scene production, and reliable production-pipeline implementation have different completion criteria.
- Added operational references for parallel worker ownership and feedback, adapter qualification, source/state provenance, coverage, runtime animation/reload, and package verification.
- Reworked visual production and review contracts around concrete targets, actual runtime images/motion, actionable defects, method escalation, independent review, character deformation, and separate asset/scene acceptance.
- Grounded the SMB3 adapter in actual queue, assembler, validator, reload, extraction and package behavior. Built assets remain candidates; the existing consumers still lack reliable quality enforcement.
- Added a standard-library evidence checker with explicit prototype/production profiles, content-pinned artifacts/context/reports, stale/failed/missing evidence rejection, and atomic no-overwrite accepted bundles.

## Checks run

- Skill Creator quick validator: passed against the updated repository skill.
- Bundled unittest suite: 19 tests passed. Covers accepted synthetic bundles, explicit prototype labeling, missing reviews/checks, stale artifacts/context/manifest/contract/evidence, failed reviews, self-review, malformed JSON, path/symlink escapes, no output on rejection, and no-overwrite publication including a race.
- Parent code review found an API-only missing-technical-report bypass; fixed and covered for both profiles.
- All local Markdown links resolve; code fences balance; CLI help runs.
- Installed `~/.codex/skills/rom-remake` resolves to this updated repository copy.

## Independent scenario reviews

These were read-only forward tests, not executed game productions or paid generation jobs.

| Request | Observed workflow decision |
| --- | --- |
| Package the existing SMB3 prototype without polishing | Preserve current art limitations, run relevant technical checks and fresh package launch; do not require photoreal approval, gate migration, or a new swarm. |
| Make the pipeline reliably produce high-fidelity assets | Require real render/critique/revision and repeatability; enforce acceptance at assembler, reload and package consumers; helper-only tests or one manually approved scene cannot finish the task. |
| Adapt to a GBA game, one town and one battle, optional image-to-3D | Qualify a compatible emulator/state adapter, define exact scope and references, retain original gameplay, test generation only if available, and require scoped visual/technical delivery. Do not reuse JSNES addresses or claim unavailable adapters exist. |
| Reuse approval after texture/lighting changes | Reject stale approval, capture changed candidate/context, obtain fresh affected technical and independent visual reviews, preserve last accepted output until replacement passes. |

A review ambiguity about a second repeatability case was fixed: a meaningful revision must exercise authored changes, returned critique, rebuild, fresh review and integration; metadata edits or recopies do not count.

## Limits and next production work

The checker verifies declarations and hashes; it does not inspect art, authenticate identities, prove semantic ROM provenance, or recursively discover omitted dependencies. Tests use synthetic fixtures and do not constitute real visual acceptance.

The existing game pipeline remains a prototype. Next implementation work is connecting real targets and returned renders to selected author jobs, enforcing accepted versions through assembler/reload/package paths, and demonstrating the complete loop with actual reviewed assets and scenes. Character quality, unimplemented adapters and incomplete game coverage remain separate documented gaps.
