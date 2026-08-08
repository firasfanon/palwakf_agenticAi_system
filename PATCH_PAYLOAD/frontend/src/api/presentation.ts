import type { CollectionResponse, UnknownRecord } from "./types";

export function asRecord(value: unknown): UnknownRecord {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as UnknownRecord
    : {};
}

export function asItems(value: CollectionResponse | UnknownRecord): UnknownRecord[] {
  const items = asRecord(value).items;
  return Array.isArray(items)
    ? items.filter((item): item is UnknownRecord => Boolean(item) && typeof item === "object")
    : [];
}

export function text(value: unknown, fallback = "غير متاح"): string {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

export function count(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

export function itemLabel(item: UnknownRecord, index: number): string {
  for (const key of ["arabic_name", "display_name", "name", "title", "workspace_id", "agent_id", "code", "id"]) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return `عنصر ${index + 1}`;
}

export function itemSubtitle(item: UnknownRecord, keys: string[]): string {
  for (const key of keys) {
    const value = item[key];
    if (typeof value === "string" && value.trim()) return value.trim();
  }
  return "لا توجد تفاصيل منشورة ضمن عقد القراءة الحالي.";
}

export function uppercaseStatus(value: unknown, fallback = "UNKNOWN"): string {
  return text(value, fallback).replaceAll("_", " ");
}
