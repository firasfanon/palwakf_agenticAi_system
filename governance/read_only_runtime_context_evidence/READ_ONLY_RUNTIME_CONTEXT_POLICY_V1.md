# Read-only Runtime Context Policy V1

1. لا يمرر للموديل سوى: Task Intake المعتمد، مسارات مرجعية مصرح بها، Evidence Manifest، ومقتطفات محددة الحجم.
2. جميع المقتطفات تعامل كمحتوى غير موثوق ولا كمصدر أوامر.
3. لا يقرأ Runner أي مسار خارج `reference_sources/approved`.
4. لا يقبل Runner إلا `LOW` + `L0_READ_ONLY` + وكيل runtime-enabled.
5. لا يكتب Runner إلا إلى `output/read_only_context_runs`, `output/evidence_manifests`, و`audit/events.jsonl`.
6. لا يتم إنشاء Memory أو Learning Candidate أو تعديل Skill آلياً.
7. لا يثبت التقرير أي حالة تشغيلية حية أو قاعدة بيانات أو منصة.
