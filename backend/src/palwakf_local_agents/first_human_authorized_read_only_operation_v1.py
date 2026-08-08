from __future__ import annotations

import hashlib
import json
import os
import tempfile
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, FastAPI, HTTPException, Query
from pydantic import BaseModel, Field

from palwakf_local_agents.operational_core_v1.codebase_index import CodebaseIndexer
from palwakf_local_agents import quality_accepted_tools_goal_planner_binding_v1 as planner

CONTRACT_ID = "FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_V1"
OPERATION_TYPE = "READ_ONLY_CODEBASE_INDEX_AND_STRUCTURE_REPORT"
TOOL_ID = "native-code-index"
API_PREFIX = "/api/v1/operational-core/first-read-only-operation"
_ALLOWED_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml"}
_EXCLUDED_DIRS = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", "backups", "runtime_state"}
_LOCK = threading.RLock()

class ExecuteRequest(BaseModel):
    operation_contract_id: str = CONTRACT_ID
    operation_key: str = Field(min_length=6, max_length=160)
    goal_id: str = Field(min_length=3, max_length=160)
    plan_version: str = Field(default="first-read-only-operation-v1", min_length=2, max_length=120)
    tool_id: str = TOOL_ID
    human_approval_reference: str = Field(min_length=12, max_length=500)
    human_authority_confirmed: bool
    confirm_read_only_scope: bool
    detail_limit: int = Field(default=250, ge=20, le=500)

def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()

def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest().upper()

def _atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd,temp_name=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=str(path.parent)); os.close(fd)
    temp=Path(temp_name)
    try:
        temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8',newline='\n')
        os.replace(temp,path)
    finally:
        temp.unlink(missing_ok=True)

