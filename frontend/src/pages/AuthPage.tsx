import { useState, type FormEvent } from "react";
import { Link, Navigate, useLocation, useSearchParams } from "react-router-dom";

import { GoogleButton } from "../components/auth/GoogleButton";
import { Loader } from "../components/common/Loader";
import { useAuthConfig, useMe, useSignIn } from "../hooks/useAuth";
import { authApi } from "../services/api";

type Mode = "login" | "register";

const copy: Record<Mode, { title: string; subtitle: string; submit: string; switchText: string; switchLink: string; switchTo: string }> = {
  login: {
    title: "Bon retour parmi nous",
    subtitle: "Connectez-vous pour accéder aux marchés.",
    submit: "Se connecter",
    switchText: "Pas encore de compte ?",
    switchLink: "Créer un compte",
    switchTo: "/register",
  },
  register: {
    title: "Créer votre compte",
    subtitle: "Gratuit. Charts, news en direct et calendrier économique.",
    submit: "Créer mon compte",
    switchText: "Déjà inscrit ?",
    switchLink: "Se connecter",
    switchTo: "/login",
  },
};

const inputClass =
  "mt-1.5 h-11 w-full rounded-xl border border-line/[0.1] bg-surface/60 px-3.5 text-sm text-fg outline-none transition placeholder:text-faint focus:border-accent/60";

/** Ne redirige qu'à l'intérieur du site (pas vers un domaine externe passé dans ?next=). */
function safeNext(value: string | null): string {
  return value && value.startsWith("/") && !value.startsWith("//") ? value : "/";
}

export function AuthPage({ mode }: { mode: Mode }) {
  const text = copy[mode];
  const [params] = useSearchParams();
  const location = useLocation();
  const next = safeNext(params.get("next"));
  const { data: user, isPending } = useMe();
  const { data: config } = useAuthConfig();
  const [form, setForm] = useState({ full_name: "", email: "", password: "" });

  const passwordSignIn = useSignIn((data: typeof form) =>
    mode === "register" ? authApi.register(data) : authApi.login({ email: data.email, password: data.password }),
  );
  const googleSignIn = useSignIn(authApi.google);
  const error = passwordSignIn.error ?? googleSignIn.error;
  const busy = passwordSignIn.isPending || googleSignIn.isPending;

  if (isPending) return <Loader className="min-h-[calc(100vh-138px)]" label="Chargement..." />;
  if (user) return <Navigate replace to={next} />;

  const onSubmit = (event: FormEvent) => {
    event.preventDefault();
    googleSignIn.reset();
    passwordSignIn.mutate(form);
  };
  const update = (field: keyof typeof form) => (event: { target: { value: string } }) =>
    setForm((current) => ({ ...current, [field]: event.target.value }));

  return (
    <main className="grid min-h-[calc(100vh-138px)] place-items-center px-4 py-10">
      <div className="w-full max-w-[400px] rounded-2xl border border-line/[0.07] bg-panel/80 p-6 shadow-[0_20px_60px_-30px_rgb(0_0_0/0.35)] sm:p-8">
        <h1 className="text-2xl font-semibold tracking-[-0.03em] text-fg">{text.title}</h1>
        <p className="mt-1.5 text-sm text-muted">{text.subtitle}</p>

        {config?.google_client_id && (
          <>
            <div className="mt-6">
              <GoogleButton
                clientId={config.google_client_id}
                label={mode === "register" ? "signup_with" : "signin_with"}
                onCredential={(credential) => {
                  passwordSignIn.reset();
                  googleSignIn.mutate(credential);
                }}
              />
            </div>
            <div className="my-5 flex items-center gap-3 text-[11px] uppercase tracking-wider text-faint">
              <span className="h-px flex-1 bg-line/[0.08]" />
              ou par e-mail
              <span className="h-px flex-1 bg-line/[0.08]" />
            </div>
          </>
        )}

        <form className={config?.google_client_id ? "" : "mt-6"} noValidate onSubmit={onSubmit}>
          <div className="space-y-4">
            {mode === "register" && (
              <label className="block text-xs font-medium text-muted">
                Nom
                <input autoComplete="name" className={inputClass} onChange={update("full_name")} required value={form.full_name} />
              </label>
            )}
            <label className="block text-xs font-medium text-muted">
              Adresse e-mail
              <input
                autoComplete="email"
                className={inputClass}
                inputMode="email"
                onChange={update("email")}
                placeholder="vous@exemple.com"
                required
                type="email"
                value={form.email}
              />
            </label>
            <label className="block text-xs font-medium text-muted">
              Mot de passe
              <input
                autoComplete={mode === "register" ? "new-password" : "current-password"}
                className={inputClass}
                onChange={update("password")}
                required
                type="password"
                value={form.password}
              />
              {mode === "register" && (
                <span className="mt-1.5 block text-[11px] font-normal text-subtle">8 caractères minimum, dont une lettre et un chiffre.</span>
              )}
            </label>
          </div>

          {error && (
            <p className="mt-4 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-700 dark:text-rose-300" role="alert">
              {error.message}
            </p>
          )}

          <button
            className="mt-5 h-11 w-full rounded-xl bg-accent text-sm font-semibold text-on-accent transition hover:brightness-105 disabled:opacity-60"
            disabled={busy}
            type="submit"
          >
            {busy ? "Veuillez patienter..." : text.submit}
          </button>
        </form>

        <p className="mt-6 text-center text-xs text-muted">
          {text.switchText}{" "}
          <Link className="font-semibold text-accent hover:underline" to={`${text.switchTo}${location.search}`}>
            {text.switchLink}
          </Link>
        </p>
      </div>
    </main>
  );
}
