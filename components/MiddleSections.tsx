"use client";

import { useRef, useState } from "react";
import gsap from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { CustomEase } from "gsap/CustomEase";
import { useGSAP } from "@gsap/react";
import "./middle-sections.css";

gsap.registerPlugin(useGSAP, ScrollTrigger, CustomEase);
CustomEase.create("agarstraMiddle", ".82,.11,.37,.82");

const stages = [
  {
    title: "Read the original.",
    description:
      "Extract graphics and observe game state. Keep every source connection visible, from the ROM to the object on screen.",
    image: "sprite-to-world",
    tags: ["Graphics", "Game state", "Source provenance"],
  },
  {
    title: "Build a new world.",
    description:
      "Parallel workers author editable Blender scripts, models and textures. A new interpretation, with a traceable origin.",
    image: "workshop",
    tags: ["Parallel workers", "Blender", "Editable assets"],
  },
  {
    title: "Keep the game alive.",
    description:
      "Export to GLB and render new assets over original gameplay. Movement, rules and timing stay with the game you started with.",
    image: "forest-village",
    tags: ["GLB", "Original simulation", "Asset reload"],
  },
  {
    title: "Make it worth playing.",
    description:
      "Render, critique, revise, accept. The skill defines this production loop; reliable high-fidelity output remains the next milestone.",
    image: "pipeline",
    tags: ["Visual review", "Revision", "Acceptance"],
  },
];
const principles = [
  {
    title: "Original at heart",
    label: "Gameplay",
    text: "New geometry. Familiar movement. The original simulation keeps control of the game.",
    image: "cartridge",
  },
  {
    title: "Open to revision",
    label: "Authorship",
    text: "Editable scripts and assets make every model a starting point you can inspect and improve.",
    image: "workshop",
  },
  {
    title: "Proof over polish",
    label: "Acceptance",
    text: "A beautiful concept is a direction. A working build is a prototype. Neither is a finished game.",
    image: "ice",
  },
];
function Label({ children }: { children: React.ReactNode }) {
  return (
    <p className="middle-label">
      <span aria-hidden="true">+</span>
      {children}
    </p>
  );
}
function Stage({ index }: { index: number }) {
  const [open, setOpen] = useState(index === 0);
  const root = useRef<HTMLDivElement>(null);
  const first = useRef(true);
  const stage = stages[index];
  useGSAP(
    () => {
      const duration =
        first.current || matchMedia("(prefers-reduced-motion: reduce)").matches
          ? 0
          : 0.3;
      first.current = false;
      gsap.to(".service-details", {
        height: open ? "auto" : 0,
        autoAlpha: open ? 1 : 0,
        duration,
        ease: "agarstraMiddle",
        overwrite: true,
        onComplete: () => ScrollTrigger.refresh(),
      });
      gsap.to(".service-closed-title", {
        height: open ? 0 : "auto",
        paddingTop: open ? 0 : 10,
        paddingBottom: open ? 0 : 10,
        autoAlpha: open ? 0 : 1,
        duration,
        ease: "agarstraMiddle",
        overwrite: true,
      });
      gsap.to(".service-toggle span", {
        rotate: open ? 0 : 270,
        duration,
        overwrite: true,
      });
    },
    { scope: root, dependencies: [open] },
  );
  return (
    <div className={`middle-service ${open ? "is-open" : ""}`} ref={root}>
      <span className="service-index">(00{index + 1})</span>
      <div className="service-body">
        <div
          className="service-details"
          id={`pipeline-stage-${index}`}
          inert={!open}
        >
          <div className="service-detail-grid">
            <figure className="service-images">
              <img src={`/agarstra/${stage.image}.jpg`} alt="" loading="lazy" />
              <figcaption>Concept art</figcaption>
            </figure>
            <div className="service-description">
              <h3>{stage.title}</h3>
              <p>{stage.description}</p>
            </div>
            <div className="service-categories">
              <p>Inside this stage</p>
              <div>
                {stage.tags.map((tag) => (
                  <span key={tag}>{tag}</span>
                ))}
              </div>
            </div>
          </div>
        </div>
        <button
          className="service-closed-title"
          onClick={() => setOpen(true)}
          tabIndex={open ? -1 : 0}
        >
          {stage.title}
        </button>
      </div>
      <button
        className="service-toggle"
        onClick={() => setOpen(!open)}
        aria-label={`${open ? "Collapse" : "Expand"} ${stage.title}`}
        aria-expanded={open}
        aria-controls={`pipeline-stage-${index}`}
      >
        <span>{open ? "−" : "+"}</span>
      </button>
    </div>
  );
}

