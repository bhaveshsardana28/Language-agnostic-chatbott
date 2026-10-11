// Public configuration only. The separate :5173 preview is CORS-allowed by FastAPI.
// Same-origin /static/v2/index.html requires no backend or routing change.
export const API_BASE = location.port === '5173'
  ? `${location.protocol}//${location.hostname}:8000` : location.origin;
export const HEALTH_TIMEOUT_MS = 8000;
