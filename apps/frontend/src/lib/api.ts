const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public requestId?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("safeclaw_token");
}

export function setToken(token: string) {
  localStorage.setItem("safeclaw_token", token);
}

export function clearToken() {
  localStorage.removeItem("safeclaw_token");
}

export async function api<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const headers: HeadersInit = {
    "Content-Type": "application/json",
    ...(options.headers || {}),
  };
  if (token) {
    (headers as Record<string, string>)["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  const requestId = res.headers.get("X-Request-ID") || undefined;

  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new ApiError(detail, res.status, undefined, requestId);
  }

  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}
