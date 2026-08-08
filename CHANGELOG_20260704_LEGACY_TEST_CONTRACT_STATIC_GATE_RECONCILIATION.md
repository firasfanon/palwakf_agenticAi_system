# Changelog — Legacy Test Contract Static Gate Reconciliation V1

- صُحح تحليل Static Gate لمسار governed operations ليقبل العقد المركب `BASE + f"{BASE}/tasks"`.
- صُحح إثبات Headers كي يقرأ Fixture المصرح به من `conftest.py` ويثبت حقنه داخل اختبارات governed/local-agent.
- لم تتغير اختبارات backend أو كود التطبيق أو التفويض الخادمي.
