# Reproducible family builds

Run `python3 outputs/smb3-photoreal/tools/build_queue.py` from the workspace. Blender defaults to `/Volumes/Blender/Blender.app/Contents/MacOS/Blender`; update `BLENDER` for another installation.

The queue reads author completion from `work/photoreal-swarm/status.json` and optional additive jobs from `extra-build-jobs.json`, but never writes either. It writes independent atomic `build-status.json`. At most two Blender processes run, including preview rendering, each with four threads. Only completed author jobs are eligible. A completed manifest plus expected GLBs permits restart without rebuilding; source hash changes force rebuilding. Render-helper changes force new contact sheets.

Each family delivers original authored build source in its job folder, `library.blend`, standalone `models/*.glb`, structural `validation.json`, an actual Blender/Cycles 24-sample `preview.png`, and logs. `phase: done` means exported, structurally validated and rendered. It does **not** certify photorealism or game fidelity. `visual-review.json` records separate actual-image inspection when available. Runtime readability requires in-game inspection.

A failed job is retried only after its build source changes. Inspect `build.log`, `validation.json` or `render.log` before fixing mechanical errors. Preserve authored geometry and source mappings when repairing API compatibility. Do not launch a second queue against the same status file.
