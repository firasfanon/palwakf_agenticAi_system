# MEGA_BATCH_LOCAL_AGENTS_GOVERNED_OPERATIONS_FOUNDATION_V1

## الهدف
بناء طبقة عمليات محلية محكومة فوق المشروع، تفصل بين:

- **إدارة دورة حياة المهمة**.
- **القرار البشري الموثق**.
- **إدارة Metadata للأدلة ومستوى الثقة**.
- **بوابة تنفيذ مستقبلية معطلة افتراضيًا**.

هذه ليست دفعة تشغيل نموذج أو Pilot.

## السطح الجديد

- UI: `/operations`
- API: `/api/v1/governed-operations/*`
- Local state: `audit/governed_operations.sqlite`

## السطح الذي يبقى دون تغيير

- `/command-center` يبقى Command Center للقراءة فقط.
- `/api/v1/local-agents/*` يبقى GET-only.
- المهمة `SAPF_DOCUMENTATION_HANDOFF_PILOT_001` لا تتغير ولا تُنفذ.

## تنبيه حول الهوية

`actor_id` داخل هذه الدفعة هو **Local Operator Identity Assertion** لتوثيق من قام بالإجراء محليًا.
لا يمثل Authentication أو RBAC متعدد المستخدمين. لا يجوز عرض ذلك كضمان هوية مستقل.
