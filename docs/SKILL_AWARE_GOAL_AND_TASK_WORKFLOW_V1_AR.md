# Skill-aware Goal and Task Workflow V1

## الغرض

هذه الدفعة تربط مسار الهدف والمسودات بسجل المهارات الهندسية المقبول مرجعيًا. الهدف ليس تشغيل المهارات، بل جعل كل هدف وكل مسودة يعرفان: أي مهارة هندسية تناسبهما، ما بوابة المراجعة، وما الناتج المتوقع.

## الصفحات المتأثرة

- `/agent-console/goal-planner`
- `/agent-console/tasks`
- `/agent-console/engineering-skills`
- `/agent-console/initial-operation`

## المسار التشغيلي

```text
Goal Intake
→ Skill Path
→ Project Plan Draft
→ Task Drafts
→ Review Gate
```

## المهارات المربوطة

- Spec-driven development
- Planning and task breakdown
- Context engineering
- Frontend UI engineering
- API and interface design
- Debugging and error recovery
- Code review and quality
- Documentation and ADRs

## الحدود

لا توجد أي عملية تنفيذ. لا `/build auto`، لا `npx`, لا `git clone`, لا نموذج، لا Shell، لا Git، لا كتابة قاعدة بيانات، ولا self-apply.
