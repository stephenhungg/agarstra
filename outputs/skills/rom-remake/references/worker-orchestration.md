# Parallel Authoring and Build Orchestration

Separate independent author work from shared integration and resource-heavy Blender jobs. Use available agent tools; do not assume a particular model, fixed worker count, or an external CLI exists.

## Dispatch from an agreed contract

Before production-scale dispatch, prove the shared coordinate/export/material conventions with one representative imported asset. For a high-fidelity batch, use an accepted exemplar and actual target image; for a prototype, a reviewed technical exemplar is enough. Fix shared uncertainty before creating many variants of it.

Partition by asset family or bounded responsibility, with explicit dependencies. Authors own their scripts and candidate output directories. One integration owner owns shared helpers, registries, mappings and accepted output. Assign independent review when production acceptance is required; an author may self-check but cannot certify their own production candidate through the bundled gate.

Use the task card in [production contracts](production-contracts.md). Supply source composites and IDs, target image paths, runtime camera, dimensions/pivots/facing, forms/poses, output paths, resource budgets, and the current defect list. A job without its needed references is not ready merely because a text prompt exists.

## Queue the complete cycle

Track stages independently:

`assigned → authored → built → technically checked → rendered → reviewed → revising or accepted → integrated → packaged`

A stage records current input/output hashes and evidence. `built` never aliases `accepted`. Failed Blender/export jobs return logs to the author. Failed visual checks return the actual images, target comparison, and localized defects. Candidate previews may bypass acceptance only in a clearly separate staging renderer; accepted manifests cannot.

Use a single coordinated build queue with limits based on observed CPU/GPU/memory capacity. Do not multiply Blender processes just because more author agents are available. Record job ownership and active process identity so resumed work does not spawn a competing queue. Reuse completed valid artifacts; invalidate only descendants of changed inputs.

If an existing worker runner prohibits rendering or feedback, adapt its selected task path before asking it for iterative production. If that change is outside the requested task, explain the missing capability rather than launching the same broad first-draft swarm and expecting a different result.

## Feedback and escalation

Set a reasonable local revision/time budget for the selected method and available resources; do not invent a user-authorized spend budget. Review progress after each render. Fix the highest-impact defect first and keep the comparison camera stable unless camera is the diagnosed problem.

When revisions stall, record what was tried and change the reference, construction approach, rig, export mapping, or integration assumption implicated by evidence. Do not hide the defect with microdetail, endless retries, or a lower acceptance threshold. If a required external input/tool is unavailable, preserve the candidate, mark the dependency blocked, and continue independent authorized work.

Budget exhaustion ends that attempt, not the acceptance criteria. Resume or ask for a material decision with concrete evidence if the remaining work cannot progress autonomously.

## Prove repeatability before scaling

For a production-pipeline deliverable, take an initial accepted candidate through the entire loop and then a representative second candidate or meaningful revision through the same machinery. Exercise a failed review and a stale-hash rejection. Confirm feedback reaches the author and accepted registries/packages consume only current accepted versions. A meaningful second revision must exercise changed authored output, returned critique, rebuild, fresh review, and integration; a metadata edit or recopy of an accepted asset does not establish repeatability. Report what remains manual.

Scale bounded variants and independent families only after that loop works. Measure accepted, integrated results and time spent correcting defects rather than author-job completions or raw mesh count.
