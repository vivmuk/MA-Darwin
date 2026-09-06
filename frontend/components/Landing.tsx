import Link from "next/link";

export function Landing() {
  return (
    <div className="landing-poster">
      <main className="landing-poster__stage">
        <h1 className="sr-only">MA-Darwin: How do skills evolve?</h1>
        <img
          className="landing-poster__image"
          src="/ma-darwin-landing.png"
          alt="MA-DARWIN infographic: How do skills evolve? From simple rules to emergent behavior to selected, inheritable capability. Wolfram dynamics, the MA Darwin evolution engine, and evolving skill lineages."
        />
      </main>
      <footer className="landing-poster__bar">
        <Link href="/app/" className="landing-poster__demo">
          Demo
        </Link>
      </footer>
    </div>
  );
}
