"use client";
import { useRef, useState, useEffect } from "react";
import gsap from "gsap";
import { useGSAP } from "@gsap/react";
import { CustomEase } from "gsap/CustomEase";
import { motion } from "@/lib/motion";
gsap.registerPlugin(useGSAP, CustomEase);
const links = [
  ["Home", "#home"],
  ["Pipeline", "#pipeline"],
  ["Prototype", "#prototype"],
  ["Progress", "#status"],
  ["Get the skill", "#get-started"],
];
export default function Header() {
  const root = useRef<HTMLElement>(null),
    toggle = useRef<HTMLButtonElement>(null),
    timeline = useRef<gsap.core.Timeline | null>(null);
  const [open, setOpen] = useState(false);
  const { contextSafe } = useGSAP(
    () => {
      CustomEase.create(motion.entranceEase, motion.entranceCurve);
      timeline.current = gsap
        .timeline({ paused: true })
        .to(
          root.current,
          {
            height: () =>
              window.innerWidth < 768 ? window.innerHeight : 745.8,
            duration: 0.5,
            ease: motion.entranceEase,
          },
          0,
        )
        .to(
          ".menu-body",
          { autoAlpha: 1, duration: 0.5, ease: motion.entranceEase },
          0,
        )
        .fromTo(
          ".menu-nav a",
          { y: -40, opacity: 0 },
          {
            y: 0,
            opacity: 1,
            duration: 0.6,
            stagger: 0.06,
            ease: "power3.out",
          },
          0.45,
        )
        .to(
          ".menu-toggle span:first-child",
          { rotation: 45, y: 5, duration: 0.3 },
          0,
        )
        .to(
          ".menu-toggle span:last-child",
          { rotation: -45, y: -5, duration: 0.3 },
          0,
        );
    },
    { scope: root },
  );
  const changeMenu = contextSafe((next: boolean) => {
    setOpen(next);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      timeline.current?.progress(next ? 1 : 0).pause();
      if (!next) toggle.current?.focus();
      return;
    }
    if (next) {
      timeline.current?.timeScale(1).play();
    } else {
      timeline.current?.timeScale(1.7).reverse();
      toggle.current?.focus();
    }
  });
  useEffect(() => {
    if (!open) return;
    const old = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const key = (event: KeyboardEvent) => {
      if (event.key === "Escape") changeMenu(false);
      if (event.key === "Tab") {
        const items = Array.from(
          root.current?.querySelectorAll<HTMLElement>("a,button") ?? [],
        ).filter((e) => e.getClientRects().length);
        const first = items[0],
          last = items[items.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last?.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first?.focus();
        }
      }
    };
    document.addEventListener("keydown", key);
    return () => {
      document.body.style.overflow = old;
      document.removeEventListener("keydown", key);
    };
  }, [open, changeMenu]);
  return (
    <header className="site-header" ref={root}>
      <nav className="top-nav" aria-label="Main navigation">
        <a
          href="#home"
          className="nav-brand"
          onClick={() => open && changeMenu(false)}
        >
          agarstra
        </a>
        {links.slice(1).map(([name, url]) => (
          <a
            className="nav-link"
            key={name}
            href={url}
            onClick={() => open && changeMenu(false)}
          >
            {name}
          </a>
        ))}
        <button
          ref={toggle}
          className="menu-toggle"
          aria-label={open ? "Close menu" : "Open menu"}
          aria-expanded={open}
          aria-controls="expanded-menu"
          onClick={() => changeMenu(!open)}
        >
          <span />
          <span />
        </button>
      </nav>
      <div className="menu-body" id="expanded-menu" inert={!open}>
        <nav className="menu-nav" aria-label="Expanded navigation">
          {links.map(([name, url]) => (
            <a key={name} href={url} onClick={() => changeMenu(false)}>
              {name}
            </a>
          ))}
        </nav>
        <div className="menu-bottom">
          <div className="menu-bottom-contact">
            <span>Old worlds. New dimensions.</span>
            <a href="/downloads/agarstra-rom-remake.zip" download>
              Get the skill ↗
            </a>
          </div>
          <div className="menu-legal">
            <a href="#faq" onClick={() => changeMenu(false)}>
              Questions
            </a>
            <a href="/agarstra/playbook.md">Read the playbook</a>
          </div>
          <p className="menu-copyright">© 2026 agarstra</p>
        </div>
      </div>
    </header>
  );
}
