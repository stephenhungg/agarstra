"use client";
import { useRef, type ReactNode } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { ScrollToPlugin } from "gsap/ScrollToPlugin";
import { CustomEase } from "gsap/CustomEase";
import { motion, heroSpring, revealSpring } from "@/lib/motion";
import "./motion.css";
gsap.registerPlugin(useGSAP, ScrollTrigger, ScrollToPlugin, CustomEase);

export default function Motion({ children }: { children: ReactNode }) {
  const root = useRef<HTMLDivElement>(null);
  useGSAP(
    (_, contextSafe) => {
      if (!root.current || !contextSafe) return;
      CustomEase.create(motion.entranceEase, motion.entranceCurve);
      CustomEase.create(motion.hoverEase, motion.hoverCurve);
      CustomEase.create("fabrica-text", "0.44,0,0.13,0.96");
      const reduced = window.matchMedia(
        "(prefers-reduced-motion: reduce)",
      ).matches;
      const cleanups: (() => void)[] = [];
      let alive = true;
      const start = contextSafe(() => {
        if (!alive || !root.current) return;
        if (!reduced) {
          const intro = gsap.timeline();
          intro
            .set(".intro-loader", { display: "flex" })
            .fromTo(
              ".loader-character",
              { opacity: 0.001, y: 270, filter: "blur(5px)" },
              {
                opacity: 1,
                y: 0,
                filter: "blur(0px)",
                duration: 0.4,
                stagger: 0.09,
                ease: motion.entranceEase,
              },
              0.3,
            )
            .to(
              ".intro-loader",
              { yPercent: -100, duration: 1.1, ease: motion.entranceEase },
              1.65,
            )
            .fromTo(
              ".hero-shell",
              { y: window.innerWidth < 768 ? 220 : 300, opacity: 0.001 },
              {
                y: 0,
                opacity: 1,
                duration: 1,
                ease: heroSpring,
                clearProps: "transform",
              },
              window.innerWidth < 768 ? 1.79 : 1.9,
            )
            .set(".intro-loader", { display: "none" }, 2.8);
          gsap.to(".hero-grain", {
            keyframes: [
              { xPercent: 2, yPercent: -3 },
              { xPercent: -1, yPercent: 2 },
              { xPercent: 3, yPercent: 1 },
              { xPercent: -2, yPercent: -1 },
              { xPercent: 0, yPercent: 0 },
            ],
            duration: 0.5,
            repeat: -1,
            ease: "steps(1)",
          });
          const mm = gsap.matchMedia();
          mm.add("(min-width: 768px)", () => {
            gsap.fromTo(
              ".clients",
              { y: -290, scale: 0.95 },
              {
                y: 0,
                scale: 1,
                ease: "none",
                scrollTrigger: {
                  start: 0,
                  end: () => window.innerHeight * 0.908,
                  scrub: true,
                  invalidateOnRefresh: true,
                },
              },
            );
          });
          cleanups.push(() => mm.revert());
          root.current
            .querySelectorAll<HTMLElement>("[data-reveal],[data-heading]")
            .forEach((el) => {
              const words: HTMLElement[] = [];
              // Preserve the original inline markup (muted spans, line breaks, etc.).
              if (
                el.hasAttribute("data-heading") &&
                /\s/.test(el.textContent?.trim() ?? "")
              ) {
                const walker = document.createTreeWalker(
                  el,
                  NodeFilter.SHOW_TEXT,
                );
                const texts: Text[] = [];
                let node: Node | null;
                while ((node = walker.nextNode()))
                  if (node.textContent?.trim()) texts.push(node as Text);
                texts.forEach((text) => {
                  const parent = text.parentNode;
                  if (!parent) return;
                  const replacements: Node[] = [];
                  for (const token of (text.textContent ?? "").split(/(\s+)/)) {
                    if (!token) continue;
                    const part = /^\s+$/.test(token)
                      ? document.createTextNode(token)
                      : document.createElement("span");
                    part.textContent = token;
                    if (part instanceof HTMLElement) {
                      part.className = "motion-heading-word";
                      words.push(part);
                    }
                    replacements.push(part);
                    parent.insertBefore(part, text);
                  }
                  parent.removeChild(text);
                  cleanups.push(() => {
                    if (replacements[0]?.parentNode === parent) {
                      parent.insertBefore(text, replacements[0]);
                      replacements.forEach(
                        (part) =>
                          part.parentNode === parent &&
                          parent.removeChild(part),
                      );
                    }
                  });
                });
              }
              if (words.length) {
                gsap.fromTo(
                  words,
                  { opacity: 0.001, y: 10 },
                  {
                    opacity: 1,
                    y: 0,
                    duration: motion.textDuration,
                    stagger: motion.textStagger,
                    ease: "fabrica-text",
                    scrollTrigger: {
                      trigger: el,
                      start: "top bottom",
                      once: true,
                    },
                    clearProps: "transform,opacity",
                  },
                );
              } else {
                gsap.fromTo(
                  el,
                  { opacity: 0.001 },
                  {
                    opacity: 1,
                    duration: 1.2,
                    delay: Number(el.dataset.delay ?? 0.2),
                    ease: revealSpring,
                    scrollTrigger: {
                      trigger: el,
                      start: "top bottom",
                      once: true,
                    },
                    clearProps: "opacity",
                  },
                );
              }
            });
        }
        const listen = (el: Element, event: string, fn: EventListener) => {
          el.addEventListener(event, fn);
          cleanups.push(() => el.removeEventListener(event, fn));
        };
        root.current
          .querySelectorAll<HTMLElement>("[data-project]")
          .forEach((card) => {
            const image = card.querySelector(".project-image"),
              logo = card.querySelector(".project-logo"),
              shade = card.querySelector(".project-blackout"),
              clip = card.querySelector(".project-image-clip");
            const hover = contextSafe((active: boolean) => {
              gsap.to(image, {
                scale: active ? 1.13 : 1,
                filter: active ? "blur(7px)" : "blur(0px)",
                duration: reduced ? 0 : 0.45,
                ease: motion.hoverEase,
              });
              gsap.to(logo, {
                scale: active ? 0.8 : 1,
                duration: reduced ? 0 : 0.45,
                ease: motion.hoverEase,
              });
              gsap.to(shade, {
                opacity: active ? 0.2 : 0.15,
                duration: 0.45,
                ease: motion.hoverEase,
              });
              gsap.to(clip, {
                inset: active ? 0 : 4,
                duration: 0.45,
                ease: motion.hoverEase,
              });
              gsap.to(card.querySelectorAll(".project-dots i"), {
                backgroundColor: (i: number) =>
                  active ? ["#ff6058", "#ffbd2e", "#28c840"][i] : "#e7e7e7",
                duration: 0.3,
              });
            });
            listen(card, "pointerenter", () => hover(true));
            listen(card, "pointerleave", () => hover(false));
            listen(card, "focus", () => hover(true));
            listen(card, "blur", () => hover(false));
          });
        root.current.querySelectorAll<HTMLElement>(".pill").forEach((pill) => {
          const text = pill.querySelector<HTMLElement>(":scope > span"),
            dot = pill.querySelector<HTMLElement>(":scope > i");
          if (!text || reduced) return;
          const originalNodes = Array.from(text.childNodes);
          const track = document.createElement("span");
          track.className = "motion-pill-track";
          originalNodes.forEach((node) => track.appendChild(node));
          const copy = document.createElement("span");
          copy.textContent = track.textContent;
          copy.className = "motion-pill-copy";
          copy.setAttribute("aria-hidden", "true");
          track.appendChild(copy);
          text.classList.add("motion-pill-label");
          text.appendChild(track);
          cleanups.push(() => {
            originalNodes.forEach((node) => text.insertBefore(node, track));
            track.remove();
            text.classList.remove("motion-pill-label");
          });
          let dotCopy: HTMLElement | null = null;
          if (dot) {
            dotCopy = document.createElement("b");
            dotCopy.className = "motion-pill-dot-copy";
            dotCopy.setAttribute("aria-hidden", "true");
            dot.appendChild(dotCopy);
            cleanups.push(() => dotCopy?.remove());
          }
          const hover = contextSafe((active: boolean) => {
            gsap.to(track, {
              y: active ? 20 : 0,
              duration: motion.hoverDuration,
              ease: motion.hoverEase,
              overwrite: true,
            });
            if (dotCopy)
              gsap.to(dotCopy, {
                opacity: active ? 1 : 0,
                duration: motion.hoverDuration,
                ease: motion.hoverEase,
                overwrite: true,
              });
          });
          listen(pill, "pointerenter", () => hover(true));
          listen(pill, "pointerleave", () => hover(false));
          listen(pill, "focusin", () => hover(true));
          listen(pill, "focusout", () => hover(false));
        });
        root.current
          .querySelectorAll<HTMLElement>(".team-contact")
          .forEach((card) => {
            const photo = card.querySelector(".team-contact-photo"),
              panel = card.querySelector(".team-contact-card");
            const hover = contextSafe((active: boolean) => {
              gsap.to(photo, {
                borderTopRightRadius: active ? 0 : 16,
                borderBottomRightRadius: active ? 0 : 16,
                duration: 0.4,
              });
              gsap.to(panel, {
                borderTopLeftRadius: active ? 0 : 16,
                borderBottomLeftRadius: active ? 0 : 16,
                duration: 0.4,
              });
            });
            listen(card, "pointerenter", () => hover(true));
            listen(card, "pointerleave", () => hover(false));
          });
        const anchors = contextSafe((event: Event) => {
          const e = event as MouseEvent;
          if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
          const anchor = (e.target as HTMLElement).closest<HTMLAnchorElement>(
            'a[href^="#"]',
          );
          if (!anchor) return;
          const href = anchor.getAttribute("href");
          if (!href || href === "#") return;
          const target = document.getElementById(href.slice(1));
          if (!target) return;
          e.preventDefault();
          history.pushState(null, "", href);
          gsap.to(window, {
            duration: reduced ? 0 : 1,
            scrollTo: { y: target, offsetY: 60, autoKill: true },
            ease: "power2.inOut",
          });
        });
        document.addEventListener("click", anchors);
        cleanups.push(() => document.removeEventListener("click", anchors));
        ScrollTrigger.refresh();
      });
      void document.fonts.ready.then(start);
      return () => {
        alive = false;
        cleanups.forEach((fn) => fn());
      };
    },
    { scope: root },
  );
  return (
    <div ref={root}>
      <div className="intro-loader" aria-hidden="true">
        <div>
          {"agarstra".split("").map((c, i) => (
            <span className="loader-character" key={i}>
              {c}
            </span>
          ))}
        </div>
      </div>
      {children}
    </div>
  );
}
