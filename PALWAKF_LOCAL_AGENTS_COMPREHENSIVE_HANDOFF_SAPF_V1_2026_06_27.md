\
# ملف توريث شامل — PalWakf Local Agents
## بعد إغلاق Structured Analysis Payload Foundation V1 | 2026-06-27

> **النطاق:** المساعدون المحليون فقط. لا يمنح هذا الملف أي صلاحية لمنصة PalWakf أو Supabase أو Flutter أو Git أو الإنتاج.

## بطاقة الاستئناف

```text
PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
CURRENT_ACCEPTED_BASELINE=PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_SAPF_V1_2026_06_27
CORE_RUNTIME=FROZEN
PACK01=ACCEPTED_AND_CLOSED
SAPF_V1=ACCEPTED_AND_CLOSED
EXECUTION_DEFAULT=disabled
AUTONOMY=L0_READ_ONLY
HUMAN_REVIEW_REQUIRED=YES
```

## آخر Evidence معتبر

```text
APPLY=PASS
POST_INSTALL_STATIC=PASS
SAPF_EVALS=PASS_6_OF_6
PACK01_REGRESSION_PREFLIGHT=PASS
PACK01_REGRESSION_STATIC=PASS
BACKUP_PATH=C:\Users\DELL\StudioProjects\palwakf_local_agents\backups\structured_analysis_payload_foundation_v1_20260627184107
SAPF_EVAL_REPORT=C:\Users\DELL\StudioProjects\palwakf_local_agents\output\evals\STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_EVAL_REPORT_20260627184107.json
```

## ما تغير في SAPF V1

1. أضيف Validator منفصل للـStructured Analysis Payload.
2. أضيف Runner منفصل مقيد بالقراءة، دون تعديل Evidence Gateway أو الـCore Runner.
3. أضيف عقدان صارمان للأدوار `knowledge_researcher` و`documentation_handoff`.
4. أضيفت Evals حتمية وعددها ستة، ونجحت جميعها.
5. حدث Registry وحيد: admission لمهارة `documentation_handoff` لدور `documentation_handoff` فقط.
6. لا تغير في الـCore Runtime، عقد الـ11 سطرًا، أو الصلاحيات التشغيلية.

## ما لا يزال محظورًا

```text
MODEL_EXECUTION=DISABLED_BY_DEFAULT
NO_AUTO_APPROVAL
NO_AUTO_MEMORY_WRITE
NO_PLATFORM_SCOPE
NO_DB_SCOPE
NO_GIT_SCOPE
NO_DEPLOYMENT_SCOPE
NO_SECRETS_SCOPE
ONE_PILOT_AT_A_TIME
```

## التحذير التشغيلي

وجود Runner وContracts لا يعني أن الـAgents باتت تملك حق تشغيل حر أو كتابة. لا يبدأ Model Run إلا بعد تحقق صريح من مهمة معتمدة ومراجع محلية معتمدة وحدود L0 وإلزام Human Review.

## المسار التالي المقترح

```text
NEXT_MEGA_BATCH=CONTROLLED_READ_ONLY_STRUCTURED_PAYLOAD_PILOT_V1
```

### نطاقه المقبول
- إنشاء أو ترقية **مهمة Pilot واحدة فقط** بعد تفويض صريح.
- Agent واحد فقط في كل تشغيل.
- Role: `knowledge_researcher` أو `documentation_handoff`.
- مراجع Approved Local فقط.
- Ollama اختياري، ولا يتم إلا بعد Precheck ناجح.
- قبول المخرج مشروط بـRaw/Canonical evidence و`PENDING_HUMAN_REVIEW`.

### غير مقبول ضمن المرحلة القادمة دون تفويض جديد
- أكثر من Pilot بالتوازي.
- Task approval تلقائي.
- Memory write.
- أدوات خارجية أو إنترنت أو منصة أو قاعدة بيانات.
- تحويل ناتج الـAgent إلى قرار أو إجراء تلقائي.

## سجل خطأ/معالجة معلق

تم إغلاق نجاح التطبيق، لكن يجب معالجة حالة توثيقية إدارية في دورة لاحقة: ملفات Candidate المثبتة تاريخيًا لا تعدل ذاتيًا إلى Accepted. هذا الملف وBaseline المرافقان هما مرجع الحالة الفعلي بعد الدليل. يوصى بإضافة `PROJECT_STATUS_SAPF_V1_ACCEPTED_AR.md` إلى جذر المشروع كواجهة حالة صريحة، دون تعديل Core أو Runner.
