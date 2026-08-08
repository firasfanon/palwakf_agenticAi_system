# Backend المحلي — الحالة في Foundation V2

المجلد يحتوي scaffold قديم لواجهة محلية. لا يعد هذا Backend بوابة أدوات أو مشغّل وكلاء آمنًا بعد.

قبل تشغيله أو توسيعه يجب بناء:
- مصادقة تشغيل محلية أو owner session.
- Task Run validation against V2 schemas.
- Agent / Skill / Tool allowlist enforcement.
- SQLite audit schema.
- redaction and data-classification controls.
- prompt injection inspection path.
- no-network-write default and safe error handling.

لا يشغّل هذا المسار Ollama تلقائيًا ولا يمنح DB أو Git أو Deployment access.
