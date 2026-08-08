# Goal Planner Productization V1 — Prepare Only

الدفعة: `MEGA_BATCH_LOCAL_AGENTS_GOAL_PLANNER_PRODUCTIZATION_V1_PREPARE_ONLY`

## الغرض

تحويل صفحة Goal Planner من شاشة تصميمية إلى تجربة تشغيلية أولية للمستخدم:

1. اختيار قالب هدف جاهز.
2. تعديل الهدف والقيود والناتج المطلوب.
3. توليد خطة أولية deterministic داخل الواجهة.
4. تحويل خطوات الخطة إلى مسودات مهام عبر Backend prepare عند توفره، أو Browser fallback عند تعذره.
5. إبقاء كل شيء prepare-only: لا تنفيذ، لا نموذج، لا Git، لا Shell، لا self-apply.

## الحدود

- `MODEL_EXECUTION = NONE`
- `PILOT_EXECUTION = NOT_EXECUTED`
- `SHELL = NO`
- `GIT = NO`
- `CODE_EXECUTION = NO`
- `SELF_APPLY = NO`
- `AUTONOMOUS_BUILD = NO`
- `DATABASE_PERSISTENCE = NONE`
- `BACKEND_SOURCE_MUTATION = NONE`

## الصفحات المتأثرة

- `/agent-console/goal-planner`
- `/agent-console/tasks` من حيث ظهور المسودات الناتجة عند التحضير
- `/agent-console/reviews` من حيث إمكانية مراجعة المسودات لاحقًا

## قرار المنتج

هذه الدفعة تجعل المسار اليومي أكثر إنتاجية للمستخدم:

`هدف → قالب → خطة → مسودات مهام → مراجعة بشرية`

ولا تحوله إلى مصنع تنفيذ ذاتي.
