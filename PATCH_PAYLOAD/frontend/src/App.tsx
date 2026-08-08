import { useEffect, useState } from "react";
import { readJson } from "./api/client";
import { asItems, asRecord, count, itemLabel, itemSubtitle, text, uppercaseStatus } from "./api/presentation";
import type { CollectionResponse, ReadState, UnknownRecord } from "./api/types";
import { Layout } from "./components/Layout";
import { Icon } from "./components/Icon";
import { BlockedAction, BoundaryPanel, MetricCard, SectionHeading, StateGate } from "./components/OperationalPanels";

function useRead<T>(path: string): ReadState<T> {
  const [state, setState] = useState<ReadState<T>>({ kind: "loading" });
  useEffect(() => {
    let active = true;
    void readJson<T>(path).then((result) => { if (active) setState(result); });
    return () => { active = false; };
  }, [path]);
  return state;
}

function postureValue(source: UnknownRecord, key: string, fallback = "غير متاح"): string {
  return text(asRecord(source.system_posture)[key], fallback);
}

function CommandCenter() {
  const dashboard = useRead<UnknownRecord>("/api/v1/local-agents/dashboard");
  const agents = useRead<CollectionResponse>("/api/v1/local-agent-core/agents");
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  return <Layout eyebrow="لوحة قراءة تشغيلية" title="مرحبًا في مركز المساعدين المحليين">
    <section className="welcome-hero">
      <div className="hero-copy">
        <div className="eyebrow-line"><span className="live-dot"/> النظام ضمن وضع المراجعة الآمنة</div>
        <h2>وضوح تشغيلي قبل أي تنفيذ</h2>
        <p>هذه الشاشة تجمع حالة المنصة، المساعدين، ومساحات العمل في سياق واحد. لا تنفذ أي إجراء ولا تطلب بيانات اعتماد؛ الهدف هو الفهم والمراجعة ضمن حدود الحوكمة.</p>
        <div className="hero-pills"><span><Icon name="shield" size={15}/> منع افتراضي</span><span><Icon name="workspace" size={15}/> سياق مساحة عمل</span><span><Icon name="lock" size={15}/> بلا كتابة</span></div>
      </div>
      <aside className="hero-guardrail"><div className="guardrail-top"><span className="guardrail-icon"><Icon name="shield" size={22}/></span><div><p>حالة الوصول</p><strong>قراءة محكومة</strong></div></div><dl><div><dt>الهوية</dt><dd>غير محمّلة في المتصفح</dd></div><div><dt>التنفيذ</dt><dd>غير متاح</dd></div><div><dt>الـPilot</dt><dd>غير منفذ</dd></div></dl></aside>
    </section>

    <StateGate state={dashboard} label="ملخص المنصة">
      {(data) => {
        const record = asRecord(data);
        const counts = asRecord(record.counts);
        const approved = count(counts.approved);
        const evidence = count(counts.evidence);
        const posture = uppercaseStatus(postureValue(record, "MODEL_EXECUTION", "NONE"));
        return <section className="metrics-grid" aria-label="ملخص تشغيل المنصة">
          <MetricCard icon="workspace" label="مساحات العمل" value="عرض محكوم" detail="لا توجد مساحة مختارة تلقائيًا" tone="blue"/>
          <MetricCard icon="task" label="مهام للمراجعة" value={approved} detail="لا يبدأ التنفيذ من هذا العرض" tone="gold"/>
          <MetricCard icon="evidence" label="عناصر دليل ظاهرة" value={evidence} detail="وفق عقد القراءة فقط" tone="slate"/>
          <MetricCard icon="agent" label="تنفيذ النموذج" value={posture} detail="يبقى محجوبًا في هذه المرحلة" tone="red"/>
        </section>;
      }}
    </StateGate>

    <section className="content-grid primary-grid">
      <article className="operational-card journey-card">
        <SectionHeading eyebrow="طريقة العمل" title="المسار التشغيلي المحكوم" detail="ما الذي تعرضه هذه الواجهة وما الذي لا تفعله."/>
        <ol className="journey-list"><li><span>01</span><div><strong>اقرأ الحالة</strong><p>راجع الصحة والمساعدين والمساحات من مصادر القراءة المعتمدة.</p></div></li><li><span>02</span><div><strong>ثبّت السياق</strong><p>يُحدد الفاعل ومساحة العمل والعميل لاحقًا على الخادم، لا داخل المتصفح.</p></div></li><li><span>03</span><div><strong>راجع قبل القرار</strong><p>تظهر الحدود والتبعات البشرية بدل تقديم أزرار تنفيذ غير مخولة.</p></div></li></ol>
      </article>
      <BoundaryPanel title="لا توجد أوامر تشغيل في هذه الواجهة" detail="الشاشة المصممة هنا هي Product Read-Only Candidate: لا إرسال، لا تعديل، لا تخزين Token، ولا تشغيل Agent أو Model."/>
    </section>

    <section className="section-block">
      <SectionHeading eyebrow="الرقابة الحالية" title="المساعدون المسجلون" detail="تظهر السجلات المعروضة دون كشف إعدادات داخلية." link={{ href: "/agent-console/tools", label: "عرض حدود الأدوات" }}/>
      <StateGate state={agents} label="سجل المساعدين">
        {(data) => <div className="agent-grid">{asItems(data).slice(0, 4).map((item, index) => <article className="agent-card" key={`${itemLabel(item,index)}-${index}`}><span className="agent-avatar"><Icon name="agent" size={21}/></span><div><strong>{itemLabel(item, index)}</strong><p>{itemSubtitle(item, ["execution_mode", "display_name", "agent_id"])}</p></div><span className="status-chip">{uppercaseStatus(item.model_execution, "READ ONLY")}</span></article>)}{asItems(data).length === 0 && <article className="empty-card">لا توجد سجلات مساعد متاحة ضمن عقد القراءة الحالي.</article>}</div>}
      </StateGate>
    </section>

    <section className="section-block">
      <SectionHeading eyebrow="السياق والسياسات" title="مساحات العمل المتاحة للعرض" detail="لا يتم اختيار مساحة أو عميل من الواجهة في هذه المرحلة." link={{ href: "/agent-console/workspaces", label: "عرض المساحات" }}/>
      <StateGate state={workspaces} label="مساحات العمل">
        {(data) => <div className="workspace-grid">{asItems(data).slice(0, 4).map((item, index) => <article className="workspace-card" key={`${itemLabel(item,index)}-${index}`}><div className="workspace-icon"><Icon name="workspace" size={20}/></div><div><p>{text(item.classification, "غير مصنف")}</p><strong>{itemLabel(item, index)}</strong><span>{text(item.policy_pack_id, "لا توجد سياسة منشورة")}</span></div><b>{uppercaseStatus(item.lifecycle_state, "DECLARED")}</b></article>)}{asItems(data).length === 0 && <article className="empty-card">لا توجد مساحات منشورة ضمن عقد القراءة الحالي.</article>}</div>}
      </StateGate>
    </section>
  </Layout>;
}

