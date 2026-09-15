from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from palwakf_local_agents.agentic_core_v1.external_skill_admission import (
    ExternalSkillAdmission,
    ExternalSkillAuthorityRequest,
    ExternalSkillSource,
    ExternalSkillStage,
    parse_agent_skill,
    sandbox_evaluate_external_skill,
    scan_skill_bundle,
    sha256_file,
    static_security_scan,
)

REPO_DIRS = {
    "supabase/agent-skills": "agent-skills",
    "obra/superpowers": "superpowers",
    "github/awesome-copilot": "awesome-copilot",
    "anthropics/skills": "skills",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inspection-root", required=True)
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    inspection_root = Path(args.inspection_root)
    inventory = json.loads(Path(args.inventory).read_text(encoding="utf-8-sig"))
    results: list[dict[str, object]] = []

    for item in inventory:
        repository = item["repository"]
        repo_dir = REPO_DIRS[repository]
        repo_root = inspection_root / repo_dir
        skill_path = repo_root / item["path"]
        parsed = parse_agent_skill(skill_path)
        findings = static_security_scan(parsed)
        bundle = scan_skill_bundle(skill_path)
        source_hash = sha256_file(skill_path)
        source_hash_pass = source_hash == item["content_sha256"]
        observed_head = subprocess.check_output(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"], text=True
        ).strip()
        repo_head_pass = observed_head.lower() == item["commit_sha"].lower()

        admission = ExternalSkillAdmission(
            skill_id=parsed.name,
            name=parsed.name,
            description=parsed.description,
            source=ExternalSkillSource(
                repository=repository,
                commit_sha=item["commit_sha"],
                path=item["path"],
                content_sha256=item["content_sha256"],
                license=item["license"],
            ),
            requested=ExternalSkillAuthorityRequest(actions=("read",)),
            stage=ExternalSkillStage.sandbox_only,
            provenance_verified=True,
            security_findings=findings,
            external_execution_authority=False,
            auto_promotion=False,
        )
        sandbox = sandbox_evaluate_external_skill(admission, skill_path)

        decision = (
            "SANDBOX_PASS"
            if (
                sandbox.parser_pass
                and source_hash_pass
                and repo_head_pass
                and sandbox.security_pass
                and not bundle.blocking_findings
                and sandbox.authority_pass
            )
            else "HOLD_REVIEW"
        )
        results.append(
            {
                **item,
                "parsed_name": parsed.name,
                "source_hash_pass": source_hash_pass,
                "repo_head_pass": repo_head_pass,
                "observed_head": observed_head,
                "security_findings": list(findings),
                "bundle_report": bundle.model_dump(mode="json"),
                "bundle_blocking_findings": [
                    finding.model_dump(mode="json")
                    for finding in bundle.blocking_findings
                ],
                "capability_flags": list(bundle.capability_flags),
                "sandbox": sandbox.model_dump(mode="json"),
                "admission_decision": decision,
                "external_execution_authority": False,
                "auto_promotion": False,
            }
        )

    output = {
        "schema": "PALWAKF_EXTERNAL_SKILL_ADMISSION_EVAL_V1",
        "bulk_install": False,
        "external_skill_execution_authority": False,
        "auto_promotion": False,
        "candidate_count": len(results),
        "sandbox_pass_count": sum(
            1 for item in results if item["admission_decision"] == "SANDBOX_PASS"
        ),
        "hold_count": sum(
            1 for item in results if item["admission_decision"] != "SANDBOX_PASS"
        ),
        "candidates": results,
    }
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print(
        json.dumps(
            {
                k: output[k]
                for k in ("candidate_count", "sandbox_pass_count", "hold_count")
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
