> Historical verification of the Fabrica recreation before the agarstra rebrand. These scores do not describe the current product landing page, whose content, images, and sections intentionally differ. Current checks: `npm run test:browser`.

# Fidelity and verification

Reference: https://fabrica.framer.media/ — captured September 8, 2026 using the user's extract-site skill, headed Chromium, live geometry inspection, recovered authored animation values, and repeated interaction captures.

## Visual comparison

| Viewport            | Pixel agreement |
| ------------------- | --------------: |
| Desktop, 1440 × 900 |          97.95% |
| Tablet, 810 × 1080  |          97.04% |
| Mobile, 390 × 844   |          96.00% |

These are area-weighted screenshot pixel agreement scores, not a universal perceptual or animation fidelity score. All 13 homepage sections and the footer were compared. Each section was captured in visible viewport strips after a 1.65-second settling interval, then stitched. Videos were paused at 3 seconds in both versions. Pixelmatch used threshold 0.15 and excluded anti-aliasing differences. Images were compared over their common height; section heights were recorded separately. Fixed headers, the local skip link, and Framer purchase badges were excluded from image comparison. Navigation was tested separately.

Scores combine the complete section comparison with a fresh footer comparison after the final corrections (black bottom bar, quote wrapping, wordmark scale). `scripts/summarize-comparison.mjs` recomputes the weighted scores directly from the final image pairs. The source's transient reveals make ordinary full-page screenshots unreliable; the viewport-strip method avoids most of that error. Raw results and images are retained locally in `reference/verification/visible/`; `summary-final.json` contains the final measurements.

## Motion

The implementation uses GSAP rather than importing Framer-generated components:

- Loader: 400 ms character entrance, 300 ms initial delay, 90 ms stagger, 270 px translation, 5 px blur, recovered cubic-bezier curve.
- Hero: delayed spring entrance with desktop and mobile translation settings.
- Clients: linear scroll-linked scale 0.95 → 1 and translateY −290 → 0. At seven matching desktop scroll samples, source/rebuild scale and translation differed by less than 0.00004 (scale units / CSS pixels).
- Text: 900 ms word reveals, 20 ms stagger, recovered easing.
- Projects: 450 ms image scale 1 → 1.13, blur 0 → 7 px, logo scale 1 → 0.8, matching overlay and inset motion.
- Pills: 20 px rolling labels and layered dots; team/blog/footer hovers also use GSAP.
- Services expand independently; pricing tabs update copy and prices; FAQs animate height and opacity.
- Menu: 60 px closed height, 745.8 px expanded desktop height, animated links and toggle strokes.

Hero/shared reveal springs are analytical approximations to recovered Framer spring settings. Native scrolling is retained instead of reproducing the source's Lenis scroll smoothing. Matching endpoint geometry and recovered timing does not prove identical intermediate frames across two animation engines.

## Verification and scope

Production build and TypeScript check passed; all 20 headed browser checks passed. A separate Lighthouse run against the production static export scored 86 performance, 97 accessibility, 100 best practices, and 100 SEO, with no console errors. The deliberately delayed reference entrance affects initial rendering metrics. Browser checks cover menu open/close and height, project hover, independent services, pricing, FAQ, showreel dialog, required form fields, loaded images, runtime errors, reduced motion, and horizontal overflow at widths 1440, 810, 768, 390, and 320.

This rebuild covers the homepage. Project, article, and legal detail links open their original source destinations. Forms open an email draft after browser validation and do not claim delivery. The original YouTube showreel loads only when opened. Framer's template-purchase overlays are omitted. Source muted colors and low-opacity text reveal states are preserved, including their contrast limitations.
