# PalWakf Local Agents — Controlled Candidate Timeout Retry V1.0.4

## السبب

أثبتت أدلة V1.0.3 أن `gemma4:latest` لم يكمل طلب Candidate خلال 90 ثانية:

```text
MODEL_PROVIDER_REQUEST_FAILED
type=TimeoutError
HTTP_STATUS=502
MODEL_RUN_PERSISTED=NO
CANDIDATE_PERSISTED=NO
SOURCE_MUTATION=FALSE
```

## استراتيجية V1.0.4

```text
MODEL=qwen2.5:3b
TIMEOUT_SECONDS=180
MAX_OUTPUT_TOKENS=1200
TEMPERATURE=0.0
ATTEMPT_LIMIT=1
AUTOMATIC_RETRY=FALSE
NETWORK=LOOPBACK_ONLY
SOURCE_APPLY=BLOCKED
```

الحزمة مبنية وجاهزة للفحص القبلي. التشغيل الحي يتطلب تفويضًا جديدًا مستقلًا:

```text
AUTHORIZE_LOCAL_AGENTS_GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_LOOPBACK_ONLY_V1
```

## التشغيل

```powershell
Set-ExecutionPolicy -Scope Process Bypass -Force
.\RUN_00_HARNESS_SELF_TEST.ps1
.\RUN_01_PREFLIGHT_AND_CONTRACT_DISCOVERY.ps1
```

بعد تسجيل التفويض الجديد، شغّل:

```powershell
.\RUN_02_EXECUTE_AUTHORIZED_LIVE_PROBE.ps1 `
  -AuthorizationToken "AUTHORIZE_LOCAL_AGENTS_GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_LOOPBACK_ONLY_V1"
```

لا يوجد Retry تلقائي. أي فشل يغلق التنفيذ بعد محاولة واحدة.
