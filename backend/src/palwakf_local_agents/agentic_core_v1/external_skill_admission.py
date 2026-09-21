from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .runtime import AuthorityError


class ExternalSkillStage(StrEnum):
    quarantined = "QUARANTINED"
    discovered = "DISCOVERED"
    source_verified = "SOURCE_VERIFIED"
    license_verified = "LICENSE_VERIFIED"
    security_reviewed = "SECURITY_REVIEWED"
    sandbox_only = "SANDBOX_ONLY"
    project_proven = "PROJECT_PROVEN"
    cross_project_candidate = "CROSS_PROJECT_CANDIDATE"
    canonical_approved = "CANONICAL_APPROVED"
    hold = "HOLD"
    rejected = "REJECTED"
    revoked = "REVOKED"


class ExternalSkillSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    repository: str = Field(pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$")
    commit_sha: str = Field(pattern=r"^[0-9a-fA-F]{40}$")
    path: str = Field(min_length=1, max_length=500)
    content_sha256: str = Field(pattern=r"^[0-9a-fA-F]{64}$")
    license: str = Field(min_length=1, max_length=160)


class ExternalSkillAuthorityRequest(BaseModel):
    actions: tuple[str, ...] = ()
    tools: tuple[str, ...] = ()
    filesystem: tuple[str, ...] = ()
    network: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    database: tuple[str, ...] = ()
    production: tuple[str, ...] = ()


class ExternalSkillAdmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(min_length=3, max_length=160)
    name: str = Field(min_length=2, max_length=240)
    description: str = Field(min_length=1, max_length=4000)
    source: ExternalSkillSource
    requested: ExternalSkillAuthorityRequest = Field(
        default_factory=ExternalSkillAuthorityRequest
    )
    stage: ExternalSkillStage = ExternalSkillStage.quarantined
    provenance_verified: bool = False
    security_findings: tuple[str, ...] = ()
    eval_passed: bool = False
    regression_passed: bool = False
    mind_review_ref: str | None = None
    workspace_decision_ref: str | None = None
    external_execution_authority: bool = False
    auto_promotion: bool = False


class SandboxEvalResult(BaseModel):
    skill_id: str
    parser_pass: bool
    source_hash_pass: bool
    security_pass: bool
    authority_pass: bool
    baseline_score: int
    skill_score: int
    changed_files: tuple[str, ...] = ()
    execution_performed: bool = False


@dataclass(frozen=True)
class ParsedAgentSkill:
    name: str
    description: str
    body: str


_SECURITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "SELF_AUTHORIZATION_DIRECTIVE",
        re.compile(r"(?i)self[-_ ]?authoriz|ignore .*authority|bypass .*approval"),
    ),
    (
        "SECRET_EXFILTRATION_DIRECTIVE",
        re.compile(
            r"(?i)(exfiltrat|upload|send).{0,40}(secret|token|credential|\.env)"
        ),
    ),
    (
        "DESTRUCTIVE_COMMAND",
        re.compile(
            r"(?i)(rm\s+-rf|git\s+push\s+--force|drop\s+database|format\s+[a-z]:)"
        ),
    ),
)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def parse_agent_skill(path: Path) -> ParsedAgentSkill:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("AGENT_SKILL_FRONTMATTER_REQUIRED")
    end = text.find("\n---\n", 4)
    if end < 0:
        raise ValueError("AGENT_SKILL_FRONTMATTER_INVALID")
    frontmatter = text[4:end]
    values: dict[str, str] = {}
    for raw in frontmatter.splitlines():
        if ":" not in raw:
            continue
        key, value = raw.split(":", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    name = values.get("name", "").strip()
    description = values.get("description", "").strip()
    if not name or not description:
        raise ValueError("AGENT_SKILL_NAME_DESCRIPTION_REQUIRED")
    return ParsedAgentSkill(name=name, description=description, body=text[end + 5 :])


def static_security_scan(parsed: ParsedAgentSkill) -> tuple[str, ...]:
    findings: list[str] = []
    for finding_id, pattern in _SECURITY_PATTERNS:
        if pattern.search(parsed.body):
            findings.append(finding_id)
    return tuple(findings)


def assert_external_skill_loadable(admission: ExternalSkillAdmission) -> None:
    if admission.stage not in {
        ExternalSkillStage.project_proven,
        ExternalSkillStage.cross_project_candidate,
        ExternalSkillStage.canonical_approved,
    }:
        raise AuthorityError("EXTERNAL_SKILL_NOT_ADMITTED")
    if not admission.provenance_verified:
        raise AuthorityError("EXTERNAL_SKILL_PROVENANCE_NOT_VERIFIED")
    if admission.security_findings:
        raise AuthorityError("EXTERNAL_SKILL_SECURITY_FINDINGS_OPEN")
    if not admission.eval_passed or not admission.regression_passed:
        raise AuthorityError("EXTERNAL_SKILL_EVAL_REGRESSION_REQUIRED")
    if not admission.mind_review_ref or not admission.workspace_decision_ref:
        raise AuthorityError("EXTERNAL_SKILL_REVIEW_DECISION_REQUIRED")
    if admission.external_execution_authority:
        raise AuthorityError("EXTERNAL_SKILL_MAY_NOT_SELF_AUTHORIZE")
    if admission.auto_promotion:
        raise AuthorityError("EXTERNAL_SKILL_AUTO_PROMOTION_FORBIDDEN")


def authority_intersection(
    requested: tuple[str, ...],
    *layers: tuple[str, ...],
) -> tuple[str, ...]:
    if not layers:
        raise AuthorityError("AUTHORITY_LAYER_REQUIRED")
    allowed = set(requested)
    for layer in layers:
        allowed &= set(layer)
    return tuple(item for item in requested if item in allowed)


def sandbox_evaluate_external_skill(
    admission: ExternalSkillAdmission,
    skill_path: Path,
) -> SandboxEvalResult:
    parsed = parse_agent_skill(skill_path)
    source_hash_pass = (
        sha256_file(skill_path).lower() == admission.source.content_sha256.lower()
    )
    findings = static_security_scan(parsed)
    authority_pass = (
        admission.external_execution_authority is False
        and admission.auto_promotion is False
    )
    parser_pass = parsed.name == admission.name
    security_pass = not findings
    baseline_score = 1
    skill_score = sum((parser_pass, source_hash_pass, security_pass, authority_pass))
    return SandboxEvalResult(
        skill_id=admission.skill_id,
        parser_pass=parser_pass,
        source_hash_pass=source_hash_pass,
        security_pass=security_pass,
        authority_pass=authority_pass,
        baseline_score=baseline_score,
        skill_score=skill_score,
    )


class BundleFinding(BaseModel):
    finding_id: str
    severity: str
    path: str
    detail: str


class SkillBundleReport(BaseModel):
    root: str
    file_count: int
    total_bytes: int
    executable_file_count: int
    manifest_sha256: str
    capability_flags: tuple[str, ...] = ()
    findings: tuple[BundleFinding, ...] = ()

    @property
    def blocking_findings(self) -> tuple[BundleFinding, ...]:
        return tuple(
            item for item in self.findings if item.severity in {"HIGH", "CRITICAL"}
        )


_BUNDLE_BLOCKING_PATTERNS: tuple[tuple[str, str, re.Pattern[str]], ...] = (
    (
        "SELF_AUTHORIZATION_DIRECTIVE",
        "CRITICAL",
        re.compile(r"(?i)self[-_ ]?authoriz|ignore .*authority|bypass .*approval"),
    ),
    (
        "SECRET_EXFILTRATION_DIRECTIVE",
        "CRITICAL",
        re.compile(
            r"(?i)(exfiltrat|upload|send).{0,50}(secret|token|credential|\.env)"
        ),
    ),
    (
        "DESTRUCTIVE_COMMAND",
        "HIGH",
        re.compile(
            r"(?i)(rm\s+-rf\s+/|git\s+push\s+--force|drop\s+database|format\s+[a-z]:)"
        ),
    ),
)

_BUNDLE_CAPABILITY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "NETWORK_ACCESS",
        re.compile(
            r"(?i)\b(curl|wget|invoke-webrequest|requests\.|httpx\.|fetch\s*\()"
        ),
    ),
    (
        "PROCESS_EXECUTION",
        re.compile(
            r"(?i)\b(subprocess\.|os\.system|child_process|powershell|bash\s+-c|cmd\.exe)"
        ),
    ),
    (
        "GIT_MUTATION",
        re.compile(
            r"(?i)\bgit\s+(push|commit|checkout|switch|merge|rebase|reset)\b|\bgh\s+(pr|repo|issue)\b"
        ),
    ),
    (
        "DATABASE_MUTATION",
        re.compile(
            r"(?i)\b(insert|update|delete|alter|create|drop)\s+(table|schema|database|policy|function)\b"
        ),
    ),
    (
        "SECRET_ACCESS",
        re.compile(r"(?i)(\.env|api[_ -]?key|access[_ -]?token|secret|credential)"),
    ),
    (
        "PRODUCTION_DEPLOYMENT",
        re.compile(r"(?i)\b(deploy|production|release|publish)\b"),
    ),
)

