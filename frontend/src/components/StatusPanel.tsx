import type { ReactNode } from "react";
import type { ReadState } from "../api/types";

export function StatusPanel<T>({ state, children }: { state: ReadState<T>; children: (data: T) => ReactNode }) {
  if (state.kind === "loading") {
    return <section className="status-panel">جارٍ قراءة البيانات التشغيلية…</section>;
  }
  if (state.kind === "denied") {
    return <section className="status-panel denied">الوصول مرفوض ({state.status}): {state.detail}</section>;
  }
  if (state.kind === "error") {
    return <section className="status-panel error">تعذر إكمال القراءة{state.status ? ` (${state.status})` : ""}: {state.detail}</section>;
  }
  return <>{children(state.data)}</>;
}
