# Backend/Frontend Alignment V1 - Approved Tools Only

## الهدف
سد الفجوة بين واجهة Local Agents المقبولة بصريًا والباك إند عبر عقود API آمنة، دون إدخال تنفيذ فعلي.

## المضاف
- `/api/v1/backend-frontend-alignment/health`
- `/api/v1/backend-frontend-alignment/tool-registry`
- `/api/v1/backend-frontend-alignment/assistants`
- `/api/v1/backend-frontend-alignment/frontend-contract`
- `/api/v1/backend-frontend-alignment/task-drafts/prepare`
- `/api/v1/backend-frontend-alignment/deferred-gate`
- `/api/v1/backend-frontend-alignment/boundary`

## الحدود
لا Shell، لا Git، لا Model، لا Pilot، لا Web Search، لا Database write، لا Platform mutation.

## ملاحظة
مسار `task-drafts/prepare` يعيد Draft envelope فقط ولا يحفظ في قاعدة بيانات أو ملف.
