export type BadgeTone = "slate" | "blue" | "gold" | "red" | "green";

export function Badge({ children, tone = "slate" }: { children: string; tone?: BadgeTone }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}
