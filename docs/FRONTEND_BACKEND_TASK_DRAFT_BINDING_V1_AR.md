# FRONTEND/BACKEND TASK DRAFT BINDING V1 — دليل عربي مختصر

الغرض: ربط زر تحضير المسودة في الواجهة بعقد Backend `task-drafts/prepare` دون حفظ دائم ودون تنفيذ.

## السلوك المعتمد

- الزر في كتالوج المساعدين وصفحة المهام يستدعي:
  `/api/v1/backend-frontend-alignment/task-drafts/prepare`
- الطلب من نوع POST محكوم لإنتاج envelope فقط.
- المخرج المتوقع يحتوي `draft_id`, `allowed_tools`, `blocked_actions`, `persistence=none`, `execution_authority=none`.
- الواجهة تعرض المسودة محليًا في `localStorage` فقط لتجربة المستخدم.

## ما لا يحدث

- لا تشغيل Model.
- لا Pilot.
- لا Shell.
- لا Git.
- لا Web search.
- لا Database write.
- لا حفظ خادمي دائم.
- لا تنفيذ مهمة.

## Fallback

إذا لم يكن Backend متاحًا أو رجع خطأ، تعرض الواجهة Browser fallback وتحفظ مسودة محلية للعرض فقط، مع إظهار سبب fallback.
