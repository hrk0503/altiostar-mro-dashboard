/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_DEMO_PASSWORD?: string;
  readonly VITE_GOOGLE_3DTILES_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
