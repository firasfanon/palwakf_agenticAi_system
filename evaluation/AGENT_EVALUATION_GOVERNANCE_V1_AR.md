# منهج تقييم المساعدين — V1

## الحالة

```text
HARNESS_DESIGN = PREPARED
MODEL_EXECUTION = NOT_EXECUTED
PILOT_EXECUTION = NOT_EXECUTED
```

## نطاق التقييم المصرح في التصميم فقط

- التزام حدود السياسة.
- مقاومة Prompt Injection.
- عدم تسريب أسرار أو عبور Workspace/Client.
- الالتزام بعقد المخرجات.
- عربية تشغيلية مفيدة.
- عدم الادعاء بتشغيل أدوات أو نموذج أو ملفات لم تُنفذ.

## المنهج

1. يعتمد Runner معتمد نسخة fixtures ذات SHA-256.
2. يسجل model/provider/version ووقت التنفيذ وactor/workspace.
3. تحفظ raw outputs داخل الأدلة فقط بعد تصنيفها.
4. يعرض scorecard وقرار reviewer؛ لا تتحول النتيجة إلى تشغيل أو صلاحية تلقائية.
5. أي فشل High severity يحجب الـPilot.

## لم يسمح به

```text
NO_PRODUCTION_DATA
NO_EXTERNAL_NETWORK
NO_TOOL_ACCESS
NO_SHELL
NO_GIT_WRITE
NO_MODEL_PROMPT_BEFORE_EXPLICIT_AUTHORIZATION
```
