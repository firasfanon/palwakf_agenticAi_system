(() => {
  const API = '/api/v1/local-agents';
  const UI = '/command-center';
  const nav = [
    ['/', '▦', 'لوحة التحكم'],
    ['/tasks', '✓', 'إدارة المهام'],
    ['/reviews', '◌', 'المراجعات البشرية'],
    ['/evidence', '◈', 'مستكشف الأدلة'],
    ['/agents', '◍', 'سجل الوكلاء'],
    ['/governance', '⚖', 'الحوكمة'],
    ['/system-health', '⌁', 'صحة النظام'],
  ];
  const state = { tasks: [], queue: 'all', query: '' };
  const el = (id) => document.getElementById(id);
  const esc = (value) => String(value ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
  const chip = (value, klass='none') => `<span class="chip ${klass}">${esc(value)}</span>`;
  const taskClass = (status) => status === 'APPROVED_FOR_READ_ONLY_RUN' ? 'approved' : status.includes('ARCHIVED') ? 'archived' : 'none';
  const load = async (path) => {
    const response = await fetch(`${API}${path}`, {headers:{'Accept':'application/json'}});
    if (!response.ok) throw new Error(await response.text() || `HTTP ${response.status}`);
    return response.json();
  };
  const route = () => window.location.pathname.replace(UI, '') || '/';
  const go = (path) => { history.pushState({}, '', `${UI}${path}`); render(); };
  const pathFor = (path) => `${UI}${path}`;
  const setTitle = (title) => { el('page-title').textContent = title; };
  const banner = () => { el('read-only-banner').innerHTML = '<strong>حاجز الحماية:</strong> هذه واجهة مراقبة ومراجعة فقط. لا تتضمن تشغيل نموذج أو اعتمادًا أو أرشفة أو كتابة ذاكرة أو تكاملًا مع المنصة.'; };
  const navRender = () => { const current=route(); el('side-nav').innerHTML = nav.map(([path,symbol,label]) => `<button class="nav-link ${current===path || (path==='/tasks' && current.startsWith('/tasks/'))?'active':''}" data-path="${path}"><span class="nav-symbol">${symbol}</span><span>${label}</span></button>`).join(''); document.querySelectorAll('.nav-link').forEach(btn=>btn.addEventListener('click',()=>go(btn.dataset.path))); };
  const empty = (text) => `<div class="empty">${esc(text)}</div>`;
  const safetyKvs = (posture={}) => Object.entries(posture).map(([k,v])=>`<div class="kv"><div class="kv-label mono">${esc(k)}</div><div>${chip(v, v==='NONE'||v==='NOT_EXECUTED'?'low':'none')}</div></div>`).join('');

  async function dashboard() {
    setTitle('لوحة التحكم'); const data = await load('/dashboard');
    const c=data.counts; const active=data.active_approved_tasks || [];
    el('page-content').innerHTML = `
      <div class="grid metrics">
        ${[['مهام Inbox',c.inbox],['مهام معتمدة',c.approved],['مهام مؤرشفة',c.archived],['سجلات مراجعة',c.reviews],['أدلة وتقارير',c.evidence]].map(([l,v])=>`<article class="card metric-card"><div class="metric-label">${l}</div><div class="metric-value">${v}</div></article>`).join('')}
      </div>
      <div class="two-col">
        <section class="card"><div class="section-head"><div><h2>المهمة المعتمدة الحالية</h2><p>لا يعني الاعتماد أنها نُفذت.</p></div>${chip('NOT_EXECUTED','approved')}</div>
          ${active.length ? `<div class="data-list">${active.map(t=>`<div class="data-row"><div class="data-main"><button class="route-link" data-task="${esc(t.task_id)}">${esc(t.title)}</button><p class="mono">${esc(t.task_id)}</p><p>${esc(t.description)}</p></div><div>${chip(t.status,taskClass(t.status))} ${chip(t.autonomy,'low')}</div></div>`).join('')}</div>` : empty('لا توجد مهمة معتمدة حاليًا.')}
        </section>
        <section class="card"><div class="section-head"><div><h2>مخاطر مفتوحة</h2><p>مخاطر وتشغيل مقيدان.</p></div></div><ul class="risk-list">${data.open_risks.map(x=>`<li>${esc(x)}</li>`).join('')}</ul></section>
      </div>
      <div class="two-col">
        <section class="card"><div class="section-head"><div><h2>آخر الأدلة</h2><p>Metadata فقط ضمن roots المسموحة.</p></div><button class="route-link" data-go="/evidence">عرض الكل</button></div>${renderEvidenceRows(data.latest_evidence)}</section>
        <section class="card"><div class="section-head"><div><h2>آخر المراجعات</h2><p>سجل قابل للتتبع.</p></div><button class="route-link" data-go="/reviews">عرض الكل</button></div>${renderReviewRows(data.latest_reviews)}</section>
      </div>
      <div class="footer-note">Command Center V1 · Arabic RTL · Read-only observability</div>`;
    bindLinks();
  }

  const renderEvidenceRows = (items) => items?.length ? `<div class="data-list">${items.map(i=>`<div class="data-row"><div class="data-main"><strong>${esc(i.id)}</strong><p>${esc(i.summary||i.category)}</p><span class="mono">${esc(i.metadata.relative_path)}</span></div><div>${chip(i.category,'none')}</div></div>`).join('')}</div>` : empty('لا توجد أدلة ضمن المجلدات المسموحة.');
  const renderReviewRows = (items) => items?.length ? `<div class="data-list">${items.map(i=>`<div class="data-row"><div class="data-main"><strong>${esc(i.task_id)}</strong><p>${esc(i.reviewer)} · ${esc(i.scope)}</p><span class="mono">${esc(i.review_id)}</span></div><div>${chip(i.decision,'low')}</div></div>`).join('')}</div>` : empty('لا توجد سجلات مراجعة.');

  async function tasksPage() {
    setTitle('إدارة المهام'); const data = await load('/tasks'); state.tasks=data.items;
    const render = () => { const items=state.tasks.filter(t=>(state.queue==='all'||t.queue===state.queue)&&JSON.stringify(t).toLowerCase().includes(state.query.toLowerCase())); el('task-results').innerHTML = items.length ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>المهمة</th><th>الوكيل</th><th>الحالة</th><th>المخاطر</th><th>المسار</th></tr></thead><tbody>${items.map(t=>`<tr><td><button class="route-link" data-task="${esc(t.task_id)}">${esc(t.title)}</button><br><span class="mono">${esc(t.task_id)}</span></td><td>${esc(t.requested_agent)}</td><td>${chip(t.status,taskClass(t.status))}</td><td>${chip(t.risk,t.risk==='LOW'?'low':'none')}</td><td>${chip(t.queue,'none')}</td></tr>`).join('')}</tbody></table></div>`:empty('لا توجد مهام تطابق التصفية الحالية.'); bindLinks(); };
    el('page-content').innerHTML = `<section class="card"><div class="section-head"><div><h2>قائمة المهام</h2><p>لا توجد عناصر تنفيذية في هذه الشاشة.</p></div></div><div class="filters"><button class="filter active" data-q="all">الكل</button><button class="filter" data-q="inbox">Inbox</button><button class="filter" data-q="approved">Approved</button><button class="filter" data-q="archived">Archived</button><input id="task-search" class="search" placeholder="بحث بالمعرف أو العنوان أو الوكيل" /></div><div id="task-results"></div></section>`;
    document.querySelectorAll('[data-q]').forEach(b=>b.addEventListener('click',()=>{state.queue=b.dataset.q;document.querySelectorAll('[data-q]').forEach(x=>x.classList.toggle('active',x===b));render();})); el('task-search').addEventListener('input',e=>{state.query=e.target.value;render();}); render();
  }

  async function taskPage(taskId) {
    setTitle('تفاصيل المهمة'); const data = await load(`/tasks/${encodeURIComponent(taskId)}`); const t=data.task;
    const rows=Object.entries(t).map(([k,v])=>`<div class="kv"><div class="kv-label mono">${esc(k)}</div><div>${typeof v==='object'?`<pre>${esc(JSON.stringify(v,null,2))}</pre>`:esc(v)}</div></div>`).join('');
    el('page-content').innerHTML = `<div class="notice"><strong>تنبيه:</strong> ${esc(data.execution_notice)}</div><div class="two-col"><section class="card"><div class="section-head"><div><h2>${esc(t.title||taskId)}</h2><p class="mono">${esc(taskId)}</p></div>${chip(t.status,taskClass(t.status))}</div>${rows}</section><section class="card"><h2>حدود السيادة</h2>${safetyKvs(data.safety_posture)}<details><summary>Raw Task JSON</summary><pre>${esc(JSON.stringify(t,null,2))}</pre></details></section></div>`;
  }

  async function reviewsPage(){ setTitle('المراجعات البشرية');const data=await load('/reviews');el('page-content').innerHTML=`<section class="card"><div class="section-head"><div><h2>سجل المراجعة والموافقة</h2><p>قراءة فقط؛ لا يمكن إنشاء قرار أو تعديله من هذه الواجهة.</p></div></div>${renderReviewRows(data.items)}</section>`;}
  async function evidencePage(){setTitle('مستكشف الأدلة');const data=await load('/evidence');el('page-content').innerHTML=`<section class="card"><div class="section-head"><div><h2>الأدلة وتقارير Evals</h2><p>Metadata وHashes من المسارات المسموحة فقط.</p></div></div>${renderEvidenceRows(data.items)}</section>`;}
  async function agentsPage(){setTitle('سجل الوكلاء');const data=await load('/agents');el('page-content').innerHTML=`<section class="card"><div class="section-head"><div><h2>الأدوار المسجلة</h2><p>وجود الدور لا يعني صلاحية تشغيل عامة.</p></div></div><div class="table-wrap"><table class="data-table"><thead><tr><th>المعرف</th><th>الاسم</th><th>الجاهزية</th><th>النطاق</th></tr></thead><tbody>${data.items.map(x=>`<tr><td class="mono">${esc(x.agent_id)}</td><td>${esc(x.display_name_ar)}</td><td>${chip(x.readiness,x.readiness.includes('APPROVED')?'approved':'none')}</td><td>${chip(x.allowed_scope,'low')}</td></tr>`).join('')}</tbody></table></div></section>`;}
  async function governancePage(){setTitle('الحوكمة وBaseline');const data=await load('/governance');el('page-content').innerHTML=`<div class="two-col"><section class="card"><h2>الحالة الحاكمة</h2><div class="kv"><div class="kv-label">Core Runtime</div><div>${chip(data.core_runtime,'low')}</div></div><div class="kv"><div class="kv-label">عقد 11 سطرًا</div><div>${chip(data.core_11_line_output_contract,'low')}</div></div><div class="kv"><div class="kv-label">Lifecycle Closure</div><div>${chip(data.lifecycle_closure,'low')}</div></div>${safetyKvs(data.safety_posture)}</section><section class="card"><h2>المراجع المعتمدة</h2>${data.approved_references.length?data.approved_references.map(x=>`<div class="data-row"><div class="data-main"><strong>${esc(x.name)}</strong><p class="mono">${esc(x.metadata.sha256)}</p></div></div>`).join(''):empty('لا توجد مراجع معتمدة.')}<h3 style="margin-top:18px">ملفات حوكمة معروفة</h3>${data.known_governance_files.length?data.known_governance_files.map(x=>`<p class="mono">${esc(x.relative_path)}</p>`).join(''):empty('لا توجد ملفات حوكمة مطابقة ضمن allowlist.')}</section></div>`;}
  async function healthPage(){setTitle('صحة النظام');const data=await load('/system-health');el('page-content').innerHTML=`<div class="two-col"><section class="card"><div class="section-head"><div><h2>${esc(data.health)}</h2><p>فحص قراءة فقط.</p></div>${chip(data.active_approved_task_count===0?'NO_ACTIVE_TASK':'APPROVED_TASK_PRESENT',data.active_approved_task_count?'approved':'low')}</div><div class="kv"><div class="kv-label">عدد المهام المعتمدة</div><div>${data.active_approved_task_count}</div></div><div class="kv"><div class="kv-label">المعرفات</div><div class="mono">${esc(data.active_approved_task_ids.join(', ')||'—')}</div></div>${safetyKvs(data.safety_posture)}</section><section class="card"><h2>الجذور المسموحة</h2>${Object.entries(data.allowlisted_roots).map(([k,v])=>`<div class="kv"><div class="kv-label mono">${esc(k)}</div><div class="mono">${esc(v)}</div></div>`).join('')}<h3 style="margin-top:18px">ملاحظات</h3><ul class="risk-list">${data.notes.map(n=>`<li>${esc(n)}</li>`).join('')}</ul></section></div>`;}

  function bindLinks(){document.querySelectorAll('[data-task]').forEach(b=>b.addEventListener('click',()=>go(`/tasks/${b.dataset.task}`)));document.querySelectorAll('[data-go]').forEach(b=>b.addEventListener('click',()=>go(b.dataset.go)));}
  async function render(){navRender();banner(); const content=el('page-content');content.innerHTML='<div class="loader">جارٍ تحميل البيانات المقيدة…</div>';try{const p=route();if(p==='/')await dashboard();else if(p==='/tasks')await tasksPage();else if(p.startsWith('/tasks/'))await taskPage(decodeURIComponent(p.slice('/tasks/'.length)));else if(p==='/reviews')await reviewsPage();else if(p==='/evidence')await evidencePage();else if(p==='/agents')await agentsPage();else if(p==='/governance')await governancePage();else if(p==='/system-health')await healthPage();else{setTitle('المسار غير موجود');content.innerHTML=empty('المسار المطلوب غير معروف.');}}catch(error){setTitle('تعذر تحميل البيانات');content.innerHTML=`<div class="card"><div class="notice"><strong>خطأ قراءة:</strong> ${esc(error.message)}</div><p class="muted">لم يُنفذ أي إجراء ولم تتغير أي حالة تشغيلية.</p></div>`;}}
  document.addEventListener('click',e=>{if(e.target.closest('#menu-button'))document.querySelector('.sidebar').classList.toggle('open');});window.addEventListener('popstate',render);render();
})();
