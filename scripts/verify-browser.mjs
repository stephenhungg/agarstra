import { chromium } from "playwright";
import fs from "node:fs/promises";

const baseURL = process.env.QA_URL || "http://localhost:3000";
const results = [];
const errors = [];
const check = (name, condition, detail) => {
  results.push({
    name,
    passed: !!condition,
    ...(detail === undefined ? {} : { detail }),
  });
  if (!condition) console.error("FAIL", name, detail);
};
const browser = await chromium.launch({ headless: false });
try {
  const page = await browser.newPage({
    viewport: { width: 1440, height: 900 },
  });
  page.on("pageerror", (error) => errors.push(error.message));
  await page.goto(baseURL, { waitUntil: "networkidle" });
  await page.waitForTimeout(3400);
  check(
    "agarstra title and hero branding",
    (await page.title()).startsWith("agarstra —") &&
      (await page.locator(".nav-brand").innerText()) === "agarstra" &&
      (await page.locator("h1").innerText()).includes("New dimensions."),
  );
  check(
    "hero entrance settles visibly",
    await page
      .locator(".hero-shell")
      .evaluate(
        (element) =>
          getComputedStyle(element).opacity === "1" &&
          element.getBoundingClientRect().height > 0,
      ),
  );
  const oldContent = await page.evaluate(() => ({
    text:
      document.body.innerText.match(
        /fabrica|\$1,990|\$2,490|trusted by.*clients|book a call/gi,
      ) || [],
    links: [...document.querySelectorAll("a[href]")]
      .map((a) => a.href)
      .filter((href) => /fabrica|framer\.(media|com)/i.test(href)),
  }));
  check(
    "no Fabrica branding, business claims, or destination links",
    !oldContent.text.length && !oldContent.links.length,
    oldContent,
  );
  const anchors = await page
    .locator('a[href^="#"]')
    .evaluateAll((links) =>
      links
        .map((link) => link.getAttribute("href"))
        .filter(
          (href) =>
            !href || href === "#" || !document.getElementById(href.slice(1)),
        ),
    );
  const navLabels = await page.locator(".top-nav .nav-link").allTextContents();
  check(
    "new navigation and all internal anchor targets exist",
    anchors.length === 0 &&
      JSON.stringify(navLabels) ===
        JSON.stringify(["Pipeline", "Prototype", "Progress", "Get the skill"]),
    { anchors, navLabels },
  );
  await page.getByRole("button", { name: "Open menu", exact: true }).click();
  await page.waitForTimeout(1100);
  check(
    "menu opens with visible navigation",
    (await page
      .getByRole("button", { name: "Close menu", exact: true })
      .getAttribute("aria-expanded")) === "true" &&
      (await page.locator(".menu-nav").isVisible()) &&
      (await page.locator(".site-header").boundingBox()).height > 700,
  );
  await page.keyboard.press("Escape");
  await page.waitForTimeout(700);
  check(
    "menu Escape closes and restores toggle focus",
    await page
      .getByRole("button", { name: "Open menu", exact: true })
      .evaluate(
        (element) =>
          element.getAttribute("aria-expanded") === "false" &&
          document.activeElement === element,
      ),
  );
  await page.getByRole("button", { name: "Open menu", exact: true }).click();
  await page.waitForTimeout(1100);
  await page
    .locator(".menu-nav")
    .getByRole("link", { name: "Pipeline", exact: true })
    .click();
  await page.waitForTimeout(1800);
  const pipelineNavigation = await page
    .locator("#pipeline")
    .evaluate((element) => ({
      top: element.getBoundingClientRect().top,
      scroll: scrollY,
      overflow: document.body.style.overflow,
    }));
  check(
    "menu link closes menu and navigates to pipeline",
    pipelineNavigation.scroll > 500 &&
      Math.abs(pipelineNavigation.top) < 120 &&
      pipelineNavigation.overflow !== "hidden" &&
      (await page
        .getByRole("button", { name: "Open menu", exact: true })
        .isVisible()),
    pipelineNavigation,
  );
  const project = page.locator("[data-project]").first();
  await project.scrollIntoViewIfNeeded();
  await page.waitForTimeout(1400);
  await project.hover();
  await page.waitForTimeout(600);
  const hover = await project.locator(".project-image").evaluate((element) => ({
    scale: new DOMMatrix(getComputedStyle(element).transform).a,
    filter: getComputedStyle(element).filter,
  }));
  check(
    "GSAP project hover scales and blurs image",
    Math.abs(hover.scale - 1.13) < 0.01 && hover.filter === "blur(7px)",
    hover,
  );
  await page.mouse.move(0, 0);
  const toggles = page.locator(".service-toggle");
  await toggles.nth(1).scrollIntoViewIfNeeded();
  await toggles.nth(1).click();
  await page.waitForTimeout(600);
  const independent =
    (await toggles.nth(0).getAttribute("aria-expanded")) === "true" &&
    (await toggles.nth(1).getAttribute("aria-expanded")) === "true";
  await toggles.nth(1).click();
  await page.waitForTimeout(450);
  check(
    "pipeline accordions open and close independently",
    independent &&
      (await toggles.nth(0).getAttribute("aria-expanded")) === "true" &&
      (await toggles.nth(1).getAttribute("aria-expanded")) === "false",
  );
  const today = page.getByRole("tab", { name: "Today", exact: true });
  const next = page.getByRole("tab", { name: "Next", exact: true });
  await today.scrollIntoViewIfNeeded();
  const current = await page.getByRole("tabpanel").innerText();
  await next.click();
  await page.waitForTimeout(500);
  check(
    "Today and Next tabs distinguish prototype from unfinished work",
    /end-to-end prototype/i.test(current) &&
      (await next.getAttribute("aria-selected")) === "true" &&
      /not production-complete/i.test(
        await page.getByRole("tabpanel").innerText(),
      ),
  );
  await next.focus();
  await page.keyboard.press("ArrowLeft");
  await page.waitForTimeout(500);
  check(
    "status tabs support keyboard navigation",
    (await today.evaluate(
      (element) =>
        document.activeElement === element &&
        element.getAttribute("aria-selected") === "true",
    )) &&
      (await page.getByRole("tabpanel").innerText()).includes(
        "The path works.",
      ),
  );
  const faq = page.locator(".ls-faq-item").first();
  await faq.scrollIntoViewIfNeeded();
  const beforeFAQ = (await faq.boundingBox()).height;
  const beforeExpanded = await faq
    .locator("button")
    .getAttribute("aria-expanded");
  await faq.locator("button").click();
  await page.waitForTimeout(600);
  check(
    "FAQ disclosure changes state and animated height",
    Math.abs(beforeFAQ - (await faq.boundingBox()).height) > 40 &&
      (await faq.locator("button").getAttribute("aria-expanded")) !==
        beforeExpanded,
  );
  const preview = page.locator(".middle-film");
  await preview.scrollIntoViewIfNeeded();
  await preview.click();
  await page.waitForTimeout(300);
  check(
    "prototype dialog shows actual runtime image",
    (await page.locator("dialog").evaluate((element) => element.open)) &&
      (await page.locator("dialog img").getAttribute("src")) ===
        "/agarstra/prototype.png" &&
      (await page
        .locator("dialog img")
        .evaluate((element) => element.complete && element.naturalWidth > 0)),
  );
  await page.keyboard.press("Escape");
  await page.waitForTimeout(100);
  check(
    "prototype dialog Escape restores trigger focus",
    (await page.locator("dialog").evaluate((element) => !element.open)) &&
      (await preview.evaluate((element) => document.activeElement === element)),
  );
  await page.context().grantPermissions(["clipboard-read", "clipboard-write"]);
  const install = page.getByRole("button", { name: "Copy install command" });
  await install.click();
  const copied = await page.evaluate(() => navigator.clipboard.readText());
  check(
    "install button copies a complete Codex instruction",
    copied === (await page.locator("#skill-install-prompt").inputValue()) &&
      copied.includes(
        "https://agarstra.stephenhung.me/downloads/agarstra-rom-remake.zip",
      ) &&
      copied.includes("$CODEX_HOME/skills/rom-remake") &&
      (await page.getByRole("status").innerText()).includes("Copied."),
  );
  await page.evaluate(() => {
    Object.defineProperty(navigator.clipboard, "writeText", {
      configurable: true,
      value: async () => {
        throw new Error("Clipboard denied");
      },
    });
  });
  await install.click();
  check(
    "clipboard denial selects a manual-copy fallback",
    (await page.getByRole("status").innerText()).includes("Select and copy") &&
      (await page
        .locator("#skill-install-prompt")
        .evaluate(
          (element) =>
            document.activeElement === element &&
            element.selectionEnd - element.selectionStart ===
              element.value.length,
        )),
  );
  const zip = await page.request.get(
    new URL("/downloads/agarstra-rom-remake.zip", baseURL).href,
  );
  const zipBytes = await zip.body();
  check(
    "skill download returns a ZIP archive",
    zip.status() === 200 &&
      zipBytes.subarray(0, 4).equals(Buffer.from([0x50, 0x4b, 0x03, 0x04])),
    { status: zip.status(), bytes: zipBytes.length },
  );
  const playbook = await page.request.get(
    new URL("/agarstra/playbook.md", baseURL).href,
  );
  const playbookText = await playbook.text();
  check(
    "playbook returns readable workflow documentation",
    playbook.status() === 200 &&
      playbookText.length > 300 &&
      /ROM|Blender/.test(playbookText) &&
      !/<html/i.test(playbookText),
    { status: playbook.status(), characters: playbookText.length },
  );
  for (const [width, height] of [
    [1440, 900],
    [810, 1080],
    [768, 1024],
    [390, 844],
    [320, 740],
  ]) {
    await page.setViewportSize({ width, height });
    await page.waitForTimeout(500);
    const dimensions = await page.evaluate(() => ({
      width: innerWidth,
      scrollWidth: document.documentElement.scrollWidth,
    }));
    check(
      `no horizontal overflow at ${width}px`,
      dimensions.scrollWidth <= dimensions.width + 1,
      dimensions,
    );
  }
  await page.setViewportSize({ width: 1440, height: 900 });
  for (
    let y = 0;
    y < (await page.evaluate(() => document.body.scrollHeight));
    y += 800
  ) {
    await page.evaluate((offset) => scrollTo(0, offset), y);
    await page.waitForTimeout(100);
  }
  await page.waitForTimeout(700);
  const broken = await page
    .locator("img")
    .evaluateAll((elements) =>
      elements
        .filter((element) => !element.complete || !element.naturalWidth)
        .map((element) => element.src),
    );
  check("all page images load", broken.length === 0, broken);
  const reduced = await browser.newPage({
    viewport: { width: 390, height: 844 },
    reducedMotion: "reduce",
  });
  reduced.on("pageerror", (error) => errors.push(error.message));
  await reduced.goto(baseURL, { waitUntil: "networkidle" });
  check(
    "reduced motion hero is immediately visible",
    await reduced
      .locator(".hero-shell")
      .evaluate((element) => getComputedStyle(element).opacity === "1"),
  );
  await reduced.getByRole("button", { name: "Open menu", exact: true }).click();
  check(
    "reduced motion menu opens instantly",
    await reduced
      .locator(".site-header")
      .evaluate(
        (element) =>
          Math.abs(element.getBoundingClientRect().height - innerHeight) < 1,
      ),
  );
  check("no browser runtime errors", errors.length === 0, errors);
} catch (error) {
  check("browser scenario completed", false, error.stack || String(error));
} finally {
  await browser.close();
  await fs.mkdir("reference/agarstra", { recursive: true });
  await fs.writeFile(
    "reference/agarstra/browser-checks.json",
    JSON.stringify(results, null, 2) + "\n",
  );
  console.log(
    `${results.filter((result) => result.passed).length}/${results.length} checks passed`,
  );
  if (results.some((result) => !result.passed)) process.exitCode = 1;
}
