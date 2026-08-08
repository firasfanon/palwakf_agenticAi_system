# Error Record — حزمة أول Probe حي

## E001 — DNS داخل Self-Test المعزول

```text
CAUSE=Self-test used example.com to prove external-network blocking, while the build environment has no DNS.
FAILED_COMPONENT=HARNESS_SELF_TEST_ONLY
SOURCE_OR_MODEL_MUTATION=NONE
FIX=Use literal non-loopback IP 8.8.8.8 so the guard is tested without DNS.
RESULT=PASS
```

## E002 — أولوية قيم استعادة الإعدادات

```text
CAUSE=Temporary provider aliases could override original settings during restore payload construction.
FAILED_COMPONENT=STATIC_REVIEW_BEFORE_RELEASE
LIVE_RUNTIME_REACHED=NO
FIX=Original settings now override temporary aliases only in restore mode.
RESULT=PASS_MOCK_VERIFIED
```

## E003 — احتمال تصادم اسم Evidence

```text
CAUSE=Preflight and live run could start within the same second.
FAILED_COMPONENT=STATIC_REVIEW_BEFORE_RELEASE
FIX=Evidence directory timestamp includes microseconds.
RESULT=PASS
```

## آخر Baseline مستقر

```text
GOVERNED_CODING_MODEL_PROVIDER_AND_CANDIDATE_GENERATION_V1_ACCEPTED_20260719
```

## E004 — فشل ربط حقول OpenAPI الحاكمة في V1.0.1

```text
CAUSE=semantic_values lacked exact normalized aliases for mandatory human authority, confirmation, goal, and candidate fields.
FAILED_COMPONENT=PREFLIGHT_ONLY_REQUEST_BODY_CONSTRUCTION
LIVE_MODEL_CALL=NOT_EXECUTED
SOURCE_MUTATION=FALSE
FIX=Add exact schema aliases and regression tests for settings/probe/generate request bodies.
RESULT=PASS_STATIC_AND_MOCK_VERIFIED_IN_V1_0_2
```

## E005 — النموذج الافتراضي غير مثبت محليًا

```text
CAUSE=V1.0.1 defaulted to qwen3-coder:latest, while the supplied Ollama inventory did not contain it.
RISK=Live probe would fail after contract repair; :cloud alternatives would violate loopback-only sovereignty.
FIX=Default to locally installed gemma4:latest and add /api/tags local-install plus remote-model rejection gate.
RESULT=PASS_MOCK_VERIFIED_IN_V1_0_2
```


## E006 — False Negative لاستجابة Provider Probe في V1.0.2

```text
EVIDENCE=POST_PROVIDER_PROBE.json
HTTP_STATUS=200
RESULT=PROBE_PASS
LOOPBACK_ONLY=TRUE
PROVIDER_MODE=ollama
SECRET_VALUE_RETURNED=FALSE
CAUSE=Harness accepted only exact generic PASS tokens and did not accept composite PROBE_PASS.
IMPACT=Candidate generation was not invoked; no model run occurred.
FIX=Exact provider-probe gate plus composite positive-status recognition.
RESULT=PASS_ACTUAL_CONTRACT_MOCK_VERIFIED_IN_V1_0_3
```

## E007 — تلوث Restore بقيم metadata في V1.0.2

```text
EVIDENCE=POST_SETTINGS_RESTORE.json
HTTP_STATUS=422
INVALID_VALUES=mode:dashboard_json,max_output_tokens:dashboard_json,timeout_seconds:dashboard_json
CAUSE=Recursive flatten allowed nested sources metadata to overwrite operational settings.
FIX=Use direct top-level operational settings only; ignore sources.*; verify restored settings by GET.
RESULT=PASS_RESTORE_BRANCH_MOCK_VERIFIED_IN_V1_0_3
```

## E008 — فشل حزمة Recovery V1.0.2

```text
ERROR=RECOVERY_PROVIDER_BASE_URL_SCHEME_BLOCKED
CAUSE=The same recursive metadata precedence selected dashboard_json as base_url.
CURRENT_SETTINGS_READ_ONLY=ORIGINAL_OPERATIONAL_STATE_CONFIRMED
ADDITIONAL_RECOVERY_REQUIRED=NO
RESULT=CLOSED_BY_EVIDENCE
```
