import fs from "node:fs/promises";
import { PNG } from "pngjs";
import pixelmatch from "pixelmatch";
const dir = "reference/verification/visible";
const reports = JSON.parse(await fs.readFile(`${dir}/summary.json`, "utf8"));
const footerReports = JSON.parse(
  await fs.readFile(`${dir}/summary-footer.json`, "utf8"),
);
for (const report of reports) {
  let pixels = 0,
    differences = 0;
  for (let i = 0; i < report.sections.length; i++) {
    const prefix = `${dir}/${report.viewport}-${String(i + 1).padStart(2, "0")}`;
    const source = PNG.sync.read(await fs.readFile(`${prefix}-source.png`));
    const rebuild = PNG.sync.read(await fs.readFile(`${prefix}-rebuild.png`));
    const width = source.width,
      height = Math.min(source.height, rebuild.height);
    const crop = (image) => {
      const out = new PNG({ width, height });
      PNG.bitblt(image, out, 0, 0, width, height, 0, 0);
      return out;
    };
    const a = crop(source),
      b = crop(rebuild);
    const mismatch = pixelmatch(a.data, b.data, null, width, height, {
      threshold: 0.15,
      includeAA: false,
    });
    differences += mismatch;
    pixels += width * height;
    report.sections[i].pixelAgreement = +(
      100 *
      (1 - mismatch / (width * height))
    ).toFixed(2);
    if (i === 13) {
      const footer = footerReports.find((f) => f.viewport === report.viewport)
        ?.sections[0];
      if (footer)
        Object.assign(report.sections[i], {
          sourceHeight: footer.sourceHeight,
          rebuildHeight: footer.rebuildHeight,
        });
    }
  }
  report.pixelAgreement = +(100 * (1 - differences / pixels)).toFixed(2);
}
await fs.writeFile(
  `${dir}/summary-final.json`,
  JSON.stringify(reports, null, 2),
);
console.log(
  reports.map(({ viewport, pixelAgreement }) => ({ viewport, pixelAgreement })),
);
