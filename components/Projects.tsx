const studies = [
  {
    name: "A place to begin again.",
    type: "Village study",
    image: "forest-village",
    description:
      "A miniature forest village with terracotta rooftops, mossy trees and a stone bridge over a jade stream.",
  },
  {
    name: "Beyond the edge of the map.",
    type: "Coastal world",
    image: "coastal-world",
    description:
      "A sculpted island coastline with a lighthouse, harbor cottages and winding paths above a translucent sea.",
  },
  {
    name: "A world, reimagined.",
    type: "World building",
    image: "world",
    description:
      "Sculpted terrain, layered materials, a different sense of scale.",
  },
  {
    name: "Character in every part.",
    type: "Asset direction",
    image: "workshop",
    description:
      "From an expressive silhouette to a world that feels made by hand.",
  },
  {
    name: "New surfaces. Same soul.",
    type: "Material study",
    image: "ice",
    description:
      "Light, texture and depth open a new way to see familiar ideas.",
  },
  {
    name: "Built to be taken apart.",
    type: "Editable by design",
    image: "pipeline",
    description:
      "Source, geometry and materials remain part of an inspectable process.",
  },
];
export default function Projects() {
  return (
    <section id="worlds" className="projects-section agarstra-worlds">
      <div className="projects-top">
        <p className="project-count">(06) / Visual explorations</p>
        <div className="projects-heading">
          <h2 data-heading>
            Imagine
            <br />
            the next life.
          </h2>
          <p>Familiar spirit. Fresh perspective.</p>
        </div>
        <div className="projects-description">
          <p>
            Every remake starts with a point of view. These original concept
            studies explore what a new dimension could feel like.
          </p>
          <small>
            AI-generated concept art.
            <br />
            Not captured gameplay.
          </small>
        </div>
      </div>
      <div className="projects-grid">
        {studies.map((s, i) => (
          <a
            className="project-card"
            data-project
            data-reveal
            href="#pipeline"
            key={s.image}
            aria-label={`${s.name} Explore the pipeline`}
          >
            <div className="project-bar">
              <div>
                <h3>{s.name}</h3>
                <span>/0{i + 1}</span>
              </div>
              <span className="project-dots" aria-hidden="true">
                <i />
                <i />
                <i />
              </span>
            </div>
            <div className="project-visual">
              <div className="project-image-clip">
                <img
                  className="project-image"
                  src={`/agarstra/${s.image}.jpg`}
                  width="1600"
                  height="900"
                  alt={s.description}
                  loading="lazy"
                />
                <div className="project-blackout" />
              </div>
              <span className="project-logo" aria-hidden="true">
                ↗
              </span>
              <span className="concept-label">{s.type} / Concept</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}
