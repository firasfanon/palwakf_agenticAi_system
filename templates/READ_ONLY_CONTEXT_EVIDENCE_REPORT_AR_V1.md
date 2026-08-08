# تقرير تحليل محلي مقيد بالأدلة

- معرف التشغيل: {{RUN_ID}}
- المهمة: {{TASK_ID}}
- الوكيل: {{AGENT_ID}}
- النموذج: {{MODEL}}
- وضع التشغيل: {{RUN_MODE}}
- الحالة: {{RUN_STATUS}}

## حدود التنفيذ
- PLATFORM_MUTATION: NONE
- DATABASE_ACCESS: NONE
- GIT_WRITE: NONE
- DEPLOYMENT: NONE
- SECRETS_ACCESS: NONE

## ما ثبت
- تم بناء Evidence Manifest: `{{EVIDENCE_MANIFEST_PATH}}`
- تم حصر القراءة داخل المصادر المرجعية المعتمدة فقط.
- لا يثبت هذا التقرير حالة حية للمنصة أو قاعدة البيانات أو التشغيل الفعلي.

## ما لم يثبت
- لا يثبت التقرير صحة أو اكتمال أي مصدر خارج الـManifest.
- لا يعتمد التقرير أي حقيقة أو قرار أو Memory أو Learning Candidate تلقائياً.

## الأدلة المستخدمة
{{EVIDENCE_SUMMARY}}

## إشارات الأمان
{{SECURITY_SUMMARY}}

## نتيجة التحقق الحتمي من مخرجات النموذج
```text
{{MODEL_VALIDATION}}
```

## مخرجات النموذج الخام
```text
{{RAW_MODEL_OUTPUT}}
```

## المراجعة البشرية
- HUMAN_REVIEW_REQUIRED: YES
- لا يعتمد أي استنتاج أو خطوة تالية قبل المراجعة البشرية.
