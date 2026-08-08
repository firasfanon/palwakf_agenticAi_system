# استراتيجية النماذج المحلية ومصفوفة القدرات V1

```text
BATCH = MEGA_BATCH_LOCAL_AGENTS_LOCAL_MODEL_STRATEGY_AND_CAPABILITY_MATRIX_V1_DESIGN_ONLY
MODE = DESIGN_ONLY
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
```

## 1. الغرض

هذه الدفعة لا تشغّل نموذجًا محليًا ولا تختبر DeepSeek أو Ollama أو أي نموذج آخر. الغرض هو تثبيت **استراتيجية اختيار النماذج** قبل التشغيل، بحيث لا نربط كل المساعدين بنموذج واحد ولا نفتح Pilot قبل معرفة الدور والحدود.

## 2. المبدأ المعتمد

قوة الوكيل المحلي لا تأتي من النموذج وحده، بل من:

```text
Model + Tools + Codebase Understanding + Governance + Workflow
```

لذلك، حتى لو كان النموذج المحلي أصغر من النماذج السحابية العملاقة، يمكن أن يكون أكثر إنتاجية داخل مشروع محدد لأنه يعمل فوق معرفة المشروع وأدواته ودورة مراجعة محكومة.

## 3. مصفوفة الأدوار

| الدور | فئة النموذج | الاستخدام | الحالة | الحد |
|---|---|---|---|---|
| Fast Triage Model | small local instruct model | فرز سريع للأخطاء والطلبات | Candidate | لا تنفيذ |
| Coding Specialist Model | coder-class local model | اقتراح كود وتحليل TypeScript/Python | Design-only | لا self-apply ولا Git |
| Reasoning / Review Model | reasoning-oriented local model | مراجعة الخطط والحدود | Design-only | لا يقرر التفويض |
| Arabic Governance Model | Arabic-capable instruct model | توثيق عربي وتوريث | Design-only | لا baseline promotion تلقائي |
| Document / Knowledge Model | summarization/extraction model | تلخيص مستندات لاحقًا | Future gate | بعد Document Reader |
| Cloud Frontier Models | external cloud model | قدرات خام أعلى | Blocked | لا إرسال كود أو ملفات لخارج الجهاز |

## 4. بوابات ما قبل التشغيل

قبل أي تشغيل نموذج فعلي يجب توفر:

1. `Local Model Inventory` — قراءة أسماء النماذج المحلية دون تشغيلها.
2. `Role-to-Model Mapping` — ربط كل مساعد بفئة نموذج مناسبة.
3. `Prompt / Output Contract` — مخرجات مقيدة قابلة للفحص.
4. `Hardware & Resource Gate` — تقدير RAM/VRAM/CPU قبل Pilot.
5. `Controlled Local Model Pilot` — تفويض مستقل، عينة UAT، وعدم self-apply.

## 5. المحظورات الحالية

```text
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_OLLAMA_INVOKE
NO_DEEPSEEK_RUN
NO_BENCHMARK
NO_SELF_APPLY
NO_SHELL
NO_GIT
NO_CODE_EXECUTION
NO_EXTERNAL_CLOUD_MODEL
```

## 6. أثرها على الواجهة

تضيف الدفعة لوحات مرئية داخل:

```text
/agent-console/projects
/agent-console/diagnostics
/agent-console/pilot-control
```

وتعرض:

- `LOCAL_MODEL_STRATEGY_AND_CAPABILITY_MATRIX_V1`
- مصفوفة الأدوار وفئات النماذج
- بوابات ما قبل التشغيل
- تأكيد أن هذه مرحلة Design-only

## 7. المرحلة التالية بعد القبول

المرحلة التالية المنطقية ليست تشغيل نموذج، بل:

```text
MEGA_BATCH_LOCAL_AGENTS_LOCAL_MODEL_RUNTIME_READINESS_GATE_V1_READ_ONLY
```

وهدفها قراءة الجاهزية فقط، دون استدعاء نموذج.
