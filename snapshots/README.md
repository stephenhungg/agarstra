# Complete FireRed working snapshot

The FireRed application, runtime, models, textures, generated web build, extracted data, checkpoints, and verification artifacts are tracked directly under `outputs/pokemon-remake`. Large binary files use Git LFS.

`firered-work.tar.gz` preserves the corresponding `work/pokemon` tree, including the local ROM, authoring inputs/scripts, source checkout files, toolchain, downloaded source models, and intermediate results. Installed `node_modules` and nested `.git` metadata are excluded. This is a point-in-time snapshot; active tasks may subsequently change local files.

Restore from a fresh clone:

```sh
git lfs install
git lfs pull
mkdir -p work
tar -xzf snapshots/firered-work.tar.gz -C work
npm --prefix outputs/pokemon-remake/app install
npm --prefix outputs/pokemon-remake/app start
```

The native application targets the existing macOS Electron setup. The restored ROM path is `work/pokemon/rom/firered-user.gba`. Source materials retain their included license and provenance records.
