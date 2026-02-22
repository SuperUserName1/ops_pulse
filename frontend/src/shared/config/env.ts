const fallbackApiBaseUrl = "/v1";

function normalizeBaseUrl(value: string | undefined): string {
  const next = value?.trim();
  if (!next) {
    return fallbackApiBaseUrl;
  }
  return next.endsWith("/") ? next.slice(0, -1) : next;
}

export const env = {
  apiBaseUrl: normalizeBaseUrl(import.meta.env.VITE_API_BASE_URL),
};
