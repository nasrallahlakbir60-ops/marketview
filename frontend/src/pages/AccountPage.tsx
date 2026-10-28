import { useState, type ReactNode } from "react";
import { useQuery } from "@tanstack/react-query";

import { ErrorMessage } from "../components/common/ErrorMessage";
import { Loader } from "../components/common/Loader";
import { useMe, useSignOut } from "../hooks/useAuth";
import { authApi } from "../services/api";

const eventLabels: Record<string, string> = {
  signup: "Création du compte",
  login: "Connexion",
  login_failed: "Tentative de connexion échouée",
  logout: "Déconnexion",
  logout_all: "Déconnexion de tous les appareils",
  data_export: "Export des données",
};

function formatDateTime(value: string | null): string {
  if (!value) return "—";
  return new Date(value).toLocaleString("fr-FR", { dateStyle: "medium", timeStyle: "short" });
}

/** "Chrome · Windows" plutôt que la chaîne User-Agent complète. */
function describeDevice(userAgent: string | null): string {
  if (!userAgent) return "Appareil inconnu";
  const browser = /Edg\//.test(userAgent) ? "Edge" : /Firefox\//.test(userAgent) ? "Firefox" : /Chrome\//.test(userAgent) ? "Chrome" : /Safari\//.test(userAgent) ? "Safari" : "Navigateur";
  const os = /Windows/.test(userAgent) ? "Windows" : /Android/.test(userAgent) ? "Android" : /iPhone|iPad/.test(userAgent) ? "iOS" : /Mac OS/.test(userAgent) ? "macOS" : /Linux/.test(userAgent) ? "Linux" : "";
  return os ? `${browser} · ${os}` : browser;
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="rounded-2xl border border-line/[0.07] bg-panel/70 p-5">
      <h2 className="text-sm font-semibold text-fg">{title}</h2>
      <div className="mt-3">{children}</div>
    </section>
  );
}

export function AccountPage() {
  const { data: user } = useMe();
  const activity = useQuery({ queryKey: ["auth", "activity"], queryFn: authApi.activity });
  const logoutAll = useSignOut(authApi.logoutAll);
  const deleteAccount = useSignOut(authApi.deleteAccount);
  const [exporting, setExporting] = useState(false);

  if (!user) return null;

  const exportData = async () => {
    setExporting(true);
    try {
      const data = await authApi.exportData();
      const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
      const link = Object.assign(document.createElement("a"), { href: url, download: "marketview-mes-donnees.json" });
      link.click();
      URL.revokeObjectURL(url);
    } finally {
      setExporting(false);
    }
  };

  const confirmDelete = () => {
    if (window.confirm("Supprimer définitivement votre compte ? Cette action est irréversible.")) deleteAccount.mutate();
  };

  return (
    <main className="mx-auto min-h-[calc(100vh-138px)] max-w-[760px] space-y-5 px-4 pb-12 pt-8 sm:px-8">
      <div className="flex items-center gap-4">
        {user.avatar_url ? (
          <img alt="" className="h-14 w-14 rounded-full" referrerPolicy="no-referrer" src={user.avatar_url} />
        ) : (
          <span className="grid h-14 w-14 place-items-center rounded-full bg-accent text-xl font-semibold text-on-accent">
            {user.full_name.charAt(0).toUpperCase()}
          </span>
        )}
        <div>
          <h1 className="text-2xl font-semibold tracking-[-0.03em] text-fg">{user.full_name}</h1>
          <p className="text-sm text-muted">{user.email}</p>
        </div>
      </div>

      <Section title="Informations du compte">
        <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs text-subtle">Membre depuis</dt>
            <dd className="text-fg">{formatDateTime(user.created_at)}</dd>
          </div>
          <div>
            <dt className="text-xs text-subtle">Dernière connexion</dt>
            <dd className="text-fg">{formatDateTime(user.last_login_at)}</dd>
          </div>
          <div>
            <dt className="text-xs text-subtle">Méthodes de connexion</dt>
            <dd className="text-fg">
              {[user.has_password && "E-mail et mot de passe", user.google_linked && "Google"].filter(Boolean).join(" · ")}
            </dd>
          </div>
        </dl>
      </Section>

      <Section title="Activité récente">
        {activity.isPending && <Loader label="Chargement de l'activité..." />}
        {activity.error && <ErrorMessage message={activity.error.message} onRetry={() => void activity.refetch()} />}
        {activity.data && (
          <ul className="divide-y divide-line/[0.06] text-sm">
            {activity.data.map((entry, index) => (
              <li className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-0.5 py-2.5" key={`${entry.created_at}-${index}`}>
                <span className={entry.event === "login_failed" ? "text-rose-600 dark:text-rose-300" : "text-fg"}>
                  {eventLabels[entry.event] ?? entry.event}
                </span>
                <span className="text-xs text-subtle">
                  {formatDateTime(entry.created_at)} · {describeDevice(entry.user_agent)}
                  {entry.ip ? ` · ${entry.ip}` : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </Section>

      <Section title="Sécurité et données personnelles">
        <div className="flex flex-wrap gap-3">
          <button
            className="rounded-lg border border-line/[0.1] px-4 py-2 text-sm text-fg transition hover:border-accent/40 disabled:opacity-60"
            disabled={exporting}
            onClick={() => void exportData()}
            type="button"
          >
            {exporting ? "Export..." : "Télécharger mes données"}
          </button>
          <button
            className="rounded-lg border border-line/[0.1] px-4 py-2 text-sm text-fg transition hover:border-accent/40 disabled:opacity-60"
            disabled={logoutAll.isPending}
            onClick={() => logoutAll.mutate()}
            type="button"
          >
            Déconnecter tous mes appareils
          </button>
          <button
            className="rounded-lg border border-rose-500/30 px-4 py-2 text-sm text-rose-700 transition hover:bg-rose-500/10 disabled:opacity-60 dark:text-rose-300"
            disabled={deleteAccount.isPending}
            onClick={confirmDelete}
            type="button"
          >
            Supprimer mon compte
          </button>
        </div>
        {(logoutAll.error ?? deleteAccount.error) && (
          <p className="mt-3 text-xs text-rose-700 dark:text-rose-300" role="alert">
            {(logoutAll.error ?? deleteAccount.error)?.message}
          </p>
        )}
      </Section>
    </main>
  );
}