def _append_jsonl(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a',encoding='utf-8',newline='\n') as f:
        f.write(json.dumps(value,ensure_ascii=False)+'\n')

class FirstHumanAuthorizedReadOnlyOperationService:
    def __init__(self, project_root: Path) -> None:
        self.project_root=project_root.resolve()
        self.runtime_root=self.project_root/'runtime_state/operational_core_v1/first_human_authorized_read_only_operation_v1'
        self.runs_root=self.runtime_root/'runs'; self.latest_file=self.runtime_root/'latest.json'; self.events_file=self.runtime_root/'events.jsonl'
        self.indexer=CodebaseIndexer(self.project_root)

    def contract(self) -> dict[str, Any]:
        return {
            'contract_id':CONTRACT_ID,'operation_type':OPERATION_TYPE,'tool_id':TOOL_ID,
            'quality_requirement':{'quality_state':'QUALITY_ACCEPTED','planner_state':'SELECTABLE','baseline_present':True},
            'human_authority':'REQUIRED_PER_OPERATION','read_scope':list(CodebaseIndexer.allowed_roots),
            'evidence_write_scope':'runtime_state/operational_core_v1/first_human_authorized_read_only_operation_v1',
            'boundaries':{'production_execution':'NOT_AUTHORIZED','source_write':'BLOCKED','database_write':'NONE','model_execution':'NONE','shell':'BLOCKED','git':'BLOCKED','network':'BLOCKED','self_apply':'BLOCKED','external_process':'NONE','file_content_in_api':'NOT_RETURNED','absolute_paths_in_api':'NOT_RETURNED'}
        }

    def health(self) -> dict[str, Any]:
        native=planner.load_quality_snapshot().get('tools',{}).get(TOOL_ID,{})
        return {'status':'ok','contract_id':CONTRACT_ID,'tool_id':TOOL_ID,'quality_state':native.get('quality_state','UNASSESSED'),'planner_state':native.get('planner_state','BLOCKED_UNASSESSED'),'baseline_present':bool(native.get('baseline_present')),'human_authority':'REQUIRED','operation_execution':'EXPLICIT_REQUEST_ONLY','source_mutation':'BLOCKED','model_shell_git_network':'BLOCKED'}

    def _iter_source_files(self):
        seen=0
        for root_rel in CodebaseIndexer.allowed_roots:
            root=(self.project_root/root_rel).resolve()
            try: root.relative_to(self.project_root)
            except ValueError: continue
            if not root.exists(): continue
            for path in root.rglob('*'):
                if seen>=3000: return
                if not path.is_file() or path.suffix.lower() not in _ALLOWED_EXTENSIONS: continue
                if any(part in _EXCLUDED_DIRS for part in path.parts): continue
                try:
                    if path.stat().st_size>1_500_000: continue
                except OSError: continue
                seen+=1; yield path

    def _source_manifest(self) -> dict[str, Any]:
        records=[]; total=0
        for path in self._iter_source_files():
            try:
                data=path.read_bytes(); rel=path.resolve().relative_to(self.project_root).as_posix()
            except (OSError,ValueError): continue
            total+=len(data); records.append((rel,len(data),_sha256_bytes(data)))
        records.sort(key=lambda x:x[0])
        digest=_sha256_bytes(json.dumps(records,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        return {'file_count':len(records),'total_bytes':total,'digest':digest}

    def _planner_selection(self, request: ExecuteRequest) -> dict[str, Any]:
        native=planner.load_quality_snapshot().get('tools',{}).get(TOOL_ID)
        if not isinstance(native,dict):
            raise HTTPException(status_code=409,detail={'code':'QUALITY_TOOL_DECISION_MISSING','tool_id':TOOL_ID})
        required={'quality_state':'QUALITY_ACCEPTED','planner_state':'SELECTABLE','baseline_present':True}
        observed={k:native.get(k) for k in required}
        if observed!=required:
            raise HTTPException(status_code=409,detail={'code':'QUALITY_GATE_NOT_SATISFIED','required':required,'observed':observed})
        plan=planner.PlannerEvaluationRequest(goal_id=request.goal_id,plan_version=request.plan_version,allow_limited_candidates=False,human_approval_reference=None,steps=[planner.PlanStep(step_id='first-read-only-operation',title='فهرسة الشيفرة المقروءة فقط',required_capabilities=['code_index'],candidate_tool_ids=[TOOL_ID])])
        result=planner.evaluate_plan(plan); selected=result.get('steps',[{}])[0].get('selected_tool')
        if not isinstance(selected,dict) or selected.get('tool_id')!=TOOL_ID:
            raise HTTPException(status_code=409,detail={'code':'PLANNER_DID_NOT_SELECT_NATIVE_CODE_INDEX'})
        if result.get('execution_performed') is not False or result.get('state_persisted') is not False:
            raise HTTPException(status_code=409,detail={'code':'PLANNER_PREVIEW_CONTRACT_FAILED'})
        return {'tool_id':TOOL_ID,'quality_state':native.get('quality_state'),'planner_state':native.get('planner_state'),'score':native.get('score'),'baseline_id':native.get('baseline_id'),'suite_id':native.get('suite_id'),'planner_preview':{'execution_performed':result.get('execution_performed'),'state_persisted':result.get('state_persisted'),'human_authority_required':result.get('human_authority_required')}}

    def _find_existing(self,key_hash:str) -> dict[str,Any]|None:
        if not self.runs_root.is_dir(): return None
        for path in sorted(self.runs_root.glob('*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True):
            try: record=json.loads(path.read_text(encoding='utf-8'))
            except (OSError,json.JSONDecodeError): continue
            if record.get('operation_key_hash')==key_hash: return record
        return None

    def latest(self) -> dict[str,Any]:
        if not self.latest_file.is_file(): return {'available':False,'contract_id':CONTRACT_ID,'message':'NO_COMPLETED_OPERATION'}
        return {'available':True,'operation':json.loads(self.latest_file.read_text(encoding='utf-8'))}

    def list_runs(self,limit:int) -> dict[str,Any]:
        limit=max(1,min(int(limit),50)); records=[]
        if self.runs_root.is_dir():
            for path in sorted(self.runs_root.glob('*.json'),key=lambda p:p.stat().st_mtime_ns,reverse=True)[:limit]:
                try: records.append(json.loads(path.read_text(encoding='utf-8')))
                except (OSError,json.JSONDecodeError): pass
        return {'runs':records,'count':len(records),'limit':limit}

    def execute(self, request: ExecuteRequest) -> dict[str, Any]:
        if request.operation_contract_id!=CONTRACT_ID: raise HTTPException(status_code=422,detail={'code':'OPERATION_CONTRACT_ID_MISMATCH'})
        if request.tool_id!=TOOL_ID: raise HTTPException(status_code=422,detail={'code':'TOOL_NOT_AUTHORIZED','allowed_tool':TOOL_ID})
        if request.human_authority_confirmed is not True: raise HTTPException(status_code=422,detail={'code':'HUMAN_AUTHORITY_CONFIRMATION_REQUIRED'})
        if request.confirm_read_only_scope is not True: raise HTTPException(status_code=422,detail={'code':'READ_ONLY_SCOPE_CONFIRMATION_REQUIRED'})
        key_hash=_sha256_bytes(request.operation_key.encode('utf-8')); approval_hash=_sha256_bytes(request.human_approval_reference.encode('utf-8'))
        with _LOCK:
            existing=self._find_existing(key_hash)
            if existing is not None: return {'result':'ALREADY_COMPLETED','idempotent_reuse':True,'operation':existing}
            selection=self._planner_selection(request); before=self._source_manifest(); index=self.indexer.build(detail_limit=request.detail_limit); after=self._source_manifest()
            if before['digest']!=after['digest']:
                raise HTTPException(status_code=409,detail={'code':'SOURCE_CHANGED_DURING_READ_ONLY_OPERATION','before':before,'after':after})
            run_id=str(uuid.uuid4()); completed=_utc_now()
            report={'schema':'palwakf.local_agents.first_read_only_operation.v1','run_id':run_id,'contract_id':CONTRACT_ID,'operation_type':OPERATION_TYPE,'operation_key_hash':key_hash,'goal_id':request.goal_id,'plan_version':request.plan_version,'completed_at':completed,'human_authority':{'confirmed':True,'approval_reference_hash':approval_hash,'approval_reference_stored':False},'quality_gate':selection,'operation':{'performed':True,'tool_id':TOOL_ID,'implementation':'python_native_codebase_indexer','read_only':True,'detail_limit':request.detail_limit},'source_integrity':{'pre_manifest':before,'post_manifest':after,'source_mutation_detected':False},'evidence':{'summary':index.get('summary',{}),'scope':index.get('scope',[]),'limits':index.get('limits',{}),'routes':index.get('routes',[]),'symbols':index.get('symbols',[]),'components':index.get('components',[]),'documents':index.get('documents',[]),'files':index.get('files',[])},'boundaries':{'production_execution':'NOT_AUTHORIZED','source_write':'NONE','database_write':'NONE','model_execution':'NONE','shell':'NONE','git':'NONE','network':'NONE','self_apply':'NONE','external_process':'NONE','runtime_evidence_write':'LOCAL_JSON_JSONL_ONLY'}}
            _atomic_write_json(self.runs_root/f'{run_id}.json',report); _atomic_write_json(self.latest_file,report)
            _append_jsonl(self.events_file,{'event_id':str(uuid.uuid4()),'occurred_at':completed,'event_type':'FIRST_HUMAN_AUTHORIZED_READ_ONLY_OPERATION_COMPLETED','run_id':run_id,'operation_key_hash':key_hash,'tool_id':TOOL_ID,'source_mutation_detected':False,'model_execution':'NONE','shell_git_network':'NONE'})
            return {'result':'COMPLETED','idempotent_reuse':False,'operation':report}

def create_router(project_root: Path) -> APIRouter:
    service=FirstHumanAuthorizedReadOnlyOperationService(project_root)
    router=APIRouter(prefix=API_PREFIX,tags=['first-human-authorized-read-only-operation-v1'])
    @router.get('/health')
    def health(): return service.health()
    @router.get('/contract')
    def contract(): return service.contract()
    @router.get('/latest')
    def latest(): return service.latest()
    @router.get('/runs')
    def runs(limit:int=Query(default=10,ge=1,le=50)): return service.list_runs(limit)
    @router.post('/execute')
    def execute(request:ExecuteRequest): return service.execute(request)
    return router

def install_first_human_authorized_read_only_operation_v1(app:FastAPI,*,project_root:Path)->None:
    state=getattr(app,'state',None)
    if state is not None and getattr(state,'first_human_authorized_read_only_operation_v1_installed',False): return
    app.include_router(create_router(project_root.resolve()))
    if state is not None: state.first_human_authorized_read_only_operation_v1_installed=True