function Workspaces() {
  const workspaces = useRead<CollectionResponse>("/api/v1/workspaces");
  const governed = useRead<CollectionResponse>("/api/v1/governed-operations/workspaces");
  return <Layout eyebrow="السياق والسياسات" title="مساحات العمل">
    <section className="page-intro"><span className="intro-icon"><Icon name="workspace" size={24}/></span><div><p>قائمة موحدة للعرض</p><h2>كل مساحة تحافظ على سياقها وسياساتها</h2><span>لا يتم فتح مساحة عمل ولا تبديل سياق أو إجراء ضمن هذه الواجهة.</span></div></section>
    <StateGate state={workspaces} label="سجل المساحات">{(data) => <WorkspaceCards data={data}/>}</StateGate>
    <section className="section-block compact-top"><SectionHeading eyebrow="التحقق المتقاطع" title="الحالة التشغيلية المحكومة" detail="عرض مقارنة فقط؛ ليس زر تهيئة أو تفعيل."/><StateGate state={governed} label="الحالة المحكومة">{(data) => <GovernedStrip data={data}/>}</StateGate></section>
    <BoundaryPanel title="لم يُحدّد Actor أو Client في المتصفح" detail="أي عمل مستقبلي يحتاج Actor Scope وWorkspace Scope وClient Scope مفروضة خادميًا قبل القراءة المقيدة أو أي كتابة."/>
  </Layout>;
}

function WorkspaceCards({ data }: { data: CollectionResponse }) {
  const items = asItems(data);
  return <section className="workspace-grid large">{items.map((item, index) => <article className="workspace-card detailed" key={`${itemLabel(item,index)}-${index}`}><div className="workspace-icon"><Icon name="workspace" size={21}/></div><div><p>{text(item.classification, "غير مصنف")}</p><strong>{itemLabel(item, index)}</strong><span>حزمة السياسة: {text(item.policy_pack_id)}</span></div><b>{uppercaseStatus(item.lifecycle_state, "DECLARED")}</b><small>عرض معلومات فقط</small></article>)}{items.length === 0 && <article className="empty-card">لا توجد مساحات منشورة ضمن عقد القراءة الحالي.</article>}</section>;
}

