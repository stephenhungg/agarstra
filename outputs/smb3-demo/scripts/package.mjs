import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { execFileSync } from "node:child_process";
import { preflight, publish, inventory, pruneModels, acceptedModels } from "./package-gate.mjs";
const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const prototype = process.argv.includes("--prototype");
const profile = prototype ? "prototype" : "production";
const name = prototype ? "SMB3 Asset Lab Prototype" : "SMB3 Asset Lab";
const output = path.resolve(root, `../${name}.app`);
await preflight(path.join(root, "public"), root, profile, false);
if (process.argv.includes("--preflight")) {
  console.log(`Package preflight passed (${profile})`);
  process.exit(0);
}
execFileSync(process.execPath, [path.join(root, "node_modules/vite/bin/vite.js"), "build"], { cwd: root, stdio: "inherit", env: { ...process.env, ASSET_PROFILE: profile } });
const registries = await preflight(path.join(root, "dist"), root, profile);
const allowedModels = prototype ? undefined : acceptedModels(path.join(root, "dist"), registries);
const builtInventory = inventory(path.join(root, "dist"), { allowedModels });
const staging = fs.mkdtempSync(path.join(path.dirname(output), ".smb3-package-"));
const stage = path.join(staging, `${name}.app`);
try {
const runtime = path.join(root, "node_modules/electron/dist/Electron.app");
execFileSync("/usr/bin/ditto", [runtime, stage]);
const resources = path.join(stage, "Contents/Resources");
const target = path.join(resources, "app");
fs.mkdirSync(target, { recursive: true });
const licenses = path.join(target, "licenses");
fs.mkdirSync(licenses, { recursive: true });
fs.copyFileSync(path.join(root, "src/vendor/jsnes/LICENSE"), path.join(licenses, "JSNES-LICENSE"));
fs.copyFileSync(path.join(root, "src/vendor/jsnes/PATCHES.md"), path.join(licenses, "JSNES-PATCHES.md"));
fs.copyFileSync(path.join(root, "node_modules/three/LICENSE"), path.join(licenses, "THREE-LICENSE"));
for (const file of ["electron.cjs", "preload.cjs"])
  fs.copyFileSync(path.join(root, file), path.join(target, file));
fs.rmSync(path.join(target, "dist"), { recursive: true, force: true });
fs.cpSync(path.join(root, "dist"), path.join(target, "dist"), {
  recursive: true,
});
if (!prototype) pruneModels(path.join(target, "dist"), allowedModels);
fs.writeFileSync(
  path.join(target, "package.json"),
  JSON.stringify(
    { name: "smb3-asset-lab", version: "0.4.0", main: "electron.cjs" },
    null,
    2,
  ),
);
fs.writeFileSync(path.join(target, "release-profile.json"), JSON.stringify({ profile, productionEvidenceAccepted: !prototype, sceneArtisticQualityGuaranteed: false }, null, 2));
const iconset = path.join(staging, "app.iconset");
fs.mkdirSync(iconset, { recursive: true });
for (const size of [16, 32, 128, 256, 512]) {
  execFileSync(
    "/usr/bin/sips",
    [
      "-z",
      String(size),
      String(size),
      path.join(root, "public/icon.png"),
      "--out",
      path.join(iconset, `icon_${size}x${size}.png`),
    ],
    { stdio: "ignore" },
  );
  execFileSync(
    "/usr/bin/sips",
    [
      "-z",
      String(size * 2),
      String(size * 2),
      path.join(root, "public/icon.png"),
      "--out",
      path.join(iconset, `icon_${size}x${size}@2x.png`),
    ],
    { stdio: "ignore" },
  );
}
execFileSync("/usr/bin/iconutil", [
  "-c",
  "icns",
  iconset,
  "-o",
  path.join(resources, "world1.icns"),
]);
const plist = path.join(stage, "Contents/Info.plist");
for (const [key, value] of Object.entries({
  CFBundleName: name,
  CFBundleDisplayName: name,
  CFBundleIdentifier: prototype ? "local.replay.smb3assetlab.prototype" : "local.replay.smb3assetlab",
  CFBundleIconFile: "world1.icns",
  CFBundleShortVersionString: "0.4.0",
  CFBundleVersion: "1",
  LSApplicationCategoryType: "public.app-category.games",
}))
  execFileSync("/usr/bin/plutil", ["-replace", key, "-string", value, plist]);
execFileSync(
  "/usr/bin/codesign",
  ["--force", "--deep", "--sign", "-", stage],
  { stdio: "inherit" },
);
execFileSync("/usr/bin/codesign", ["--verify", "--deep", "--strict", stage], {
  stdio: "inherit",
});
await preflight(path.join(target, "dist"), root, profile);
if (inventory(path.join(target, "dist")) !== builtInventory) throw new Error("Staged package bytes differ from verified build");
publish(stage, output);
console.log(`Packaged ${profile}: ${output}`);
} finally {
  fs.rmSync(staging, { recursive: true, force: true });
}
