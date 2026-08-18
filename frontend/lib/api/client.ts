import type { OperationOutcome } from "./types";

// base api url. defaults to relative /api/v1 for the reverse proxy.
// set NEXT_PUBLIC_API_BASE_URL for local dev.
export function getApiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (configured && configured.trim().length > 0) {
    return configured.replace(/\/+$/, "");
  }
  return "/api/v1";
}

const TOKEN_STORAGE_KEY = "clerkstone.access_token";

// get jwt for auth header
export function getAuthToken(): string | null {
  if (typeof window !== "undefined") {
    try {
      const stored = window.localStorage.getItem(TOKEN_STORAGE_KEY);
      if (stored) return stored;
    } catch {}
  }
  const fromEnv = process.env.NEXT_PUBLIC_DEMO_TOKEN;
  if (fromEnv && fromEnv.trim().length > 0) return fromEnv;
  return null;
}

// save jwt
export function setAuthToken(token: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (token) {
      window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
    } else {
      window.localStorage.removeItem(TOKEN_STORAGE_KEY);
    }
  } catch {}
}

// offline / network error
export class BackendOfflineError extends Error {
  readonly name = "BackendOfflineError";
  readonly offline = true;

  constructor(message: string, readonly cause?: unknown) {
    super(message);
  }
}

// non-200 api response
export class ApiError extends Error {
  readonly name = "ApiError";
  readonly status: number;
  readonly operationOutcome: OperationOutcome | null;

  constructor(message: string, status: number, operationOutcome: OperationOutcome | null = null) {
    super(message);
    this.status = status;
    this.operationOutcome = operationOutcome;
  }
}

// check if backend is unreachable
export function isBackendOffline(error: unknown): boolean {
  if (error instanceof BackendOfflineError) return true;
  if (error instanceof ApiError) return error.status === 0;
  if (error instanceof TypeError) {
    const message = error.message.toLowerCase();
    return message.includes("fetch") || message.includes("network") || message.includes("load failed");
  }
  return false;
}

export interface ApiRequestOptions {
  method?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  body?: unknown;
  signal?: AbortSignal;
  // additional headers
  headers?: Record<string, string>;
}

const DEFAULT_TIMEOUT_MS = 10_000;

// raw api fetch with auth and fhir error mapping
export async function apiFetch<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith("/") ? path : `/${path}`}`;

  const token = getAuthToken();
  const headers: Record<string, string> = {
    Accept: "application/json",
    "Content-Type": "application/json",
    ...options.headers,
  };
  if (token) headers.Authorization = `Bearer ${token}`;

  const timeoutController = new AbortController();
  const timeoutId = setTimeout(() => timeoutController.abort(), DEFAULT_TIMEOUT_MS);
  const signal = options.signal ?? timeoutController.signal;

  let response: Response;
  try {
    response = await fetch(url, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal,
      cache: "no-store",
    });
  } catch (error) {
    clearTimeout(timeoutId);
    if (error instanceof DOMException && error.name === "AbortError") {
      throw new BackendOfflineError(
        `The Clerkstone API at ${base} did not respond within ${DEFAULT_TIMEOUT_MS / 1000}s. It may be offline.`,
        error,
      );
    }
    throw new BackendOfflineError(
      `Unable to reach the Clerkstone API at ${base}. Is the backend running?`,
      error,
    );
  }
  clearTimeout(timeoutId);

  if (response.status === 204) {
    return undefined as T;
  }

  let body: unknown = null;
  const text = await response.text();
  if (text) {
    try {
      body = JSON.parse(text);
    } catch {
      body = null;
    }
  }

  if (!response.ok) {
    const outcome =
      body && typeof body === "object" && (body as OperationOutcome).resourceType === "OperationOutcome"
        ? (body as OperationOutcome)
        : null;
    const message = outcome
      ? outcome.issue.map((issue) => issue.diagnostics ?? issue.details?.text ?? issue.code).join("; ") ||
        "OperationOutcome returned no issues"
      : `Request failed with status ${response.status}`;
    throw new ApiError(message, response.status, outcome);
  }

  return body as T;
}

export function buildQueryString<T extends object>(params: T): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === "") continue;
    search.set(key, String(value));
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}