function GovernedStrip({ data }: { data: CollectionResponse }) {
  const items = asItems(data);
  return <div className="governed-strip">{items.length === 0 ? <span>لا توجد حالة تشغيلية منشورة.</span> : items.map((item,index) => <article key={`${itemLabel(item,index)}-${index}`}><strong>{itemLabel(item,index)}</strong><span>{text(item.policy_pack_id)}</span><b>{uppercaseStatus(item.lifecycle_state, "DECLARED")}</b></article>)}</div>;
}

function Diagnostics() {
  const health = useRead<UnknownRecord>("/health");
  return <Layout eyebrow="سلامة النظام" title="التشخيص الصحي">
    <section className="page-intro"><span className="intro-icon"><Icon name="pulse" size={24}/></span><div><p>قراءة حالة الخدمة</p><h2>فحص شفاف بلا تغيير إعدادات</h2><span>تعرض هذه الصفحة العقد الصحي المتاح؛ لا تبدأ خدمة ولا تعيد تشغيل أي مكوّن.</span></div></section>
    <StateGate state={health} label="الحالة الصحية">{(data) => { const record = asRecord(data); return <div className="diagnostic-grid"><MetricCard icon="pulse" label="الخدمة" value={text(record.service)} detail={`نطاق الربط: ${text(record.bind_scope)}`} tone="blue"/><MetricCard icon="shield" label="التحقق الآمن" value={record.safety_ok === true ? "سليم" : "يتطلب مراجعة"} detail="قيمة مقروءة من /health" tone={record.safety_ok === true ? "gold" : "red"}/><MetricCard icon="agent" label="تنفيذ المساعد" value={record.agent_execution_enabled === true ? "مفعل" : "محجوب"} detail="لا تغيّر هذه الشاشة الوضع" tone="red"/><MetricCard icon="lock" label="وصول قاعدة البيانات" value={record.database_access_enabled === true ? "مفعل" : "غير مفعل"} detail="عرض حالة فقط" tone="slate"/></div>; }}</StateGate>
    <BoundaryPanel title="الصحة ليست تفويضًا" detail="نجاح التشخيص لا يفتح Model أو Pilot أو كتابة أو نشر. لكل انتقال بوابة تفويض مستقلة ودليل قبول منفصل."/>
  </Layout>;
}

