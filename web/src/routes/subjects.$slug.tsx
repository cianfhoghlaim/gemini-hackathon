import { useSession } from "../components/session/SessionContext";
import { MarimoEmbed } from "../components/marimo/MarimoEmbed";
import { Link, useParams } from "react-router-dom";

function SubjectDetailPage() {
  const { subnation, session } = useSession();
  const { slug } = useParams();

  // The cycle is part of the session identity. The notebook pre-fills
  // its (subnation, cycle, subject) dropdowns from the URL.
  const cycle = session?.cycle ?? "leaving_cycle";
  const subject = slug ?? "mathematics";

  return (
    <div className="max-w-6xl mx-auto p-6 space-y-6">
      <header>
        <h1 className="text-3xl font-[var(--font-heading)] text-[var(--color-primary)]">
          {subnation.flag} {subnation.name} · <em>{subject}</em>
        </h1>
        <p className="mt-2 text-sm text-[var(--color-text)]/70">
          Interactive notebook powered by marimo (runs in your browser via
          WebAssembly). Switch the dropdowns inside the notebook to see a
          different subnation / cycle / subject.
        </p>
        <Link
          to="/subjects"
          className="text-sm text-[var(--color-secondary)] underline"
        >
          ← Back to all subjects
        </Link>
      </header>

      <section
        className="rounded border overflow-hidden"
        style={{ borderColor: "var(--color-secondary)/20" }}
      >
        <MarimoEmbed
          subnation={subnation.code}
          cycle={cycle}
          subject={subject}
          mode="wasm"
          width={1000}
          height={680}
        />
      </section>

      <p className="text-xs text-[var(--color-text)]/50 text-center">
        Notebook loads from marimo.app via WebAssembly. No backend required.
        For the live Cloud Run deployment, switch <code>mode=&quot;app&quot;</code>{" "}
        with the <code>appUrl</code> of your marimo.run deployment.
      </p>
    </div>
  );
}

export default SubjectDetailPage;
