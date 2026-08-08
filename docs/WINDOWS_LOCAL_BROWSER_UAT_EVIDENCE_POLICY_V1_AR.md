---
document_id: WINDOWS_LOCAL_BROWSER_UAT_EVIDENCE_POLICY_V1
status: ACTIVE_FOR_AUTHORIZED_V1
---

# سياسة أدلة Windows Local Browser UAT

## تصنيف الدليل

| الملف | الغرض | حالة الاعتماد |
|---|---|---|
| `environment.json` | نسخ الأدوات والـbind وflags الأمان | إلزامي |
| `source_preimage_sha256.json` | مرجع سلامة المصدر قبل التشغيل | إلزامي |
| `health.json` | إثبات safety flags | إلزامي |
| `http_runtime_results.json` | مسارات القراءة والـassets وغياب Set-Cookie | إلزامي |
| `browser_render_capture_manifest.json` + PNG/DOM | rendering حقيقي بمحرك Edge/Chrome | إلزامي ما لم يذكر Skip صراحة |
| `browser_network.har` | شبكات المتصفح الفعلية | إلزامي للقبول الكامل |
| `browser_network_har_summary.json` | تحليل HAR | إلزامي |
| `BROWSER_UAT_RESULT_AR.md` | نتيجة مركزة | إلزامي |
| `*.zip` + `*.sha256.txt` | أرشفة دائمة قابلة للتحقق | إلزامي |

## الحظر

لا تقبل هذه الدفعة أي دليل يدعي:

- نجاح تشغيل نموذج أو Ollama.
- ربط Supabase أو منصة PalWakf.
- صلاحية React للكتابة.
- صلاحية Production.
- صلاحية قاعدة بيانات تشغيلية خارج Worktree.

## الاحتفاظ

تُحفظ الحزمة النهائية تحت:

```text
output/windows_local_browser_uat/<RUN_ID>.zip
```

مع بصمة SHA-256 المجاورة. لا تُحذف حزمة archive بعد المراجعة؛ يمكن حذف Worktree المؤقت فقط.
