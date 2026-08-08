# Decision Record Contract V1

A review record is stored under `audit/human_reviews/` and contains task/run/manifest identities, artifact hashes, verification results, reviewer identity, reason, decision, and `review_scope=READ_ONLY_PILOT_RUN_REVIEW_ONLY`.

A review record must never grant platform authority, database access, write capability, release permission, memory promotion, or an additional model run.
