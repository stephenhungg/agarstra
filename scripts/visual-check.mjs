// Headed, settled screenshot pairs. Run against the live reference + local dev server.
import { chromium } from "playwright";
import fs from "node:fs/promises";
const browser = await chromium.launch({ headless: false });
const dest = "reference/verification/screens";
await fs.mkdir(dest, { recursive: true });
for (const [name, width, height] of [
  ["desktop", 1440, 900],
  ["mobile", 390, 844],
  ["tablet", 810, 1080],
]) {
  for (const [side, url] of [
    ["source", "https://fabrica.framer.media/"],
    ["rebuild", "http://localhost:3000"],
  ]) {
    const page = await browser.newPage({ viewport: { width, height } });
    await page.goto(url, { waitUntil: "networkidle" });
    await page.waitForTimeout(3500);
    await page.evaluate(async () => {
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
    });
    const sections = page.locator("main section");
    const count = await sections.count();
    for (let i = 0; i < count; i++) {
      const el = sections.nth(i);
      await el.scrollIntoViewIfNeeded();
      await page.waitForTimeout(1600);
      await el.screenshot({
        path: `${dest}/${name}-${String(i + 1).padStart(2, "0")}-${side}.png`,
        timeout: 30000,
      });
    }
    await page.close();
  }
}
await browser.close();
