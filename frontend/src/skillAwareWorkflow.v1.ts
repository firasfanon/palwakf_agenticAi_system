export const SKILL_AWARE_WORKFLOW_V1 = {
  mode: "prepare-only",
  path: ["spec", "plan", "build", "verify", "review", "ship"],
  execution: "blocked",
  buildAuto: "blocked",
  npx: "blocked",
  git: "blocked"
} as const;
