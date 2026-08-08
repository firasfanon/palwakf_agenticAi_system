# Guide Update Snippet — PALWAKF_PLATFORM_COMPREHENSIVE_GUIDE.md
## Local Agents / Evidence Runner

- تم اعتماد `HAR Filename Reconciliation V1` بعد تطبيق محلي ناجح وStatic Gate ناجح.
- يجب على Runner قبول `browser_network.har` كاسم أساسي.
- إذا غاب الاسم الأساسي ووجد ملف HAR وحيد في جذر Evidence Root، يجب تسويته وتسجيل القرار.
- وجود أكثر من ملف HAR بديل يجب أن يفشل صراحة باسم `HAR_FILENAME_AMBIGUOUS`.
- هذا الإصلاح لا يغير عقد التشغيل: React يبقى `GET_ONLY` و`credentials: "omit"`، ولا React write ولا Model/Pilot أو Database/Platform mutation.
