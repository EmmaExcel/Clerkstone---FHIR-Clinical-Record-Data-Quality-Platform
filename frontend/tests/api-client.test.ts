import { afterEach, describe, expect, it, vi } from "vitest";
import {
  ApiError,
  BackendOfflineError,
  apiFetch,
  buildQueryString,
  isBackendOffline,
} from "@/lib/api/client";

describe("buildQueryString", () => {
  it("builds a query string and omits empty values", () => {
    expect(buildQueryString({ family: "smith", gender: "", _count: undefined, _page: 1 })).toBe(
      "?family=smith&_page=1",
    );
  });

  it("returns an empty string for no params", () => {
    expect(buildQueryString({})).toBe("");
  });
});

describe("apiFetch", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("parses a 2xx JSON response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify({ status: "ok" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const result = await apiFetch<{ status: string }>("/health");
    expect(result).toEqual({ status: "ok" });
  });

  it("throws ApiError carrying the OperationOutcome on a non-2xx response", async () => {
    const outcome = {
      resourceType: "OperationOutcome",
      issue: [{ severity: "error", code: "required", diagnostics: "identifier required" }],
    };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        new Response(JSON.stringify(outcome), {
          status: 400,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const error = await apiFetch("/patients").catch((e) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(400);
    expect((error as ApiError).operationOutcome?.issue[0].code).toBe("required");
  });

  it("throws BackendOfflineError when the network request fails", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new TypeError("fetch failed")));

    const error = await apiFetch("/health").catch((e) => e);
    expect(error).toBeInstanceOf(BackendOfflineError);
  });
});

describe("isBackendOffline", () => {
  it("identifies offline errors", () => {
    expect(isBackendOffline(new BackendOfflineError("down"))).toBe(true);
    expect(isBackendOffline(new TypeError("fetch failed"))).toBe(true);
    expect(isBackendOffline(new ApiError("x", 0))).toBe(true);
  });

  it("does not treat a real API error as offline", () => {
    expect(isBackendOffline(new ApiError("x", 500))).toBe(false);
    expect(isBackendOffline(new Error("something else"))).toBe(false);
  });
});
