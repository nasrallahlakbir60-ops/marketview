import type { ReactNode } from "react";
import { Navigate, useLocation } from "react-router-dom";

import { useMe } from "../../hooks/useAuth";
import { ErrorMessage } from "../common/ErrorMessage";
import { Loader } from "../common/Loader";

/** Réserve une page aux comptes connectés ; sinon renvoie vers /login en mémorisant la page demandée. */
export function RequireAuth({ children }: { children: ReactNode }) {
  const { data: user, error, isPending, refetch } = useMe();
  const location = useLocation();

  if (isPending) return <Loader className="min-h-[calc(100vh-138px)]" label="Chargement..." />;
  if (error) {
    return (
      <div className="mx-auto max-w-md px-4 py-16">
        <ErrorMessage message={error.message} onRetry={() => void refetch()} />
      </div>
    );
  }
  if (!user) {
    const next = `${location.pathname}${location.search}`;
    return <Navigate replace to={next === "/" ? "/login" : `/login?next=${encodeURIComponent(next)}`} />;
  }
  return <>{children}</>;
}
