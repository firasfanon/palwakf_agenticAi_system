
# Command Center — إغلاق تراكم مستمعات الأحداث V1

## الهدف
إزالة إعادة ربط مستمعات أحداث الواجهة بعد كل `render()`؛ وهي الحلقة التي سببت تكرار طلبات `system-health` حتى `ERR_INSUFFICIENT_RESOURCES` في Edge.

## التغيير المسموح
ملف واحد فقط: `backend/src/palwakf_local_agents/command_center/static/app.js`.

## الحل
- لا يستدعي `render()` الدالة `wire()`.
- يستخدم التطبيق Event Delegation عبر مستمع click واحد على `document`.
- استخدام `bindUiOnce()` مع حارس `window.__PWF_COMMAND_CENTER_UI_BOUND__`.
- مستمع `popstate` يربط مرة واحدة.

## خارج النطاق
لا Router، لا Store، لا app.py، لا SQLite، لا API، لا تنفيذ نماذج، لا Pilot.
