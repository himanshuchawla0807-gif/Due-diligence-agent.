/// <reference types="vite/client" />

interface ImportMetaEnv {
    readonly VITE_API_URL: string
    readonly VITE_SESSION_SERVICE_URL: string
    readonly VITE_SERVICE_KEY?: string
    readonly VITE_SENTRY_DSN?: string
    readonly VITE_ENVIRONMENT?: string
    readonly VITE_APP_VERSION?: string
}

interface ImportMeta {
    readonly env: ImportMetaEnv
}
