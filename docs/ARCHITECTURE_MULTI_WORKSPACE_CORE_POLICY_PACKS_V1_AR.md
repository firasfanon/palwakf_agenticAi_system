# Multi-Workspace Core + Policy Packs V1

## الغرض
تأسيس Local Agents Core واحد مع مساحات عمل منطقية معزولة وسياسات مستقلة، دون نقل أو دمج بيانات PalWakf أو تفعيل أي تنفيذ.

## الحدود
- هذه الدفعة تعلن Workspaces وPolicy Packs وتوفر Readiness/Observability فقط.
- لا تنشئ state.sqlite أو audit.sqlite داخل أي Workspace خلال التثبيت أو طلبات القراءة الحالية.
- لا تهاجر `audit/governed_operations.sqlite`؛ يبقى Legacy منفصلًا حتى تفويض Migration مستقل.

## مساحات العمل المعلنة
1. `palwakf_government` → `government_strict_v1`
2. `personal_development` → `developer_controlled_v1`
3. `commercial_projects` → `client_isolated_v1`
4. `research_learning` → `research_read_prepare_v1`

## العزل
لا تسمح Core بقراءة أو كتابة أو أدوات أو ذاكرة أو تدقيق مشترك بين مساحات العمل. معرّف Workspace يُتحقق منه ضمن allowlist قبل تكوين أي مسار منطقي.
