# Snippet للدمج في PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md

## Local Agents — Legacy Write Authorization Closure V1 (2026-07-04)

تم تثبيت Boundary خادمي fail-closed في نسخة معزولة لمسارات الكتابة Legacy. كل write route يجب أن يمر قبل Store mutation عبر: actor authentication، workspace scope، action scope، declared actor match، وسياق client التجاري عند الاقتضاء. `POST /api/tasks` القديم غير المحدد بمساحة عمل معطل بـ410. الكتابة التجارية في `governed_operations` و`local_agent_core` مرفوضة عمدًا حتى تُنفذ `client_id` persistence القابل للتدقيق. Negative UAT أعاد 25/25 PASS مع إثبات snapshot عدم تغير الحالة بعد startup. لا يزال Full Backend Suite غير معتمد (48 passed / 16 failed) بسبب اختبارات Legacy غير محدثة؛ لذلك React write وPositive write UAT وModel/Pilot وProduction تبقى محظورة.
