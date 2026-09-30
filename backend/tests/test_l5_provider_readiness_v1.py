import pytest
from palwakf_local_agents.agentic_core_v1.provider_readiness import (
    HardwareProfile,
    ModelCapabilityEvidence,
    ProviderCapabilityError,
    WorkloadProfile,
    select_certified_local_route,
)
from palwakf_local_agents.agentic_core_v1.providers import OllamaProvider
from pydantic import ValidationError


def hardware(cpu: str = "cpu-a") -> HardwareProfile:
    return HardwareProfile(
        machine="Futuer-IT",
        cpu=cpu,
        gpu_devices=("GeForce GTX 1050",),
        gpu_memory_mb=(4096,),
        system_memory_mb=16384,
    )


def workload(
    workload_class: str = "REPOSITORY_DIAGNOSTIC_MEDIUM",
    *,
    structured: bool = True,
    tools: bool = False,
) -> WorkloadProfile:
    return WorkloadProfile(
        task_class="READ_ONLY_DIAGNOSTIC",
        workload_class=workload_class,
        prompt_tokens_estimate=900,
        min_context_length=8192,
        requires_structured_output=structured,
        requires_tools=tools,
        max_latency_ms=20_000,
        total_deadline_ms=45_000,
    )


def evidence(
    *,
    model: str = "palwakf-llama3.2-3b-64k:ctx64k",
    provider_version: str = "0.34.2",
    hw: HardwareProfile | None = None,
    wl: WorkloadProfile | None = None,
    success: bool = True,
    latency_ms: float = 8_000,
    context_length: int = 131_072,
    structured: bool = True,
    tools: bool = True,
) -> ModelCapabilityEvidence:
    hw = hw or hardware()
    wl = wl or workload()
    return ModelCapabilityEvidence(
        provider_version=provider_version,
        model=model,
        hardware_fingerprint=hw.fingerprint,
        workload_fingerprint=wl.fingerprint,
        success=success,
        latency_ms=latency_ms,
        context_length=context_length,
        structured_output=structured,
        tools=tools,
        prompt_eval_count=900,
        prompt_tokens_per_second=120.0,
        eval_count=20,
        tokens_per_second=18.0,
        failure_reason=None if success else "TIMEOUT",
    )


def select(items: list[ModelCapabilityEvidence], *, hw=None, wl=None):
    hw = hw or hardware()
    wl = wl or workload()
    return select_certified_local_route(
        items,
        hardware=hw,
        workload=wl,
        current_provider_version="0.34.2",
        eligible_models=(
            "palwakf-llama3.2-3b-64k:ctx64k",
            "llama3.2:3b",
        ),
    )


def test_exact_workload_evidence_selects_local_model() -> None:
    decision = select([evidence()])
    assert decision.model == "palwakf-llama3.2-3b-64k:ctx64k"
    assert decision.authority_expanded is False


def test_failed_preferred_model_is_skipped_for_fallback() -> None:
    preferred = evidence(success=False)
    fallback = evidence(model="llama3.2:3b")
    decision = select([preferred, fallback])
    assert decision.model == "llama3.2:3b"


@pytest.mark.parametrize(
    "mutator",
    [
        lambda item: item.model_copy(update={"provider_version": "0.33.3"}),
        lambda item: item.model_copy(
            update={"hardware_fingerprint": hardware("cpu-b").fingerprint}
        ),
        lambda item: item.model_copy(
            update={
                "workload_fingerprint": workload(
                    "TINY_MICRO_BENCHMARK"
                ).fingerprint
            }
        ),
        lambda item: item.model_copy(update={"latency_ms": 30_000}),
        lambda item: item.model_copy(update={"context_length": 4096}),
        lambda item: item.model_copy(update={"structured_output": False}),
    ],
)
def test_stale_or_insufficient_evidence_fails_closed(mutator) -> None:
    with pytest.raises(
        ProviderCapabilityError,
        match="NO_LOCAL_MODEL_CERTIFIED_FOR_WORKLOAD",
    ):
        select([mutator(evidence())])


def test_cloud_model_is_never_eligible() -> None:
    item = evidence(model="deepseek-v4-flash:cloud")
    with pytest.raises(ProviderCapabilityError):
        select_certified_local_route(
            [item],
            hardware=hardware(),
            workload=workload(),
            current_provider_version="0.34.2",
            eligible_models=("deepseek-v4-flash:cloud",),
        )


def test_tool_requirement_must_be_proven() -> None:
    wl = workload(tools=True)
    item = evidence(wl=wl, tools=False)
    with pytest.raises(ProviderCapabilityError):
        select([item], wl=wl)


def test_total_deadline_must_bound_attempt_latency() -> None:
    with pytest.raises(
        ValidationError,
        match="ATTEMPT_LATENCY_EXCEEDS_TOTAL_DEADLINE",
    ):
        WorkloadProfile(
            task_class="READ_ONLY_DIAGNOSTIC",
            workload_class="INVALID_DEADLINE",
            prompt_tokens_estimate=900,
            min_context_length=8192,
            max_latency_ms=50_000,
            total_deadline_ms=20_000,
        )


def test_gpu_memory_shape_is_fail_closed() -> None:
    with pytest.raises(
        ValidationError,
        match="GPU_MEMORY_DEVICE_COUNT_MISMATCH",
    ):
        HardwareProfile(
            machine="Futuer-IT",
            cpu="cpu-a",
            gpu_devices=("gpu-a", "gpu-b"),
            gpu_memory_mb=(4096,),
            system_memory_mb=16384,
        )


def test_empty_evidence_is_explicitly_unresolved() -> None:
    with pytest.raises(
        ProviderCapabilityError,
        match="NO_LOCAL_MODEL_CERTIFIED_FOR_WORKLOAD",
    ):
        select([])

def test_ollama_generate_prefers_explicit_json_schema(monkeypatch) -> None:
    provider = OllamaProvider()
    captured: dict[str, object] = {}

    def fake_request(
        path: str,
        payload: dict[str, object] | None = None,
        timeout: int = 10,
    ) -> dict[str, object]:
        captured["path"] = path
        captured["payload"] = payload or {}
        captured["timeout"] = timeout
        return {
            "model": "model-a",
            "response": "{}",
            "prompt_eval_count": 1,
            "prompt_eval_duration": 1_000_000_000,
            "eval_count": 1,
            "eval_duration": 1_000_000_000,
        }

    monkeypatch.setattr(provider, "_request", fake_request)
    schema = {
        "type": "object",
        "properties": {"authority_expanded": {"type": "boolean"}},
        "required": ["authority_expanded"],
    }
    provider.generate(
        "model-a",
        "return structured output",
        json_mode=True,
        format_schema=schema,
        timeout=17,
    )

    assert captured["path"] == "/api/generate"
    assert captured["timeout"] == 17
    payload = captured["payload"]
    assert isinstance(payload, dict)
    assert payload["format"] == schema
