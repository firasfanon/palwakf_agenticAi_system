# Guide Update Snippet — PalWakf Platform Comprehensive Guide

## Local Agents — HAR Filename Reconciliation V1

تم تجهيز Patch أدوات أدلة لمعالجة اختلاف اسم HAR الذي يصدره Edge في UAT المحلي. يعمل Runner على الاسم القياسي `browser_network.har` أولًا، ثم يقبل ملف HAR وحيدًا موجودًا مباشرةً في Evidence Root ويطبّعه إلى الاسم القياسي قبل التحليل. يتعمد رفض تعدد ملفات HAR لتجنب قبول دليل غامض.

لا تغيّر هذه الدفعة التطبيق أو عقد القراءة فقط أو أي صلاحية تشغيلية. يصبح التحديث baseline معتمدًا فقط بعد preimage-guard وStatic Gate على Windows.
