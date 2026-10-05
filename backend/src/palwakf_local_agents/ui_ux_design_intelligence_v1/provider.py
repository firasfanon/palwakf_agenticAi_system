from __future__ import annotations

import atexit
import base64
import hashlib
import importlib
import json
import shutil
import sys
import tempfile
import zipfile
from contextlib import contextmanager
from io import BytesIO
from pathlib import Path
from typing import Any, Iterator, Mapping

from .snapshot_blob import (
    PROVIDER_MANIFEST_JSON,
    SNAPSHOT_ARCHIVE_B64,
    SNAPSHOT_ARCHIVE_SHA256,
)

DESIGN_INTELLIGENCE_ID = "PALWAKF_UI_UX_DESIGN_INTELLIGENCE_V1"
PROVIDER_REPOSITORY = "nextlevelbuilder/ui-ux-pro-max-skill"
PROVIDER_PINNED_HEAD = "477bcb28c9812b385cb51a4605ddf30d7b2266e2"
PROVIDER_PINNED_TREE = "0041561a8accf20fcd186de04689c74377db8c16"
PROVIDER_LICENSE = "MIT"

_MATERIALIZED_PROVIDER_ROOT: Path | None = None

_ALLOWED_DOMAINS = frozenset(
    {
        "style", "color", "chart", "landing", "product", "ux",
        "typography", "google-fonts", "icons", "gsap", "react", "web",
    }
)
_ALLOWED_STACKS = frozenset(
    {
        "react", "nextjs", "vue", "svelte", "astro", "swiftui",
        "react-native", "flutter", "nuxtjs", "nuxt-ui", "html-tailwind",
        "shadcn", "jetpack-compose", "threejs", "angular", "laravel",
        "javafx", "wpf", "winui", "avalonia", "uno", "uwp",
    }
)
_ADMITTED_SCRIPT_PATHS = (
    "scripts/core.py",
    "scripts/design_system.py",
    "scripts/reasoning_contract.py",
)
_DORMANT_SNAPSHOT_PATHS = ("scripts/search.py",)
_DENIED_PATH_PREFIXES = ("cli/", ".claude/")
_BANNED_RUNTIME_TOKENS = (
    "subprocess.",
    "os.system",
    "child_process",
    "requests.",
    "httpx.",
    "urllib.request",
    "socket.",
    "shell=true",
    "powershell",
    "cmd.exe",
)

_PALWAKF_IDENTITY_POLICY = {
    "authority": "PALWAKF_PRODUCT_IDENTITY_AND_WORKSPACE_ACCEPTANCE",
    "direction": "RTL",
    "character": "institutional_operational",
    "palette_baseline": "navy_gold",
    "palette_literal_lock": False,
    "provider_palette_authority": False,
    "provider_typography_authority": False,
    "visual_creativity": "BROAD_WITHIN_PRODUCT_IDENTITY_AND_ACCEPTANCE_GATES",
    "execution_authority": "NONE",
}


class ProviderIntegrityError(RuntimeError):
    pass


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_bytes(path.read_bytes())


def _load_manifest() -> dict[str, Any]:
    try:
        payload = json.loads(PROVIDER_MANIFEST_JSON)
    except json.JSONDecodeError as exc:
        raise ProviderIntegrityError("UI_UX_PROVIDER_MANIFEST_UNREADABLE") from exc
    if payload.get("schema_id") != "palwakf.ui_ux_pro_max.snapshot.v1":
        raise ProviderIntegrityError("UI_UX_PROVIDER_MANIFEST_SCHEMA_MISMATCH")
    if payload.get("repository") != PROVIDER_REPOSITORY:
        raise ProviderIntegrityError("UI_UX_PROVIDER_REPOSITORY_MISMATCH")
    if payload.get("pinned_head") != PROVIDER_PINNED_HEAD:
        raise ProviderIntegrityError("UI_UX_PROVIDER_HEAD_MISMATCH")
    if payload.get("pinned_tree") != PROVIDER_PINNED_TREE:
        raise ProviderIntegrityError("UI_UX_PROVIDER_TREE_MISMATCH")
    if payload.get("license") != PROVIDER_LICENSE:
        raise ProviderIntegrityError("UI_UX_PROVIDER_LICENSE_MISMATCH")
    return payload


