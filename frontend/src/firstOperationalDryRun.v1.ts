export const FIRST_OPERATIONAL_DRY_RUN_V1 = {
  id: "FIRST_OPERATIONAL_DRY_RUN_V1_NO_EXECUTION",
  posture: "prepare_only_no_execution",
  path: ["Goal", "Plan", "Skill Path", "Task Drafts", "Review Gate", "Accepted as Plan", "No Execution Proof"],
  persistence: "browser_local_storage_only",
  blocked: ["model", "pilot", "shell", "git", "code_execution", "db_persistence", "self_apply", "autonomous_build"],
};
