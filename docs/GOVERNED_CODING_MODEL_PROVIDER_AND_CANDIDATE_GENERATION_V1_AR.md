# مزود النموذج البرمجي المحكوم وتوليد Candidate V1

## الغرض

تضيف هذه الدفعة طبقة تشغيل نموذج برمجي محلي محكوم لتوليد Candidate Patch داخل Workspace معزول فقط. لا تكتب على المصدر الحقيقي، ولا تطبق Candidate، ولا تستخدم Shell أو Git أو قاعدة بيانات.

## أوضاع المزود

- `disabled`: الوضع الآمن الافتراضي.
- `ollama`: اتصال Loopback فقط عبر `POST /api/generate`.
- `openai_compatible`: اتصال Loopback فقط عبر `POST /v1/chat/completions`.

لا تسمح V1 بمزود Remote خارجي. عنوان المزود يجب أن يكون `127.0.0.1` أو `localhost` أو `::1`. تُعطّل الـProxy والـRedirects داخل Adapter.

## أولوية الإعدادات

1. إعدادات لوحة التحكم المحلية المخزنة في JSON.
2. متغيرات البيئة كاحتياط.
3. القيم الافتراضية.

لا تُخزن قيمة API Key. يُخزن اسم متغير البيئة فقط، وتقرأ القيمة وقت التشغيل من البيئة.

## مسار العمل

`Human Goal → Project Context Read-Only → Explicit Model Authorization → Loopback Model Call → Strict JSON → AST Safety Gate → Candidate Workspace → Direct-Argv Tests → Unified Diff → Human Review Required`

## مخرجات النموذج المطلوبة

- ملخص.
- خطة تنفيذ.
- افتراضات.
- مخاطر.
- كود وحدة FastAPI واحدة مقروءة فقط.

يمر الكود عبر AST/Compile gate وقائمة Imports محددة. ثم يُختبر داخل Candidate Workspace قبل اعتماد الحالة `MODEL_CANDIDATE_HUMAN_REVIEW_REQUIRED`.

## الحدود

- `PRODUCTION_EXECUTION=NOT_AUTHORIZED`
- `MODEL_EXECUTION=EXPLICIT_HUMAN_AUTHORIZATION_ONLY`
- `PROVIDER_NETWORK=LOOPBACK_ONLY`
- `REAL_SOURCE_WRITE=NONE`
- `SOURCE_APPLY=BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION`
- `SHELL=NONE`
- `GIT=NONE`
- `DATABASE_WRITE=NONE`
- `SELF_APPLY=BLOCKED`

## الواجهة

`http://127.0.0.1:8010/agent-console/coding-model`

## واجهات API

- `GET /api/v1/operational-core/coding-model/health`
- `GET /api/v1/operational-core/coding-model/contract`
- `GET /api/v1/operational-core/coding-model/providers`
- `GET|POST /api/v1/operational-core/coding-model/settings`
- `POST /api/v1/operational-core/coding-model/providers/probe`
- `GET /api/v1/operational-core/coding-model/runs`
- `GET /api/v1/operational-core/coding-model/runs/latest`
- `GET /api/v1/operational-core/coding-model/candidates`
- `GET /api/v1/operational-core/coding-model/candidates/latest`
- `GET /api/v1/operational-core/coding-model/candidates/{candidate_id}`
- `POST /api/v1/operational-core/coding-model/candidates/generate`

لا توجد Apply API.
