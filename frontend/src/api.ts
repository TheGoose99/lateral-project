const API_BASE = "/api/v1";
const CSRF_COOKIE = "takeaway_csrf";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function readCookie(name: string): string {
  const prefix = `${name}=`;
  const found = document.cookie.split("; ").find((part) => part.startsWith(prefix));
  return found ? decodeURIComponent(found.slice(prefix.length)) : "";
}

function csrfHeader(method: string): Record<string, string> {
  if (!["POST", "PUT", "PATCH", "DELETE"].includes(method.toUpperCase())) {
    return {};
  }
  const token = readCookie(CSRF_COOKIE);
  return token ? { "X-CSRF-Token": token } : {};
}

let refreshInFlight: Promise<boolean> | null = null;

async function rotateRefreshToken(): Promise<boolean> {
  if (refreshInFlight) return refreshInFlight;

  refreshInFlight = (async () => {
    const response = await fetch(`${API_BASE}/auth/refresh`, {
      method: "POST",
      credentials: "include",
      headers: {
        "Content-Type": "application/json",
        ...csrfHeader("POST"),
      },
    });
    return response.ok;
  })();

  try {
    return await refreshInFlight;
  } finally {
    refreshInFlight = null;
  }
}

function shouldSkipRefresh(path: string): boolean {
  return (
    path.startsWith("/auth/login") ||
    path.startsWith("/auth/register") ||
    path.startsWith("/auth/refresh") ||
    path.startsWith("/auth/logout")
  );
}

function errorFromBody(data: unknown, status: number): ApiError {
  const detail = (data as { detail?: unknown } | null)?.detail;
  const message =
    typeof detail === "string"
      ? detail
      : Array.isArray(detail)
        ? detail
            .map((entry: { msg?: string }) => entry.msg ?? "Invalid input")
            .join("; ")
        : `Request failed (${status})`;
  return new ApiError(message, status);
}

export async function api<T>(
  path: string,
  options: RequestInit = {},
  retried = false,
): Promise<T> {
  const method = (options.method ?? "GET").toUpperCase();
  const headers = new Headers(options.headers);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const csrf = csrfHeader(method);
  if (csrf["X-CSRF-Token"] && !headers.has("X-CSRF-Token")) {
    headers.set("X-CSRF-Token", csrf["X-CSRF-Token"]);
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });
  if (response.status === 204) return undefined as T;

  const data = await response.json().catch(() => null);

  if (
    response.status === 401 &&
    !retried &&
    !shouldSkipRefresh(path) &&
    readCookie(CSRF_COOKIE)
  ) {
    const refreshed = await rotateRefreshToken();
    if (refreshed) {
      return api<T>(path, options, true);
    }
    window.dispatchEvent(new Event("takeaway-auth-expired"));
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }

  if (response.status === 401) {
    window.dispatchEvent(new Event("takeaway-auth-expired"));
    throw new ApiError("Your session has expired. Please sign in again.", 401);
  }

  if (!response.ok) {
    throw errorFromBody(data, response.status);
  }

  return data as T;
}

export async function logoutOnServer(): Promise<void> {
  try {
    await api("/auth/logout", { method: "POST" });
  } catch {
    // Client-side logout still proceeds if the network call fails.
  }
}
