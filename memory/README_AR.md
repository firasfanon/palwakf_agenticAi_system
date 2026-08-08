# Memory Register

## القاعدة
تُحفظ الذاكرة هنا بشكل Versioned ومصدر ومراجعة. لا تنسخ المخرجات الخام إلى الذاكرة.

## المجلدات
- `project/`: الحالة والـBaselines المعتمدة.
- `semantic/`: facts وعقود الأنظمة.
- `episodic/`: runs/batches/incidents المقبولة.
- `procedural/`: skills/SOPs المعتمدة.
- `error/`: أخطاء وregression rules.
- `feedback/`: ملاحظات بشرية صالحة للتعميم.
- `learning_candidates/`: غير معتمدة بعد.
- `sensitive/`: يبقى فارغًا افتراضيًا ولا يوضع فيه secret.

كل سجل يجب أن يحمل: المصدر، تاريخ التحقق، الثقة، النطاق، التصنيف، والحالة.
