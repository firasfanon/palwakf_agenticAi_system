# دليل التطبيق

1. شغّل `CandidateSyntax` ثم `Preflight` ثم Installer مع `-WhatIf`.
2. لا تطبق فعليًا إلا بتفويض Apply منفصل.
3. بعد التطبيق: شغّل `StaticEval`، ثم Runtime UAT على 390px–512px.
4. فحص UAT يتأكد من Drawer، Scrim، Escape، إغلاق القائمة بعد التنقل، وعدم وجود overflow أفقي أو أخطاء JavaScript.

**ملاحظة:** 404 الخاص بـfavicon أو Chrome DevTools-only endpoint ليس خطأ تطبيقيًا ما لم يصاحبه فشل HTTP لمسارات Command Center أو خطأ JavaScript.
