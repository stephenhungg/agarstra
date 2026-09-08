import fs from "node:fs/promises";
import path from "node:path";
const reference = JSON.parse(
  await fs.readFile("reference/inspection/live.json", "utf8"),
);
const urls = new Set(
  reference.nodes
    .filter(
      (n) => ["IMG", "VIDEO"].includes(n.tag) && n.src?.startsWith("https://"),
    )
    .map((n) => n.src),
);
for (const font of reference.fonts.filter(
  (f) => f.includes("U+0-FF") && f.includes("font-style: normal"),
)) {
  const u = font.match(/url\("([^"]+)/)?.[1];
  if (u) urls.add(u);
}
await fs.mkdir("public/assets", { recursive: true });
let list = [...urls];
let map = {};
await Promise.all(
  Array.from({ length: 8 }, async () => {
    while (list.length) {
      const u = list.shift();
      const key = new URL(u).pathname;
      const filename = path.basename(key);
      const local = "/assets/" + filename;
      try {
        await fs.access("public" + local);
      } catch {
        const r = await fetch(u);
        if (!r.ok) throw Error(u + " " + r.status);
        await fs.writeFile(
          "public" + local,
          new Uint8Array(await r.arrayBuffer()),
        );
      }
      map[key] = local;
    }
  }),
);
await fs.writeFile("lib/asset-map.json", JSON.stringify(map, null, 2));
const css = reference.fonts
  .filter((f) => f.includes("U+0-FF") && f.includes("font-style: normal"))
  .map((f) => f.replace(/https:\/\/[^/]+([^"\)]+)/g, (_, p) => map[p] || p))
  .join("\n");
await fs.writeFile("app/fonts.css", css);
console.log(`Prepared ${Object.keys(map).length} original assets.`);
