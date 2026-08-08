# MEGA_BATCH_LOCAL_AGENTS_GOAL_TO_PLAN_TOOL_SELECTION_V1_DESIGN_ONLY

## الغرض

هذه الدفعة تثبت طبقة تصميمية لتحويل الهدف العالي المستوى إلى خطة ومصفوفة اختيار أدوات، دون أي تنفيذ ذاتي.

المسار المقصود لاحقًا:

```text
Goal Intake
→ Goal Analyzer
→ Project Plan Draft
→ Tool Selection Matrix
→ Human Review Gate
→ Execution Gate لاحقًا فقط
```

## ما تضيفه الواجهة

- صفحة `/agent-console/goal-planner`.
- نموذج Goal Intake محلي للعرض فقط.
- Project Plan Draft بنيوي قابل للمراجعة.
- Tool Selection Matrix تربط أنواع المهام بالأدوات والمساعدين.
- لوحات مختصرة داخل الصفحة الرئيسية، المهام، الأدوات، قارئ المشروع، والتشخيص.

## ما لا تفعله

```text
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_LANGGRAPH_RUNTIME
NO_SHELL
NO_GIT
NO_CODE_EXECUTION
NO_SELF_APPLY
NO_AUTONOMOUS_BUILD
NO_DATABASE_PERSISTENCE
NO_BACKEND_SOURCE_MUTATION
```

## قرار التصميم

هذه الدفعة لا تجعل الوكيل يبني مشروعًا. هي تجهز طريقة التفكير والتصنيف: عندما يعطي المستخدم هدفًا، ما الشكل الآمن للخطة، وما الأدوات المرشحة، وما الذي يبقى محظورًا حتى بوابة مستقلة.

## الدفعات اللاحقة الممكنة

1. `LOCAL_PROJECT_STATE_MANAGER_V1_DESIGN_OR_PREPARE_ONLY` لتتبع حالة خطة المشروع دون حفظ دائم.
2. `GOAL_PLAN_BACKEND_CONTRACT_V1_PREPARE_ONLY` لتحويل خطة الهدف إلى عقد Backend prepare لا ينفذ.
3. `GOVERNED_TOOL_PROPOSAL_V1` للسماح للوكيل باقتراح أداة جديدة دون كتابتها أو تسجيلها ذاتيًا.
