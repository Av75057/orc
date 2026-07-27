import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlparse, parse_qs


def _json_response(data: Any, status: int = 200) -> tuple:
    body = json.dumps(data, indent=2, default=str).encode("utf-8")
    return (status, {"Content-Type": "application/json"}, body)


def _text_response(text: str, status: int = 200,
                   content_type: str = "text/plain") -> tuple:
    body = text.encode("utf-8")
    return (status, {"Content-Type": content_type}, body)


def _error(msg: str, status: int = 400) -> tuple:
    return _json_response({"error": msg}, status)


def _read_file_or_404(path: Path) -> Optional[tuple]:
    if not path.exists():
        return _json_response({"error": "File not found", "path": str(path)}, 404)
    try:
        return _text_response(path.read_text(encoding="utf-8"))
    except OSError as e:
        return _json_response({"error": f"Cannot read file: {e}", "path": str(path)}, 500)


def _dir_tree(base: Path) -> dict:
    if not base.exists():
        return {"path": str(base), "type": "missing", "children": []}
    return _build_tree(base)


def _build_tree(path: Path) -> dict:
    if path.is_file():
        return {"name": path.name, "type": "file", "size": path.stat().st_size}
    children = []
    try:
        for child in sorted(path.iterdir()):
            children.append(_build_tree(child))
    except OSError:
        pass
    return {"name": path.name, "type": "directory", "children": children}


