"use client";

import { useRef, useState } from "react";

export const installPrompt =
  "Install the agarstra rom-remake skill from https://agarstra.stephenhung.me/downloads/agarstra-rom-remake.zip into $CODEX_HOME/skills/rom-remake (default ~/.codex/skills/rom-remake). Download and inspect the archive, then extract its rom-remake folder there. Preserve any existing installation by backing it up before replacing it. Read SKILL.md, verify the installation, and tell me how to start with my local ROM.";

export default function SkillInstall() {
  const [status, setStatus] = useState("");
  const prompt = useRef<HTMLTextAreaElement>(null);

  async function copy() {
    try {
      await navigator.clipboard.writeText(installPrompt);
      setStatus("Copied. Paste into Codex and send to install.");
    } catch {
      prompt.current?.focus();
      prompt.current?.select();
      setStatus(
        "Select and copy the instruction below, then paste into Codex.",
      );
    }
  }

  return (
    <div className="skill-install">
      <button className="ls-submit" onClick={copy}>
        Copy install command <span aria-hidden="true">↗</span>
      </button>
      <p className="skill-install-status" role="status">
        {status || "One click to copy. Paste into Codex to install."}
      </p>
      <label className="skill-install-label" htmlFor="skill-install-prompt">
        Your Codex instruction
      </label>
      <textarea
        id="skill-install-prompt"
        ref={prompt}
        readOnly
        value={installPrompt}
        rows={5}
        spellCheck={false}
      />
      <a
        className="ls-text-link"
        href="/downloads/agarstra-rom-remake.zip"
        download
      >
        Or download the ZIP ↓
      </a>
    </div>
  );
}
