import Header from "@/components/Header";
import Hero from "@/components/Hero";
import Projects from "@/components/Projects";
import Motion from "@/components/Motion";
import MiddleSections from "@/components/MiddleSections";
import LowerSections from "@/components/LowerSections";
export default function Home() {
  return (
    <Motion>
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <Header />
      <main id="main" className="page-content font-sans">
        <Hero />
        <Projects />
        <div className="section-break">
          <MiddleSections />
        </div>
        <div className="section-break">
          <LowerSections />
        </div>
      </main>
    </Motion>
  );
}
