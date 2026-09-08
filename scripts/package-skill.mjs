import fs from "node:fs/promises";
import path from "node:path";
import { execFileSync } from "node:child_process";
const source = path.resolve("outputs/skills/rom-remake");
const stage = await fs.mkdtemp("/tmp/agarstra-skill-");
const target = path.join(stage, "rom-remake");
await fs.cp(source, target, {
  recursive: true,
  filter: (p) => !p.split(path.sep).some((part) => ["__pycache__", "node_modules", "dist"].includes(part)) && !p.endsWith(".pyc"),
});
const portable = async (directory) => {
  for (const item of await fs.readdir(directory, { withFileTypes: true })) {
    const file = path.join(directory, item.name);
    if (item.isDirectory()) await portable(file);
    else if (item.name.endsWith(".md")) {
      const text = await fs.readFile(file, "utf8");
      await fs.writeFile(
        file,
        text
          .replaceAll(
            "/Users/stephenhung/Documents/GitHub/agarstra",
            "<project-root>",
          )
          .replaceAll(
            "/Users/stephenhung/Documents/Codex/2026-09-08/o",
            "<legacy-workspace>",
          )
          .replaceAll(
            "/Users/stephenhung/Downloads/Super Mario Bros. 3.zip",
            "<your-ROM-path>",
          ),
      );
    }
  }
};
await portable(target);
const output = path.resolve("public/downloads/agarstra-rom-remake.zip");
await fs.rm(output, { force: true });
execFileSync("zip", ["-qr", output, "rom-remake"], { cwd: stage });
await fs.rm(stage, { recursive: true, force: true });
console.log("Packaged portable rom-remake skill (no ROMs or game assets).");
