# PROJECT CONTINUITY MEMORY AND TASK BOARD V1 — DESIGN ONLY

## الهدف

معالجة خطر نسيان الوكيل وفقدان سياق المشروع عبر تصميم طبقة استمرارية تشغيلية تقرأ الحالة الحالية وتعرضها للمستخدم دون فتح ذاكرة دائمة أو قاعدة بيانات.

## المسار المقترح

```text
Working State → Project Board/TODO → Checkpoints → Standing Rules → Long-term Memory Gate
```

## ما تضيفه الدفعة

- صفحة `/agent-console/project-board`.
- عرض Project State Snapshot.
- عرض TODO Board من مسودات المتصفح الحالية فقط.
- عرض طبقات الذاكرة المستقبلية.
- عرض Context Drift Guard.
- عرض Standing Rules وInnovation Review كتصميم فقط.

## ما لا تفعله

```text
CHROMADB = NO
VECTOR_MEMORY = NO
DATABASE_PERSISTENCE = NONE
MODEL_EXECUTION = NONE
PILOT_EXECUTION = NOT_EXECUTED
SHELL = NO
GIT = NO
CODE_EXECUTION = NO
SELF_APPLY = NO
```

## لماذا هذه الدفعة مهمة؟

هذه الصفحة تصبح بداية "ذاكرة تشغيلية مرئية" للمشروع: المستخدم يرى أين وصل، ما هو الهدف، ما هي المسودات، وما هي الحدود. لاحقًا يمكن تحويل التصميم إلى تخزين محلي محكوم بعد بوابة مستقلة.
