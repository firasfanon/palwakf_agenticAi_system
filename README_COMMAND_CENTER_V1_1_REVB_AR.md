# Command Center V1.1 Rev B — واجهة التشغيل المحلية المقيدة

هذه الحزمة تصلح مسار إدماج Command Center V1 في بنية المشروع الحقيقية:

`backend/src/palwakf_local_agents`

بدل وضع وحدة Python عند جذر المشروع، تنشئ الحزمة:

- `backend/src/palwakf_local_agents/command_center/`
- `backend/tests/test_command_center_read_only.py`
- Mount صريح محدود في `backend/src/palwakf_local_agents/app.py`

## الغرض
واجهة عربية RTL للاستعراض والمراجعة فقط عبر `/command-center`.

## لا تفعله الحزمة
- لا تشغّل Ollama أو أي نموذج.
- لا تشغّل الـPilot.
- لا تضيف زر اعتماد أو أرشفة أو تشغيل.
- لا تكتب منصة أو قاعدة بيانات أو Git أو أسرار أو ذاكرة.
- لا تمس `command_center/` الموجود عند جذر المشروع؛ يبقى Legacy Artifact غير مستخدم حتى إغلاق قبول منفصل.

## مسارات الواجهة
- `/command-center`
- `/command-center/tasks`
- `/command-center/reviews`
- `/command-center/evidence`
- `/command-center/agents`
- `/command-center/governance`
- `/command-center/system-health`

## المسارات البرمجية
- API مقيد بـ`/api/v1/local-agents/*` وبـGET فقط.
- إدماج التطبيق يقتصر على:
  `from .command_center import mount_command_center`
  ثم `mount_command_center(app, project_root=PROJECT_ROOT)`.

## ملاحظة
التطبيق الرئيسي الحالي يحتوي أصلًا على مسارات POST قديمة خارج Command Center. هذه الحزمة لا توسّعها ولا تعتمد عليها؛ ضمان GET-only مقصور على API prefix الخاص بـCommand Center.
