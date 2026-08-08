# MEGA_BATCH_LOCAL_AGENTS_CODEBASE_UNDERSTANDING_READ_MODEL_V1_DESIGN_ONLY

## الغرض

هذه الدفعة تثبت طبقة **Codebase Understanding Read Model** كتصميم وقراءة فقط فوق `Project Reader V1` المقبول.

المقصود ليس تشغيل RAG فعلي الآن، بل رسم خريطة انتقال محكومة من قارئ مشروع بسيط إلى فهم هندسي للمستودع البرمجي.

## ما تضيفه

1. لوحة داخل `/agent-console/projects` تعرض طبقات فهم المشروع.
2. لوحة داخل `/agent-console/diagnostics` تعرض نفس النموذج ضمن التشخيص.
3. عقد JSON يصف طبقات القراءة والحدود الصلبة.
4. هذا الدليل كمرجع Backend/Frontend لاحق.

## طبقات القراءة المقترحة

| الطبقة | الحالة | المصدر | المخرج |
|---|---|---|---|
| Repository Surface Map | current | Project Reader V1 | allowed roots + key files + route matrix |
| Frontend Component Index | design_only | frontend/src | components/pages/routes لاحقًا |
| Backend Route Index | design_only | backend/src | FastAPI endpoints/contracts لاحقًا |
| Tool Contract Index | design_only | tool registry/backend contracts | حدود الأدوات وعلاقة المساعد بها |
| Agent Registry Index | design_only | agents/registry*.yaml | هوية المساعدين وقدراتهم |
| Governance Docs Index | design_only | docs/*.md | قرارات الحوكمة ونقاط القبول |
| Vector Codebase RAG | future | ChromaDB/LanceDB/Qdrant | مؤجل |
| Agent Coding / Self Apply | blocked | Shell/Git/Code execution | محظور |

## الحدود

```text
NO_BACKEND_SOURCE_MUTATION
NO_DATABASE_WRITE
NO_MODEL_EXECUTION
NO_PILOT_EXECUTION
NO_SHELL
NO_GIT
NO_CODE_EXECUTION
NO_VECTOR_DB
NO_EMBEDDINGS
NO_LANGGRAPH
NO_WEB_SEARCH
NO_PLATFORM_MUTATION
```

## لماذا design-only الآن؟

المحادثة الخارجية التي تمت مراجعتها تقترح أدوات ثقيلة مثل Tree-sitter وChromaDB وLangGraph. هذه أدوات صحيحة على المدى الطويل، لكنها لا تدخل الآن لأن المرحلة الحالية ما زالت في مسار prepare/read-only.

## الدفعة التالية المحتملة

بعد قبول هذه الدفعة بصريًا، يمكن فتح واحدة من التالي:

```text
MEGA_BATCH_LOCAL_AGENTS_CODEBASE_SYMBOL_ROUTE_COMPONENT_INDEX_V1_READ_ONLY
```

أو:

```text
MEGA_BATCH_LOCAL_AGENTS_DOCUMENT_READER_V1_READ_ONLY_WORKSPACE_SCOPED
```

الأولى تعمق فهم الكود، والثانية تضيف قراءة مستندات محكومة.
