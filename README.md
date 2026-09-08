# agarstra

A product landing page for a ROM-driven 3D remake workflow, built with Next.js App Router, React, Tailwind CSS 4, and GSAP. Adapted from the Fabrica editorial layout with original Higgsfield concept imagery and an actual prototype capture.

## Run

```sh
npm install
npm run dev
```

Open http://localhost:3000. Static production build:

```sh
npm run build
npm start
```

The build exports to `out/`. No deployment or signup backend is configured.

## Product status

The end-to-end prototype extracts graphics and game state with provenance, coordinates Blender asset production, exports GLB, and renders original gameplay. The full production pipeline remains incomplete: visual acceptance enforcement in game consumers, character production, and complete game mapping are ongoing. Image-to-3D generation and Unreal integration are not implemented.

The page distinguishes generated concept art from the actual prototype screenshot. The prototype dialog displays a capture, not a running game. Calls to action download the portable skill and its setup guide.

## Structure

- `components/`: navigation, hero, concept studies, pipeline, prototype, status, FAQ, and downloads.
- `components/Motion.tsx`: shared GSAP entry, text, scroll, and hover motion.
- `app/agarstra.css`: brand and responsive adaptations.
- `public/agarstra/`: six Higgsfield-generated concept images, prototype capture, and playbook.
- `public/downloads/agarstra-rom-remake.zip`: portable skill, without ROMs or game assets.
- `outputs/skills/rom-remake/`: skill source and evidence-gate tooling.
- `outputs/agarstra-landing-media.json`: Higgsfield generation provenance.

GSAP powers the loader, entrance choreography, scroll reveals, parallax, image hovers, rolling labels, navigation, accordions, and status transitions. Reduced motion is respected. Interactive controls support keyboard navigation, and the prototype dialog restores focus on close.

## Verify and maintain

```sh
npm run typecheck
npm run build
npm run test:browser
npm run package:skill
```

Browser checks require a server on port 3000 and Playwright Chromium (`npx playwright install chromium`). The suite covers branding, navigation, motion, accordions, status tabs, dialog behavior, actual downloads, image loading, reduced motion, and five viewport widths. Results are written to `reference/agarstra/browser-checks.json`.

`npm run package:skill` refreshes the download after skill edits. Game experiments in `outputs/` and `work/` are excluded from the website TypeScript project.

`FIDELITY.md` and `npm run test:reference` preserve historical Fabrica comparison work; their scores do not apply to this intentionally rebranded page.

## Repository snapshot

This repository includes the landing page, downloadable portable skill, game application source, authoring tools, tests, and documentation. Local ROMs, emulator-state captures, generated model/texture libraries, native app bundles, and the experimental `work/` tree are excluded. The game experiments need their local extracted/generated assets; a fresh clone does not contain those assets. The portable skill can instead create a new supported NES reconstruction from a user-supplied ROM; see `outputs/skills/rom-remake/references/portable-runner.md`.

The complete FireRed artifact set is now additionally tracked with Git LFS. Restore its working directory using [snapshots/README.md](snapshots/README.md). The exclusions described above continue to apply to the other game experiments.

## Production landing page

Live at https://agarstra.stephenhung.me, hosted by the `agarstra` Vercel project.
The main install button copies a Codex instruction that installs the downloadable
`rom-remake` skill. The instruction is also visible for manual copying, and a ZIP
link remains available.

Deploy the landing page from this repository with `vercel deploy --prod --project agarstra`.
`.vercelignore` excludes game artifacts, local ROM workspaces, snapshots, dependencies,
and local build outputs. Vercel builds the Next.js static export from source.
Verify production with `QA_URL=https://agarstra.stephenhung.me npm run test:browser`.
