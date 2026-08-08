import type { ReadState } from "./types";

function detailFrom(value: unknown): string {
  if (typeof value === "string") return value;
  if (value && typeof value === "object" && "detail" in value) {
    const detail = (value as { detail?: unknown }).detail;
    if (typeof detail === "string") return detail;
    return JSON.stringify(detail);
  }
  return "UNKNOWN_READ_ERROR";
}

/**
 * Read-only client contract. It intentionally sends only GET requests, omits
 * credentials, and never stores an authorization token in the browser.
 */
export async function readJson<T>(path: string): Promise<ReadState<T>> {
  try {
    const response = await fetch(path, {
      method: "GET",
      headers: { Accept: "application/json" },
      credentials: "omit",
    });
    const body: unknown = await response.json().catch(() => null);
    if (!response.ok) {
      if (response.status === 401 || response.status === 403) {
        return { kind: "denied", status: response.status, detail: detailFrom(body) };
      }
      return { kind: "error", status: response.status, detail: detailFrom(body) };
    }
    return { kind: "ready", data: body as T };
  } catch (error) {
    return {
      kind: "error",
      detail: error instanceof Error ? error.message : "NETWORK_OR_RESPONSE_ERROR",
    };
  }
}
