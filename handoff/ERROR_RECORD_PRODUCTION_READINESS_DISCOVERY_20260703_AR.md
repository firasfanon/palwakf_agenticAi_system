# Error Record — Production Readiness Discovery — 2026-07-03

## ER-PRR-001

| الحقل | القيمة |
|---|---|
| التصنيف | React activation runtime blocker |
| السبب | `app.py` يذكر `StaticFiles` و`FileResponse` في مسار التفعيل الشرطي من دون import |
| الملفات | `backend/src/palwakf_local_agents/app.py` |
| ما فشل | لم ينفذ runtime؛ الفشل متوقع فقط بعد وجود `frontend/dist` وتقييم الشرط |
| الحل المرشح | imports صريحة + شرط `dist/assets` دفاعي |
| آخر baseline مستقر | `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260702` |
| الحالة | STAGED_NOT_APPLIED |

## ER-PRR-002

| الحقل | القيمة |
|---|---|
| التصنيف | React read-client credential leakage risk |
| السبب | `credentials: "same-origin"` قد يرفق Cookies تلقائيًا |
| الملفات | `frontend/src/api/client.ts` |
| ما فشل | لا يوجد run؛ خطر تصميمي اكتشف static |
| الحل المرشح | `credentials: "omit"` |
| آخر baseline مستقر | `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260702` |
| الحالة | STAGED_NOT_APPLIED |

## ER-PRR-003

| الحقل | القيمة |
|---|---|
| التصنيف | Authorization closure blocker |
| السبب | تفاوت نضج تفويض مسارات الكتابة؛ `POST /api/tasks` لا يظهر Actor/Workspace/Client enforcement موحدًا |
| الملفات | `app.py` وrouters التشغيلية ذات الصلة |
| ما فشل | لم يُجرَ UAT كتابة ولا React write binding |
| الحل | inventory + owner mapping + unified server-side authorization + negative UAT قبل React write |
| آخر baseline مستقر | `LOCAL_AGENTS_COMPREHENSIVE_BASELINE_20260702` |
| الحالة | OPEN_BLOCKER |
