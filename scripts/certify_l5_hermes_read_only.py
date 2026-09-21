from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidence" / "l5_one_mega_batch" / "providers"
OLLAMA_EVIDENCE = OUT / "OLLAMA_L5_CERTIFICATION.json"
EXPECTED_HERMES_VERSION = "0.21.3"
EXPECTED_MODEL = "llama3.2:3b"
EXPECTED_RESPONSE = "HERMES_LOCAL_READ_ONLY_PASS"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _tracked_snapshot() -> dict[str, str]:
    files = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()
    return {
        relative: _sha256(ROOT / relative)
        for relative in files
        if (ROOT / relative).is_file()
    }
def _real_user_config() -> Path:
    local_app_data = os.getenv("LOCALAPPDATA", "").strip()
    if local_app_data:
        return Path(local_app_data) / "hermes" / "config.yaml"
    return Path.home() / ".hermes" / "config.yaml"


def _optional_sha(path: Path) -> str:
    return _sha256(path) if path.is_file() else "ABSENT"


def _load_ollama_evidence() -> dict[str, Any]:
    payload = json.loads(OLLAMA_EVIDENCE.read_text(encoding="utf-8"))
    if payload.get("final_result") != "PASS":
        raise RuntimeError("OLLAMA_L5_CERTIFICATION_NOT_PASS")
    route = payload.get("route_decision") or {}
    if route.get("model") != EXPECTED_MODEL:
        raise RuntimeError("OLLAMA_L5_ROUTE_MODEL_MISMATCH")
    if route.get("provider_id") != "ollama":
        raise RuntimeError("OLLAMA_L5_ROUTE_PROVIDER_MISMATCH")
    return payload


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ollama_evidence = _load_ollama_evidence()
    hermes = shutil.which("hermes")
    if not hermes:
        raise RuntimeError("HERMES_COMMAND_NOT_FOUND")

    version_run = subprocess.run(
        [hermes, "--version"],
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    version_text = (version_run.stdout or version_run.stderr).strip()
    preimage = _tracked_snapshot()
    user_config = _real_user_config()
    user_config_before = _optional_sha(user_config)

    report: dict[str, Any] = {
        "schema": "palwakf.agentic.l5.hermes.read_only.v1",
        "hermes_version_output": version_text,
        "expected_hermes_version": EXPECTED_HERMES_VERSION,
        "ollama_provider_version": ollama_evidence.get("provider_version"),
        "model": EXPECTED_MODEL,
        "provider": "custom",
        "endpoint": "http://127.0.0.1:11434/v1",
        "egress_policy": "PROXY_DENY_EXTERNAL_ALLOW_LOOPBACK_ONLY",
        "tool_surface": "vision_only",
        "safe_mode": True,
        "ignore_rules": True,
        "user_config_loaded": False,
        "bounded_write_tested": False,
        "bounded_write_status": "FORBIDDEN_BY_L5_AUTHORIZATION",
        "main_merge": False,
        "baseline_promotion": False,
        "production": False,
        "shared_db_mutation": False,
    }

    with tempfile.TemporaryDirectory(
        prefix="palwakf-hermes-l5-"
    ) as temp_root:
        temp = Path(temp_root)
        hermes_home = temp / "home"
        probe = temp / "probe"
        hermes_home.mkdir()
        probe.mkdir()
        usage_path = temp / "usage.json"

        env = dict(os.environ)
        env["HERMES_HOME"] = str(hermes_home)
        env["CUSTOM_BASE_URL"] = "http://127.0.0.1:11434/v1"
        env["OPENAI_API_KEY"] = "palwakf-local-loopback-only"
        env["OPENROUTER_BASE_URL"] = "http://127.0.0.1:11434/v1"
        env["HTTP_PROXY"] = "http://127.0.0.1:9"
        env["HTTPS_PROXY"] = "http://127.0.0.1:9"
        env["ALL_PROXY"] = "http://127.0.0.1:9"
        env["NO_PROXY"] = "127.0.0.1,localhost,::1"
        env["no_proxy"] = "127.0.0.1,localhost,::1"
        prompt = (
            "Return exactly HERMES_LOCAL_READ_ONLY_PASS and nothing else."
        )
        command = [
            hermes,
            "-z",
            prompt,
            "--provider",
            "custom",
            "-m",
            EXPECTED_MODEL,
            "--reasoning",
            "none",
            "-t",
            "vision",
            "--safe-mode",
            "--ignore-rules",
            "--in",
            str(probe),
            "--usage-file",
            str(usage_path),
        ]
        started = __import__("time").monotonic()
        run = subprocess.run(
            command,
            cwd=probe,
            env=env,
            capture_output=True,
            text=True,
            timeout=90,
            check=False,
        )
        latency_ms = round(
            (__import__("time").monotonic() - started) * 1000, 2
        )
        usage = (
            json.loads(usage_path.read_text(encoding="utf-8"))
            if usage_path.is_file()
            else {}
        )
        probe_files = sorted(
            str(path.relative_to(probe))
            for path in probe.rglob("*")
            if path.is_file()
        )
        report.update(
            {
                "process_exit": run.returncode,
                "latency_ms": latency_ms,
                "stdout": run.stdout.strip(),
                "stderr": run.stderr.strip(),
                "usage": usage,
                "probe_files": probe_files,
                "isolated_hermes_home_files": sorted(
                    str(path.relative_to(hermes_home))
                    for path in hermes_home.rglob("*")
                    if path.is_file()
                ),
            }
        )

    postimage = _tracked_snapshot()
    changed = sorted(
        key
        for key in set(preimage) | set(postimage)
        if preimage.get(key) != postimage.get(key)
    )
    user_config_after = _optional_sha(user_config)
    report.update(
        {
            "tracked_source_changed": changed,
            "tracked_source_mutation": bool(changed),
            "real_user_config_path": str(user_config),
            "real_user_config_sha_before": user_config_before,
            "real_user_config_sha_after": user_config_after,
            "real_user_config_unchanged": (
                user_config_before == user_config_after
            ),
        }
    )

    usage = report.get("usage") or {}
    gates = {
        "version": (
            version_run.returncode == 0
            and EXPECTED_HERMES_VERSION in version_text
        ),
        "process": report.get("process_exit") == 0,
        "semantic": report.get("stdout") == EXPECTED_RESPONSE,
        "stderr": report.get("stderr") == "",
        "usage_completed": (
            usage.get("completed") is True
            and usage.get("failed") is False
        ),
        "usage_model": usage.get("model") == EXPECTED_MODEL,
        "usage_provider": usage.get("provider") == "custom",
        "single_api_call": usage.get("api_calls") == 1,
        "probe_unchanged": report.get("probe_files") == [],
        "source_unchanged": not report.get("tracked_source_mutation"),
        "user_config_unchanged": bool(
            report.get("real_user_config_unchanged")
        ),
    }
    report["gates"] = gates
    report["certification"] = (
        "PASS" if all(gates.values()) else "FAIL_CLOSED"
    )
    report["runtime_admission"] = "NOT_GRANTED_BY_REVALIDATION"
    report["read_only_revalidation"] = (
        "PASS_RUNTIME_HARDBLOCK_PRESERVED"
        if report["certification"] == "PASS"
        else "FAIL_CLOSED"
    )
    report["authority_expanded"] = False

    output = OUT / "HERMES_0_21_3_READ_ONLY_CERTIFICATION.json"
    output.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"EVIDENCE={output}")
    print(f"HERMES_VERSION={version_text}")
    print(f"PROCESS_EXIT={report.get('process_exit')}")
    print(f"EXPECTED_RESPONSE_MATCH={gates['semantic']}")
    print(f"TRACKED_SOURCE_MUTATION={report['tracked_source_mutation']}")
    print(f"REAL_USER_CONFIG_UNCHANGED={gates['user_config_unchanged']}")
    print(f"CERTIFICATION={report['certification']}")
    return 0 if report["certification"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
