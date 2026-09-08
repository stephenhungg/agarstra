# Visual Production: Target → Revision → Accepted Scene

Use this workflow for high-fidelity, polished, photoreal, or production-ready output and for a pipeline intended to produce it reliably. A technically working prototype remains useful but is a different deliverable. These instructions do not mean that character production, review enforcement, image-to-3D, or Unreal integration already exists. Inspect [implementation status](implementation-status.md) and the relevant project adapter.

If the task is to improve this skill, improve and test its instructions/tools; do not start asset production as a substitute. For implementation, work through the active production gate. Acceptance normally belongs to a qualified reviewing agent; ask the user only for a material unresolved art-direction decision or when they reserved approval for themselves.

## 0. Establish what is real

Inspect the current candidate, actual runtime captures, author scripts, review and promotion code. Record the ROM revision, renderer, tested scene/form/action coverage, asset versions, tool availability and latest evidence. Preserve source provenance, original simulation, useful technical tests and unrelated projects.

Use the records in [production contracts](production-contracts.md). Separate:

- **Prototype complete:** the scoped extraction → build → playable renderer → package path works.
- **Asset accepted:** a particular export meets the target under the reviewed context.
- **Scene accepted:** accepted assets together meet composition, gameplay-state and motion criteria in a playable sequence.
- **Production pipeline demonstrated:** the feedback and enforcement path repeats without admitting failed or stale candidates.

A contact sheet, valid GLB, named animation clips or high asset count cannot establish the latter three. No percentage measures “photorealism” without a defined reference set, denominator and assessment method.

## 1. Freeze a concrete visual target

Choose one bounded representative scene and short deterministic replay before scaling production. For a character platformer this may be a hero, an enemy, terrain and a few interactive props. Honor the user's game and chosen scope; game-selection advice belongs in [game selection](game-selection.md).

The target packet must include actual images, not only adjectives:

1. Assembled source sprites/composites with palette, form and action IDs; preserve byte or runtime-observation provenance.
2. An authored target frame or paintover at the intended gameplay camera and output size. Add close views only for shapes/materials the frame does not resolve.
3. Material references, silhouette and proportion guidance, camera/projection, axes/units, visual root and collision correspondence, lighting and color-management settings.
4. Required source states and transitions, known unsupported cases, and explicit deliberate departures from the original appearance.
5. Observable acceptance criteria: for example continuous shoulder construction, readable face at gameplay size, distinct cloth/skin response, no visible foot drift during planted contact, and no lost identity in facing/form changes.

Hash the packet. Generated concept art is an authored design target, never evidence of recovered ROM geometry or a completed 3D model. If reference images disagree, resolve the conflict before detailed modeling. When routine choices suffice, document them and proceed; do not invent a mandatory user-approval ceremony.

**Exit:** an accepted target packet and a broad-shape runtime frame that demonstrates workable scale, silhouette and value hierarchy. A finished studio model is premature while the game camera remains undecided.

## 2. Build one candidate through the whole path

Choose a method appropriate to the object. Procedural Blender scripts suit modular structures and repeatable geometry. Organic heroes may require sculpting, topology cleanup or a separately verified reference-conditioned generation tool. Do not claim that text-generated Blender primitives are image-to-3D. An unavailable generator or engine is a recorded capability gap, not a reason to fabricate output.

Order the work: large forms and silhouette → construction/joints → deformation topology where needed → material separation → texture detail. Review plain shading and grayscale at gameplay size before microdetail. Use material-specific inputs; skin, eyes, cloth, metal and foliage are not interchangeable noise recipes. Set texture density and geometry budgets from screen size and measured runtime needs.

Keep editable source and reproducible export commands. Export to GLB, then inspect the **imported asset in the real renderer**. Verify axes, dimensions, pivot, normals, UVs, packed/baked maps, alpha, shader compatibility and animation names. Preserve proportions; a runtime that independently stretches axes to fit tile rectangles can invalidate the model's design. Record the mapping between visual dimensions and original collision bounds.

Candidate outputs live separately from accepted assets. Never overwrite the accepted release set merely to inspect a build. An isolated staging scene may load an unapproved candidate if its status stays explicit.

**Exit:** one technically valid candidate and runtime evidence bound to its exact artifacts and render context. This is permission to review, not approval to promote.

## 3. Make render feedback an actual worker loop

Give the author the target packet, ownership boundaries, budgets, render command/queue route and required evidence before dispatch. Workers may build directly or submit to a coordinated Blender/GPU queue. A central queue must return actual images and errors to the author. Do not forbid render inspection and then expect one-turn authoring to yield accepted art.

For each revision:

1. Build/export into a new candidate directory; record hashes and technical results.
2. Capture fixed comparison frames in the runtime, plus continuous motion when relevant. Use identical replay frames, camera, lighting and viewport to the comparison context. Keep a close diagnostic view when needed, but do not substitute it for gameplay framing.
3. The author opens the images, compares against the target and identifies the largest visible defect. Separate direct observations from inferred causes.
4. An independent reviewer inspects actual images/motion and writes a verdict with concrete defects: location/frame, symptom, target criterion, likely cause, correction and required recheck.
5. Return that evidence to the author. Revise the editable source or the proven integration cause; rebuild, recapture and obtain a fresh review.

