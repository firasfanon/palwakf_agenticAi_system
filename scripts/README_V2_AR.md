# Scripts V2

## Install-AgenticOperatingSystemV2.ps1
- `New`: ينشئ مشروعًا جديدًا من الحزمة.
- `Upgrade`: يضيف/يحدث طبقات V2 فقط مع إبقاء `tasks/evidence/output/audit/reference_sources` الموجودة.
- يدعم `-WhatIf`.
- لا يشغل نموذجًا ولا يفتح قاعدة بيانات ولا يعدل منصة PalWakf.

## Test-AgenticOperatingSystemV2.ps1
فحص ثابت لملفات V2 وعقود السجل والـSkills. لا يشغّل Ollama ولا يغيّر أي ملف.
