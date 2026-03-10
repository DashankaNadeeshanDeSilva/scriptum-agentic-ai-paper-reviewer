/**
 * Typed API client for the SCRIPTUM backend.
 *
 * Uses the native fetch API with typed request/response helpers.
 * Base URL is read from the NEXT_PUBLIC_API_URL environment variable.
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

export class ApiError extends Error {
  constructor(
    public status: number,
    public detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json", ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail ?? res.statusText);
  }
  return res.json();
}

export const api = {
  get: <T>(path: string) => request<T>(path),

  post: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    }),

  put: <T>(path: string, body?: unknown) =>
    request<T>(path, {
      method: "PUT",
      body: body ? JSON.stringify(body) : undefined,
    }),

  delete: <T>(path: string) => request<T>(path, { method: "DELETE" }),

  /**
   * Upload files via multipart form data.
   * Deliberately omits Content-Type so the browser sets the multipart boundary.
   */
  upload: async <T>(path: string, files: File[]): Promise<T> => {
    const form = new FormData();
    files.forEach((f) => form.append("files", f));
    const res = await fetch(`${API_BASE}/api/v1${path}`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({ detail: res.statusText }));
      throw new ApiError(res.status, body.detail ?? res.statusText);
    }
    return res.json();
  },
};