Use a bounded revision budget in the task card. A reasonable initial default is three render/review revisions per modeling method, adjustable to task size and available resources. After two revisions fail to improve the same blocking defect, stop repeating that fix and change the method: reshape/sculpt, repair topology, replace material construction, correct camera/export, or seek a specialist. Budget exhaustion means `changes-required` or a named external blocker; it never converts failure into acceptance. Preserve the latest candidate, defect history and concrete next action.

Do not change the target to match a weak candidate. A justified target change gets a new context version and a fresh review. Do not make every refinement a blocker: distinguish agreed requirements from optional improvements.

## 4. Produce characters for deformation and gameplay motion

Required actions inform topology and rigging before final surface detail. For organic characters, require connected construction where continuity is visible, deformation-friendly joints, usable edge flow around bending regions, correct rest transforms, an articulated rig and inspected skin weights. Deliberately rigid/mechanical art can use rigid parts if the target calls for it; rigid limbs are not evidence of a convincing organic character pipeline.

Prove the export early with bend tests at shoulders, elbows, hips, knees and other relevant joints. Look for detached parts, collapsing volume, intersecting clothing, poor weight gradients and broken normal response. Keep rig controls/editable source even when GLB exports only deformation bones and clips. Reject unsupported constraints or shader features that do not survive baking/export.

Inspect required idle, move, acceleration, jump, landing, hit/death and interaction states, including facing/form/carrying variants actually in scope. Evaluate poses and continuous transitions: weight shift, planted contact, stride relative to travel, sliding, penetration and popping. Clip existence alone is insufficient. Record unsupported actions instead of silently reusing one pose everywhere.

Original simulation owns displacement, collision, AI and event timing. Playback and blends follow the source timeline; prevent double root motion. Verify frame step, pause/resume, replay, reset and live asset replacement. Exported deformation and runtime motion are separate evidence from Blender playback.

**Exit:** current rig/mesh/clip artifacts, inspected extreme-pose evidence and a continuous runtime sequence that passes required motion criteria.

## 5. Accept the playable scene, then enforce promotion

Review the combined scene at the player's camera: foreground/gameplay/background separation, source identity, relative scale, lighting/material consistency, object contact and hero readability. Include supported variants and interactions in a reproducible replay. Missing coverage must have explicit behavior; do not silently switch an entire scene to original graphics or freeze original gameplay because one replacement is unavailable.

Keep two required gates:

- **Technical:** provenance links, GLB/material/clip import, source-state correspondence, controls, scoped interactions, timing, reload and measured performance.
- **Visual:** target identity/proportions, material response, scene composition, lighting, deformation, motion/contact and temporal coherence.

The review binds exact candidate artifacts, technical evidence, reference packet, runtime context and image/motion evidence. Any affected content change invalidates its approval. A reviewer must inspect evidence; a helper can check records and hashes but cannot perceive quality or prove a reviewer told the truth. See [production contracts](production-contracts.md) for review obligations and promotion integration.

Only candidates passing both current gates enter the accepted manifest. Use one promotion owner, immutable candidate versions and an atomic manifest update; preserve the last accepted release on failure. If the existing assembler ignores reviews, it is not a release gate. For a requested pipeline fix, wire enforcement into the actual integration path and test missing, failed and stale reviews. A standalone validation helper is a useful component, not proof that the runtime assembler is protected.

An asset passing alone does not approve every scene that uses it. Re-review affected scene evidence after changes to placement, lighting, camera, materials, state mapping or shared animations. Packaging must use the accepted release manifest for an accepted-art release. Clearly labeled prototype packages may contain candidates without claiming visual acceptance.

## 6. Demonstrate repeatability before scaling

Produce one accepted representative scene through a real failed review and source revision when defects arise; never manufacture a rejection for theater. Rebuild from editable sources in a clean output directory, repeat the replay/captures, validate the resulting versions and promote only with current evidence. If builds are nondeterministic, record why and re-review changed outputs; old hashes cannot approve new bytes.

Test successful reload and failed replacement retention without resetting source gameplay. Verify packaging resolves the intended accepted manifest and launch the package without a dev server. State exact source, scene/action coverage, quality status, hardware/viewport and remaining failures.

Then parallelize bounded asset families, variants, material work, rigs and independent reviews against the accepted exemplar. Keep isolated ownership and one integration owner. Separate author concurrency from Blender/GPU capacity and use a single coordinated queue. Measure accepted integrated assets and revision effort, not first-draft model counts.

A comprehensive skill can specify missing integrations and provide tested gate machinery. It must not claim a high-fidelity production pipeline has been demonstrated until actual assets, runtime feedback, independent acceptance, enforcement and repeatable delivery establish it.
