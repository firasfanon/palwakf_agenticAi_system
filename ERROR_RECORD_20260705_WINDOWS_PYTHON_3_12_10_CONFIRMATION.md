# Error Record — 2026-07-05

## Non-blocking warnings

### FastAPI startup event deprecation
- السبب: استخدام `@app.on_event("startup")`.
- الأثر: 54 تحذيرًا تقريبًا ضمن تشغيل الاختبارات.
- ما فشل: لا شيء؛ الاختبارات نجحت.
- الحل المقترح: ترحيل لاحق إلى FastAPI lifespan handlers.
- آخر baseline مستقر: WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED.

### Starlette/httpx deprecation
- السبب: تحذير توافق TestClient.
- الأثر: تحذير واحد.
- ما فشل: لا شيء؛ الاختبارات نجحت.
- الحل المقترح: مراجعة pinning/compatibility للحزم في دفعة Dependencies مستقلة.
- آخر baseline مستقر: WINDOWS_PYTHON_3_12_10_CONFIRMATION_ACCEPTED.
