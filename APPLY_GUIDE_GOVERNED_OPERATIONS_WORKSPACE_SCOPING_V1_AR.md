# دليل التطبيق — Governed Operations Workspace Scoping V1

**هذه الحزمة Candidate فقط. لا تطبقها قبل تفويض Apply منفصل.**

## المرحلة 1: Syntax + Preflight

```powershell
$target = "C:\Users\DELL\StudioProjects\palwakf_local_agents"
$package = "<EXTRACTED_PACKAGE_ROOT>"

& "$package\scripts\Test-GovernedOperationsWorkspaceScopingV1CandidateSyntax.ps1" -PackageRoot $package

& "$package\scripts\Test-GovernedOperationsWorkspaceScopingV1Preflight.ps1" `
  -ProjectRoot $target `
  -PackageRoot $package
```

احتفظ بقيمة `PREFLIGHT_MANIFEST=...` الناتجة.

## المرحلة 2: WhatIf فقط

```powershell
& "$package\scripts\Install-GovernedOperationsWorkspaceScopingV1.ps1" `
  -ProjectRoot $target `
  -PackageRoot $package `
  -PreflightManifest "<PREFLIGHT_MANIFEST>" `
  -Mode Upgrade `
  -WhatIf
```

## ممنوع في هذه المرحلة
- لا تستخدم `-Apply`.
- لا تشغّل نموذجًا أو Pilot.
- لا تنفذ انتقالات دورة الحياة قبل اعتماد Apply ثم UAT.