class GraceAPI:
    def __init__(self, base_dir: str = "."):
        self._base = Path(base_dir).resolve()

    def _abs(self, *parts: str) -> Path:
        return self._base.joinpath(*parts).resolve()

    def handle_health(self) -> tuple:
        return _json_response({"status": "ok", "version": "1.0"})

    def handle_state(self) -> tuple:
        return _read_file_or_404(self._abs("grace_state.json"))

    def handle_artifacts(self) -> tuple:
        docs = self._abs("docs")
        if not docs.exists():
            return _json_response({"path": "docs", "files": []})
        files = []
        for f in sorted(docs.iterdir()):
            if f.is_file():
                files.append({
                    "name": f.name,
                    "path": str(f.relative_to(self._base)),
                    "size": f.stat().st_size,
                })
        return _json_response({"path": "docs", "files": files})

    def handle_artifact_create(self, body: Optional[bytes]) -> tuple:
        if not body:
            return _error("Request body is required")
        data = {}
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error("Invalid JSON body")
        rel_path = data.get("path", "").lstrip("/")
        if not rel_path:
            return _error("Missing 'path' field")
        ext = os.path.splitext(rel_path)[1].lower()
        if ext not in (".xml", ".md"):
            return _error(f"File extension '{ext}' not allowed. Only .xml and .md are permitted.", 403)
        full = self._abs("docs", rel_path)
        docs_dir = self._abs("docs")
        if not str(full).startswith(str(docs_dir) + os.sep):
            return _error("Path traversal not allowed", 403)
        if full.exists():
            return _error(f"File already exists: {rel_path}", 409)
        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text("", encoding="utf-8")
        except OSError as e:
            return _json_response({"error": f"Cannot create file: {e}", "path": str(full)}, 500)
        return _json_response({"success": True, "path": str(full.relative_to(self._base))})


    def handle_artifact_save(self, body: Optional[bytes]) -> tuple:
        if not body:
            return _error("Request body is required")
        try:
            data = json.loads(body.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return _error("Invalid JSON body")

        rel_path = data.get("path", "").lstrip("/")
        content = data.get("content", "")
        if not rel_path:
            return _error("Missing 'path' field")

        full = self._abs(rel_path)
        docs_dir = self._abs("docs")
        if not str(full).startswith(str(docs_dir)):
            return _error("Path must be inside docs/", 403)

        try:
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_text(content, encoding="utf-8")
        except OSError as e:
            return _json_response({"error": f"Cannot save file: {e}"}, 500)

        return _json_response({"success": True, "path": str(full.relative_to(self._base))})

    def handle_artifact_file(self, query: str, body: Optional[bytes]) -> tuple:
        params = parse_qs(urlparse(f"?{query}").query)
        paths = params.get("path", [])
        if not paths:
            return _json_response({"error": "Missing 'path' parameter"}, 400)
        rel_path = paths[0].lstrip("/")
        full = self._abs(rel_path)
        docs_dir = self._abs("docs")
        if not str(full).startswith(str(docs_dir)):
            return _json_response({"error": "Path must be inside docs/"}, 403)
        if body is not None:
            try:
                data = json.loads(body.decode("utf-8"))
                content = data.get("content", "")
                full.write_text(content, encoding="utf-8")
                return _json_response({"status": "saved", "path": rel_path})
            except (OSError, json.JSONDecodeError, UnicodeDecodeError) as e:
                return _json_response({"error": f"Cannot save: {e}"}, 500)
        return _read_file_or_404(full)

    def handle_evidence_tree(self) -> tuple:
        return _json_response(_dir_tree(self._abs("evidence")))

    def handle_evidence_file(self, query: str) -> tuple:
        params = parse_qs(urlparse(f"?{query}").query)
        paths = params.get("path", [])
        if not paths:
            return _json_response({"error": "Missing 'path' query parameter"}, 400)
        rel_path = paths[0].lstrip("/")
        full = self._abs("evidence", rel_path)
        if not str(full).startswith(str(self._abs("evidence"))):
            return _json_response({"error": "Path traversal not allowed"}, 403)
        return _read_file_or_404(full)

    def handle_run(self, body: Optional[bytes]) -> tuple:
        plan_arg = "docs/development-plan.xml"
        worker_cmd = ""
        state_path = ""
        extra_env = {}
        if body:
            try:
                data = json.loads(body.decode("utf-8"))
                plan_arg = data.get("plan", plan_arg)
                worker_cmd = data.get("worker", "")
                state_path = data.get("state", "")
                if data.get("openai_api_key"):
                    extra_env["OPENAI_API_KEY"] = data["openai_api_key"]
                if data.get("github_token"):
                    extra_env["GITHUB_TOKEN"] = data["github_token"]
                if data.get("llm_model"):
                    extra_env["LLM_MODEL"] = data["llm_model"]
                if data.get("llm_api_url"):
                    extra_env["LLM_API_URL"] = data["llm_api_url"]
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass
        cmd = [sys.executable, "-m", "src.grace.cli", plan_arg]
        if worker_cmd:
            cmd.extend(["--worker", worker_cmd])
        if state_path:
            cmd.extend(["--state", state_path])
        if data.get("workspace"):
            cmd.extend(["--workspace", data["workspace"]])
        env = {**os.environ, **extra_env}
        try:
            proc = subprocess.Popen(cmd, cwd=str(self._base),
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, env=env)
            stdout, stderr = proc.communicate(timeout=120)
            return _json_response({
                "status": "completed",
                "exit_code": proc.returncode,
                "stdout": stdout, "stderr": stderr,
            })
        except subprocess.TimeoutExpired:
            proc.kill()
            return _json_response({"status": "timeout", "exit_code": -1})
        except OSError as e:
            return _json_response({"error": f"Failed to start: {e}"}, 500)
        except Exception:
            return _json_response({"error": "Unknown error"}, 500)

    def _delete_state(self) -> tuple:
        state_path = self._abs("grace_state.json")
        try:
            if state_path.exists():
                state_path.unlink()
            return _json_response({"status": "state_reset"})
        except OSError as e:
            return _json_response({"error": f"Cannot delete state: {e}"}, 500)

    def dispatch(self, method: str, path: str,
                 body: Optional[bytes] = None,
                 query: str = "") -> tuple:
        if method == "GET" and path == "/api/health":
            return self.handle_health()
        if method == "GET" and path == "/api/state":
            return self.handle_state()
        if method == "GET" and path == "/api/artifacts":
            return self.handle_artifacts()
        if method == "POST" and path == "/api/artifacts/save":
            return self.handle_artifact_save(body)
        if method == "POST" and path == "/api/artifacts/create":
            return self.handle_artifact_create(body)
        if method in ("GET", "POST") and path == "/api/artifacts/file":
            return self.handle_artifact_file(query, body)
        if method == "GET" and path == "/api/evidence":
            return self.handle_evidence_tree()
        if method == "GET" and path == "/api/evidence/file":
            return self.handle_evidence_file(query)
        if method == "POST" and path == "/api/run":
            return self.handle_run(body)
        if method == "DELETE" and path == "/api/state":
            return self._delete_state()
        return _json_response({"error": "Not found"}, 404)



