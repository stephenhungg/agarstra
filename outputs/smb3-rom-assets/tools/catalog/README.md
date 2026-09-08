# Reproducible Catalog Tools

See `../../catalog/README.md` for commands, coverage, and unresolved cases. These Node.js scripts write to `../../catalog/` relative to their own location and accept a source ROM as argument 1 or via `SMB3_ROM` where needed. No scratch paths or global package installations are required.

`vendor/jsnes/` is JSNES 2.1 source with the documented odd-table 8×16 top-tile correction; its LICENSE is included. `vendor/pngjs/` is pngjs 7.0.0 with its LICENSE. `extractor.js` captures immutable CHR and palette state at rendering time. The scripts do not alter ROM bytes.
