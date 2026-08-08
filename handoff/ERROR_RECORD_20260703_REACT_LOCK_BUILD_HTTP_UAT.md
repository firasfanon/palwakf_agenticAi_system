# Error Record — React Lock / Build / HTTP UAT

| ID | الحالة | السبب | ما فشل | الحل/الحالة | آخر baseline مستقر |
|---|---|---|---|---|---|
| ER-PRR-003 | OPEN_BLOCKER | 11 write APIs تحتاج تفويضًا خادميًا موحدًا وإثبات Negative UAT | غير مشمول في هذه الدفعة | يمنع React write وProduction | 20260703_REACT_BUILD_HTTP_UAT |
| ER-RBU-001 | ENVIRONMENT_BLOCKED | Chromium النظامي يطبق `URLBlocklist=["*"]` | Browser navigation إلى local URL | لا سياسة تغيير/لا bypass؛ نفذ UAT في Windows أو متصفح غير محجوب | 20260703_REACT_BUILD_HTTP_UAT |
| ER-RBU-002 | OPEN_RECONCILIATION | اختبارات `governed_operations` تتوقع legacy non-workspace routes؛ runtime الحالي workspace-scoped | 5 اختبارات operations و1 UI marker | Discovery/Reconciliation مستقل؛ لا patch أو write enablement هنا | 20260703_REACT_BUILD_HTTP_UAT |
| ER-RBU-003 | ENVIRONMENT_VARIANCE | Python الحاوية 3.13.5 مقابل contract `<3.13` وtarget 3.12 | لا يمنع npm/Vite؛ يحد من قبول pytest runtime | أعد backend UAT على Python 3.12 | 20260703_REACT_BUILD_HTTP_UAT |
