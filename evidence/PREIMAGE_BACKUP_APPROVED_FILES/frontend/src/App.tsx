import { useEffect, useState } from "react";
import { readJson } from "./api/client";
import type { CollectionResponse, ReadState, UnknownRecord } from "./api/types";
import { Layout } from "./components/Layout";
import { StatusPanel } from "./components/StatusPanel";

function useRead<T>(path: string): ReadState<T> {
  const [state, setState] = useState<ReadState<T>>({ kind: "loading" });
  useEffect(() => {
    let active = true;
    void readJson<T>(path).then((result) => {
      if (active) setState(result);
    });
    return () => { active = false; };
  }, [path]);
  return state;
}

function recordLabel(record: UnknownRecord, index: number): string {
  for (const key of ["name", "workspace_id", "title", "agent_id", "code", "id"]) {
    const value = record[key];
    if (typeof value === "string" && value.trim()) return value;
  }
  return `عنصر ${index + 1}`;
}

function ReadOnlyNotice({ title, detail }: { title: string; detail: string }) {
  return (
    <section className="notice-grid">
      <article className="notice-card"><h2>{title}</h2><p>{detail}</p></article>
      <article className="notice-card"><h2>حد التنفيذ</h2><p>هذه الواجهة لا ترسل طلبات كتابة ولا تحفظ Token أو بيانات اعتماد.</p></article>
      <article className="notice-card"><h2>السياق المطلوب لاحقًا</h2><p>سيتم ربط Actor Scope وWorkspace Scope وClient Scope في أول Vertical Slice Full Stack.</p></article>
    </section>
  );
}

function CommandCenter() {
  const dashboard = useRead<UnknownRecord>("/api/v1/local-agents/dashboard");
  const agents = useRead<CollectionResponse>("/api/v1/local-agent-core/agents");
  return (
    <Layout eyebrow="واجهة تشغيل موحدة" title="مركز القيادة">
      <section className="hero-panel">
        <p>الواجهة تقرأ فقط من المسارات المتاحة دون Actor Token؛ المسارات المقيدة تبقى مرئية كحالة حوكمة وليست بيانات تجريبية.</p>
        <div className="hero-tags"><span>RTL</span><span>Legacy fallback محفوظ</span><span>Pilot غير منفذ</span></div>
      </section>
      <section className="grid two">
        <StatusPanel state={dashboard}>{(data) => <DataCard title="ملخص مركز القيادة" data={data} />}</StatusPanel>
        <StatusPanel state={agents}>{(data) => <CollectionCard title="سجل المساعدين" data={data} />}</StatusPanel>
      </section>
    </Layout>
  );
}

function Workspaces() {
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  const governed = useRead<CollectionResponse>("/api/v1/governed-operations/workspaces");
  return (
    <Layout eyebrow="Workspace Context" title="مساحات العمل والسياسات">
      <section className="grid two">
        <StatusPanel state={workspaces}>{(data) => <CollectionCard title="السجل السيادي لمساحات العمل" data={data} />}</StatusPanel>
        <StatusPanel state={governed}>{(data) => <CollectionCard title="الحالة التشغيلية المحكومة" data={data} />}</StatusPanel>
      </section>
      <ReadOnlyNotice title="السياق قبل الإجراء" detail="لا اختيار تلقائي لمساحة عمل ولا تجاوز للصلاحيات. أي تشغيل لاحق يتطلب Actor موثق ونطاقًا صريحًا." />
    </Layout>
  );
}

function DataCard({ title, data }: { title: string; data: UnknownRecord }) {
  const entries = Object.entries(data).slice(0, 12);
  return <article className="data-card"><h2>{title}</h2><dl>{entries.map(([key, value]) => <div key={key}><dt>{key}</dt><dd>{typeof value === "object" ? JSON.stringify(value) : String(value)}</dd></div>)}</dl></article>;
}

function CollectionCard({ title, data }: { title: string; data: CollectionResponse }) {
  const items = Array.isArray(data.items) ? data.items : [];
  return <article className="data-card"><h2>{title}</h2><p className="muted">عدد العناصر المقروءة: {items.length}</p><ul className="data-list">{items.length === 0 ? <li>لا توجد عناصر متاحة عبر عقد القراءة الحالي.</li> : items.slice(0, 12).map((item, index) => <li key={`${recordLabel(item, index)}-${index}`}><strong>{recordLabel(item, index)}</strong><span>{JSON.stringify(item)}</span></li>)}</ul></article>;
}

function ControlledPage({ title, eyebrow, detail }: { title: string; eyebrow: string; detail: string }) {
  return <Layout eyebrow={eyebrow} title={title}><ReadOnlyNotice title={title} detail={detail} /></Layout>;
}

function Diagnostics() {
  const health = useRead<UnknownRecord>("/health");
  return <Layout eyebrow="Diagnostics" title="التشخيص الصحي"><StatusPanel state={health}>{(data) => <DataCard title="حالة خدمة Local Agents" data={data} />}</StatusPanel><ReadOnlyNotice title="الحدود التشغيلية" detail="التشخيص لا يبدأ خدمة جديدة ولا يغير إعدادات التشغيل." /></Layout>;
}

export function App() {
  const path = location.pathname.replace(/\/$/, "") || "/agent-console";
  if (path === "/agent-console" || path === "/agent-console/index.html") return <CommandCenter />;
  if (path === "/agent-console/workspaces") return <Workspaces />;
  if (path === "/agent-console/diagnostics") return <Diagnostics />;
  const pages: Record<string, [string, string, string]> = {
    "/agent-console/tasks": ["المهام", "Task Workspace", "قائمة المهام المقيدة تحتاج Actor Scope قبل إظهار بياناتها."],
    "/agent-console/projects": ["المشاريع", "Client Isolation", "المشاريع التجارية تتطلب Client Context مفروضًا على الخادم."],
    "/agent-console/evidence": ["سجل الأدلة", "Evidence Ledger", "سيظهر المستعرض بعد توحيد عقد Ledger للقراءة المحكومة."],
    "/agent-console/reviews": ["المراجعات البشرية", "Human Review", "قرارات المراجعة لا تنفذ من هذه الواجهة في مرحلة Foundation."],
    "/agent-console/tools": ["الأدوات", "Deterministic Tools", "المرحلة الحالية تعرض حدود الأدوات ولا تنفذ Shell أو Git أو Model."],
    "/agent-console/pilot-control": ["الـPilot", "Controlled Pilot", "الـPilot غير منفذ ويتطلب تفويضًا بشريًا منفصلًا."],
  };
  const page = pages[path];
  return <ControlledPage title={page?.[0] ?? "الصفحة غير موجودة"} eyebrow={page?.[1] ?? "Not Found"} detail={page?.[2] ?? "المسار المطلوب غير مسجل في React Foundation V1."} />;
}
