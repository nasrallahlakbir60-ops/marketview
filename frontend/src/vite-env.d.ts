/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_URL?: string;
  readonly VITE_WS_URL?: string;
  /** "false" : pas de WebSocket (hébergement serverless type Vercel), les news sont rechargées toutes les 60 s. */
  readonly VITE_ENABLE_WS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
