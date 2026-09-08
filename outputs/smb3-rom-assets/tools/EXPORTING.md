# Edit Blender assets and export replacements

Open `blender/rom-source-assets.blend`. The registered colored assets are in `02_Assembled_Source_Assets`; the runtime currently uses its 193 individual 8×8 tiles. Find an object by its `tile-…` asset ID. Edit its mesh in Edit Mode or add modifiers. Preserve its top-left origin, scale of 1/16 Blender unit per pixel, and `asset_id` / `source_provenance` custom properties. Save your intended edits in Blender before running the command below.

Export one edited object to the app's source assets:

```sh
blender --background --python-exit-code 1 \
  --python /path/to/smb3-rom-assets/tools/export_replacements.py -- \
  --registry /path/to/smb3-rom-assets/blender/replacement-registry.json \
  --output /path/to/smb3-demo/public/assets/source-glb \
  --asset-id tile-a76793605446b3cf2113
```

Repeat `--asset-id` for multiple objects. Omit it to export all 193 registered runtime tiles. If `blender` is not on PATH, use your Blender executable's full path; on this machine it is `/Volumes/Blender/Blender.app/Contents/MacOS/Blender`.

The script opens the existing `.blend`, exports actual edited mesh geometry and modifiers, and retains source metadata in GLB extras. It temporarily removes each object's catalog-grid translation, preserving local geometry and its top-left origin. It restores the loaded scene's object transforms afterward and **never saves the `.blend`**. Stable GLB filenames let the runtime reconnect replacements to the original CHR-and-palette identities. `replacement-export.json` records the exported IDs and file hashes.

After exporting to `public/assets/source-glb`, run `npm run build` from `smb3-demo`, then restart the source demo. Run `npm run package` to update the standalone `SMB3 Asset Lab.app`. For a quick test of an already built app, export directly to `smb3-demo/dist/assets/source-glb` and click `Reload Blender edits` in the source demo; a later build replaces that directory, so keep durable exports in `public`.

## Verified roundtrip

`tile-a76793605446b3cf2113` was reexported with Blender 4.5 and imported back through Blender's glTF importer. Its world-space geometry bounds match the original GLB, its catalog translation is zero, and its `asset_id` and complete `source_provenance` are unchanged. The app's visual comparison is a separate runtime check.
