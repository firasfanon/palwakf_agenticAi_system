export const PROJECT_CONTINUITY_MEMORY_AND_TASK_BOARD_V1 = {
  id: "PROJECT_CONTINUITY_MEMORY_AND_TASK_BOARD_V1_DESIGN_ONLY",
  route: "/agent-console/project-board",
  posture: "design_only_read_browser_state",
  memoryLayers: ["working_state", "project_board", "checkpoints", "standing_rules", "long_term_memory_future_gate"],
  blocked: ["database_persistence", "chromadb", "model_execution", "pilot_execution", "shell", "git", "code_execution", "self_apply"],
};