const routeDetails: Record<string, { title: string; eyebrow: string; icon: "task" | "project" | "evidence" | "review" | "tool" | "lock"; summary: string; why: string; blocked: Array<["lock" | "shield" | "agent", string, string]> }> = {
  "/agent-console/tasks": { title: "المهام", eyebrow: "عرض محكوم", icon: "task", summary: "توجد المهام كمسار تشغيلي، لكن لا يتم نشر قائمة مقيدة دون Actor Scope صريح.", why: "هذا يحمي المساحات والعميل من العرض العرضي أو الالتباس بين السجلات.", blocked: [["lock", "إنشاء مهمة", "يتطلب هوية فاعل وسياق مساحة عمل مفروضًا خادميًا."], ["shield", "تغيير الحالة", "مقفل إلى أن يثبت عقد lifecycle والتفويض المناسب."], ["agent", "تشغيل مهمة", "تشغيل الوكلاء والنموذج خارج نطاق هذا المرشح."]] },
  "/agent-console/projects": { title: "المشاريع", eyebrow: "حدود العميل", icon: "project", summary: "المشاريع ذات البعد التجاري تحتاج Client Scope دائمًا، لكنها غير معروضة أو قابلة للكتابة هنا.", why: "لا يجوز أن يكون اختيار العميل أو حفظه مسؤولية المتصفح أو ذاكرة الجلسة.", blocked: [["lock", "فتح مشروع عميل", "يتطلب Client Scope ومصدرًا خادميًا قابلاً للتدقيق."], ["shield", "إنشاء مشروع", "حزمة client_id persistence ما زالت مرشّحًا غير مطبق."], ["agent", "تنفيذ تجاري", "لا Pilot أو تنفيذ تجاري في هذا المسار."]] },
  "/agent-console/evidence": { title: "الأدلة", eyebrow: "السجل والمراجع", icon: "evidence", summary: "تتجه الواجهة إلى مستعرض أدلة واضح، لكن عقد Ledger الموحد للـReact غير مغلق بعد.", why: "تعرض الأدلة لاحقًا وفق مساحة العمل والصلاحية، لا كملفات مفتوحة عامة.", blocked: [["lock", "رفع دليل", "الكتابة والحفظ خارج هذا العرض."], ["shield", "تعديل سجل", "التعديل يتطلب سببًا وهوية وسجل تدقيق."], ["agent", "توليد دليل", "لا تشغيل أدوات أو نموذج من الواجهة."]] },
  "/agent-console/reviews": { title: "المراجعات", eyebrow: "قرار بشري", icon: "review", summary: "المراجعة البشرية تظهر هنا كجزء من الحوكمة، لا كزر قبول أو رفض مباشر.", why: "يجب توثيق القرار ومجاله وسببه قبل تطبيق أي انتقال حالة.", blocked: [["lock", "اعتماد قرار", "لا قرار بشري من واجهة Read-Only."], ["shield", "تغيير مراجعة", "يتطلب سجل تدقيق وحزمة تفويض منفصلة."], ["agent", "استبدال المراجع", "لا تستبدل المنصة التحقق البشري في هذا المسار."]] },
  "/agent-console/tools": { title: "الأدوات", eyebrow: "قراءة وتحضير", icon: "tool", summary: "توضح الصفحة حدود الأدوات المسموح قراءتها، ولا تشغّل Shell أو Git أو Model.", why: "تظهر القدرات كسياق حوكمي قبل بناء واجهة تنفيذ مستقبلية.", blocked: [["lock", "تشغيل أداة", "لا تنفيذ تقني من React في هذه المرحلة."], ["shield", "الوصول إلى Git", "مقفل خارج حدود عقد القراءة."], ["agent", "تشغيل نموذج", "Model Execution غير مفعل."]] },
  "/agent-console/pilot-control": { title: "الـPilot", eyebrow: "بوابة تجريب مقفلة", icon: "lock", summary: "الـPilot غير منفذ. هذه الصفحة تبيّن الحالة بدل إيهام المستخدم بوجود تشغيل فعلي.", why: "أي Pilot يحتاج تفويضًا مستقلاً، نطاقًا محددًا، وUAT موثقًا قبل فتحه.", blocked: [["lock", "بدء Pilot", "لا يوجد تفويض تشغيل Pilot."], ["shield", "تعديل السياسات", "يستلزم حزمة حوكمة واعتمادًا منفصلين."], ["agent", "إطلاق Agent", "تشغيل المساعدين محجوب."]] },
};

function ControlledPage({ title, eyebrow, icon, summary, why, blocked }: { title: string; eyebrow: string; icon: "task" | "project" | "evidence" | "review" | "tool" | "lock"; summary: string; why: string; blocked: Array<["lock" | "shield" | "agent", string, string]> }) {
  return <Layout eyebrow={eyebrow} title={title}>
    <section className="page-intro"><span className="intro-icon"><Icon name={icon} size={24}/></span><div><p>واجهة توضيحية مقيدة</p><h2>{summary}</h2><span>{why}</span></div></section>
    <section className="blocked-list">{blocked.map(([blockedIcon, blockedTitle, detail]) => <BlockedAction key={blockedTitle} icon={blockedIcon} title={blockedTitle} detail={detail}/>)}</section>
    <BoundaryPanel title="المسار موجود، لكن التنفيذ لا يزال محجوبًا" detail="هذا تصميم مقصود: إظهار حقيقة الحدود أفضل من إخفاء المسار أو بناء واجهة شكلية يمكن فهمها على أنها تشغيل."/>
  </Layout>;
}

export function App() {
  const path = location.pathname.replace(/\/$/, "") || "/agent-console";
  if (path === "/agent-console" || path === "/agent-console/index.html") return <CommandCenter/>;
  if (path === "/agent-console/workspaces") return <Workspaces/>;
  if (path === "/agent-console/diagnostics") return <Diagnostics/>;
  const page = routeDetails[path];
  return page ? <ControlledPage {...page}/> : <ControlledPage title="الصفحة غير موجودة" eyebrow="مسار غير مسجل" icon="lock" summary="المسار المطلوب غير مشمول ضمن React Read-Only Candidate V1." why="لم تضف هذه الدفعة مسارات خادمية أو واجهات كتابة." blocked={[["lock", "لا يوجد انتقال", "ارجع إلى لوحة البداية أو أحد المسارات المسجلة."]]}/>;
}
