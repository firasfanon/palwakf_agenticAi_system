# القلب التشغيلي 6-in-1 — V1

تجمع هذه الدفعة ستة مسارات في شريحة Full-stack واحدة قابلة للفحص:

1. `OPERATIONAL_CORE_VERTICAL_SLICE_V1_NO_EXECUTION`
2. `LOCAL_STATE_STORE_V1_JSONL_PROJECT_STATE`
3. `CODEBASE_SYMBOL_ROUTE_COMPONENT_INDEX_V1_READ_ONLY`
4. `GOVERNED_READ_ONLY_TOOL_RUNTIME_V1`
5. `STANDING_RULES_REGISTRY_V1`
6. `LOCAL_MODEL_RUNTIME_READINESS_GATE_V1`

## الأثر التشغيلي

- تحضير هدف وخطة ومسودات مهام ومراجعتها دون تنفيذ.
- حفظ الحالة محليًا في `runtime_state/operational_core_v1`:
  - `project_state.json`
  - `events.jsonl`
  - `standing_rules.json`
- فهرسة رموز Python ومسارات FastAPI ومكونات React/TypeScript ووثائق Markdown قراءةً فقط.
- استدعاء أدوات قراءة فقط بعقود معلنة.
- فحص وجود Ollama وقائمة النماذج عبر `GET /api/tags` على localhost فقط، دون prompt أو inference.

## الحدود

لا Shell، لا Git، لا Code execution، لا Model inference، لا Pilot، لا Self-Apply، ولا كتابة قاعدة بيانات. الكتابة الوحيدة وقت التشغيل هي حالة محلية محكومة داخل مجلد runtime state.