_EXECUTABLE_SUFFIXES = frozenset(
    {
        ".py",
        ".sh",
        ".ps1",
        ".bat",
        ".cmd",
        ".js",
        ".ts",
        ".mjs",
        ".cjs",
        ".rb",
        ".pl",
    }
)


def scan_skill_bundle(skill_path: Path) -> SkillBundleReport:
    root = skill_path.parent.resolve()
    manifest: list[str] = []
    findings: list[BundleFinding] = []
    capability_flags: set[str] = set()
    total_bytes = 0
    executable_count = 0
    file_count = 0

    for candidate in sorted(root.rglob("*"), key=lambda item: item.as_posix()):
        if candidate.is_dir():
            continue
        relative = candidate.relative_to(root).as_posix()
        if candidate.is_symlink():
            target = candidate.resolve()
            outside = not _is_path_within(target, root)
            findings.append(
                BundleFinding(
                    finding_id="BUNDLE_SYMLINK_OUTSIDE_ROOT"
                    if outside
                    else "BUNDLE_SYMLINK_PRESENT",
                    severity="CRITICAL" if outside else "MEDIUM",
                    path=relative,
                    detail=str(target),
                )
            )
            continue
        if not candidate.is_file():
            continue
        file_count += 1
        size = candidate.stat().st_size
        total_bytes += size
        if candidate.suffix.lower() in _EXECUTABLE_SUFFIXES:
            executable_count += 1
        raw = candidate.read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        manifest.append(f"{relative}\0{digest}\0{size}")
        if size > 1_000_000:
            continue
        text = raw.decode("utf-8", errors="ignore")
        for finding_id, severity, pattern in _BUNDLE_BLOCKING_PATTERNS:
            if pattern.search(text):
                instruction_bearing = (
                    relative == "SKILL.md"
                    or candidate.suffix.lower() in _EXECUTABLE_SUFFIXES
                )
                findings.append(
                    BundleFinding(
                        finding_id=finding_id,
                        severity=severity if instruction_bearing else "MEDIUM",
                        path=relative,
                        detail=(
                            "Instruction-bearing static security pattern matched."
                            if instruction_bearing
                            else (
                                "Reference text mentions a sensitive operation; "
                                "adaptation review required."
                            )
                        ),
                    )
                )
        for capability, pattern in _BUNDLE_CAPABILITY_PATTERNS:
            if pattern.search(text):
                capability_flags.add(capability)

    manifest_sha = hashlib.sha256("\n".join(manifest).encode("utf-8")).hexdigest()
    return SkillBundleReport(
        root=str(root),
        file_count=file_count,
        total_bytes=total_bytes,
        executable_file_count=executable_count,
        manifest_sha256=manifest_sha,
        capability_flags=tuple(sorted(capability_flags)),
        findings=tuple(findings),
    )


def _is_path_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False
