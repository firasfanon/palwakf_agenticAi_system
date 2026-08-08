# حوكمة تهيئة مساحات العمل

## النطاق
التوسعة لا تمنح صلاحية تشغيلية. هي فقط تربط التعريف المنطقي لمساحة العمل الموجودة في Workspace Core ببنية مادية دنيا مستقلة.

## المساحات الجديدة
### personal_development
تحمل سياسة `developer_controlled_v1`، لكن لا تمنح قراءة مستودع أو تنفيذ فحص أو تعديل شفرة. أي قدرة لاحقة تحتاج Candidate مستقلًا.

### commercial_projects
تحمل سياسة `client_isolated_v1`. لا تحتوي على عميل أو مشروع فعلي. أي عملية مستقبلية يجب أن تقدم `client_id` و`project_id` ولا يسمح بالانتقال بين العملاء أو المشاريع.

### research_learning
تحمل سياسة `research_read_prepare_v1`. لا تنشئ مخزن مصادر أو فهرس أو اتصال خارجي في هذه المرحلة.

## ثوابت عالمية
`MODEL_EXECUTION=NONE`, `PILOT_EXECUTION=NOT_EXECUTED`, `SHELL_EXECUTION=NONE`, `GIT_WRITE=NONE`, `PROJECT_FILE_WRITE=NONE`, `DEPLOYMENT=NONE`, `EXTERNAL_NETWORK=NONE`, و`HUMAN_REVIEW=MANDATORY`.


## ملاحظة إصلاح Preflight Anchor Reconciliation

عدّ مرساة `local_agent_core` يجب أن يستخدم أنماط Regex صحيحة، ولا يجوز أن يؤدي اختلاف escape داخل أداة الفحص إلى تجاوز بصمة `app.py` المقبولة. هذا الإصلاح لا يمنح أي صلاحية تنفيذ أو نموذج أو كتابة.
