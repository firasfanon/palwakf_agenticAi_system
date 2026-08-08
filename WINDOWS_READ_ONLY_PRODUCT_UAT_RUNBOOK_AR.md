# Runbook — UAT بصري Read-Only لمرشح شاشة البدء

**لا ينفذ هذا الـRunbook ضمن الدفعة الحالية.**

## الشروط

- المرشح مطبق داخل isolated worktree فقط وبوابة static ناجحة.
- FastAPI المحلي يعمل بنسخة worktree، مع mount `/agent-console` الموروث دون تعديل.
- لا Actor token ولا client_id ولا صلاحيات كتابة.

## صفحات الفحص

1. `/agent-console/` — Desktop: 1440px أو أكثر.
2. `/agent-console/` — Mobile: عرض 390px؛ التنقل Drawer وليس قائمة كاملة فوق المحتوى.
3. `/agent-console/workspaces` — بطاقات السياق والسياسة دون إجراء.
4. `/agent-console/tasks` — توضيح الحجب دون زر كتابة.
5. `/agent-console/diagnostics` — عرض `GET /health` فقط.

## أدلة مطلوبة

- Screenshot وDOM لكل صفحة أعلاه.
- HAR أو Network summary يثبت أن React لم يرسل إلا `GET`.
- لا Authorization، ولا Bearer، ولا Cookies صادرة من React.
- Console errors/warnings.
- نتيجة `npm run check` و`npm run build` من worktree.

## حالات قبول

```text
RTL_RENDER = PASS
DESKTOP_NAVIGATION = PASS
MOBILE_DRAWER = PASS
NO_MOBILE_NAV_STACKING = PASS
NO_RAW_JSON_PRIMARY_SURFACE = PASS
GET_ONLY_NETWORK = PASS
CREDENTIALS_OMIT = PASS
NO_REACT_WRITE = PASS
NO_MODEL_OR_PILOT_EXECUTION = PASS
SOURCE_PROJECT_MUTATION = NONE
```

## الرفض المباشر

أي POST/PUT/PATCH/DELETE صادر من React، أو token في المتصفح، أو عرض بيانات تجارية/عميل دون سياق خادمي، أو إظهار زر تنفيذ يعمل، يرفض المرشح ويمنع baseline acceptance.
