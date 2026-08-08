# مسار تطوير البرمجيات المحكوم وأول Candidate Patch — V1

## ما تنفذه الدفعة

تنشئ مسارًا فعليًا لتطوير البرمجيات دون السماح بالتطبيق الذاتي:

`Goal → Plan → Project Understanding → Candidate Workspace → Controlled Edit → Tests → Diff → Human Review`

## أول Candidate

`READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1`

يقترح إضافة:

- `development_diagnostic_v1.py`
- تسجيل نقطة `GET /api/v1/operational-core/development-diagnostic/health`

ويختبر الـCandidate داخل Workspace معزول. لا ينتقل إلى المصدر الحقيقي.

## المزوّد

يستخدم أول Pilot مولدًا حتميًا محليًا دون نموذج. Ollama وOpenAI-Compatible يبقيان محجوبين حتى تفويض مستقل.

## التطبيق على المصدر

لا يوجد Apply endpoint في V1. حتى بعد موافقة المراجع، تبقى الحالة:

`HUMAN_APPROVED_APPLY_STILL_BLOCKED`

ويحتاج التطبيق لاحقًا إلى تفويض Candidate-specific مستقل.
