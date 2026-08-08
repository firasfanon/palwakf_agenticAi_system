# سجل قرار — إغلاق التفويض قبل React Write

## القرار

```text
NO_REACT_WRITE_CONTROL = ACTIVE
```

## الأساس

واجهة React الحالية مصدر قراءة فقط. توجد مسارات كتابة مختلفة النضج؛ بعض المسارات تعتمد نموذج actor/scope داخل `governed_capability_foundation`، بينما لا يُثبت مسار التفويض الموحد في كل Legacy write route عبر التوقيع أو evidence المتاح.

## شروط إلغاء الحظر

لكل مسار كتابة يراد استهلاكه من React:

1. مصدر هوية Actor محدد ومثبت.
2. فحص Workspace Scope مفروض خادميًا.
3. فحص Commercial Client Scope عند `commercial_projects`.
4. Default-deny واضح عند غياب أو فشل أي قيد.
5. Contract request/response/error code.
6. Audit event + evidence reference.
7. Negative UAT: missing actor, wrong workspace, wrong client, forged client_id, CSRF/session policy.
8. Browser proof يثبت أن React لا يرسل Tokens أو Cookies غير مقصودة.

لا يكفي وجود endpoint أو نجاح طلب إيجابي واحد.