export default function MiddleSections() {
  const root = useRef<HTMLDivElement>(null);
  const dialog = useRef<HTMLDialogElement>(null);
  const previewTrigger = useRef<HTMLButtonElement>(null);
  const [previewOpen, setPreviewOpen] = useState(false);
  const { contextSafe } = useGSAP(
    () => {
      if (matchMedia("(prefers-reduced-motion: reduce)").matches) return;
      gsap.fromTo(
        ".middle-case-portrait",
        { scale: 1.15, y: -30 },
        {
          scale: 1,
          y: 0,
          ease: "none",
          scrollTrigger: {
            trigger: ".middle-case",
            start: "top bottom",
            end: "bottom top",
            scrub: true,
          },
        },
      );
      gsap.from(".middle-approach-word", {
        opacity: 0.2,
        stagger: 0.045,
        scrollTrigger: {
          trigger: ".middle-approach",
          start: "top 85%",
          end: "bottom 50%",
          scrub: true,
        },
      });
    },
    { scope: root },
  );
  const portraitHover = contextSafe((active: boolean) => {
    if (!matchMedia("(prefers-reduced-motion: reduce)").matches)
      gsap.to(".advantages-portrait > img", {
        scale: active ? 1.1 : 1,
        filter: active ? "blur(5px)" : "blur(0px)",
        duration: 0.5,
        ease: "agarstraMiddle",
        overwrite: true,
      });
  });
  const openPreview = () => {
    setPreviewOpen(true);
    dialog.current?.showModal();
  };
  const closePreview = () => {
    dialog.current?.close();
  };
  return (
    <div ref={root} className="middle-sections">
      <section className="middle-section middle-advantages" id="approach">
        <div className="middle-section-top">
          <Label>A different kind of remake</Label>
          <h2 className="middle-statement" data-heading>
            The game stays original.
            <br />
            <span>The world gets another life.</span>
          </h2>
        </div>
        <div className="advantages-content">
          <a
            href="#pipeline"
            className="advantages-portrait"
            data-reveal
            onMouseEnter={() => portraitHover(true)}
            onMouseLeave={() => portraitHover(false)}
            onFocus={() => portraitHover(true)}
            onBlur={() => portraitHover(false)}
          >
            <img
              src="/agarstra/workshop.jpg"
              alt="Concept art for an agarstra asset workshop"
              loading="lazy"
            />
            <span className="portrait-plus" aria-hidden="true">
              +
            </span>
            <div>
              <small>Concept art</small>
              <p>From a small source to a world you can shape.</p>
              <span className="pill">
                <span>Explore the pipeline</span>
                <i aria-hidden="true" />
              </span>
            </div>
          </a>
          <div className="advantages-items">
            <p className="advantages-intro">
              A remake with a memory.{" "}
              <span>
                agarstra connects new assets to their source, while original
                gameplay drives what happens next.
              </span>
            </p>
            <div className="advantages-stats">
              <article data-reveal>
                <div className="advantages-number">
                  <span>ROM</span>
                  <small>01</small>
                </div>
                <div className="advantages-stat-bottom">
                  <h3>
                    Keep the source
                    <br />
                    in the picture.
                  </h3>
                  <p>
                    Extracted graphics and observed state carry provenance into
                    the asset workflow.
                  </p>
                </div>
              </article>
              <article data-reveal>
                <div className="advantages-number">
                  <span>GLB</span>
                  <small>02</small>
                </div>
                <div className="advantages-stat-bottom">
                  <h3>
                    Keep the work
                    <br />
                    in your hands.
                  </h3>
                  <p>
                    Blender scripts, models and textures stay editable as the
                    world takes shape.
                  </p>
                </div>
              </article>
            </div>
          </div>
        </div>
      </section>
      <section className="middle-section middle-services" id="pipeline">
        <div className="middle-section-top">
          <Label>From source to scene</Label>
          <h2 className="middle-display" data-heading>
            Pipeline.<sup>(4)</sup>
          </h2>
        </div>
        <div className="middle-services-list">
          {stages.map((stage, index) => (
            <Stage key={stage.title} index={index} />
          ))}
        </div>
        <div className="middle-service-cta">
          <a href="#prototype" className="pill">
            <span>See the prototype</span>
            <i aria-hidden="true" />
          </a>
        </div>
      </section>
      <section className="middle-section middle-showreel" id="prototype">
        <div className="middle-section-top">
          <Label>Working today</Label>
          <div className="middle-about-heading">
            <p className="middle-brand">agarstra</p>
            <h2 className="middle-statement" data-heading>
              A real beginning.
              <br />
              <span>An unfinished frontier.</span>
            </h2>
            <p className="middle-about-description">
              An end-to-end local prototype already connects ROM extraction,
              Blender assets and a playable renderer. High-fidelity production
              is still in progress.
            </p>
          </div>
        </div>
        <div className="middle-showreel-content">
          <div className="middle-steps">
            {[
              "Source-linked graphics and game state",
              "Parallel Blender authoring",
              "Original-gameplay-driven rendering",
              "Basic animation, reload and packaging",
            ].map((title, i) => (
              <article key={title} data-reveal>
                <div className="middle-step-top">
                  <span aria-hidden="true">↗</span>
                  <small>0{i + 1}</small>
                </div>
                <h3>{title}</h3>
              </article>
            ))}
          </div>
          <button
            className="middle-film"
            onClick={openPreview}
            ref={previewTrigger}
            aria-haspopup="dialog"
          >
            <img
              src="/agarstra/prototype.png"
              alt="Actual SMB3 reference prototype running with replacement 3D assets"
              loading="lazy"
            />
            <span className="middle-film-cta">
              <span className="middle-play" aria-hidden="true">
                ↗
              </span>
              <span>
                Inside the prototype
                <small>Actual runtime capture · limited scene coverage</small>
              </span>
            </span>
          </button>
        </div>
      </section>
      <section className="middle-section middle-testimonials" id="principles">
        <div className="middle-section-top">
          <Label>Built on a few beliefs</Label>
          <div>
            <h2 className="middle-display" data-heading>
              Principles.
            </h2>
            <p className="middle-year">Keep what matters.</p>
          </div>
        </div>
        <div className="middle-reviews">
          <article className="middle-review-intro">
            <div className="middle-principle-intro">
              <p>
                New worlds.
                <br />
                Old instincts.
              </p>
              <span>
                The goal isn’t to replace the game’s logic. It’s to give its
                world a new visual language.
              </span>
            </div>
            <div>
              <p className="middle-brand">agarstra</p>
              <a className="middle-review-link" href="#pipeline">
                Follow the process <span aria-hidden="true">↗</span>
              </a>
            </div>
          </article>
          {principles.map((principle, i) => (
            <article
              className={`middle-review ${i === 1 ? "middle-review-reversed" : ""}`}
              key={principle.title}
              data-reveal
            >
              <div className="middle-review-person">
                <span className="principle-index">0{i + 1}</span>
                <div>
                  <h3>{principle.title}</h3>
                  <p>{principle.label}</p>
                </div>
              </div>
              <div className="middle-review-quote">
                <figure>
                  <img
                    src={`/agarstra/${principle.image}.jpg`}
                    alt=""
                    loading="lazy"
                  />
                  <figcaption>Concept art</figcaption>
                </figure>
                <p>{principle.text}</p>
              </div>
            </article>
          ))}
        </div>
      </section>
      <section className="middle-section middle-text">
        <div className="middle-metrics">
          {[
            ["Read", "Find the source."],
            ["Build", "Author the world."],
            ["Play", "Keep the rules."],
            ["Refine", "Earn acceptance."],
          ].map(([word, label]) => (
            <article key={word}>
              <div>{word}</div>
              <p>{label}</p>
            </article>
          ))}
        </div>
        <div className="middle-text-bottom">
          <div>
            <p className="middle-brand">agarstra</p>
            <p>The next connection matters more than the next model count.</p>
          </div>
          <div>
            <p className="middle-approach">
              {"Render. Look closely. Revise. Repeat. The machinery can move an asset into a game. The craft is making it belong there."
                .split(" ")
                .map((word, i) => (
                  <span className="middle-approach-word" key={i}>
                    {word}{" "}
                  </span>
                ))}
            </p>
            <p className="middle-text-description">
              The skill now defines a stronger review loop and evidence gate.
              Reliable visual iteration, convincing character production and
              broader game coverage still need to be proven in the playable
              pipeline.
            </p>
          </div>
        </div>
      </section>
      <section
        className="middle-section middle-bento"
        aria-label="From source to playable world"
      >
        <div className="middle-case" data-reveal>
          <img
            className="middle-case-portrait"
            src="/agarstra/world.jpg"
            alt="Concept art of a reimagined game environment"
            loading="lazy"
          />
          <div className="middle-case-top">
            <div>
              <p>A world, reimagined.</p>
              <small>Concept art · visual direction</small>
            </div>
            <span aria-hidden="true">+</span>
          </div>
          <p className="middle-case-brand">agarstra</p>
          <div className="middle-case-bottom">
            <a href="#prototype">See what runs today ↗</a>
            <div>
              <p>
                A destination for the art.
                <br />A source for every step.
              </p>
              <small>Concepts are not runtime captures.</small>
            </div>
          </div>
        </div>
        <article className="middle-performance" data-reveal>
          <div>
            <p>The source</p>
            <h3>
              Small pixels.
              <br />
              Specific origins.
            </h3>
            <p>The authored layer</p>
            <h3>
              New forms.
              <br />
              Editable by design.
            </h3>
          </div>
          <div>
            <span className="middle-artifact-mark" aria-hidden="true">
              ↗
            </span>
            <p>
              Graphics and state come from the game. Geometry, materials and
              visual depth are new interpretations.
            </p>
          </div>
        </article>
        <div className="middle-bento-right">
          <article className="middle-score" data-reveal>
            <div className="middle-score-dial" aria-hidden="true">
              <span>GLB</span>
            </div>
            <h3>Built to enter the scene.</h3>
            <p>Portable assets meet a renderer driven by original gameplay.</p>
          </article>
          <article className="middle-chart" data-reveal>
            <p className="middle-status-label">Next milestone</p>
            <h3>
              From candidate
              <br />
              to accepted.
            </h3>
            <div className="middle-review-flow">
              <span>Render</span>
              <span>Critique</span>
              <span>Revise</span>
              <span>Accept</span>
            </div>
            <p className="middle-status-note">
              A production loop to prove, not a finished promise.
            </p>
          </article>
        </div>
      </section>
      <dialog
        className="middle-video-dialog"
        ref={dialog}
        aria-labelledby="prototype-dialog-title"
        onClick={(event) => {
          if (event.target === event.currentTarget) closePreview();
        }}
        onCancel={(event) => {
          event.preventDefault();
          closePreview();
        }}
        onClose={() => {
          setPreviewOpen(false);
          previewTrigger.current?.focus({ preventScroll: true });
        }}
      >
        <button
          onClick={closePreview}
          aria-label="Close prototype preview"
          autoFocus
        >
          ×
        </button>
        {previewOpen && (
          <figure>
            <img
              src="/agarstra/prototype.png"
              alt="Actual SMB3 prototype with original gameplay and replacement 3D assets"
            />
            <figcaption>
              <h2 id="prototype-dialog-title">The working prototype</h2>
              <p>
                Actual runtime capture. The current reconstruction covers a
                limited area; high-fidelity art, complete character actions and
                full game mapping are not finished.
              </p>
            </figcaption>
          </figure>
        )}
      </dialog>
    </div>
  );
}
