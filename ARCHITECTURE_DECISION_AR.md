# قرار معماري — React TypeScript Frontend Foundation V1

## لماذا هذا الشكل؟

النظام القائم يملك أربع واجهات Static منفصلة. هذه الدفعة لا تحذفها ولا تستبدلها مباشرة. تضيف تطبيق React مستقلًا في `frontend/` وتُفعّل مساره فقط عند توفر مخرجات Vite المبنية.

## المسارات

- React runtime: `/agent-console`
- Legacy fallback: `/command-center`, `/operations`, `/local-agents`, `/workspaces`

## العقد

1. `frontend/` مصدر مستقل.
2. FastAPI يركّب `dist/assets` فقط إن كانت `dist/index.html` موجودة.
3. لا بناء ولا تنزيل حزم ضمن Apply.
4. بعد مصدر React، يتحول التطوير إلى Vertical Slices: UI + API + AuthZ + Audit + UAT.
