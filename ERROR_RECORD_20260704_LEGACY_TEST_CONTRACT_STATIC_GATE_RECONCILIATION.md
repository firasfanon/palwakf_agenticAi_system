# Error Record — Static Gate Contract Drift

## السبب الجذري
الـStatic Gate السابق افترض أن `Authorization` والمسار scoped موجودان كنص متصل داخل كل ملف اختبار. العقد الفعلي يستعمل Fixtures موحدة وتعريف `BASE` مركبًا.

## الأثر
فشل Gate كاذب على Windows رغم أن جميع ملفات Postimage مطابقة لحزمة المرشح، بما فيها الملفات الجديدة وبوابة الاختبار نفسها.

## الحل
تعديل Gate فقط ليتحقق من السلسلة الصحيحة: Fixture + injection، وBase contract + route construction.

## آخر baseline سليم
Windows Postimage Reconciliation: كل ملفات ترحيل الاختبارات تطابق الـPostimage؛ لا تغيير في backend source.
