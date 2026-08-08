# ربط الأدوات المقبولة جودةً بمخطط الهدف واختيار الأدوات — V1

## القاعدة
- Baseline بجودة `QUALITY_ACCEPTED`: قابل للاختيار.
- Baseline بجودة `PASS_WITH_LIMITATIONS`: قابل للاختيار مع تحذير.
- Benchmark دون Baseline بشري: انتظار اعتماد بشري.
- `QUALITY_FAILED`: محجوب.
- `QUARANTINED`: ممنوع.

## الأسطح
- `/agent-console/quality-tool-selection`
- ربط بصري داخل `/agent-console/goal-planner`
- ربط بصري داخل `/agent-console/tasks`

## الحدود
لا Model inference، لا تشغيل أدوات، لا حفظ لنص الهدف، لا تثبيت اختيار تلقائي، ولا تجاوز للمراجعة البشرية.
