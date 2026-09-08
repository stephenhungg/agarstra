# SMB3 project location

The complete project now lives in `/Users/stephenhung/Documents/GitHub/agarstra`.
The existing Next.js project at the repository root is preserved.

- `outputs/smb3-demo/`: playable Electron/Three.js app source, tests, and dependencies.
- `outputs/smb3-photoreal/`: Blender authoring sources, material/build tools, 73 models, libraries, gallery, and verification.
- `outputs/smb3-rom-assets/`: ROM extraction tools, catalog, and source asset libraries.
- `work/`: all intermediate code, 24 worker jobs and logs, source checkouts, experiments, and runtime tools.
- `outputs/Launch Demo.command`: launch the packaged app.

Run from the new repository root:

```sh
npm --prefix outputs/smb3-demo run start:prototype
npm --prefix outputs/smb3-demo test
python3 outputs/smb3-photoreal/tools/build_gallery.py
```

For binary manifest extraction, the runnable source-checkout copy is `work/asset-map-v2/extract_manifest.py`.

The old Codex workspace contains compatibility symlinks named `outputs` and `work`; the files themselves have moved. These preserve earlier links and historical absolute paths in authored jobs without modifying their verified source hashes. The ROM remains in Downloads, and Blender remains at its existing external application path.

No commit or push was performed.

Production enforcement is now connected to assembly, both GLB reload consumers, and packaging. See `outputs/smb3-photoreal/PRODUCTION_PIPELINE.md`. Existing assets have no production acceptance; the launcher opens the separately labeled prototype package.
