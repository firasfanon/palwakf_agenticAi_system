# Session Handoff — Structured Analysis Payload Foundation V1 Candidate

## نقطة الاستئناف
```text
PROJECT_ROOT=C:\Users\DELL\StudioProjects\palwakf_local_agents
LAST_ACCEPTED_BASELINE=PALWAKF_LOCAL_AGENTS_ACCEPTED_BASELINE_2026_06_27
CURRENT_CANDIDATE=LOCAL_AGENT_STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1
CANDIDATE_STATUS=PREPARED_NOT_APPLIED
```

## ما تم بناؤه
1. Contract JSON مستقل لـ`knowledge_researcher`.
2. Contract JSON مستقل لـ`documentation_handoff`.
3. Validator مستقل بحدود حجم، JSON صارم، مفاتيح مضبوطة، Evidence-ID allowlist، وhost-owned envelope.
4. Runner مستقل للمخرج المنظم، لا يغير Core Runner أو Gateway أو عقد 11 سطرًا.
5. Profiles/Charters/Templates/Evals.
6. Installer بحفظ Registry backup قبل إضافة skill وحيدة: `documentation_handoff`.
7. Error Record لتعارض توثيق V1.3 في الأرشيف.

## القرارات
- لا تعديل في Core Runtime أو `MODEL_OUTPUT_CONTRACT_V1.json`.
- لا تعديل Gateway أو Runner المجمد.
- `knowledge_researcher` يستعمل skill موجودة: `knowledge_source_review`.
- `documentation_handoff` يحتاج admission ضيق للـskill المطابق لاسمه، دون أي صلاحية كتابة أو رفع Autonomy.
- الناتج يبقى `PENDING_HUMAN_REVIEW`؛ لا memory أو baseline أو action.

## بوابات لازمة
1. Package Syntax Gate.
2. Pack01 baseline recheck: preflight/static/evals.
3. Candidate preflight.
4. WhatIf.
5. Apply.
6. Candidate static test.
7. Candidate deterministic evals.

## ما لم ينفذ
- لم يجر تشغيل PowerShell على جهاز Windows.
- لم يطبق Installer.
- لم يشغل Ollama.
- لم ينشئ Pilot task.
- لم ينقل Task إلى Approved.
- لم يعدل منصة أو DB أو Git أو Deployment أو Secrets أو Memory.

## الدليل المطلوب بعد التطبيق
اجمع ملفي output فقط:
- آخر `output\evals\STRUCTURED_ANALYSIS_PAYLOAD_FOUNDATION_V1_EVAL_REPORT_*.json`
- console transcript يثبت كل بوابات PASS.
