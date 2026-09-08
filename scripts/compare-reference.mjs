import { chromium } from "playwright";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
import fs from "node:fs/promises";
const browser = await chromium.launch({ headless: false });
const dir = "reference/verification/final";
await fs.mkdir(dir, { recursive: true });
const summary = [];
for (const [name, width, height] of [
  ["desktop", 1440, 900],
  ["tablet", 810, 1080],
  ["mobile", 390, 844],
]) {
  const pages = [];
  for (const [side, url] of [
    ["source", "https://fabrica.framer.media/"],
    ["rebuild", "http://localhost:3000"],
  ]) {
    const p = await browser.newPage({ viewport: { width, height } });
    await p.goto(url, { waitUntil: "networkidle" });
    await p.waitForTimeout(3300);
    for (
      let y = 0;
      y < (await p.evaluate(() => document.body.scrollHeight));
      y += height * 0.8
    ) {
      await p.evaluate((y) => scrollTo(0, y), y);
      await p.waitForTimeout(130);
    }
    await p.waitForTimeout(3000);
    await p.addStyleTag({
      content:
        'header,.skip-link,[data-framer-name="Delete me!"],#__framer-badge-container{visibility:hidden!important}',
    });
    await p.evaluate(async () => {
      for (const v of document.querySelectorAll("video")) {
        v.pause();
        v.currentTime = 3;
      }
      await Promise.all(
        [...document.querySelectorAll("video")].map(
          (v) =>
            new Promise((resolve) => {
              if (!v.seeking) resolve();
              else v.addEventListener("seeked", resolve, { once: true });
            }),
        ),
      );
      scrollTo(0, 0);
    });
    await p.waitForTimeout(1800);
    const geometry = await p.locator("main section").evaluateAll((els) =>
      els.map((e) => {
        const r = e.getBoundingClientRect();
        return {
          name: e.getAttribute("data-framer-name") || e.className,
          y: r.y + scrollY,
          h: r.height,
        };
      }),
    );
    const img = PNG.sync.read(
      await p.screenshot({
        fullPage: true,
        path: `${dir}/${name}-${side}.png`,
      }),
    );
    pages.push({ geometry, img });
    await p.close();
  }
  const [a, b] = pages;
  const sections = [];
  for (let i = 0; i < a.geometry.length; i++) {
    const aa = a.geometry[i],
      bb = b.geometry[i];
    if (!bb) continue;
    const h = Math.floor(Math.min(aa.h, bb.h));
    const imgs = pages.map((p, j) => {
      const im = new PNG({ width, height: h });
      const y = Math.round((j ? bb : aa).y);
      PNG.bitblt(p.img, im, 0, Math.max(0, y), width, h, 0, 0);
      return im;
    });
    const diff = new PNG({ width, height: h });
    const mismatched = pixelmatch(
      imgs[0].data,
      imgs[1].data,
      diff.data,
      width,
      h,
      { threshold: 0.15, includeAA: false },
    );
    const score = 100 * (1 - mismatched / (width * h));
    await fs.writeFile(
      `${dir}/${name}-${String(i + 1).padStart(2, "0")}-diff.png`,
      PNG.sync.write(diff),
    );
    sections.push({
      section: aa.name,
      sourceHeight: aa.h,
      rebuildHeight: bb.h,
      heightDelta: bb.h - aa.h,
      pixelAgreement: Math.round(score * 100) / 100,
    });
  }
  const value = { viewport: name, width, height, sections };
  summary.push(value);
  await fs.writeFile(`${dir}/summary.json`, JSON.stringify(summary, null, 2));
  console.log(JSON.stringify(value));
}
await browser.close();
