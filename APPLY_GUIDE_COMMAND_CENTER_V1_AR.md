# دليل إدماج Command Center V1

> لا يوجد هنا تعديل تلقائي لملف دخول FastAPI، لأن بنية التطبيق الفعلية لم تُرفع ضمن هذه الجلسة. الحزمة تطور Module كاملًا قابلًا للتركيب، وتحمي الـCore Runtime من التعديل التخمينـي.

## 1. فحص المرشح
```powershell
$target = 'C:\Users\DELL\StudioProjects\palwakf_local_agents'
$package = 'C:\path\to\PALWAKF_LOCAL_AGENTS_COMMAND_CENTER_V1_READ_ONLY_CANDIDATE'
& "$package\scripts\Install-CommandCenterV1Overlay.ps1" -PackageRoot $package -ProjectRoot $target -WhatIf
```

## 2. التطبيق
```powershell
& "$package\scripts\Install-CommandCenterV1Overlay.ps1" -PackageRoot $package -ProjectRoot $target
```

## 3. الربط داخل FastAPI الحالي
في ملف دخول FastAPI الحالي، أضف بعد إنشاء `app` فقط:
```python
from pathlib import Path
from command_center import mount_command_center

mount_command_center(
    app,
    project_root=Path(__file__).resolve().parent,
    ui_prefix='/command-center',
    api_prefix='/api/v1/local-agents',
)
```
لا تنشئ تطبيق FastAPI ثانيًا ولا تضف `uvicorn.run` جديدًا.

## 4. الاختبار
```powershell
python -m unittest tests.test_command_center_read_only
& "$target\scripts\Test-CommandCenterV1Static.ps1" -ProjectRoot $target
```
ثم شغّل اختبارات Lifecycle Closure وSAPF وPack01 الموجودة دون تعديل.

## 5. UAT
افتح `http://127.0.0.1:<port>/command-center` وتحقق من المسارات والشروط الموضحة في `COMMAND_CENTER_V1_UAT.md`.
