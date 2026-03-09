import { describe, it, expect, vi, beforeEach } from "vitest";
import { api, ApiError } from "@/lib/api/client";

// Mock global fetch
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("api client", () => {
  it("GET sends correct request and returns JSON", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ ok: true }));

    const result = await api.get<{ ok: boolean }>("/test");

    expect(result).toEqual({ ok: true });
    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/v1/test"),
      expect.objectContaining({
        headers: expect.objectContaining({ "Content-Type": "application/json" }),
      }),
    );
  });

  it("POST sends JSON body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "123" }));

    const result = await api.post<{ id: string }>("/items", { name: "test" });

    expect(result).toEqual({ id: "123" });
    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("POST");
    expect(JSON.parse(opts.body)).toEqual({ name: "test" });
  });

  it("PUT sends JSON body", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ updated: true }));

    await api.put("/items/1", { name: "updated" });

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("PUT");
  });

  it("DELETE sends correct method", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ deleted: true }));

    await api.delete("/items/1");

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("DELETE");
  });

  it("throws ApiError on non-ok response", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Not found" }, 404),
    );

    await expect(api.get("/missing")).rejects.toThrow(ApiError);
  });

  it("ApiError has status and detail", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "Unauthorized" }, 401),
    );

    try {
      await api.get("/secret");
      expect.unreachable("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.detail).toBe("Unauthorized");
    }
  });

  it("upload sends FormData without Content-Type", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse([{ file_id: "f1" }]),
    );

    const file = new File(["content"], "paper.pdf", { type: "application/pdf" });
    await api.upload("/files/upload", [file]);

    const [, opts] = mockFetch.mock.calls[0];
    expect(opts.method).toBe("POST");
    expect(opts.body).toBeInstanceOf(FormData);
    // Should NOT have Content-Type header (browser sets it with boundary)
    expect(opts.headers).toBeUndefined();
  });
});
