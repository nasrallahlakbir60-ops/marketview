import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="grid min-h-[calc(100vh-138px)] place-items-center px-5">
      <div className="text-center">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-accent">Erreur 404</p>
        <h1 className="mt-3 text-3xl font-semibold text-fg">Cette page n’existe pas.</h1>
        <Link className="mt-6 inline-flex rounded-lg bg-accent px-4 py-2.5 text-sm font-semibold text-on-accent" to="/">
          Retour aux marchés
        </Link>
      </div>
    </main>
  );
}
