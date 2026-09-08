# Production Contracts

Keep these compact records in the project's existing format. They are operational handoffs, not substitutes for actual image inspection or implementation. For executable validation, use the canonical schema and commands in [evidence gate](evidence-gate.md); do not send the prose examples below to a tool expecting another schema. Existing game-specific validators may require explicit adapters.

## Slice record

Record one bounded unit of playable acceptance:

- Game/platform, immutable ROM hash/revision, source adapter and emulator configuration.
- Renderer/build, scene, forms/actions/transitions included, explicit unsupported coverage.
- Actual reference packet with image hashes, source composite IDs and authored target frame.
- Camera/projection, viewport, axes/units, visual root/pivots, source-to-world conversion and collision correspondence.
- Lighting, material palette, color management and deliberate departures from original art.
- Deterministic input replay, checkpoint frames and continuous motion sequence.
- Current stage, prototype status, asset/scene visual status, accepted manifest/version.
- Active blockers, owner, revision budget, method decisions and next concrete action.

Keep source behavior/coverage, visual appearance, motion and performance separate. A claimed percentage needs a denominator, reference set and evaluation method. Technical pass counts are not visual fidelity.

## Worker task card

```text
Task/version: hero-opening / revision 1
Outcome: one character that meets the accepted target in the opening scene.
Author: assigned worker identity; independent reviewer: a different identity.
Inputs: actual source composites, target image packet and accepted exemplar, with hashes.
Scope: required forms/actions/transitions; explicit exclusions and dependencies.
Coordinates: units, axes, facing, root/pivots, visual dimensions and collision correspondence.
Runtime: renderer/build, camera, viewport, light/material settings and replay checkpoints.
Ownership: isolated editable-source/candidate directories; integration owner.
Construction: required silhouette, material separation, topology/rig/deformation requirements.
Deliverables: script/build command, editable source, textures, GLB, provenance and evidence.
Resources: geometry/texture/frame budgets, build queue route, allowed generation costs.
Revision budget: initial planned iterations/time; method-review trigger; escalation options.
Acceptance: required technical and visual checks with observable pass conditions.
Feedback: return actual runtime captures and review defects to the author after every build.
Status: candidate until current independent review and technical evidence pass.
```

Use concrete image paths and real values when dispatching; placeholders are not a task-ready packet. Authors must be able to inspect rendered output. A centralized build queue may own Blender execution but must not sever the author-feedback loop.

## Candidate and evidence identity

A candidate is a versioned set of files, not “the newest GLB.” Record the authored source, runtime exports, external textures/animations and their hashes. Include the target/reference packet, runtime source or reproducible build identity, render configuration, replay/scene state and acceptance contract in the review context. Hash any other dependency whose changes could alter the reviewed result. A dirty source tree needs a content snapshot; a commit name alone does not describe it.

Evidence includes actual runtime stills and, for animated assets/scenes, continuous motion. Record capture frames/time range, replay identity, viewport and renderer configuration. Hash evidence files. Technical and visual reports must identify the same candidate and acceptance contract. Keep Blender diagnostic renders separately labeled; they cannot establish runtime appearance.

The acceptance contract declares required checks and required artifact/context keys before review. It must require source provenance, actual target images and runtime evidence appropriate to the slice. Motion/deformation checks are required for characters when the target calls for them; a static prop can omit them only through an explicit scoped contract with a reason. Do not silently mark a character's motion not applicable to get approval.

Any changed artifact or relevant context produces a new candidate/review requirement. Shared material, renderer, camera or lighting changes invalidate affected scene evidence even if the GLB is unchanged. Changing the contract to remove a failed requirement changes the agreed target; record why and obtain a fresh review.

## Independent visual review

The reviewer receives the target, candidate, technical report and actual captured evidence—not merely the author's conclusion. The production reviewer must differ from the author. A separate agent is suitable; independence means inspecting the evidence and making its own judgment, not parroting the author. If no independent reviewer is available, preserve provisional status and describe the gap; do not impersonate another identity.

For every required criterion record:

- **Observation:** what is actually visible, with image/frame/time reference.
- **Verdict:** pass, fail or pending; the executable gate admits only required passes.
- **Reason:** why the observation meets or misses the target.
- **Evidence:** concrete inspected file(s), bound by hashes in the machine record.

Typical visual criteria are identity/silhouette, proportions/scale, material response, scene readability/lighting, deformation, motion/contact and source form/state correspondence. Adapt criteria to the scope, not to whatever the candidate happens to do well. Inspect the entire required motion sequence; a flattering still cannot approve transitions or contact.

Review output includes reviewer identity, inspected confirmation, candidate/contract identity, overall verdict, required-check results and blocking defects. The executable report fields and enum values are defined in [evidence gate](evidence-gate.md). Do not fabricate a passing report as a fixture for real production. Synthetic passing fixtures belong only in clearly labeled tests.

