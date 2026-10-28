import { useEffect, useRef, useState } from "react";

import { useThemeStore } from "../../store/themeStore";

const SCRIPT_URL = "https://accounts.google.com/gsi/client";

interface GoogleAccounts {
  id: {
    initialize: (options: { client_id: string; callback: (response: { credential: string }) => void; ux_mode?: string }) => void;
    renderButton: (element: HTMLElement, options: Record<string, unknown>) => void;
  };
}

declare global {
  interface Window {
    google?: { accounts: GoogleAccounts };
  }
}

let scriptPromise: Promise<void> | null = null;

function loadScript(): Promise<void> {
  if (window.google?.accounts) return Promise.resolve();
  scriptPromise ??= new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = SCRIPT_URL;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => {
      scriptPromise = null;
      reject(new Error("Google indisponible"));
    };
    document.head.appendChild(script);
  });
  return scriptPromise;
}

interface GoogleButtonProps {
  clientId: string;
  onCredential: (credential: string) => void;
  label: "signin_with" | "signup_with";
}

/** Bouton officiel « Se connecter avec Google » (Google Identity Services). */
export function GoogleButton({ clientId, onCredential, label }: GoogleButtonProps) {
  const container = useRef<HTMLDivElement>(null);
  const callback = useRef(onCredential);
  callback.current = onCredential;
  const theme = useThemeStore((state) => state.theme);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadScript()
      .then(() => {
        if (cancelled || !container.current || !window.google) return;
        window.google.accounts.id.initialize({ client_id: clientId, callback: (response) => callback.current(response.credential) });
        window.google.accounts.id.renderButton(container.current, {
          type: "standard",
          theme: theme === "dark" ? "filled_black" : "outline",
          size: "large",
          text: label,
          shape: "pill",
          locale: "fr",
          width: container.current.offsetWidth || 320,
        });
      })
      .catch(() => !cancelled && setFailed(true));
    return () => {
      cancelled = true;
    };
  }, [clientId, label, theme]);

  if (failed) return <p className="text-center text-xs text-subtle">Connexion Google momentanément indisponible.</p>;
  return <div className="flex min-h-[44px] w-full justify-center" ref={container} />;
}
