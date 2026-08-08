from __future__ import annotations

import ast
import hashlib
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


_ROUTE_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
_COMPONENT_RE = re.compile(r"(?:export\s+)?(?:default\s+)?function\s+([A-Z][A-Za-z0-9_]*)|(?:export\s+)?const\s+([A-Z][A-Za-z0-9_]*)\s*=", re.MULTILINE)
_FRONTEND_ROUTE_RE = re.compile(r"['\"](/agent-console(?:/[a-zA-Z0-9_./{}:-]+)?)['\"]")
_MD_HEADING_RE = re.compile(r"^#{1,3}\s+(.+)$", re.MULTILINE)


class CodebaseIndexer:
    allowed_roots = (
        "frontend/src",
        "backend/src/palwakf_local_agents",
        "agents",
        "docs",
    )
    allowed_extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".md", ".json", ".yaml", ".yml", ".toml"}
    excluded_dirs = {".git", ".venv", "node_modules", "dist", "build", "__pycache__", "backups", "runtime_state"}

    def __init__(self, project_root: Path) -> None:
        self.project_root = project_root.resolve()

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    def _iter_files(self):
        seen = 0
        for root_rel in self.allowed_roots:
            root = (self.project_root / root_rel).resolve()
            try:
                root.relative_to(self.project_root)
            except ValueError:
                continue
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if seen >= 3000:
                    return
                if not path.is_file() or path.suffix.lower() not in self.allowed_extensions:
                    continue
                if any(part in self.excluded_dirs for part in path.parts):
                    continue
                try:
                    if path.stat().st_size > 1_500_000:
                        continue
                except OSError:
                    continue
                seen += 1
                yield path

    def _relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.project_root).as_posix()

    @staticmethod
    def _safe_text(path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return path.read_text(encoding="utf-8", errors="replace")

    @staticmethod
    def _decorator_route(node: ast.AST) -> tuple[str, str] | None:
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            return None
        method = node.func.attr.lower()
        if method not in _ROUTE_METHODS or not node.args:
            return None
        first = node.args[0]
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return method.upper(), first.value
        return None

    def build(self, detail_limit: int = 250) -> dict[str, Any]:
        detail_limit = max(20, min(int(detail_limit), 500))
        symbols: list[dict[str, Any]] = []
        routes: list[dict[str, Any]] = []
        components: list[dict[str, Any]] = []
        docs: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []
        ext_counts: Counter[str] = Counter()
        total_bytes = 0

        for path in self._iter_files():
            rel = self._relative(path)
            try:
                stat = path.stat()
                total_bytes += stat.st_size
                ext_counts[path.suffix.lower() or "<none>"] += 1
                if len(files) < detail_limit:
                    files.append({"path": rel, "size": stat.st_size, "extension": path.suffix.lower()})
                text = self._safe_text(path)
            except OSError:
                continue

            if path.suffix.lower() == ".py":
                try:
                    tree = ast.parse(text)
                except SyntaxError:
                    continue
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and len(symbols) < detail_limit:
                        kind = "class" if isinstance(node, ast.ClassDef) else ("async_function" if isinstance(node, ast.AsyncFunctionDef) else "function")
                        symbols.append({"name": node.name, "kind": kind, "path": rel, "line": getattr(node, "lineno", None)})
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        for deco in node.decorator_list:
                            route = self._decorator_route(deco)
                            if route and len(routes) < detail_limit:
                                routes.append({"method": route[0], "route": route[1], "handler": node.name, "path": rel, "line": getattr(node, "lineno", None)})
            elif path.suffix.lower() in {".ts", ".tsx", ".js", ".jsx"}:
                for match in _COMPONENT_RE.finditer(text):
                    name = match.group(1) or match.group(2)
                    if name and len(components) < detail_limit:
                        line = text.count("\n", 0, match.start()) + 1
                        components.append({"name": name, "path": rel, "line": line})
                for match in _FRONTEND_ROUTE_RE.finditer(text):
                    if len(routes) >= detail_limit:
                        break
                    routes.append({"method": "UI", "route": match.group(1), "handler": None, "path": rel, "line": text.count("\n", 0, match.start()) + 1})
            elif path.suffix.lower() == ".md":
                headings = _MD_HEADING_RE.findall(text)
                if len(docs) < detail_limit:
                    docs.append({"path": rel, "headings": headings[:8], "heading_count": len(headings)})

        fingerprint_source = json_fingerprint({
            "files": [(item["path"], item["size"]) for item in files],
            "routes": [(item["method"], item["route"], item["path"]) for item in routes],
            "components": [(item["name"], item["path"]) for item in components],
        })
        return {
            "schema": "palwakf.local_agents.codebase_index.v1",
            "generated_at": self._now(),
            "scope": list(self.allowed_roots),
            "read_only": True,
            "summary": {
                "file_count": sum(ext_counts.values()),
                "total_bytes": total_bytes,
                "symbol_count": len(symbols),
                "route_count": len(routes),
                "component_count": len(components),
                "document_count": len(docs),
                "by_extension": dict(sorted(ext_counts.items())),
                "fingerprint": fingerprint_source,
            },
            "symbols": symbols,
            "routes": dedupe(routes, ("method", "route", "path")),
            "components": dedupe(components, ("name", "path")),
            "documents": docs,
            "files": files,
            "limits": {"detail_limit": detail_limit, "max_files": 3000, "max_file_bytes": 1_500_000},
        }

    def metadata_for(self, relative_path: str) -> dict[str, Any]:
        normalized = relative_path.replace("\\", "/").lstrip("/")
        candidate = (self.project_root / normalized).resolve()
        try:
            candidate.relative_to(self.project_root)
        except ValueError as exc:
            raise ValueError("PATH_OUTSIDE_PROJECT") from exc
        allowed = any(normalized == root or normalized.startswith(root + "/") for root in self.allowed_roots)
        if not allowed:
            raise ValueError("PATH_NOT_IN_ALLOWED_ROOTS")
        if not candidate.is_file():
            raise FileNotFoundError(normalized)
        stat = candidate.stat()
        h = hashlib.sha256()
        with candidate.open("rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return {
            "path": normalized,
            "size": stat.st_size,
            "extension": candidate.suffix.lower(),
            "sha256": h.hexdigest().upper(),
            "modified_ns": stat.st_mtime_ns,
            "content_returned": False,
        }


def dedupe(items: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    seen = set()
    result = []
    for item in items:
        marker = tuple(item.get(key) for key in keys)
        if marker in seen:
            continue
        seen.add(marker)
        result.append(item)
    return result


def json_fingerprint(value: Any) -> str:
    import json
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest().upper()
