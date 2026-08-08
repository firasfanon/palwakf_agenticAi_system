# مركز قيادة المساعدين المحليين — Command Center V1

## النبذة العربية
هذه الحزمة تطور شاشات تشغيلية للمتابعة والمراجعة داخل النظام المحلي. كلمة **تشغيلية** هنا تعني عرض الحالة، المهمة المعتمدة، الأدلة، المراجعات، ونتائج الفحوصات؛ ولا تعني تشغيل النموذج أو تحريك المهام أو إجراء تغييرات على المنصة.

## ما تم تطويره
- واجهة عربية كاملة RTL ومتجاوبة.
- لوحة تحكم، مهام، تفاصيل مهمة، مراجعات، أدلة، وكلاء، حوكمة، وصحة نظام.
- API محلي GET-only ضمن `/api/v1/local-agents`.
- قارئ ملفات محكوم Allowlist للمجلدات المصرح بها فقط.
- رفض Task IDs غير الآمنة ومنع path traversal.
- اختبارات أمنية ووظيفية للقراءة فقط.

## الدمج الآمن
بما أن ملف دخول FastAPI الفعلي لم يكن ضمن الملفات المتاحة عند بناء الحزمة، لا يُطبق أي تعديل تلقائي على Core Runtime. أضف فقط الاستدعاء الموضح في `integration_example.py` إلى تطبيق FastAPI الحالي، بعد أخذ نسخة قبلية وضمن Mega Batch Command Center V1.

## الروابط بعد الدمج
- `/command-center`
- `/command-center/tasks`
- `/command-center/tasks/{taskId}`
- `/command-center/reviews`
- `/command-center/evidence`
- `/command-center/agents`
- `/command-center/governance`
- `/command-center/system-health`

## حدود غير قابلة للتفاوض
```text
MODEL_EXECUTION=NONE
PILOT_EXECUTION=NOT_EXECUTED
PLATFORM_MUTATION=NONE
DATABASE_ACCESS=NONE
GIT_WRITE=NONE
DEPLOYMENT=NONE
SECRETS_ACCESS=NONE
MEMORY_WRITE=NONE
```
