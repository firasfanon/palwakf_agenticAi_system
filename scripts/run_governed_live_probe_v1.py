#!/usr/bin/env python3
"""Governed loopback-only coding-model probe and isolated candidate UAT.

Standard-library only. It never invokes shell/git/database/source-apply operations.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import ipaddress
import json
import os
import pathlib
import re
import socket
import sys
import traceback
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

AUTHORIZATION_TOKEN = "AUTHORIZE_LOCAL_AGENTS_GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_LOOPBACK_ONLY_V1"
PROMPT_VERSION = "PALWAKF_LOCAL_AGENTS_GOVERNED_MODEL_TIMEOUT_RETRY_PROMPT_V1"
TASK_ID = "GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_V1"
CONTRACT = "READ_ONLY_DEVELOPMENT_DIAGNOSTIC_ENDPOINT_V1"
HARNESS_VERSION = "1.0.4"

API_PATHS = {
    "health": "/api/v1/operational-core/coding-model/health",
    "contract": "/api/v1/operational-core/coding-model/contract",
    "providers": "/api/v1/operational-core/coding-model/providers",
    "settings": "/api/v1/operational-core/coding-model/settings",
    "probe": "/api/v1/operational-core/coding-model/providers/probe",
    "runs": "/api/v1/operational-core/coding-model/runs",
    "runs_latest": "/api/v1/operational-core/coding-model/runs/latest",
    "candidates": "/api/v1/operational-core/coding-model/candidates",
    "candidates_latest": "/api/v1/operational-core/coding-model/candidates/latest",
    "generate": "/api/v1/operational-core/coding-model/candidates/generate",
}

SOURCE_ROOTS = (
    "backend/src",
    "frontend/src",
)
SOURCE_SINGLE_FILES = (
    "backend/pyproject.toml",
    "backend/requirements.txt",
    "frontend/package.json",
    "frontend/package-lock.json",
    "frontend/tsconfig.json",
    "frontend/vite.config.ts",
)
EXCLUDED_DIRS = {"__pycache__", "node_modules", "dist", "build", ".git", ".idea", ".venv", "venv"}
REDACT_RE = re.compile(r"api.?key|secret|password|bearer|credential", re.I)


class BlockRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[override]
        raise RuntimeError(f"REDIRECT_BLOCKED:{code}:{newurl}")


class Evidence:
    def __init__(self, root: pathlib.Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=False)
        self.events: list[dict[str, Any]] = []

    def event(self, name: str, status: str, **details: Any) -> None:
        row = {
            "time_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
            "name": name,
            "status": status,
            **details,
        }
        self.events.append(row)
        print(f"{name}={status}")

    def write_json(self, name: str, value: Any) -> None:
        (self.root / name).write_text(
            json.dumps(redact(value), ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def finalize(self, summary: dict[str, Any]) -> None:
        self.write_json("EVENTS.json", self.events)
        self.write_json("FINAL_STATUS.json", summary)
        lines = [f"{k}={v}" for k, v in summary.items() if not isinstance(v, (dict, list))]
        (self.root / "FINAL_SUMMARY.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        out: dict[str, Any] = {}
        for k, v in value.items():
            if REDACT_RE.search(str(k)):
                out[k] = "<REDACTED>" if v not in (None, "", False) else v
            else:
                out[k] = redact(v)
        return out
    if isinstance(value, list):
        return [redact(v) for v in value]
    return value


def normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]", "", value.lower())


def assert_loopback_url(url: str, *, label: str, allowed_port: int | None = None) -> None:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError(f"{label}_SCHEME_NOT_ALLOWED:{parsed.scheme}")
    if parsed.username or parsed.password:
        raise ValueError(f"{label}_USERINFO_BLOCKED")
    host = parsed.hostname
    if not host:
        raise ValueError(f"{label}_HOST_MISSING")
    if allowed_port is not None and parsed.port != allowed_port:
        raise ValueError(f"{label}_PORT_NOT_ALLOWED:{parsed.port}")
    addresses: set[str] = set()
    try:
        addresses.add(str(ipaddress.ip_address(host)))
    except ValueError:
        for item in socket.getaddrinfo(host, parsed.port or 80, type=socket.SOCK_STREAM):
            addresses.add(item[4][0])
    if not addresses:
        raise ValueError(f"{label}_NO_RESOLVED_ADDRESS")
    for address in addresses:
        if not ipaddress.ip_address(address).is_loopback:
            raise ValueError(f"{label}_NON_LOOPBACK_ADDRESS:{address}")


def make_opener() -> urllib.request.OpenerDirector:
    return urllib.request.build_opener(urllib.request.ProxyHandler({}), BlockRedirect())


def http_json(
    opener: urllib.request.OpenerDirector,
    method: str,
    url: str,
    *,
    body: Any | None = None,
    headers: dict[str, str] | None = None,
    timeout: float = 120.0,
) -> tuple[int, Any, dict[str, str]]:
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    all_headers = {"Accept": "application/json"}
    if body is not None:
        all_headers["Content-Type"] = "application/json; charset=utf-8"
    if headers:
        all_headers.update(headers)
    req = urllib.request.Request(url, data=data, headers=all_headers, method=method)
    try:
        with opener.open(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
            try:
                parsed: Any = json.loads(raw) if raw else None
            except json.JSONDecodeError:
                parsed = {"_non_json_body": raw}
            return int(resp.status), parsed, {k: v for k, v in resp.headers.items()}
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw) if raw else None
        except json.JSONDecodeError:
            parsed = {"_non_json_body": raw}
        return int(exc.code), parsed, {k: v for k, v in exc.headers.items()}


def hash_file(path: pathlib.Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest().upper()


def source_snapshot(project_root: pathlib.Path) -> dict[str, str]:
    result: dict[str, str] = {}
    for rel_root in SOURCE_ROOTS:
        root = project_root / pathlib.PurePosixPath(rel_root)
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if not path.is_file() or any(part in EXCLUDED_DIRS for part in path.parts):
                continue
            rel = path.relative_to(project_root).as_posix()
            result[rel] = hash_file(path)
    for rel in SOURCE_SINGLE_FILES:
        path = project_root / pathlib.PurePosixPath(rel)
        if path.is_file():
            result[rel] = hash_file(path)
    return result


def resolve_schema(schema: Any, openapi: dict[str, Any], seen: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(schema, dict):
        return {}
    seen = set() if seen is None else set(seen)
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
        if ref in seen:
            return {}
        seen.add(ref)
        name = ref.rsplit("/", 1)[-1]
        target = openapi.get("components", {}).get("schemas", {}).get(name, {})
        resolved = resolve_schema(target, openapi, seen)
        merged = dict(resolved)
        merged.update({k: v for k, v in schema.items() if k != "$ref"})
        return merged
    if "allOf" in schema:
        merged: dict[str, Any] = {}
        required: list[str] = []
        properties: dict[str, Any] = {}
        for part in schema.get("allOf", []):
            item = resolve_schema(part, openapi, seen)
            properties.update(item.get("properties", {}))
            required.extend(item.get("required", []))
            merged.update({k: v for k, v in item.items() if k not in {"properties", "required"}})
        merged["properties"] = properties
        merged["required"] = sorted(set(required))
        return merged
    return schema


def operation_schema(openapi: dict[str, Any], path: str, method: str = "post") -> tuple[dict[str, Any], list[str]]:
    op = openapi.get("paths", {}).get(path, {}).get(method.lower(), {})
    body = op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {})
    schema = resolve_schema(body, openapi)
    header_names: list[str] = []
    for param in op.get("parameters", []):
        if param.get("in") == "header" and isinstance(param.get("name"), str):
            header_names.append(param["name"])
    return schema, header_names


def validate_authorized_retry_limits(openapi: dict[str, Any], args: argparse.Namespace, evidence: Evidence) -> None:
    """Validate the one-attempt timeout retry against the runtime OpenAPI contract."""
    if args.model != "qwen2.5:3b":
        raise RuntimeError(f"RETRY_MODEL_NOT_AUTHORIZED:{args.model}")
    if args.timeout_seconds != 180:
        raise RuntimeError(f"RETRY_TIMEOUT_NOT_AUTHORIZED:{args.timeout_seconds}")
    if args.max_output != 1200:
        raise RuntimeError(f"RETRY_MAX_OUTPUT_NOT_AUTHORIZED:{args.max_output}")
    if float(args.temperature) != 0.0:
        raise RuntimeError(f"RETRY_TEMPERATURE_NOT_AUTHORIZED:{args.temperature}")

    schema, _ = operation_schema(openapi, API_PATHS["settings"])
    settings_prop = resolve_schema(schema.get("properties", {}).get("settings", {}), openapi)
    props = settings_prop.get("properties", {}) if isinstance(settings_prop, dict) else {}

    timeout_schema = resolve_schema(props.get("timeout_seconds", {}), openapi)
    output_schema = resolve_schema(props.get("max_output_tokens", {}), openapi)
    temperature_schema = resolve_schema(props.get("temperature", {}), openapi)

    timeout_max = timeout_schema.get("maximum")
    output_max = output_schema.get("maximum")
    temperature_min = temperature_schema.get("minimum")

    if timeout_max is not None and args.timeout_seconds > float(timeout_max):
        raise RuntimeError(f"RETRY_TIMEOUT_EXCEEDS_OPENAPI_MAX:{args.timeout_seconds}>{timeout_max}")
    if output_max is not None and args.max_output > float(output_max):
        raise RuntimeError(f"RETRY_MAX_OUTPUT_EXCEEDS_OPENAPI_MAX:{args.max_output}>{output_max}")
    if temperature_min is not None and args.temperature < float(temperature_min):
        raise RuntimeError(f"RETRY_TEMPERATURE_BELOW_OPENAPI_MIN:{args.temperature}<{temperature_min}")

    evidence.write_json("AUTHORIZED_RETRY_LIMITS.json", {
        "attempt_limit": 1,
        "automatic_retry": False,
        "model": args.model,
        "timeout_seconds": args.timeout_seconds,
        "max_output_tokens": args.max_output,
        "temperature": args.temperature,
        "openapi_timeout_maximum": timeout_max,
        "openapi_max_output_tokens_maximum": output_max,
        "openapi_temperature_minimum": temperature_min,
    })
    evidence.event("AUTHORIZED_RETRY_LIMITS", "PASS")


def deep_find_settings(value: Any) -> dict[str, Any]:
    best: dict[str, Any] = {}
    best_score = -1
    def visit(node: Any) -> None:
        nonlocal best, best_score
        if isinstance(node, dict):
            keys = {normalize_key(str(k)) for k in node}
            score = sum(k in keys for k in {"provider", "providermode", "mode", "baseurl", "model", "modelname", "timeoutseconds"})
            if score > best_score:
                best, best_score = node, score
            for v in node.values():
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(value)
    return best


SETTINGS_SCALAR_KEYS = {
    "provider",
    "providermode",
    "mode",
    "baseurl",
    "endpoint",
    "providerurl",
    "model",
    "modelname",
    "timeout",
    "timeoutseconds",
    "requesttimeoutseconds",
    "maxoutput",
    "maxoutputchars",
    "maxoutputtokens",
    "maxtokens",
    "temperature",
    "apikeyenvname",
    "apikeyenvvar",
}


def direct_settings_values(value: Any) -> dict[str, Any]:
    """Read only direct scalar settings fields.

    Response metadata such as ``sources.mode = "dashboard_json"`` must never
    overwrite the actual operational value ``mode = "ollama"``.
    """
    settings = deep_find_settings(value)
    out: dict[str, Any] = {}
    if not isinstance(settings, dict):
        return out
    for key, raw in settings.items():
        normalized = normalize_key(str(key))
        if normalized in SETTINGS_SCALAR_KEYS and not isinstance(raw, (dict, list)):
            out[normalized] = raw
    return out


def critical_settings(value: Any) -> dict[str, Any]:
    direct = direct_settings_values(value)
    return {
        "mode": direct.get("mode", direct.get("providermode", direct.get("provider"))),
        "base_url": direct.get("baseurl", direct.get("providerurl", direct.get("endpoint"))),
        "model": direct.get("model", direct.get("modelname")),
        "timeout_seconds": direct.get(
            "timeoutseconds", direct.get("requesttimeoutseconds", direct.get("timeout"))
        ),
        "max_output_tokens": direct.get(
            "maxoutputtokens",
            direct.get("maxoutputchars", direct.get("maxoutput", direct.get("maxtokens"))),
        ),
        "temperature": direct.get("temperature"),
        "api_key_env_var": direct.get("apikeyenvvar", direct.get("apikeyenvname")),
    }


def target_critical_settings(args: argparse.Namespace) -> dict[str, Any]:
    return {
        "mode": args.provider,
        "base_url": args.provider_base_url,
        "model": args.model,
        "timeout_seconds": args.timeout_seconds,
        "max_output_tokens": args.max_output,
        "temperature": args.temperature,
        "api_key_env_var": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY",
    }


def operational_settings_match(left: Any, right: Any) -> bool:
    left_critical = critical_settings(left) if not (
        isinstance(left, dict) and set(left).issubset({
            "mode", "base_url", "model", "timeout_seconds",
            "max_output_tokens", "temperature", "api_key_env_var"
        })
    ) else left
    right_critical = critical_settings(right) if not (
        isinstance(right, dict) and set(right).issubset({
            "mode", "base_url", "model", "timeout_seconds",
            "max_output_tokens", "temperature", "api_key_env_var"
        })
    ) else right
    for key in (
        "mode", "base_url", "model", "timeout_seconds",
        "max_output_tokens", "temperature", "api_key_env_var"
    ):
        left_value = left_critical.get(key)
        right_value = right_critical.get(key)
        # API evidence may redact only the API-key environment variable.
        if key == "api_key_env_var" and "<REDACTED>" in {left_value, right_value}:
            continue
        if left_value != right_value:
            return False
    return True


def semantic_values(args: argparse.Namespace, original_settings: Any | None = None) -> dict[str, Any]:
    prompt = (
        "Create exactly one isolated candidate for GET "
        "/api/v1/operational-core/development-diagnostic/health. Return deterministic JSON only. "
        "No database write, network call, shell, Git, secret, path, hash, environment value, or source content. "
        "Modify candidate workspace only; never real source. Include candidate files, unified diff, "
        "AST safety PASS, direct-argv tests PASS, human_review_required=true, and source_apply_blocked=true."
    )
    vals: dict[str, Any] = {}
    aliases: dict[str, Any] = {
        "provider": args.provider,
        "providermode": args.provider,
        "mode": args.provider,
        "providername": args.provider,
        "baseurl": args.provider_base_url,
        "endpoint": args.provider_base_url,
        "providerurl": args.provider_base_url,
        "model": args.model,
        "modelname": args.model,
        "timeout": args.timeout_seconds,
        "timeoutseconds": args.timeout_seconds,
        "requesttimeoutseconds": args.timeout_seconds,
        "maxoutput": args.max_output,
        "maxoutputchars": args.max_output,
        "maxoutputtokens": args.max_output,
        "maxtokens": args.max_output,
        "temperature": args.temperature,
        "apikeyenvname": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY",
        "apikeyenvvar": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY",
        "authorization": AUTHORIZATION_TOKEN,
        "authorizationtoken": AUTHORIZATION_TOKEN,
        "approvaltoken": AUTHORIZATION_TOKEN,
        "humanauthorization": AUTHORIZATION_TOKEN,
        "humanapproval": AUTHORIZATION_TOKEN,
        "humanapprovalreference": AUTHORIZATION_TOKEN,
        "humanauthorityconfirmed": True,
        "confirmnosecretstorage": True,
        "confirmloopbackonly": True,
        "confirmmodelexecution": True,
        "confirmcandidateworkspaceonly": True,
        "confirmloopbackprovideronly": True,
        "authorizedby": "human_operator",
        "taskid": TASK_ID,
        "runid": TASK_ID,
        "requestid": TASK_ID,
        "candidateid": TASK_ID,
        "candidatekey": "governed_model_candidate_timeout_retry_qwen2_5_3b_v1",
        "goalid": TASK_ID,
        "goaltext": prompt,
        "title": "Governed model candidate timeout retry Qwen2.5 3B UAT",
        "name": "Governed model candidate timeout retry Qwen2.5 3B UAT",
        "taskname": "Governed model candidate timeout retry Qwen2.5 3B UAT",
        "objective": prompt,
        "prompt": prompt,
        "instruction": prompt,
        "instructions": prompt,
        "description": prompt,
        "request": prompt,
        "task": prompt,
        "contract": CONTRACT,
        "contractid": CONTRACT,
        "promptversion": PROMPT_VERSION,
        "project": "palwakf_local_agents",
        "projectid": "palwakf_local_agents",
        "workspace": "palwakf_local_agents",
        "workspaceid": "palwakf_local_agents",
        "targetfiles": [
            "backend/src/palwakf_local_agents/development_diagnostic_v1.py",
            "backend/src/palwakf_local_agents/app.py",
        ],
        "allowedfiles": [
            "backend/src/palwakf_local_agents/development_diagnostic_v1.py",
            "backend/src/palwakf_local_agents/app.py",
        ],
        "files": [
            "backend/src/palwakf_local_agents/development_diagnostic_v1.py",
            "backend/src/palwakf_local_agents/app.py",
        ],
        "acceptancecriteria": [
            "strict_json_output",
            "ast_safety_gate_pass",
            "direct_argv_tests_pass",
            "unified_diff_generated",
            "real_source_mutation_false",
            "source_apply_blocked",
        ],
        "requirements": [
            "loopback_only",
            "candidate_workspace_only",
            "no_shell",
            "no_git",
            "no_database_write",
            "no_source_apply",
        ],
        "testargv": ["python", "-m", "pytest", "-q"],
        "sourceapply": False,
        "apply": False,
        "dryrun": False,
        "humanreviewrequired": True,
    }
    vals.update(aliases)
    # During restoration, only direct operational fields from the original
    # settings may win. Nested response metadata (for example "dashboard_json")
    # is deliberately excluded.
    if original_settings is not None:
        vals.update(direct_settings_values(original_settings))
    return vals


def build_from_schema(schema: dict[str, Any], values: dict[str, Any], openapi: dict[str, Any], path: str = "$") -> tuple[Any, list[str]]:
    schema = resolve_schema(schema, openapi)
    if "default" in schema:
        default = schema["default"]
    else:
        default = None
    enum = schema.get("enum")
    typ = schema.get("type")
    if not typ and "properties" in schema:
        typ = "object"
    if not typ and "items" in schema:
        typ = "array"
    if typ == "object":
        props = schema.get("properties", {})
        required = set(schema.get("required", []))
        result: dict[str, Any] = {}
        missing: list[str] = []
        for name, child in props.items():
            nk = normalize_key(name)
            if nk in values:
                result[name] = values[nk]
                continue
            child_resolved = resolve_schema(child, openapi)
            if child_resolved.get("type") == "object" or "properties" in child_resolved:
                built, child_missing = build_from_schema(child_resolved, values, openapi, f"{path}.{name}")
                if built not in ({}, None) or name in required:
                    result[name] = built
                missing.extend(child_missing)
                continue
            if "default" in child_resolved:
                result[name] = child_resolved["default"]
                continue
            if name in required:
                missing.append(f"{path}.{name}")
        return result, missing
    if typ == "array":
        return default if default is not None else [], []
    if enum:
        return enum[0], []
    return default, ([] if default is not None else [path])


def build_body(openapi: dict[str, Any], path: str, args: argparse.Namespace, original_settings: Any | None = None) -> tuple[Any, list[str], list[str]]:
    schema, header_names = operation_schema(openapi, path)
    values = semantic_values(args, original_settings)
    if not schema:
        return {}, ["REQUEST_SCHEMA_NOT_FOUND"], header_names
    if schema.get("type") != "object" and "$ref" not in schema and "properties" not in schema:
        return {}, ["REQUEST_SCHEMA_UNSUPPORTED"], header_names
    body, missing = build_from_schema(schema, values, openapi)
    # Fill top-level known properties that the schema builder could not infer through aliases.
    if isinstance(body, dict):
        for key in list(body):
            if body[key] is None:
                body.pop(key)
    return body, missing, header_names


def authorization_headers(names: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        nk = normalize_key(name)
        if any(token in nk for token in ("authorization", "approval", "human", "token")):
            out[name] = AUTHORIZATION_TOKEN
    # Include conservative project-specific headers; servers ignore unknown headers.
    out.setdefault("X-PalWakf-Human-Authorization", AUTHORIZATION_TOKEN)
    out.setdefault("X-Local-Authorization", AUTHORIZATION_TOKEN)
    return out


def verify_ollama_local_model(
    opener: urllib.request.OpenerDirector,
    provider_base_url: str,
    model: str,
    evidence: Evidence,
) -> None:
    """Prove the selected Ollama model is installed locally and is not a cloud proxy."""
    if model.lower().endswith(":cloud"):
        raise RuntimeError(f"OLLAMA_CLOUD_MODEL_BLOCKED:{model}")
    tags_url = provider_base_url.rstrip("/") + "/api/tags"
    status, payload, _ = http_json(opener, "GET", tags_url, timeout=30)
    if status != 200 or not isinstance(payload, dict):
        raise RuntimeError(f"OLLAMA_TAGS_FETCH_FAILED:{status}")
    rows = payload.get("models")
    if not isinstance(rows, list):
        raise RuntimeError("OLLAMA_TAGS_MODELS_LIST_MISSING")
    inventory: list[dict[str, Any]] = []
    selected: dict[str, Any] | None = None
    for raw in rows:
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or raw.get("model") or "").strip()
        remote_host = raw.get("remote_host")
        remote_model = raw.get("remote_model")
        is_remote = bool(remote_host or remote_model or name.lower().endswith(":cloud"))
        inventory.append({
            "name": name,
            "is_remote": is_remote,
            "capabilities": raw.get("capabilities", []),
        })
        if name == model or str(raw.get("model") or "").strip() == model:
            selected = raw
    evidence.write_json("OLLAMA_MODEL_INVENTORY.json", {
        "requested_model": model,
        "models": inventory,
    })
    if selected is None:
        raise RuntimeError(f"OLLAMA_MODEL_NOT_INSTALLED_LOCALLY:{model}")
    if selected.get("remote_host") or selected.get("remote_model") or model.lower().endswith(":cloud"):
        raise RuntimeError(f"OLLAMA_REMOTE_MODEL_BLOCKED:{model}")
    capabilities = selected.get("capabilities")
    if isinstance(capabilities, list) and capabilities and "completion" not in capabilities:
        raise RuntimeError(f"OLLAMA_MODEL_COMPLETION_CAPABILITY_NOT_PROVEN:{model}")
    evidence.event("OLLAMA_LOCAL_MODEL_CONTRACT", "PASS", model=model)


def recursive_find(value: Any, patterns: tuple[str, ...]) -> list[Any]:
    found: list[Any] = []
    def visit(node: Any) -> None:
        if isinstance(node, dict):
            for k, v in node.items():
                nk = normalize_key(str(k))
                if any(p in nk for p in patterns):
                    found.append(v)
                visit(v)
        elif isinstance(node, list):
            for v in node:
                visit(v)
    visit(value)
    return found


def positive_status(value: Any) -> bool:
    if value is True:
        return True
    if not isinstance(value, str):
        return False
    normalized = value.strip().upper()
    if not normalized:
        return False
    tokens = [token for token in re.split(r"[^A-Z0-9]+", normalized) if token]
    negative = {"FAIL", "FAILED", "FALSE", "NO", "NOT", "BLOCKED", "ERROR", "DENIED", "REJECTED"}
    if any(token in negative for token in tokens):
        return False
    return any(token in {"PASS", "PASSED", "SUCCESS", "OK", "TRUE"} for token in tokens)


def any_pass(value: Any, patterns: tuple[str, ...]) -> bool:
    return any(positive_status(item) for item in recursive_find(value, patterns))


def any_false(value: Any, patterns: tuple[str, ...]) -> bool:
    vals = recursive_find(value, patterns)
    for item in vals:
        if item is False:
            return True
        if isinstance(item, str) and item.strip().upper() in {"FALSE", "NONE", "NO", "BLOCKED"}:
            return True
    return False


def contains_text(value: Any, needle: str) -> bool:
    return needle.lower() in json.dumps(value, ensure_ascii=False).lower()


def provider_probe_contract_pass(payload: Any, provider: str) -> tuple[bool, dict[str, bool]]:
    result_pass = any_pass(
        payload,
        ("result", "success", "status", "probe", "reachable", "healthy"),
    )
    loopback_only = any_pass(payload, ("loopbackonly",))
    provider_match = contains_text(payload, provider)
    secret_fields = recursive_find(payload, ("secretvaluereturned",))
    secret_not_returned = bool(secret_fields) and any_false(payload, ("secretvaluereturned",))
    gates = {
        "result_pass": result_pass,
        "loopback_only": loopback_only,
        "provider_match": provider_match,
        "secret_not_returned": secret_not_returned,
    }
    return all(gates.values()), gates


def candidate_id(value: Any) -> str | None:
    vals = recursive_find(value, ("candidateid",))
    for v in vals:
        if isinstance(v, str) and v.strip():
            return v.strip()
    return None


def merge_for_verification(*values: Any) -> dict[str, Any]:
    return {f"payload_{i}": v for i, v in enumerate(values)}


def run(args: argparse.Namespace) -> int:
    if args.authorization != AUTHORIZATION_TOKEN:
        print("AUTHORIZATION_TOKEN_MISMATCH", file=sys.stderr)
        return 20
    assert_loopback_url(args.origin, label="APP_ORIGIN", allowed_port=8010)
    assert_loopback_url(args.provider_base_url, label="PROVIDER_BASE_URL")
    project_root = pathlib.Path(args.project_root).resolve()
    if not project_root.is_dir():
        print(f"PROJECT_ROOT_NOT_FOUND:{project_root}", file=sys.stderr)
        return 21
    output_base = pathlib.Path(args.output_root).resolve()
    stamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    evidence = Evidence(output_base / f"LOCAL_AGENTS_GOVERNED_MODEL_TIMEOUT_RETRY_QWEN2_5_3B_V1_{stamp}")
    summary: dict[str, Any] = {
        "phase": "MEGA_BATCH_LOCAL_AGENTS_GOVERNED_MODEL_CANDIDATE_TIMEOUT_RETRY_QWEN2_5_3B_V1",
        "harness_version": HARNESS_VERSION,
        "authorization": "CONFIRMED",
        "execution_mode": "LIVE" if args.execute_live else "PREFLIGHT_ONLY",
        "origin": args.origin,
        "provider": args.provider,
        "provider_base_url": args.provider_base_url,
        "model": args.model,
        "prompt_version": PROMPT_VERSION,
        "source_apply": "BLOCKED",
        "database_write": "NONE_BY_HARNESS",
        "shell": "NOT_INVOKED",
        "git": "NOT_INVOKED",
        "result": "IN_PROGRESS",
    }
    opener = make_opener()
    original_settings: Any = None
    openapi: dict[str, Any] = {}
    settings_changed = False
    before_source: dict[str, str] = {}
    after_source: dict[str, str] = {}
    try:
        before_source = source_snapshot(project_root)
        evidence.write_json("SOURCE_PREIMAGE_SHA256.json", before_source)
        evidence.event("SOURCE_PREIMAGE_CAPTURE", "PASS", file_count=len(before_source))
        if not before_source:
            raise RuntimeError("SOURCE_PREIMAGE_EMPTY")

        status, openapi, _ = http_json(opener, "GET", args.origin.rstrip("/") + "/openapi.json", timeout=30)
        evidence.write_json("OPENAPI.json", openapi)
        if status != 200 or not isinstance(openapi, dict):
            raise RuntimeError(f"OPENAPI_FETCH_FAILED:{status}")
        evidence.event("OPENAPI_FETCH", "PASS")
        validate_authorized_retry_limits(openapi, args, evidence)

        if args.provider == "ollama":
            verify_ollama_local_model(opener, args.provider_base_url, args.model, evidence)

        coding_paths = [p for p in openapi.get("paths", {}) if "/coding-model/" in p]
        apply_paths = [p for p in coding_paths if any(x in p.lower() for x in ("/apply", "/commit", "/source-write"))]
        evidence.write_json("CODING_MODEL_PATHS.json", {"paths": coding_paths, "apply_like_paths": apply_paths})
        if apply_paths:
            raise RuntimeError(f"SOURCE_APPLY_ENDPOINT_PRESENT:{apply_paths}")
        evidence.event("SOURCE_APPLY_ENDPOINT_ABSENT", "PASS")

        responses: dict[str, Any] = {}
        for key in ("health", "contract", "providers", "settings", "runs_latest", "candidates_latest"):
            path = API_PATHS[key]
            st, payload, headers = http_json(opener, "GET", args.origin.rstrip("/") + path, timeout=30)
            responses[key] = {"status": st, "payload": payload, "headers": headers}
            evidence.write_json(f"GET_{key.upper()}.json", responses[key])
            if key in {"health", "contract", "providers", "settings"} and st != 200:
                raise RuntimeError(f"REQUIRED_GET_FAILED:{key}:{st}")
            evidence.event(f"GET_{key.upper()}", "PASS" if st == 200 else f"HTTP_{st}")
        original_settings = responses["settings"]["payload"]
        original_settings_object = deep_find_settings(original_settings)
        evidence.write_json("ORIGINAL_SETTINGS_OBJECT.json", original_settings_object)

        # Build and record exact schema-aware request bodies before any POST.
        settings_body, settings_missing, settings_headers = build_body(openapi, API_PATHS["settings"], args)
        probe_body, probe_missing, probe_headers = build_body(openapi, API_PATHS["probe"], args)
        generate_body, generate_missing, generate_headers = build_body(openapi, API_PATHS["generate"], args)
        evidence.write_json("REQUEST_BODIES_PREVIEW.json", {
            "settings": settings_body,
            "settings_missing_required": settings_missing,
            "probe": probe_body,
            "probe_missing_required": probe_missing,
            "generate": generate_body,
            "generate_missing_required": generate_missing,
        })
        all_missing = settings_missing + probe_missing + generate_missing
        if all_missing:
            raise RuntimeError("OPENAPI_REQUIRED_FIELDS_UNRESOLVED:" + ",".join(all_missing))
        evidence.event("OPENAPI_REQUEST_CONTRACT_RESOLUTION", "PASS")

        if not args.execute_live:
            summary.update({
                "provider_probe": "NOT_EXECUTED_PREFLIGHT_ONLY",
                "model_run": "NOT_EXECUTED_PREFLIGHT_ONLY",
                "candidate_generation": "NOT_EXECUTED_PREFLIGHT_ONLY",
                "source_mutation": "FALSE",
                "result": "PASS_PREFLIGHT_READY_FOR_LIVE",
                "evidence_root": str(evidence.root),
            })
            return 0

        # Avoid a settings write when the currently active operational fields
        # already match the authorized target. This also eliminates unnecessary
        # restoration risk.
        original_critical = critical_settings(original_settings_object)
        target_critical = target_critical_settings(args)
        evidence.write_json("SETTINGS_CHANGE_DECISION.json", {
            "original_critical": original_critical,
            "target_critical": target_critical,
            "already_matched": operational_settings_match(original_critical, target_critical),
        })
        if operational_settings_match(original_critical, target_critical):
            settings_changed = False
            summary["provider_settings_change"] = "NOT_REQUIRED_ALREADY_MATCHED"
            evidence.event("PROVIDER_SETTINGS_ENABLE", "NOT_REQUIRED_ALREADY_MATCHED")
        else:
            st, payload, _ = http_json(
                opener, "POST", args.origin.rstrip("/") + API_PATHS["settings"],
                body=settings_body,
                headers=authorization_headers(settings_headers),
                timeout=30,
            )
            evidence.write_json("POST_SETTINGS_ENABLE.json", {"status": st, "payload": payload})
            if st < 200 or st >= 300:
                raise RuntimeError(f"SETTINGS_ENABLE_FAILED:{st}")
            settings_changed = True
            summary["provider_settings_change"] = "APPLIED_TEMPORARILY"
            evidence.event("PROVIDER_SETTINGS_ENABLE", "PASS")

        st, probe_payload, _ = http_json(
            opener, "POST", args.origin.rstrip("/") + API_PATHS["probe"],
            body=probe_body,
            headers=authorization_headers(probe_headers),
            timeout=max(30, args.timeout_seconds + 15),
        )
        evidence.write_json("POST_PROVIDER_PROBE.json", {"status": st, "payload": probe_payload})
        if st < 200 or st >= 300:
            raise RuntimeError(f"PROVIDER_PROBE_FAILED:{st}")
        probe_passed, probe_gates = provider_probe_contract_pass(probe_payload, args.provider)
        evidence.write_json("PROVIDER_PROBE_GATES.json", probe_gates)
        if not probe_passed:
            failed_gates = ",".join(name for name, passed in probe_gates.items() if not passed)
            raise RuntimeError("PROVIDER_PROBE_CONTRACT_NOT_PROVEN:" + failed_gates)
        evidence.event("PROVIDER_PROBE", "PASS")

        before_candidate = candidate_id(responses.get("candidates_latest", {}).get("payload"))
        evidence.write_json("MODEL_GENERATION_ATTEMPT_BUDGET.json", {
            "authorized_attempt_limit": 1,
            "attempt_number": 1,
            "automatic_retry": False,
            "model": args.model,
            "timeout_seconds": args.timeout_seconds,
            "max_output_tokens": args.max_output,
        })
        evidence.event("MODEL_GENERATION_ATTEMPT", "STARTED", attempt_number=1)
        st, generation_payload, _ = http_json(
            opener, "POST", args.origin.rstrip("/") + API_PATHS["generate"],
            body=generate_body,
            headers=authorization_headers(generate_headers),
            timeout=max(60, args.timeout_seconds + 30),
        )
        evidence.write_json("POST_CANDIDATE_GENERATE.json", {"status": st, "payload": generation_payload})
        if st < 200 or st >= 300:
            detail = generation_payload.get("detail") if isinstance(generation_payload, dict) else None
            code = detail.get("code") if isinstance(detail, dict) else None
            error_type = detail.get("type") if isinstance(detail, dict) else None
            evidence.write_json("CANDIDATE_GENERATE_FAILURE_CLASSIFICATION.json", {
                "http_status": st,
                "provider_error_code": code,
                "provider_error_type": error_type,
                "automatic_retry_performed": False,
                "attempt_budget_exhausted": True,
            })
            raise RuntimeError(f"CANDIDATE_GENERATE_FAILED:{st}:{code or 'UNKNOWN'}:{error_type or 'UNKNOWN'}")
        evidence.event("MODEL_GENERATED_CANDIDATE_REQUEST", "PASS")

        # Read canonical runtime records after generation.
        post: dict[str, Any] = {}
        for key in ("runs_latest", "candidates_latest"):
            st2, payload2, headers2 = http_json(opener, "GET", args.origin.rstrip("/") + API_PATHS[key], timeout=30)
            post[key] = {"status": st2, "payload": payload2, "headers": headers2}
            evidence.write_json(f"POST_GET_{key.upper()}.json", post[key])
            if st2 != 200:
                raise RuntimeError(f"POST_READ_FAILED:{key}:{st2}")
        combined = merge_for_verification(generation_payload, post["runs_latest"]["payload"], post["candidates_latest"]["payload"])
        new_candidate = candidate_id(combined)
        if not new_candidate:
            raise RuntimeError("NEW_CANDIDATE_ID_NOT_FOUND")
        if before_candidate and new_candidate == before_candidate:
            raise RuntimeError("CANDIDATE_ID_DID_NOT_CHANGE")
        evidence.event("NEW_CANDIDATE_RECORDED", "PASS", candidate_id=new_candidate)

        structured_output = isinstance(generation_payload, (dict, list))
        ast_pass = any_pass(combined, ("astsafety", "astgate", "safetygate"))
        tests_pass = any_pass(combined, ("directargv", "tests", "testresult", "teststatus"))
        diff_generated = bool(recursive_find(combined, ("unifieddiff", "diff")))
        source_apply_blocked = (
            any_false(combined, ("sourceapply", "applyavailable", "applyallowed"))
            or contains_text(combined, "source_apply_blocked")
            or contains_text(combined, "BLOCKED_REQUIRES_SEPARATE_CANDIDATE_AUTHORIZATION")
        )
        prompt_recorded = contains_text(combined, PROMPT_VERSION)
        model_recorded = contains_text(combined, args.model)
        human_review = contains_text(combined, "HUMAN_REVIEW_REQUIRED") or any_pass(combined, ("humanreviewrequired",))

        gates = {
            "structured_output": structured_output,
            "ast_safety_gate": ast_pass,
            "direct_argv_tests": tests_pass,
            "unified_diff_generated": diff_generated,
            "source_apply_blocked": source_apply_blocked,
            "prompt_version_recorded": prompt_recorded,
            "model_version_recorded": model_recorded,
            "human_review_required": human_review,
        }
        evidence.write_json("RUNTIME_GATES.json", gates)
        for name, passed in gates.items():
            evidence.event(name.upper(), "PASS" if passed else "NOT_PROVEN")
        if not all(gates.values()):
            raise RuntimeError("RUNTIME_ACCEPTANCE_GATES_NOT_ALL_PROVEN")

        summary.update({
            "provider_probe": "PASS",
            "model_run_human_authorized": "PASS",
            "structured_output": "PASS",
            "ast_safety_gate": "PASS",
            "direct_argv_tests": "PASS",
            "unified_diff": "GENERATED",
            "candidate_id": new_candidate,
            "candidate_state": "HUMAN_REVIEW_REQUIRED",
            "source_apply": "BLOCKED",
        })
    except Exception as exc:
        summary["error"] = f"{type(exc).__name__}:{exc}"
        summary["traceback"] = traceback.format_exc()
        summary["result"] = "FAIL_CLOSED"
        evidence.event("EXECUTION", "FAIL_CLOSED", error=str(exc))
    finally:
        if args.execute_live and settings_changed and original_settings is not None:
            try:
                restore_body, restore_missing, restore_headers = build_body(
                    openapi, API_PATHS["settings"], args, original_settings_object
                )
                evidence.write_json("SETTINGS_RESTORE_REQUEST_PREVIEW.json", {
                    "body": restore_body,
                    "missing": restore_missing,
                })
                if restore_missing:
                    raise RuntimeError("RESTORE_REQUIRED_FIELDS_UNRESOLVED:" + ",".join(restore_missing))
                st, payload, _ = http_json(
                    opener, "POST", args.origin.rstrip("/") + API_PATHS["settings"],
                    body=restore_body,
                    headers=authorization_headers(restore_headers),
                    timeout=30,
                )
                evidence.write_json("POST_SETTINGS_RESTORE.json", {"status": st, "payload": payload})
                if st < 200 or st >= 300:
                    raise RuntimeError(f"SETTINGS_RESTORE_FAILED:{st}")
                verify_status, verify_payload, verify_headers = http_json(
                    opener, "GET", args.origin.rstrip("/") + API_PATHS["settings"], timeout=30
                )
                evidence.write_json("GET_SETTINGS_AFTER_RESTORE.json", {
                    "status": verify_status,
                    "payload": verify_payload,
                    "headers": verify_headers,
                })
                if verify_status != 200:
                    raise RuntimeError(f"SETTINGS_RESTORE_VERIFY_GET_FAILED:{verify_status}")
                if not operational_settings_match(original_settings_object, verify_payload):
                    raise RuntimeError("SETTINGS_RESTORE_VERIFICATION_MISMATCH")
                evidence.event("PROVIDER_SETTINGS_RESTORE", "PASS")
                summary["provider_settings_restored"] = "PASS_VERIFIED"
            except Exception as restore_exc:
                evidence.event("PROVIDER_SETTINGS_RESTORE", "FAIL", error=str(restore_exc))
                summary["provider_settings_restored"] = "FAIL"
                summary["result"] = "FAIL_CLOSED_RESTORE_FAILED"
                summary["restore_error"] = str(restore_exc)
        if args.execute_live and not settings_changed:
            summary.setdefault("provider_settings_restored", "NOT_REQUIRED_ORIGINAL_ALREADY_MATCHED")
        try:
            after_source = source_snapshot(project_root)
            evidence.write_json("SOURCE_POSTIMAGE_SHA256.json", after_source)
            source_unchanged = before_source == after_source and bool(before_source)
            evidence.event("REAL_SOURCE_MUTATION", "FALSE" if source_unchanged else "DETECTED")
            summary["source_mutation"] = "FALSE" if source_unchanged else "DETECTED"
            if not source_unchanged:
                summary["result"] = "FAIL_CLOSED_SOURCE_MUTATION_DETECTED"
        except Exception as hash_exc:
            summary["source_mutation"] = "NOT_PROVEN"
            summary["result"] = "FAIL_CLOSED_SOURCE_POSTIMAGE_ERROR"
            summary["source_postimage_error"] = str(hash_exc)
        if summary.get("result") == "IN_PROGRESS":
            summary["result"] = "PASS"
        summary["evidence_root"] = str(evidence.root)
        evidence.finalize(summary)
        print(f"EVIDENCE_ROOT={evidence.root}")
        print(f"FINAL_RESULT={summary['result']}")
    return 0 if str(summary.get("result", "")).startswith("PASS") else 1


def self_test() -> int:
    assert_loopback_url("http://127.0.0.1:8010", label="TEST", allowed_port=8010)
    assert_loopback_url("http://localhost:11434", label="TEST_PROVIDER")
    try:
        assert_loopback_url("http://8.8.8.8:80", label="TEST_EXTERNAL")
    except ValueError:
        pass
    else:
        raise AssertionError("external URL not blocked")
    sample = {"api_key": "secret", "nested": {"model": "x", "password": "p"}}
    redacted = redact(sample)
    assert redacted["api_key"] == "<REDACTED>"
    assert redacted["nested"]["password"] == "<REDACTED>"
    openapi = {
        "components": {"schemas": {"Req": {"type": "object", "required": ["provider", "base_url"], "properties": {
            "provider": {"type": "string"}, "base_url": {"type": "string"}
        }}}},
        "paths": {"/x": {"post": {"requestBody": {"content": {"application/json": {"schema": {"$ref": "#/components/schemas/Req"}}}}}}}
    }
    ns = argparse.Namespace(provider="ollama", provider_base_url="http://127.0.0.1:11434", model="m", timeout_seconds=180, max_output=1200, temperature=0.0)
    body, missing, _ = build_body(openapi, "/x", ns)
    assert not missing and body["provider"] == "ollama" and body["base_url"].startswith("http://127.")
    governance_openapi = {
        "paths": {
            "/settings": {"post": {"requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["settings", "human_approval_reference", "human_authority_confirmed", "confirm_no_secret_storage"],
                "properties": {
                    "settings": {"type": "object", "required": ["mode", "base_url", "model"], "properties": {
                        "mode": {"type": "string"}, "base_url": {"type": "string"}, "model": {"type": "string"}
                    }},
                    "human_approval_reference": {"type": "string"},
                    "human_authority_confirmed": {"type": "boolean"},
                    "confirm_no_secret_storage": {"type": "boolean"}
                }
            }}}}}},
            "/probe": {"post": {"requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["human_approval_reference", "human_authority_confirmed", "confirm_loopback_only"],
                "properties": {
                    "human_approval_reference": {"type": "string"},
                    "human_authority_confirmed": {"type": "boolean"},
                    "confirm_loopback_only": {"type": "boolean"}
                }
            }}}}}},
            "/generate": {"post": {"requestBody": {"content": {"application/json": {"schema": {
                "type": "object",
                "required": ["candidate_key", "goal_id", "goal_text", "human_approval_reference", "human_authority_confirmed", "confirm_model_execution", "confirm_candidate_workspace_only", "confirm_loopback_provider_only"],
                "properties": {
                    "candidate_key": {"type": "string"}, "goal_id": {"type": "string"}, "goal_text": {"type": "string"},
                    "human_approval_reference": {"type": "string"}, "human_authority_confirmed": {"type": "boolean"},
                    "confirm_model_execution": {"type": "boolean"},
                    "confirm_candidate_workspace_only": {"type": "boolean"},
                    "confirm_loopback_provider_only": {"type": "boolean"}
                }
            }}}}}}
        }
    }
    for path in ("/settings", "/probe", "/generate"):
        governance_body, governance_missing, _ = build_body(governance_openapi, path, ns)
        assert not governance_missing, (path, governance_missing, governance_body)
    assert governance_body["confirm_model_execution"] is True
    assert governance_body["candidate_key"] == "governed_model_candidate_timeout_retry_qwen2_5_3b_v1"
    assert positive_status("PROBE_PASS")
    assert positive_status("AST_SAFETY_PASS")
    assert positive_status("DIRECT_ARGV_TESTS_PASS")
    assert not positive_status("PROBE_FAIL")
    probe_ok, probe_gates = provider_probe_contract_pass({
        "result": "PROBE_PASS",
        "loopback_only": True,
        "provider_mode": "ollama",
        "secret_value_returned": False,
    }, "ollama")
    assert probe_ok and all(probe_gates.values()), probe_gates
    metadata_settings = {
        "mode": "ollama",
        "base_url": "http://127.0.0.1:11434",
        "model": "m",
        "timeout_seconds": 180,
        "max_output_tokens": 1200,
        "temperature": 0.0,
        "api_key_env_var": "PALWAKF_LOCAL_AGENTS_MODEL_API_KEY",
        "sources": {
            "mode": "dashboard_json",
            "base_url": "dashboard_json",
            "model": "dashboard_json",
            "timeout_seconds": "dashboard_json",
            "max_output_tokens": "dashboard_json",
        },
    }
    direct = direct_settings_values(metadata_settings)
    assert direct["mode"] == "ollama"
    assert direct["maxoutputtokens"] == 1200
    assert "dashboard_json" not in direct.values()
    assert operational_settings_match(metadata_settings, target_critical_settings(ns))
    retry_openapi = {
        "components": {"schemas": {
            "ProviderSettingsInput": {
                "type": "object",
                "properties": {
                    "timeout_seconds": {"type": "integer", "maximum": 180},
                    "max_output_tokens": {"type": "integer", "maximum": 4096},
                    "temperature": {"type": "number", "minimum": 0.0},
                },
            },
            "SaveProviderSettingsRequest": {
                "type": "object",
                "properties": {
                    "settings": {"$ref": "#/components/schemas/ProviderSettingsInput"}
                },
            },
        }},
        "paths": {
            API_PATHS["settings"]: {
                "post": {
                    "requestBody": {
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/SaveProviderSettingsRequest"}
                            }
                        }
                    }
                }
            }
        },
    }
    class _Evidence:
        def write_json(self, *args: Any, **kwargs: Any) -> None:
            return None
        def event(self, *args: Any, **kwargs: Any) -> None:
            return None
    retry_ns = argparse.Namespace(
        model="qwen2.5:3b",
        timeout_seconds=180,
        max_output=1200,
        temperature=0.0,
    )
    validate_authorized_retry_limits(retry_openapi, retry_ns, _Evidence())
    print("HARNESS_SELF_TEST=PASS")
    return 0


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--project-root", default=r"C:\Users\DELL\StudioProjects\palwakf_local_agents")
    p.add_argument("--output-root", default=r"D:\PALWAKF_ASSISTANT_BASELINES")
    p.add_argument("--origin", default="http://127.0.0.1:8010")
    p.add_argument("--provider", choices=("ollama", "openai_compatible"), default="ollama")
    p.add_argument("--provider-base-url", default="http://127.0.0.1:11434")
    p.add_argument("--model", default="qwen2.5:3b")
    p.add_argument("--timeout-seconds", type=int, default=180)
    p.add_argument("--max-output", type=int, default=1200)
    p.add_argument("--temperature", type=float, default=0.0)
    p.add_argument("--authorization", default="")
    p.add_argument("--execute-live", action="store_true")
    p.add_argument("--self-test", action="store_true")
    return p.parse_args()


if __name__ == "__main__":
    parsed = parse_args()
    if parsed.self_test:
        raise SystemExit(self_test())
    raise SystemExit(run(parsed))
