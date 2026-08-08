# Payload Validation and Host Envelope Policy V1

## ملكية المخرجات
النموذج يرسل JSON واحدًا فقط وفق Schema الدور. المضيف هو وحده الذي ينشئ:
- `envelope_id`
- `run_id`
- `task_id`
- `agent_id`
- `evidence_manifest_id`
- `validated_at_utc`
- `validation_result`
- حدود `STRUCTURED_ANALYSIS_PAYLOAD_START/END`

## شروط القبول
1. JSON object واحد فقط، دون Markdown أو code fences.
2. لا مفاتيح إضافية ولا حقول host-owned من النموذج.
3. الحد الأقصى لحجم المخرج: 12,288 bytes UTF-8.
4. حقول ثابتة:
   - `schema_version=1.0.0`
   - `analysis_status=PENDING_HUMAN_REVIEW`
   - `recommended_next_step=HUMAN_REVIEW_REQUIRED`
5. كل Fact وكل Handoff Section يحمل Evidence IDs من Manifest الحالي فقط.
6. `knowledge_researcher` يضيف `source_assessments` بحالة `REFERENCE_CONTENT_ONLY`.
7. `documentation_handoff` يضيف على الأقل `CURRENT_STATE` و`RESUMPTION_POINT` مع أدلة.
8. أي رفض ينتج Raw artifact وتقريرًا فقط؛ لا يتم إنشاء Canonical envelope.

## أثر الحوكمة
لا يثبت الـPayload حالة حية، ولا يعتمد مصدرًا، ولا يغيّر Task أو Memory أو Baseline أو منصة.
