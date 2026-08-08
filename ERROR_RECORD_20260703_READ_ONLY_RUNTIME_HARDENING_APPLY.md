# Error Record — Production Readiness Apply — 20260703

## ER-PRR-001 — React conditional mount import blocker

| الحقل | القيمة |
|---|---|
| السبب | `StaticFiles` و`FileResponse` كانا مستخدمين بلا imports عند تحقق dist الشرطي |
| الملفات | `backend/src/palwakf_local_agents/app.py` |
| الحل | imports صريحة وشرط دفاعي على index وassets |
| فحص الحل | hash postimage + import smoke بمجلد dist اصطناعي مؤقت |
| الحالة | **RESOLVED_AND_VALIDATED** |

## ER-PRR-002 — Cookie credential leakage risk

| الحقل | القيمة |
|---|---|
| السبب | `credentials: "same-origin"` قد يرفق Cookies في عميل React للقراءة |
| الملفات | `frontend/src/api/client.ts` |
| الحل | `credentials: "omit"` |
| فحص الحل | scan كامل لـ`frontend/src` لغياب storage/auth/bearer/write methods وتحقق قيمة credentials |
| الحالة | **RESOLVED_AND_VALIDATED** |

## ER-PRR-003 — Write authorization closure

| الحقل | القيمة |
|---|---|
| السبب | السجل الساكن يظهر `11` مسارات كتابة لا تُظهر في signature دليل Actor + Workspace موحدًا |
| الملفات | `app.py` ومسارات Backend ذات الصلة وفق inventory المرفق |
| ما فشل | لم يجر أي UAT كتابة، ولم تُنشأ UI write |
| الحل المطلوب | owner mapping + unified server-side authorization + negative UAT + audit/evidence linkage قبل أي binding React write |
| آخر baseline مستقر | `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260703` |
| الحالة | **OPEN_BLOCKER** |
