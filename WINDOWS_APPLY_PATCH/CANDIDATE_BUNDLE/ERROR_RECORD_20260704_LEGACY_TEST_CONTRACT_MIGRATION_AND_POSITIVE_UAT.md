# Error Record — Legacy Test Contract Migration + Controlled Positive Authorization UAT V1

## ER-01 — Legacy tests bypassed new authorization boundary

- **السبب:** اختبارات سابقة استدعت write routes دون Bearer Actor وبمسارات غير scoped.
- **الملفات:** `test_governed_local_agent_core.py`, `test_governed_operations.py`, `test_governed_operations_workspace_scoping.py`.
- **ما فشل:** `48 passed / 16 failed` بعد إغلاق write authorization.
- **الحل المرشّح:** fixture test-only يكتب registry مؤقت، مسارات Workspace، وأدوار actions محدودة.
- **آخر baseline مستقر:** `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260704_LEGACY_WRITE_AUTHORIZATION_TARGETED_ACCEPTANCE`.

## ER-02 — UI tests used removed implementation markers

- **السبب:** assertion لرموز `workspaceLabels`, `formatValue`, `raw-json` وmarker غير موجودة في الملف الحالي.
- **الحل المرشّح:** اختبار السلوك والعناصر الموجودة بالفعل (`labels`, `format`, `tech-details`, `JSON.stringify`, RTL).

## ER-03 — Capability Foundation write needs initialized Foundation workspace

- **السبب:** route يُرجع `WORKSPACE_FOUNDATION_NOT_INITIALIZED` قبل إنشاء state.
- **الحل المرشّح:** تهيئة `research_learning` داخل fixture مؤقت قبل لقطة baseline، لأن API لا يحتوي bootstrap route عام.
- **الحد:** لا يضيف هذا المسار Bootstrap production ولا يثبت صلاحية Government Foundation write.
