const stages = [
  ["01", "ROM", "Start with the source"],
  ["02", "State", "Keep the original rules"],
  ["03", "Blender", "Make it editable"],
  ["04", "GLB", "Bring assets to life"],
  ["05", "Review", "Inspect. Revise. Repeat."],
  ["06", "Play", "Build a playable slice"],
];

export function TeamContact() {
  return (
    <a href="#get-started" className="team-contact">
      <div className="team-contact-photo">
        <img
          src="/agarstra/cartridge.jpg"
          alt="An original cartridge concept"
          width="170"
          height="216"
        />
      </div>
      <div className="team-contact-card">
        <div>
          <p className="team-role">For world builders</p>
          <p className="team-company">The agarstra workflow</p>
          <p className="team-name">Start creating.</p>
        </div>
        <span className="pill">
          <span>Get the skill</span>
          <i />
        </span>
      </div>
    </a>
  );
}

export default function Hero() {
  return (
    <section className="hero-section agarstra-hero" id="home">
      <div className="first-screen">
        <div className="hero-shell">
          <div className="hero-backdrop">
            <img
              className="hero-art"
              src="/agarstra/hero.jpg"
              alt="Concept art: a pixel landscape becoming a dimensional game world"
              width="2752"
              height="1536"
              fetchPriority="high"
            />
            <div className="agarstra-hero-wash" />
            <div className="hero-grain" aria-hidden="true" />
          </div>
          <div className="hero-content">
            <div className="hero-top">
              <div className="hero-company">
                <div className="agarstra-wordmark" aria-label="agarstra">
                  agarstra
                  <span className="agarstra-mark" aria-hidden="true">
                    ✳
                  </span>
                </div>
                <p className="agarstra-kicker">
                  A new dimension for the games you love.
                </p>
              </div>
              <div className="hero-services">
                <p>Original gameplay.</p>
                <p>Editable worlds.</p>
                <p>Every asset, traceable.</p>
                <a href="#status" className="hero-status">
                  <i /> Prototype in progress
                </a>
              </div>
            </div>
            <div className="hero-crosses" aria-hidden="true">
              {[0, 1, 2, 3].map((i) => (
                <span key={i}>+</span>
              ))}
            </div>
            <div className="hero-bottom">
              <div className="hero-description">
                <h1>
                  <span>
                    Old worlds.
                    <br />
                    New dimensions.
                  </span>
                  <small>
                    A workflow for turning game ROMs into editable 3D assets and
                    playable remakes. Keep the original rules. Reimagine
                    everything you see.
                  </small>
                </h1>
                <a href="#pipeline" className="hero-explore">
                  Explore the pipeline <span aria-hidden="true">↓</span>
                </a>
              </div>
              <TeamContact />
            </div>
            <p className="hero-art-credit">
              Visual direction / AI-generated concept art
            </p>
          </div>
        </div>
      </div>
      <div className="clients">
        <div className="clients-inner">
          <div className="clients-label">
            <span>
              <i className="plus-disc">+</i>From bytes to worlds
            </span>
            <span>One connected workflow.</span>
          </div>
          <div className="clients-grid">
            {stages.map(([number, name, detail]) => (
              <a
                className="client-logo stage-tile"
                key={number}
                href="#pipeline"
                data-reveal
              >
                <span className="stage-number">/{number}</span>
                <strong>{name}</strong>
                <span>{detail}</span>
              </a>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
