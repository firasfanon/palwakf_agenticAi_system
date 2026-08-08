# Error Record — Human Review & Archive Closure

| معرف | السبب | ما فشل | الحل | آخر Baseline مستقر |
|---|---|---|---|---|
| PLC_REVB_RECURSIVE_DESCENDANT_COPY | `Copy-Item` من temp root إلى child root | Evals Rev B علقت بسبب `bad\\bad\\...` recursion | Rev C نقل fixture السلبي إلى sibling root وأضاف containment guard | Lifecycle Closure Rev C accepted |
| PLC_REVC_EXTERNAL_WRAPPER_EXITCODE_EMPTY | Process wrapper أعاد ExitCode فارغًا | Harness أصدر false failure رغم أن stdout أثبت نجاح 6/6 | اعتبار stdout الحتمي مصدرًا مكملًا، وعدم اعتبار ExitCode فارغًا فشلًا منفردًا | Lifecycle Closure Rev C accepted |
| TASK_STATUS_DRIFT_AFTER_EXECUTION | المهمة القديمة بقيت Approved بعد اكتمال Pilot | منع one-pilot-at-a-time من التقدم | Human Review Decision ثم Archive المعتمد ثم Active State check | Human Review Archive Closure accepted |

## حظر ثابت
لا تعالج drift أو archive بتعديل JSON يدويًا. استخدم مسار Lifecycle Closure فقط.
