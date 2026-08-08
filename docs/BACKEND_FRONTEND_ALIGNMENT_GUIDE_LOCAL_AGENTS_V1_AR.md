# دليل مطابقة الفرونت إند والباك إند — Local Agents Frontend Mega Workspace V1

## الحالة

تم قبول الواجهة الأمامية بصريًا حتى:

- `ASSISTANT_CATALOG_AND_TASK_STARTER_UI_V1_VISUALLY_ACCEPTED`
- `TOOL_REGISTRY_AND_TASK_DRAFTING_V1_VISUALLY_ACCEPTED`
- `PROJECT_READER_TOOL_V1_VISUALLY_ACCEPTED`

هذه الدفعة توسع الفرونت إند كمنتج تشغيلي موحد، لكنها لا تضيف Backend جديدًا ولا تفتح تنفيذًا.

## القاعدة الحاكمة

```text
FRONTEND_CAN_SHOW = YES
BACKEND_MUST_AUTHORIZE = BEFORE_PERSISTENCE_OR_EXECUTION
NO_SHELL
NO_GIT
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_EXTERNAL_WEB
NO_PLATFORM_MUTATION
NO_UNGOVERNED_DB_WRITE
```

## إجراءات Backend المطلوبة لاحقًا

### P0 — قبل تحويل مسودات المتصفح إلى سجلات خادمية

1. **Task Draft API**
   - Endpoint مقترح: `GET /api/v1/task-drafts`, `POST /api/v1/task-drafts`
   - الحالة: Prepare-only.
   - لا يسمح بأي execution dispatch.
   - الحقول الدنيا: `id`, `workspace_id`, `agent_id`, `title`, `description`, `allowed_tools`, `status`, `created_at`.

2. **Tool Registry API**
   - Endpoint مقترح: `GET /api/v1/tools/registry`
   - يعيد الأدوات بحالات: `approved`, `deferred`, `blocked`.
   - لا يحتوي endpoint استدعاء أداة.

3. **Assistant Tool Map API**
   - Endpoint مقترح: `GET /api/v1/assistants/tool-map`
   - مصدر موحد لربط المساعدين بالأدوات.
   - يمنع اختلاف الواجهة عن Backend.

### P1 — بعد تثبيت P0

4. **Project Reader Detail Contract**
   - توسيع `project-reader` لقراءة تفاصيل ملفات مختارة فقط.
   - يجب أن يكون allowlist-based وworkspace-scoped.
   - يمنع secrets، `.env`, private keys, node_modules, dist artifacts.

5. **Task Review Gate API**
   - Endpoint لاحق: `POST /api/v1/task-drafts/{id}/review`
   - ينقل المسودة إلى مراجعة بشرية فقط.
   - المراجعة ليست تنفيذًا.

### P2 — مؤجل

6. **Document Reader API**
   - Read-only فقط.
   - قيود حجم وصيغ.
   - لا OCR في النسخة الأولى.

7. **Local Task Store SQLite**
   - مسموح لاحقًا إذا تم تفويض الكتابة المحلية صراحة.
   - لا DB خارجي.

## عناصر تبقى محظورة

- Shell execution
- Git operations
- Code execution
- Model/Pilot execution
- Open Web Search
- Platform mutation
- Uncontrolled DB writes
- Agent self-apply

## معيار عدم الفجوة

لا تضف أي زر Frontend جديد يوحي بالتنفيذ قبل وجود واحد من الآتي:

```text
1. Backend read-only contract
2. Prepare-only backend contract
3. Explicit blocked state with no callable action
```

## الدفعة التالية الموصى بها بعد قبول هذه الواجهة

```text
MEGA_BATCH_LOCAL_AGENTS_BACKEND_TASK_DRAFT_API_AND_TOOL_REGISTRY_CONTRACTS_V1_PREPARE_ONLY
```

هدفها: نقل مسودات localStorage إلى Backend prepare-only محكوم، دون تنفيذ.