def _expected_entries() -> dict[str, tuple[int, str]]:
    manifest = _load_manifest()
    entries = manifest.get("files")
    if not isinstance(entries, list) or not entries:
        raise ProviderIntegrityError("UI_UX_PROVIDER_MANIFEST_FILES_INVALID")
    expected: dict[str, tuple[int, str]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise ProviderIntegrityError("UI_UX_PROVIDER_MANIFEST_ENTRY_INVALID")
        relative = str(entry.get("path", "")).replace("\\", "/")
        size = entry.get("size")
        digest = str(entry.get("sha256", "")).lower()
        if (
            not relative
            or relative.startswith("/")
            or ".." in Path(relative).parts
            or not isinstance(size, int)
            or size < 0
            or len(digest) != 64
        ):
            raise ProviderIntegrityError("UI_UX_PROVIDER_MANIFEST_ENTRY_INVALID")
        if relative.startswith(_DENIED_PATH_PREFIXES):
            raise ProviderIntegrityError("UI_UX_PROVIDER_DENIED_PATH_IN_MANIFEST")
        expected[relative] = (size, digest)
    return expected


def _cleanup_materialized_root() -> None:
    global _MATERIALIZED_PROVIDER_ROOT
    root = _MATERIALIZED_PROVIDER_ROOT
    _MATERIALIZED_PROVIDER_ROOT = None
    if root is not None:
        shutil.rmtree(root, ignore_errors=True)


atexit.register(_cleanup_materialized_root)


def _materialize_provider_snapshot() -> Path:
    global _MATERIALIZED_PROVIDER_ROOT
    if _MATERIALIZED_PROVIDER_ROOT is not None and _MATERIALIZED_PROVIDER_ROOT.is_dir():
        return _MATERIALIZED_PROVIDER_ROOT

    try:
        archive = base64.b64decode(SNAPSHOT_ARCHIVE_B64, validate=True)
    except (ValueError, TypeError) as exc:
        raise ProviderIntegrityError("UI_UX_PROVIDER_ARCHIVE_ENCODING_INVALID") from exc
    if _sha256_bytes(archive) != SNAPSHOT_ARCHIVE_SHA256:
        raise ProviderIntegrityError("UI_UX_PROVIDER_ARCHIVE_HASH_MISMATCH")

    expected = _expected_entries()
    root = Path(tempfile.mkdtemp(prefix="palwakf_ui_ux_pro_max_")).resolve()
    try:
        with zipfile.ZipFile(BytesIO(archive), "r") as bundle:
            names = [name.replace("\\", "/") for name in bundle.namelist()]
            if set(names) != set(expected) or len(names) != len(expected):
                raise ProviderIntegrityError("UI_UX_PROVIDER_ARCHIVE_FILESET_MISMATCH")
            for relative in names:
                if relative.startswith("/") or ".." in Path(relative).parts:
                    raise ProviderIntegrityError("UI_UX_PROVIDER_ARCHIVE_PATH_INVALID")
                raw = bundle.read(relative)
                expected_size, expected_hash = expected[relative]
                if len(raw) != expected_size:
                    raise ProviderIntegrityError(
                        f"UI_UX_PROVIDER_ARCHIVE_SIZE_MISMATCH:{relative}"
                    )
                if _sha256_bytes(raw) != expected_hash:
                    raise ProviderIntegrityError(
                        f"UI_UX_PROVIDER_ARCHIVE_ENTRY_HASH_MISMATCH:{relative}"
                    )
                target = (root / Path(relative)).resolve()
                try:
                    target.relative_to(root)
                except ValueError as exc:
                    raise ProviderIntegrityError(
                        "UI_UX_PROVIDER_ARCHIVE_PATH_ESCAPE"
                    ) from exc
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(raw)
        _MATERIALIZED_PROVIDER_ROOT = root
        return root
    except Exception:
        shutil.rmtree(root, ignore_errors=True)
        raise


def _provider_root() -> Path:
    return _materialize_provider_snapshot()


def _provider_file_state(root: Path) -> dict[str, tuple[int, str]]:
    return {
        path.relative_to(root).as_posix(): (path.stat().st_size, _sha256_file(path))
        for path in root.rglob("*")
        if path.is_file()
    }


def verify_provider_snapshot() -> Mapping[str, Any]:
    root = _provider_root()
    expected = _expected_entries()
    actual = _provider_file_state(root)
    if set(actual) != set(expected):
        raise ProviderIntegrityError("UI_UX_PROVIDER_FILESET_MISMATCH")
    for relative, state in actual.items():
        if state != expected[relative]:
            raise ProviderIntegrityError(f"UI_UX_PROVIDER_FILE_MISMATCH:{relative}")

    for relative in _ADMITTED_SCRIPT_PATHS:
        script = root / relative
        if not script.is_file():
            raise ProviderIntegrityError(
                f"UI_UX_PROVIDER_ADMITTED_SCRIPT_MISSING:{relative}"
            )
        lowered = script.read_text(encoding="utf-8").lower().replace(" ", "")
        for token in _BANNED_RUNTIME_TOKENS:
            if token.replace(" ", "") in lowered:
                raise ProviderIntegrityError(
                    f"UI_UX_PROVIDER_RUNTIME_SURFACE_FORBIDDEN:{relative}:{token}"
                )

    return {
        "design_intelligence_id": DESIGN_INTELLIGENCE_ID,
        "repository": PROVIDER_REPOSITORY,
        "pinned_head": PROVIDER_PINNED_HEAD,
        "pinned_tree": PROVIDER_PINNED_TREE,
        "license": PROVIDER_LICENSE,
        "file_count": len(actual),
        "manifest_sha256": _sha256_bytes(PROVIDER_MANIFEST_JSON.encode("utf-8")),
        "archive_sha256": SNAPSHOT_ARCHIVE_SHA256,
        "integrity": "PASS",
        "execution_authority": "NONE",
        "persistence_authority": "NONE",
        "network_authority": "NONE",
        "runtime_materialization": "BOUNDED_EPHEMERAL_TEMP_ONLY",
    }


@contextmanager
def _provider_import_scope() -> Iterator[Path]:
    verify_provider_snapshot()
    root = _provider_root()
    scripts = (root / "scripts").resolve()
    before_path = list(sys.path)
    before_bytecode = sys.dont_write_bytecode
    removed: dict[str, Any] = {}
    module_names = ("core", "design_system", "reasoning_contract")
    try:
        sys.path.insert(0, str(scripts))
        sys.dont_write_bytecode = True
        importlib.invalidate_caches()
        for name in module_names:
            if name in sys.modules:
                removed[name] = sys.modules.pop(name)
        yield root
    finally:
        for name in module_names:
            sys.modules.pop(name, None)
        sys.modules.update(removed)
        sys.path[:] = before_path
        sys.dont_write_bytecode = before_bytecode


def provider_metadata() -> Mapping[str, Any]:
    verified = dict(verify_provider_snapshot())
    manifest = _load_manifest()
    verified.update(
        {
            "skill_json_version": manifest.get("skill_json_version"),
            "cli_package_version": manifest.get("cli_package_version"),
            "admitted_scope": manifest.get("admitted_scope"),
            "identity_policy": dict(_PALWAKF_IDENTITY_POLICY),
        }
    )
    return verified


def provider_runtime_policy_v1() -> Mapping[str, Any]:
    return {
        "schema_id": "palwakf.ui_ux_design_intelligence.policy.v1",
        "design_intelligence_id": DESIGN_INTELLIGENCE_ID,
        "provider": PROVIDER_REPOSITORY,
        "pinned_head": PROVIDER_PINNED_HEAD,
        "pinned_tree": PROVIDER_PINNED_TREE,
        "allowed": (
            "data/**",
            "scripts/core.py",
            "scripts/design_system.py",
            "scripts/reasoning_contract.py",
        ),
        "dormant_snapshot_only": _DORMANT_SNAPSHOT_PATHS,
        "denied": (
            "cli/**",
            ".claude/**",
            "global_install",
            "auto_update",
            "persist",
            "mutating_generators",
            "project_source_write",
            "external_network_action",
        ),
        "advisory_only": True,
        "remote_capability_admitted": False,
        "visual_creativity_policy": "BROAD_WITHIN_PRODUCT_IDENTITY_AND_ACCEPTANCE_GATES",
    }


def _validate_query(query: str) -> str:
    value = str(query or "").strip()
    if not value:
        raise ValueError("UI_UX_QUERY_REQUIRED")
    if len(value) > 1200:
        raise ValueError("UI_UX_QUERY_TOO_LONG")
    return value


def _validate_limit(max_results: int) -> int:
    value = int(max_results)
    if value < 1 or value > 20:
        raise ValueError("UI_UX_MAX_RESULTS_OUT_OF_RANGE")
    return value


def search_domain(
    query: str,
    domain: str,
    max_results: int = 5,
) -> Mapping[str, Any]:
    value = _validate_query(query)
    normalized_domain = str(domain or "").strip()
    if normalized_domain not in _ALLOWED_DOMAINS:
        raise ValueError("UI_UX_DOMAIN_NOT_ADMITTED")
    limit = _validate_limit(max_results)
    before = _provider_file_state(_provider_root())
    with _provider_import_scope():
        core = importlib.import_module("core")
        result = core.search(value, normalized_domain, limit)
    after = _provider_file_state(_provider_root())
    if before != after:
        raise ProviderIntegrityError("UI_UX_PROVIDER_MUTATED_DURING_SEARCH")
    return {
        "provider": provider_metadata(),
        "mode": "READ_ONLY_LOCAL_SEARCH",
        "domain": normalized_domain,
        "query": value,
        "result": result,
        "source_mutation": False,
        "external_action": False,
    }


def search_stack(
    query: str,
    stack: str,
    max_results: int = 5,
) -> Mapping[str, Any]:
    value = _validate_query(query)
    normalized_stack = str(stack or "").strip()
    if normalized_stack not in _ALLOWED_STACKS:
        raise ValueError("UI_UX_STACK_NOT_ADMITTED")
    limit = _validate_limit(max_results)
    before = _provider_file_state(_provider_root())
    with _provider_import_scope():
        core = importlib.import_module("core")
        result = core.search_stack(value, normalized_stack, limit)
    after = _provider_file_state(_provider_root())
    if before != after:
        raise ProviderIntegrityError("UI_UX_PROVIDER_MUTATED_DURING_STACK_SEARCH")
    return {
        "provider": provider_metadata(),
        "mode": "READ_ONLY_LOCAL_STACK_SEARCH",
        "stack": normalized_stack,
        "query": value,
        "result": result,
        "source_mutation": False,
        "external_action": False,
    }


def recommend_design_system(
    query: str,
    *,
    project_name: str = "PalWakf Agentic Console",
    variance: int = 4,
    motion: int = 2,
    density: int = 6,
) -> Mapping[str, Any]:
    value = _validate_query(query)
    for name, setting in (
        ("VARIANCE", variance),
        ("MOTION", motion),
        ("DENSITY", density),
    ):
        if int(setting) < 1 or int(setting) > 10:
            raise ValueError(f"UI_UX_{name}_OUT_OF_RANGE")

    before = _provider_file_state(_provider_root())
    with _provider_import_scope():
        design_system = importlib.import_module("design_system")
        generated = design_system.generate_design_system(
            value,
            project_name,
            "markdown",
            persist=False,
            page=None,
            output_dir=None,
            variance=int(variance),
            motion=int(motion),
            density=int(density),
            force=False,
        )
    after = _provider_file_state(_provider_root())
    if before != after:
        raise ProviderIntegrityError("UI_UX_PROVIDER_MUTATED_DURING_DESIGN_REASONING")
    persistence = generated.get("persistence")
    if persistence not in (None, {}, False):
        raise ProviderIntegrityError("UI_UX_PROVIDER_UNEXPECTED_PERSISTENCE")

    return {
        "schema_id": "palwakf.ui_ux_design_intelligence.recommendation.v1",
        "design_intelligence_id": DESIGN_INTELLIGENCE_ID,
        "provider": provider_metadata(),
        "query": value,
        "project_name": project_name,
        "identity_policy": dict(_PALWAKF_IDENTITY_POLICY),
        "recommendation_authority": "ADVISORY_ONLY",
        "automatic_source_write": False,
        "automatic_dependency_write": False,
        "automatic_palette_adoption": False,
        "automatic_typography_adoption": False,
        "persistence": None,
        "design_system": generated.get("design_system"),
        "text": generated.get("text"),
        "palwakf_acceptance_rules": (
            "PRESERVE_RECOGNIZABLE_RTL_INSTITUTIONAL_OPERATIONAL_CHARACTER",
            "ALLOW_BROAD_VISUAL_EXPLORATION",
            "DO_NOT_TREAT_PROVIDER_OUTPUT_AS_ACCEPTANCE_AUTHORITY",
            "REQUIRE_BROWSER_VISUAL_ACCESSIBILITY_ACCEPTANCE",
        ),
    }


def search_design_intelligence_v1(
    query: str,
    *,
    domain: str | None = None,
    stack: str | None = None,
    max_results: int = 5,
) -> Mapping[str, Any]:
    if domain and stack:
        raise ValueError("UI_UX_DOMAIN_AND_STACK_MUTUALLY_EXCLUSIVE")
    if stack:
        return search_stack(query, stack, max_results)
    if domain is None:
        domain = "ux"
    return search_domain(query, domain, max_results)


recommend_design_system_v1 = recommend_design_system
