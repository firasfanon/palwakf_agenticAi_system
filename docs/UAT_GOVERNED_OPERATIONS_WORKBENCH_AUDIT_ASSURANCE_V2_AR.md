# UAT

1. Desktop + mobile browser rendering for all Workbench views.
2. Controlled local lifecycle: draft → inbox → under_review → approved, with required evidence.
3. Negative checks: stale expected_version gives 409; approval without required evidence gives 409; execute/dispatch gives 404.
4. Verify task and global audit chain return PASS.
5. Verify no model, Pilot, platform, external DB, Git, deployment, secrets, or memory activity.
