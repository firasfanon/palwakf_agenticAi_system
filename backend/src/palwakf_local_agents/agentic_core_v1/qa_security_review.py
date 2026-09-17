from __future__ import annotations

import ast
import fnmatch
import hashlib
import re
import subprocess
from pathlib import Path

from .contracts import IndependentReviewSpec, RunRequest

_HIGH_RISK_PATTERNS = {
    "PRIVATE_KEY": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "API_TOKEN": re.compile(r"(?:ghp_|github_pat_|sk-)[A-Za-z0-9_-]{16,}"),
    "PASSWORD_LITERAL": re.compile(
        r"(?i)(?:password|passwd|secret|api[_-]?key)\s*=\s*['\"][^'\"]{8,}['\"]"
    ),
    "SHELL_TRUE": re.compile(r"shell\s*=\s*True"),
    "OS_SYSTEM": re.compile(r"\bos\.system\s*\("),
    "DYNAMIC_EVAL": re.compile(r"\b(?:eval|exec)\s*\("),
}


def _git(root: Path, *args: str, text: bool = True) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=text,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"GIT_REVIEW_COMMAND_FAILED:{' '.join(args)}")
    return result.stdout if text else result.stdout.decode("utf-8", errors="replace")


def _matches_any(path: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def _added_lines(patch: str) -> list[str]:
    return [
        line[1:]
        for line in patch.splitlines()
        if line.startswith("+") and not line.startswith("+++")
    ]


def _validate_evidence(spec: IndependentReviewSpec) -> list[str]:
    failures: list[str] = []
    seen_ids: set[str] = set()
    evidence_types: set[str] = set()
    for item in spec.evidence:
        if item.evidence_id in seen_ids:
            failures.append("DUPLICATE_EVIDENCE_ID")
        seen_ids.add(item.evidence_id)
        evidence_types.add(item.evidence_type)
        if item.source_head_sha != spec.head_sha:
            failures.append("EVIDENCE_HEAD_MISMATCH")
        if item.status not in {"PASS", "BASELINE_IDENTICAL"}:
            failures.append("EVIDENCE_NOT_PASSING")
    missing = sorted(set(spec.required_evidence_types) - evidence_types)
    if missing:
        failures.append("REQUIRED_EVIDENCE_MISSING:" + ",".join(missing))
    return failures


def run_independent_review(
    *, project_root: Path, request: RunRequest
) -> dict[str, object]:
    spec = request.review_spec
    if spec is None:
        raise RuntimeError("INDEPENDENT_REVIEW_SPEC_REQUIRED")

    root = project_root.resolve()
    head = _git(root, "rev-parse", "HEAD").strip()
    if head != spec.head_sha:
        raise RuntimeError("REVIEW_HEAD_MISMATCH")

    actual_files = sorted(
        line.strip()
        for line in _git(
            root, "diff", "--name-only", f"{spec.base_sha}..{spec.head_sha}"
        ).splitlines()
        if line.strip()
    )
    expected_files = sorted(spec.expected_changed_files)
    failures: list[str] = []
    if actual_files != expected_files:
        failures.append("CHANGED_FILES_MISMATCH")
    if any(not _matches_any(path, spec.allowed_path_patterns) for path in actual_files):
        failures.append("REVIEW_SCOPE_VIOLATION")

    diff_check = subprocess.run(
        [
            "git",
            "-C",
            str(root),
            "diff",
            "--check",
            f"{spec.base_sha}..{spec.head_sha}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if diff_check.returncode != 0:
        failures.append("GIT_DIFF_CHECK_FAILED")

    syntax_failures: list[str] = []
    for path in actual_files:
        if not path.endswith(".py"):
            continue
        source = _git(root, "show", f"{spec.head_sha}:{path}")
        try:
            ast.parse(source, filename=path)
        except SyntaxError:
            syntax_failures.append(path)
    if syntax_failures:
        failures.append("PYTHON_SYNTAX_FAILURE")

    patch = _git(root, "diff", "--unified=0", f"{spec.base_sha}..{spec.head_sha}")
    patch_sha256 = hashlib.sha256(patch.encode("utf-8")).hexdigest()
    findings: list[dict[str, str]] = []
    for line in _added_lines(patch):
        for finding_type, pattern in _HIGH_RISK_PATTERNS.items():
            if pattern.search(line):
                findings.append(
                    {
                        "type": finding_type,
                        "line_sha256": hashlib.sha256(line.encode()).hexdigest(),
                    }
                )
    if findings:
        failures.append("HIGH_RISK_DIFF_FINDINGS")

    failures.extend(_validate_evidence(spec))
    dimensions = {
        "code_review": not syntax_failures and diff_check.returncode == 0,
        "security_review": not findings,
        "scope_review": actual_files == expected_files
        and all(
            _matches_any(path, spec.allowed_path_patterns) for path in actual_files
        ),
        "regression_review": not any(
            item.status not in {"PASS", "BASELINE_IDENTICAL"} for item in spec.evidence
        ),
        "evidence_review": not _validate_evidence(spec),
    }
    successful = not failures and all(dimensions.values())
    return {
        "provider_id": request.provider_id.value,
        "successful": successful,
        "action_type": "INDEPENDENT_QA_SECURITY_REVIEW",
        "reviewed_files": actual_files,
        "patch_sha256": patch_sha256,
        "review_dimensions": dimensions,
        "findings": findings,
        "observations": [
            {
                "review_mode": "DETERMINISTIC_READ_ONLY",
                "external_scanners": "NOT_INVOKED_UNADMITTED",
                "source_head": spec.head_sha,
                "base_sha": spec.base_sha,
            }
        ],
        "errors": [{"code": failure} for failure in failures],
        "changed_files": [],
        "evidence": [
            {
                "type": "INDEPENDENT_REVIEW_RECEIPT",
                "patch_sha256": patch_sha256,
                "reviewed_file_count": len(actual_files),
            }
        ],
        "process_success": True,
        "policy_success": not failures,
        "tool_execution_success": True,
        "objective_success": successful,
        "postcondition_success": successful,
        "tool_call_observed": True,
    }
