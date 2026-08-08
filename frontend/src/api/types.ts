export type UnknownRecord = Record<string, unknown>;

export type ReadState<T> =
  | { kind: "loading" }
  | { kind: "ready"; data: T }
  | { kind: "denied"; status: number; detail: string }
  | { kind: "error"; status?: number; detail: string };

export interface CollectionResponse {
  items?: UnknownRecord[];
  [key: string]: unknown;
}
