# ملاحظات الإصلاح

المرشح السابق فشل بسبب `False Positive` في فاحص نصي كان يستثني `env` فقط.

هذا المرشح يستبدل الفحص النصي العام بفحص نطاقي يعتمد على Variable Tokens التي ينتجها PowerShell Parser، ثم يطبق قائمة نطاقات معتمدة.

`$workspaceId:$sqlite` يبقى مرفوضاً في الاختبار الذاتي، بينما `$env:USERPROFILE` و`$script:checks` ومثيلاتها تمر.
