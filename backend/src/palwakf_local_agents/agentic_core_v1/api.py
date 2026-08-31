from __future__ import annotations

from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from .contracts import RunRequest
from .providers import HermesProvider, NativeProvider, OllamaProvider
from .registry_projection import build_projection
from .runtime import AgenticRuntime, AuthorityError

UI = """<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>PalWakf Agentic AI</title>
<style>body{font-family:Segoe UI,Tahoma,Arial;background:#f5f7fa;color:#17243a;margin:0}header{background:#0b2e55;color:white;padding:24px}main{max-width:1100px;margin:auto;padding:22px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px}.card{background:white;border:1px solid #dfe5ec;border-radius:13px;padding:17px}.badge{display:inline-block;background:#eef3f8;padding:5px 9px;border-radius:999px;margin:3px}.ok{background:#e6f5eb}.warn{background:#fff3d7}pre{white-space:pre-wrap;background:#101827;color:#d9e6ff;padding:12px;border-radius:10px}</style></head>
<body><header><h1>PalWakf Agentic AI — Core Runtime V1</h1><p>تشغيل محكوم تحت سلطة خارجية — قراءة فقط افتراضيًا.</p></header><main><div class="grid"><div class="card"><h2>Core</h2><div id="h">...</div></div><div class="card"><h2>Ollama</h2><div id="m">...</div></div><div class="card"><h2>Execution Providers</h2><div id="p">...</div></div><div class="card"><h2>Agents</h2><div id="a">...</div></div></div><div class="card" style="margin-top:14px"><h2>حدود السلطة</h2><p>SELF_AUTHORIZATION=FORBIDDEN · CROSS_PROJECT=DENY_BY_DEFAULT · WRITE=SEPARATE_AUTHORITY</p></div><pre id="raw">—</pre></main>
<script>
const raw=document.getElementById('raw');const b=(x,c='')=>`<span class="badge ${c}">${x}</span>`;
async function g(u){const r=await fetch(u);const j=await r.json();raw.textContent=JSON.stringify(j,null,2);return j}
(async()=>{let x=await g('/api/v1/agentic/health');h.innerHTML=b(x.status,x.status==='PASS'?'ok':'warn');x=await g('/api/v1/agentic/providers/models');m.innerHTML=b(x.ollama.healthy?'HEALTHY':'NOT READY',x.ollama.healthy?'ok':'warn')+' '+x.ollama.models.map(v=>b(v)).join('');x=await g('/api/v1/agentic/providers/execution');p.innerHTML=Object.values(x).map(v=>b(v.provider_id+': '+(v.healthy?'HEALTHY':'NOT READY'),v.healthy?'ok':'warn')).join('');x=await g('/api/v1/agentic/agents');a.innerHTML=b(x.length+' agents')+' '+b(x.filter(v=>v.runnable).length+' mapped','ok')})()
</script></body></html>"""


def mount_agentic_core_v1(app: FastAPI, *, project_root: Path, source_commit_sha: str) -> None:
    runtime = AgenticRuntime(project_root, source_commit_sha)
    ollama = OllamaProvider()
    native = NativeProvider()
    hermes = HermesProvider()

    @app.get("/api/v1/agentic/health")
    def health() -> dict:
        agents = build_projection(project_root, source_commit_sha)
        return {
            "status": "PASS" if len(agents) == 14 and all(a.runnable for a in agents) else "FAIL_CLOSED",
            "source_commit_sha": source_commit_sha,
            "agent_count": len(agents),
            "mapped_agent_count": sum(1 for a in agents if a.runnable),
            "self_authorization": "FORBIDDEN",
            "authority_expansion": "FORBIDDEN",
            "default_execution": "READ_ONLY",
            "cross_project_access": "DENY_BY_DEFAULT",
        }

    @app.get("/api/v1/agentic/agents")
    def agents() -> list[dict]:
        return [a.model_dump(mode="json") for a in build_projection(project_root, source_commit_sha)]

    @app.get("/api/v1/agentic/providers/models")
    def model_providers() -> dict:
        return {"ollama": ollama.health()}

    @app.get("/api/v1/agentic/providers/execution")
    def execution_providers() -> dict:
        return {"native": native.health(), "hermes": hermes.health()}

    @app.post("/api/v1/agentic/runs")
    def run(request: RunRequest) -> dict:
        try:
            return runtime.execute(request).model_dump(mode="json")
        except AuthorityError as error:
            raise HTTPException(status_code=403, detail={"code": str(error), "fail_closed": True}) from error

    @app.get("/agentic-core", response_class=HTMLResponse, include_in_schema=False)
    def ui() -> HTMLResponse:
        return HTMLResponse(UI)
