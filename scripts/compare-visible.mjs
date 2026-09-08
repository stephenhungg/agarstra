import { chromium } from "playwright";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
import fs from "node:fs/promises";
const browser = await chromium.launch({ headless: false });
const dir = "reference/verification/visible";
await fs.mkdir(dir, { recursive: true });
const summary = [];
const footerOnly = process.env.SECTION === "footer";
for (const [name, width, height] of [
  ["desktop", 1440, 900],
  ["tablet", 810, 1080],
  ["mobile", 390, 844],
]) {
  if (process.env.VIEWPORT && process.env.VIEWPORT !== name) continue;
  const captures = [];
  for (const [side, url] of [
    ["source", "https://fabrica.framer.media/"],
    ["rebuild", "http://localhost:3000"],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForTimeout(3400);
    await page.addStyleTag({
      content:
        'header,.skip-link,[data-framer-name="Delete me!"],#__framer-badge-container{visibility:hidden!important}',
    });
    await page.mouse.move(width - 1, 1);
    const els = page.locator(footerOnly ? "footer" : "main section,footer");
    const info = [];
    for (let i = 0; i < (await els.count()); i++) {
      const el = els.nth(i);
      const g = await el.evaluate((e) => {
        const r = e.getBoundingClientRect();
        return {
          name: e.getAttribute("data-framer-name") || e.className,
          y: r.y + scrollY,
          h: r.height,
        };
      });
      if (g.h < 100) continue;
      const out = new PNG({ width, height: Math.ceil(g.h) });
      for (let offset = 0; offset < out.height; offset += height) {
        await page.evaluate((y) => scrollTo(0, y), g.y + offset);
        await page.waitForTimeout(1650);
        await page.evaluate(async () => {
          for (const v of document.querySelectorAll("video")) {
            v.pause();
            v.currentTime = 3;
          }
          await Promise.all(
            [...document.querySelectorAll("video")].map(
              (v) =>
                new Promise((r) => {
                  if (!v.seeking) r();
                  else v.addEventListener("seeked", r, { once: true });
                }),
            ),
          );
        });
        await page.waitForTimeout(80);
        const scrollY = await page.evaluate(() => window.scrollY);
        const shot = PNG.sync.read(await page.screenshot());
        const sourceY = Math.max(0, Math.round(g.y + offset - scrollY));
        const rows = Math.min(height - sourceY, out.height - offset);
        if (rows > 0) PNG.bitblt(shot, out, 0, sourceY, width, rows, 0, offset);
      }
      await fs.writeFile(
        `${dir}/${name}-${String(footerOnly ? 14 : i + 1).padStart(2, "0")}-${side}.png`,
        PNG.sync.write(out),
      );
      info.push({ geometry: g, image: out });
    }
    captures.push(info);
    await page.close();
  }
  const sections = [];
  let same = 0,
    total = 0;
  for (let i = 0; i < Math.min(captures[0].length, captures[1].length); i++) {
    const a = captures[0][i],
      b = captures[1][i];
    const h = Math.min(a.image.height, b.image.height);
    const crop = (p) => {
      const out = new PNG({ width, height: h });
      PNG.bitblt(p, out, 0, 0, width, h, 0, 0);
      return out;
    };
    const aa = crop(a.image),
      bb = crop(b.image);
    const diff = new PNG({ width, height: h });
    const mismatch = pixelmatch(aa.data, bb.data, diff.data, width, h, {
      threshold: 0.15,
      includeAA: false,
    });
    same += width * h - mismatch;
    total += width * h;
    await fs.writeFile(
      `${dir}/${name}-${String(footerOnly ? 14 : i + 1).padStart(2, "0")}-diff.png`,
      PNG.sync.write(diff),
    );
    sections.push({
      name: a.geometry.name,
      sourceHeight: a.geometry.h,
      rebuildHeight: b.geometry.h,
      pixelAgreement: +(100 * (1 - mismatch / (width * h))).toFixed(2),
    });
  }
  const report = {
    viewport: name,
    width,
    height,
    pixelAgreement: +((same / total) * 100).toFixed(2),
    sections,
  };
  summary.push(report);
  await fs.writeFile(
    `${dir}/summary${footerOnly ? "-footer" : ""}${process.env.VIEWPORT ? "-" + process.env.VIEWPORT : ""}.json`,
    JSON.stringify(summary, null, 2),
  );
  console.log(JSON.stringify(report));
}
await browser.close();