### Actionable defect record

```text
ID: hero-shoulder-02
Criterion: continuous organic body construction
Evidence: runtime-side.png, left shoulder; run.mp4 at 00:02.4
Observation: an exposed gap appears between sleeve and torso during arm swing.
Consequence: character reads as disconnected toy parts at gameplay scale.
Cause hypothesis: separate rigid shoulder assembly; inspect topology and weights.
Revision: join/reshape the shoulder region and reweight the arm deformation.
Owner: hero author
Recheck: same camera and motion interval, plus maximum arm bend diagnostic.
Priority: blocker
State: open → revised → verified (only a fresh review closes it)
```

Keep observations separate from cause hypotheses. Nonblocking refinements may remain after acceptance only when all agreed requirements pass. Unresolved blocking defects prevent promotion. Preserve failed reviews rather than overwriting them with a success summary.

## Iteration and escalation record

For each candidate, log method, changed files, largest defect addressed, rendered evidence, reviewer verdict and next action. Set a bounded local budget suited to the work; three revisions per method is a starting estimate, not a universal stop rule or a permission requirement. Repeated failure to improve the same defect triggers method review before more identical attempts.

Escalation can mean changing construction, retopologizing, sculpting, fixing the export/runtime cause, using a verified generation provider within scope, narrowing an explicitly negotiable slice, or asking for a genuinely missing input. Do not quietly reduce the target or substitute surface noise for structural repair. Exhausted budget leaves an honest failed/pending candidate and a resumable next step.

## Promotion and release contract

The bundled `scripts/evidence_gate.py` checks declared file hashes, candidate/contract agreement, required checks, evidence, reviewer separation and report verdicts. With `--output`, it creates a staged bundle and acceptance record only after the selected profile passes. Read its documented commands and schema rather than inventing flags.

This helper does **not** inspect beauty, authenticate reviewer identity, validate the truth of provenance, or wire itself into an existing compiler. A valid report can still contain a dishonest judgment. Honest evidence inspection and integration tests remain required.

For production integration, the actual assembler/reload/package path must consume a validated accepted bundle/manifest, not arbitrary build-directory files. Use immutable candidate versions, one integration owner, an atomic accepted-manifest update and last-good rollback. Stage candidates for inspection separately. Avoid a time-of-check/time-of-use gap by consuming the validated bundle rather than mutable originals.

Required gate tests cover accepted matching evidence, absent review, failed verdict/check, missing required context, changed asset/reference/runtime context, changed evidence and same-author review. Rejection must leave the accepted manifest and last working runtime asset unchanged. Test the **real consumer path** once integrated, not only the helper in isolation.

Prototype delivery is an explicit profile with its technical checks and unapproved visual status retained. It is not a bypass that produces an accepted-art release. An accepted asset is also not automatic scene approval: the combined scene needs its own reviewed context and required sequence.

## Representative playable sequence

Use a deterministic replay with the actual scoped interactions. A platformer sequence might include idle → walk → accelerate → jump → land → stomp/hit → death → retry. Include facing/form changes, carrying or subareas only when claimed as supported. Compare source state and runtime presentation at checkpoint frames; inspect continuous motion and separate pause/resume, reset and reload checks.

Report untested scenes/states/transitions. Performance evidence records hardware, resolution, route, sample duration and method; distinguish simulation rate, presentation rate and input latency.

## Failure routing

| Visible problem | Inspect first | Avoid |
| --- | --- | --- |
| Assembled-toy character | Silhouette, continuous construction, joints and deformation topology | More stitches/noise |
| Stiff or sliding character | Articulated rig, planted phases, stride/travel and transitions | More clip names |
| Uniform plastic materials | Material-specific references, scale, normals and optical response | Universal 4K textures |
| Studio model fails in game | Export, framing, scale, orientation, lighting and shader support | Approving the studio render |
| Flat or incoherent scene | Depth, value hierarchy, composition and contact | Unmeasured engine migration |
| Wrong suit/action/orientation | Source-state mapping, variant selection and placement | Reusing the nearest asset silently |
| Few accepted outputs despite many builds | Target clarity, feedback loop and enforcement | More first-draft workers |

## Pipeline completion evidence

A credible completion report separates what ran from what is specified. Include the accepted slice/version, target and current reports, meaningful revision history, clean rebuild/replay result, promotion rejection tests, reload/rollback results and a fresh packaged launch. Keep editable source and provenance links accessible. Identify unresolved quality and coverage explicitly.

Skill instructions plus a tested helper establish reusable workflow machinery. They do not establish that a legacy assembler enforces it or that production-quality art has been made. Record those as separate milestones until demonstrated.
