"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { CustomEase } from "gsap/CustomEase";
import "./lower-sections.css";

gsap.registerPlugin(useGSAP, CustomEase);
const hoverEase = CustomEase.create(
  "agarstra-lower-hover",
  "0.82,0.11,0.37,0.82",
);
const download = "/downloads/agarstra-rom-remake.zip";
const roles = [
  {
    name: "The observer.",
    role: "01 / Extract",
    image: "cartridge",
    description:
      "Connect graphics and live state to the ROM bytes, banks, and frames that produced them.",
  },
  {
    name: "The conductor.",
    role: "02 / Coordinate",
    image: "pipeline",
    description:
      "Give parallel workers a shared target, isolated files, clear ownership, and a bounded build queue.",
  },
  {
    name: "The maker.",
    role: "03 / Build",
    image: "workshop",
    description:
      "Author editable Blender scenes, export GLBs, then inspect what actually survives in the renderer.",
  },
  {
    name: "The reviewer.",
    role: "04 / Refine",
    image: "world",
    description:
      "Return visible defects to the author. Revision and current acceptance belong between a build and a release.",
  },
];
const questions = [
  [
    "Does agarstra include a ROM?",
    "No. You provide your own local ROM. The reference prototype checks for the supported SMB3 revision. The skill download contains workflow instructions and evidence-checking tools, not a game ROM.",
  ],
  [
    "Can I use it with any game?",
    "The workflow is reusable; game support is not automatic. Each game and revision needs a qualified extraction and state adapter. The current reference implementation is SMB3 with JSNES and Three.js. Its extractor requires immutable CHR-ROM.",
  ],
  [
    "Who controls the gameplay?",
    "The original simulation. It owns movement, collisions, enemies, rules, sound, and timing. The 3D renderer follows observed state; its animations must not introduce a second gameplay simulation.",
  ],
  [
    "Is the production pipeline finished?",
    "No. An end-to-end prototype works today. The skill now describes the render, critique, revision, and acceptance loop and includes a tested evidence gate. That gate does not yet enforce acceptance in the prototype’s assembler, reload, or packaging paths.",
  ],
  [
    "Does it generate 3D models from images or use Unreal?",
    "Neither integration is implemented in the reference project. Its models come from Blender scripts and run in Three.js/Electron. Concept imagery on this page illustrates the direction; it is not a screenshot of finished gameplay.",
  ],
  [
    "What does the download require?",
    "An agent that can read skills and work with local files. Blender, a compatible emulator adapter, and a renderer are needed to build a remake. The bundled evidence checker uses Python 3.9 or newer. Start with the included SKILL.md and the playbook.",
  ],
];
const notes = [
  {
    title: "A prototype is a beginning.",
    category: "01 / Current state",
    description:
      "What runs today, and what still stands between a valid model and an accepted scene.",
    image: "cartridge",
    href: "#status",
  },
  {
    title: "Build. Render. Review. Repeat.",
    category: "02 / The playbook",
    description:
      "Follow the path from source evidence to authored assets, honest critique, and playable delivery.",
    image: "workshop",
    href: "/agarstra/playbook.md",
  },
];
function Plus() {
  return (
    <span className="ls-plus" aria-hidden="true">
      +
    </span>
  );
}
function Pill({
  children,
  href = "#get-started",
}: {
  children: React.ReactNode;
  href?: string;
}) {
  return (
    <a className="pill" href={href}>
      <span>{children}</span>
      <i />
    </a>
  );
}
function FaqItem({
  question,
  answer,
  index,
}: {
  question: string;
  answer: string;
  index: number;
}) {
  const root = useRef<HTMLDivElement>(null);
  const [open, setOpen] = useState(index === 0);
  const { contextSafe } = useGSAP(
    () => {
      gsap.set(root.current!.querySelector(".ls-plus"), {
        rotation: index === 0 ? 45 : 0,
      });
    },
    { scope: root },
  );
  const toggle = contextSafe(() => {
    const next = !open;
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? 0
      : 0.45;
    gsap.to(root.current!.querySelector(".ls-faq-answer"), {
      height: next ? "auto" : 0,
      opacity: next ? 1 : 0,
      duration,
      ease: "power3.inOut",
      overwrite: true,
    });
    gsap.to(root.current!.querySelector(".ls-plus"), {
      rotation: next ? 45 : 0,
      duration,
      overwrite: true,
    });
    setOpen(next);
  });
  return (
    <div className="ls-faq-item" ref={root}>
      <button
        aria-expanded={open}
        aria-controls={`faq-answer-${index}`}
        onClick={toggle}
      >
        {question}
        <Plus />
      </button>
      <div
        className="ls-faq-answer"
        id={`faq-answer-${index}`}
        aria-hidden={!open}
        style={{
          height: index === 0 ? "auto" : 0,
          opacity: index === 0 ? 1 : 0,
        }}
      >
        <p>{answer}</p>
      </div>
    </div>
  );
}
function RoleCard({ role }: { role: (typeof roles)[number] }) {
  const root = useRef<HTMLButtonElement>(null);
  const [expanded, setExpanded] = useState(false);
  const { contextSafe } = useGSAP({ scope: root });
  const show = contextSafe((visible: boolean) => {
    setExpanded(visible);
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? 0
      : 0.45;
    gsap.to(root.current!.querySelector("img"), {
      scale: visible ? 1.1 : 1,
      filter: visible ? "blur(5px)" : "blur(0px)",
      opacity: visible ? 0.4 : 0.8,
      duration,
      ease: hoverEase,
      overwrite: true,
    });
    gsap.to(root.current!.querySelector(".ls-team-description"), {
      y: visible ? 0 : 24,
      opacity: visible ? 1 : 0,
      duration,
      overwrite: true,
    });
    gsap.to(root.current!.querySelector(".ls-plus"), {
      rotation: visible ? 45 : 0,
      duration,
      overwrite: true,
    });
  });
  return (
    <button
      className="ls-team-card"
      ref={root}
      aria-expanded={expanded}
      onPointerEnter={(event) => {
        if (event.pointerType === "mouse") show(true);
      }}
      onPointerLeave={(event) => {
        if (event.pointerType === "mouse") show(false);
      }}
      onFocus={(event) => {
        if (event.currentTarget.matches(":focus-visible")) show(true);
      }}
      onBlur={() => show(false)}
      onClick={() => show(!expanded)}
    >
      <img src={`/agarstra/${role.image}.jpg`} alt="" loading="lazy" />
      <div className="ls-team-top">
        <Plus />
        <p>
          {role.role}
          <small>Pipeline role</small>
        </p>
      </div>
      <div className="ls-team-bottom">
        <p className="ls-team-description">{role.description}</p>
        <h3>{role.name}</h3>
      </div>
    </button>
  );
}
export default function LowerSections() {
  const root = useRef<HTMLDivElement>(null);
  const [next, setNext] = useState(false);
  const { contextSafe } = useGSAP(
    (_, safe) => {
      if (!root.current || !safe) return;
      const reduced = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      const cleanup: Array<() => void> = [];
      root.current
        .querySelectorAll<HTMLElement>(".ls-blog-card, .ls-blog-feature")
        .forEach((card) => {
          const feature = card.classList.contains("ls-blog-feature");
          const hover = safe((active: boolean) => {
            gsap.to(
              card.querySelector("img"),
              feature
                ? {
                    scale: active ? 1.04 : 1,
                    duration: reduced ? 0 : 0.45,
                    ease: hoverEase,
                    overwrite: true,
                  }
                : {
                    width: active ? 150 : 100,
                    height: active ? 150 : 100,
                    duration: reduced ? 0 : 0.45,
                    ease: hoverEase,
                    overwrite: true,
                  },
            );
            gsap.to(card.querySelector(".ls-plus"), {
              rotation: active ? 90 : 0,
              duration: reduced ? 0 : 0.45,
              ease: hoverEase,
              overwrite: true,
            });
          });
          const enter = (event: PointerEvent) => {
            if (event.pointerType === "mouse") hover(true);
          };
          const leave = () => hover(false),
            focus = () => hover(true);
          card.addEventListener("pointerenter", enter);
          card.addEventListener("pointerleave", leave);
          card.addEventListener("focus", focus);
          card.addEventListener("blur", leave);
          cleanup.push(() => {
            card.removeEventListener("pointerenter", enter);
            card.removeEventListener("pointerleave", leave);
            card.removeEventListener("focus", focus);
            card.removeEventListener("blur", leave);
          });
        });
      return () => cleanup.forEach((remove) => remove());
    },
    { scope: root },
  );
  const changeTab = contextSafe((value: boolean) => {
    setNext(value);
    const duration = window.matchMedia("(prefers-reduced-motion: reduce)")
      .matches
      ? 0
      : 0.4;
    gsap.to(root.current!.querySelector(".ls-price-indicator"), {
      xPercent: value ? 100 : 0,
      duration,
      ease: "power3.inOut",
      overwrite: true,
    });
    gsap.fromTo(
      root.current!.querySelector(".ls-plan-content"),
      { y: 12, opacity: 0.3 },
      { y: 0, opacity: 1, duration, overwrite: true },
    );
  });
  return (
    <div ref={root} className="lower-sections">
      <section className="ls-pricing" id="status">
        <div className="ls-pricing-heading">
          <p className="ls-eyebrow">
            <Plus />
            An honest progress report
          </p>
          <h2 data-heading>In motion.</h2>
        </div>
        <div className="ls-pricing-body">
          <div className="ls-status-aside">
            <p>
              Working machinery.
              <br />
              <span>Unfinished magic.</span>
            </p>
            <small>
              The prototype proves the path. Production quality is the work
              ahead.
            </small>
          </div>
          <div className="ls-capabilities">
            <div
              className="ls-price-tabs"
              role="tablist"
              aria-label="Pipeline capability status"
              onKeyDown={(event) => {
                if (
                  ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
                ) {
                  event.preventDefault();
                  const value =
                    event.key === "End"
                      ? true
                      : event.key === "Home"
                        ? false
                        : !next;
                  changeTab(value);
                  root.current
                    ?.querySelector<HTMLButtonElement>(
                      `#status-tab-${value ? "next" : "today"}`,
                    )
                    ?.focus();
                }
              }}
            >
              <span className="ls-price-indicator" />
              <button
                id="status-tab-today"
                role="tab"
                tabIndex={next ? -1 : 0}
                aria-controls="status-panel"
                aria-selected={!next}
                onClick={() => changeTab(false)}
              >
                Today
              </button>
              <button
                id="status-tab-next"
                role="tab"
                tabIndex={next ? 0 : -1}
                aria-controls="status-panel"
                aria-selected={next}
                onClick={() => changeTab(true)}
              >
                Next
              </button>
            </div>
            <div className="ls-price-card" data-reveal>
              <div
                className="ls-plan-content"
                role="tabpanel"
                id="status-panel"
                aria-labelledby={`status-tab-${next ? "next" : "today"}`}
                tabIndex={0}
              >
                <p className="ls-status-kicker">
                  {next ? "Not production-complete" : "End-to-end prototype"}
                </p>
                <h3>{next ? "Close the loop." : "The path works."}</h3>
                <ul>
                  {(next
                    ? [
                        "A visual target that guides every revision",
                        "Accepted assets enforced in the game",
                        "Convincing rigs and character motion",
                        "Broader scene, form, and action coverage",
                      ]
                    : [
                        "ROM graphics and live state, with provenance",
                        "Parallel authors, editable Blender sources",
                        "GLB assets in an original-gameplay renderer",
                        "Basic animation, reload, checks, and packaging",
                      ]
                  ).map((item) => (
                    <li key={item}>
                      <Plus />
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
              <div className="ls-price-bottom">
                <p>
                  {next
                    ? "Image-to-3D and Unreal remain separate, unimplemented integrations."
                    : "Reference stack: JSNES · Blender · Three.js · Electron"}
                </p>
                <a
                  className="ls-white-cta"
                  href={next ? "/agarstra/playbook.md" : "#prototype"}
                >
                  {next ? "Read the playbook" : "See the prototype"}
                  <span aria-hidden="true">↗</span>
                </a>
              </div>
            </div>
          </div>
        </div>
        <div className="ls-pricing-quote">
          <p>What comes next</p>
          <p className="ls-quote" data-heading>
            <span>Render → critique → revision → acceptance.</span> Moving an
            asset through the system is only the beginning. Making it worth
            shipping is the goal.
          </p>
        </div>
      </section>
      <section className="ls-team" id="roles">
        <div className="ls-team-copy">
          <div>
            <p className="ls-brand">agarstra</p>
            <h2 data-heading>
              One world.
              <br />
              <span>Many hands.</span>
            </h2>
          </div>
          <div className="ls-team-mission">
            <p>
              Independent workers. Shared references. One accountable path from
              source to scene.
            </p>
            <Pill href="/agarstra/playbook.md">Meet the workflow</Pill>
            <small>
              Illustrations below are concept art, not runtime captures.
            </small>
          </div>
        </div>
        <div className="ls-team-grid">
          {roles.map((role) => (
            <RoleCard key={role.name} role={role} />
          ))}
        </div>
      </section>
      <section className="ls-faq" id="faq">
        <div className="ls-faq-heading">
          <h2 data-heading>FAQ.</h2>
          <p>
            A few things to know before bringing an old world into a new
            dimension.
          </p>
        </div>
        <div className="ls-faq-list">
          {questions.map(([question, answer], index) => (
            <FaqItem
              key={question}
              question={question}
              answer={answer}
              index={index}
            />
          ))}
        </div>
      </section>
      <section className="ls-blog" id="notes">
        <div className="ls-blog-heading">
          <h2 data-heading>
            Notes from
            <br />
            <span>the workshop.</span>
          </h2>
          <div>
            <p>
              The working parts, the open questions,
              <br />
              and a practical place to start.
            </p>
            <Pill href="/agarstra/playbook.md">Read the playbook</Pill>
          </div>
        </div>
        <div className="ls-blog-grid">
          {notes.map((note) => (
            <a className="ls-blog-card" key={note.title} href={note.href}>
              <img src={`/agarstra/${note.image}.jpg`} alt="" loading="lazy" />
              <Plus />
              <div>
                <small>{note.category}</small>
                <h3>{note.title}</h3>
                <p>{note.description}</p>
              </div>
            </a>
          ))}
          <a className="ls-blog-feature" href="#prototype">
            <img
              src="/agarstra/prototype.png"
              alt="Actual agarstra SMB3 prototype"
              loading="lazy"
            />
            <div>
              <span>03 / Actual prototype</span>
              <Plus />
            </div>
            <h3>
              Original play.
              <br />
              New perspective.
            </h3>
          </a>
        </div>
      </section>
      <section className="ls-contact" id="get-started">
        <div className="ls-contact-grid">
          <div className="ls-download-card" data-reveal>
            <p className="ls-brand">agarstra / rom-remake</p>
            <h2>
              Get the
              <br />
              <span>skill.</span>
            </h2>
            <p className="ls-download-description">
              The workflow, production contracts, and Python evidence gate. A
              starting point for your agent—not a one-click game converter.
            </p>
            <a className="ls-submit" href={download} download>
              Download the skill <span aria-hidden="true">↓</span>
            </a>
            <a className="ls-text-link" href="/agarstra/playbook.md">
              Read the setup playbook ↗
            </a>
            <small>ZIP archive · No ROM included · No account required</small>
          </div>
          <div className="ls-contact-copy">
            <p className="ls-eyebrow">
              <Plus />
              Start small. Build something real.
            </p>
            <h2 data-heading>
              Your next
              <br />
              dimension.
            </h2>
            <ol className="ls-setup">
              <li>
                <span>01</span>
                <div>
                  <h3>Unpack the skill.</h3>
                  <p>
                    Place the rom-remake folder in your agent’s skills
                    directory. Read SKILL.md before running the included tools.
                  </p>
                </div>
              </li>
              <li>
                <span>02</span>
                <div>
                  <h3>Connect your tools.</h3>
                  <p>
                    Bring a local ROM, Blender, and a compatible
                    emulator/renderer adapter. The reference project uses JSNES
                    and Three.js.
                  </p>
                </div>
              </li>
              <li>
                <span>03</span>
                <div>
                  <h3>Prove one playable scene.</h3>
                  <p>
                    Keep source provenance. Set a visual target. Build, inspect,
                    and revise before expanding the asset library.
                  </p>
                </div>
              </li>
            </ol>
          </div>
        </div>
      </section>
      <footer className="ls-footer">
        <div className="ls-footer-top">
          <p className="ls-footer-quote" data-heading>
            Keep what made it matter.
            <br />
            <span>Discover what it could become.</span>
          </p>
          <div className="ls-footer-nav">
            <nav aria-label="Footer navigation">
              <a href="#pipeline">The pipeline</a>
              <a href="#prototype">The prototype</a>
              <a href="#status">Today & next</a>
              <a href="#faq">Questions</a>
            </nav>
            <nav aria-label="Resources">
              <a href="/agarstra/playbook.md">The playbook</a>
              <a href={download} download>
                Download the skill ↗
              </a>
              <a href="#get-started">Get started</a>
            </nav>
          </div>
        </div>
        <a
          className="ls-footer-wordmark"
          href="#main"
          aria-label="agarstra — back to top"
        >
          agarstra
        </a>
        <div className="ls-footer-bottom">
          <p>Old worlds. New dimensions.</p>
          <span>A working prototype. An open-ended pursuit.</span>
          <a href="#main">Back to top ↑</a>
        </div>
      </footer>
    </div>
  );
}
