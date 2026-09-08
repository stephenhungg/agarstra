import fs from "node:fs";
import { execFileSync } from "node:child_process";
export function readROM() {
  const file =
    process.env.NES_ROM ||
    "/Users/stephenhung/Downloads/Super Mario Bros. 3.zip";
  if (!file.toLowerCase().endsWith(".zip")) return fs.readFileSync(file);
  const entry = execFileSync("/usr/bin/unzip", ["-Z1", file], {
    encoding: "utf8",
  })
    .split("\n")
    .find((n) => /\.nes$/i.test(n));
  if (!entry) throw new Error("No .nes ROM in archive");
  return execFileSync("/usr/bin/unzip", ["-p", file, entry], {
    maxBuffer: 8 * 1024 * 1024,
  });
}
