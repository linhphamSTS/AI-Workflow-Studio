#!/usr/bin/env python3
"""
Diagram-WorkFlow web app — a local UI over the `linhpham-diagram` skill.

Flow (one workspace per project):
    inputs (prompt / uploaded docs / a folder)
      -> REFINE   : `claude -p` runs the skill head-less -> spec/manifest.json  (GATE)
      -> confirm / edit the manifest in the browser
      -> GENERATE : deterministic Python renderers -> output/diagrams/*.png/.svg/.drawio/.docx
      -> PREVIEW  : view PNGs; iterate (edit + re-run) until happy
      -> EXPORT   : download a zip of the output folder

Refine is an LLM step (the real skill via the installed `claude` CLI, no API key).
Generate is pure Python (fast, no LLM) using the skill's build_cloud / build_graph /
build_sequence / build_diagram_doc / diagram_check scripts.

Run:
    python webapp/server.py            # -> http://127.0.0.1:8000
    DIAGRAM_REFINE_MODEL=sonnet python webapp/server.py   # optional model override
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import threading
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

# --------------------------------------------------------------------------- paths
# webapp/ sits at the monorepo root, beside the skill folders:
#   <repo>/webapp/  <repo>/diagram/  <repo>/technical-proposal/
WEBAPP_DIR = Path(__file__).resolve().parent
REPO_ROOT = WEBAPP_DIR.parent
SKILL_DIR = REPO_ROOT / "diagram" / "skill" / "linhpham-diagram"
SCRIPTS_DIR = SKILL_DIR / "scripts"
# (future) proposal generation drives the sibling skill:
PROPOSAL_SKILL_DIR = REPO_ROOT / "technical-proposal" / "skill" / "linhpham-technicalproposal"
# Where a user's workspaces (their inputs + generated output) live. Override with
# DIAGRAM_WORKSPACES_DIR to keep data outside the repo, or to point tests elsewhere
# so they never touch real data.
WORKSPACES_DIR = Path(os.environ.get("DIAGRAM_WORKSPACES_DIR", str(WEBAPP_DIR / "workspaces"))).resolve()
STATIC_DIR = WEBAPP_DIR / "static"
REFINE_PROMPT_TMPL = WEBAPP_DIR / "refine_prompt.md"
PROPOSAL_ANALYZE_TMPL = WEBAPP_DIR / "proposal_analyze_prompt.md"
PROPOSAL_GENERATE_TMPL = WEBAPP_DIR / "proposal_generate_prompt.md"

WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

CLAUDE = shutil.which("claude") or "claude"
REFINE_MODEL = os.environ.get("DIAGRAM_REFINE_MODEL", "").strip()
REFINE_TIMEOUT = int(os.environ.get("DIAGRAM_REFINE_TIMEOUT", "900"))   # seconds
PROPOSAL_ANALYZE_TIMEOUT = int(os.environ.get("PROPOSAL_ANALYZE_TIMEOUT", "1200"))    # 20 min
PROPOSAL_GENERATE_TIMEOUT = int(os.environ.get("PROPOSAL_GENERATE_TIMEOUT", "3600"))  # 60 min (heavy)
RENDER_TIMEOUT = int(os.environ.get("DIAGRAM_RENDER_TIMEOUT", "180"))   # per diagram

RENDERER = {"cloud": "build_cloud.py", "graph": "build_graph.py", "sequence": "build_sequence.py"}

# Run child processes without flashing a console window on Windows. 0 (the default)
# on macOS/Linux, so this is safe cross-platform.
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0


def _hidden_console() -> dict:
    """Spawn kwargs so a child runs in a HIDDEN console on Windows. CREATE_NO_WINDOW gives the
    child NO console, so ITS OWN children each allocate a fresh VISIBLE console (the flash). A
    hidden NEW console is instead INHERITED by grandchildren, so nothing flashes. Used for
    `claude -p`, which internally runs many tools (python/dot/bash). No-op off Windows; set
    DIAGRAM_HIDDEN_CONSOLE=0 to fall back to CREATE_NO_WINDOW."""
    if os.name != "nt":
        return {}
    if os.environ.get("DIAGRAM_HIDDEN_CONSOLE", "1") != "1":
        return {"creationflags": subprocess.CREATE_NO_WINDOW}
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 0  # SW_HIDE
    return {"startupinfo": si, "creationflags": subprocess.CREATE_NEW_CONSOLE}

# in-memory job registry: ws_id -> {"phase","running","log":[...] }
JOBS: dict[str, dict] = {}
JOBS_LOCK = threading.Lock()


# --------------------------------------------------------------------------- helpers
def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _child_env() -> dict:
    """Environment for renderer / claude subprocesses: Graphviz on PATH + UTF-8 io."""
    env = os.environ.copy()
    gv = Path.home() / "graphviz_portable" / "bin"
    if gv.exists():
        env["PATH"] = str(gv) + os.pathsep + env.get("PATH", "")
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def ws_dir(ws_id: str) -> Path:
    d = WORKSPACES_DIR / ws_id
    if not d.exists() or not (d / "meta.json").exists():
        raise HTTPException(404, f"workspace not found: {ws_id}")
    return d


def read_meta(ws_id: str) -> dict:
    return json.loads((ws_dir(ws_id) / "meta.json").read_text(encoding="utf-8"))


def write_meta(ws_id: str, meta: dict) -> None:
    meta["updated"] = _now()
    (WORKSPACES_DIR / ws_id / "meta.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")


def set_status(ws_id: str, status: str, **extra) -> None:
    meta = read_meta(ws_id)
    meta["status"] = status
    meta.update(extra)
    write_meta(ws_id, meta)


def job_log(ws_id: str, line: str) -> None:
    with JOBS_LOCK:
        JOBS.setdefault(ws_id, {"log": []})["log"].append(line)


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    return s or "diagram"


# --------------------------------------------------------------------------- ingest
def run_ingest(ws_id: str, source_dir: Path) -> Path | None:
    """Build spec/_ingest_digest.md from a folder of docs. Returns digest path or None."""
    d = WORKSPACES_DIR / ws_id
    digest = d / "spec" / "_ingest_digest.md"
    digest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SCRIPTS_DIR / "ingest.py"),
           "--dir", str(source_dir), "--out", str(digest)]
    job_log(ws_id, f"$ ingest {source_dir}")
    p = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), env=_child_env(), creationflags=_NO_WINDOW,
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=300)
    if p.stdout:
        job_log(ws_id, p.stdout.strip())
    if p.returncode != 0:
        job_log(ws_id, f"! ingest failed: {p.stderr.strip()[:500]}")
        return None
    return digest if digest.exists() else None


# --------------------------------------------------------------------------- REFINE
def build_refine_prompt(ws_id: str, meta: dict) -> str:
    tmpl = REFINE_PROMPT_TMPL.read_text(encoding="utf-8")
    d = WORKSPACES_DIR / ws_id
    return (tmpl
            .replace("{{MODE}}", meta.get("mode", "text"))
            .replace("{{WORKSPACE_DIR}}", str(d).replace("\\", "/"))
            .replace("{{SKILL_DIR}}", str(SKILL_DIR).replace("\\", "/"))
            .replace("{{PROMPT_TEXT}}", meta.get("prompt", "") or "(no free-text prompt; use the ingest digest)"))


def refine_job(ws_id: str):
    try:
        meta = read_meta(ws_id)
        d = WORKSPACES_DIR / ws_id
        (d / "spec").mkdir(parents=True, exist_ok=True)

        # 1) ingest any uploaded files and/or an external folder into one digest
        sources: list[Path] = []
        inputs_dir = d / "inputs"
        if inputs_dir.exists() and any(inputs_dir.iterdir()):
            sources.append(inputs_dir)
        if meta.get("folder"):
            fp = Path(meta["folder"])
            if fp.exists():
                sources.append(fp)
            else:
                job_log(ws_id, f"! folder not found, ignoring: {fp}")
        # ingest the first available source folder (inputs preferred; else the external folder)
        if sources:
            run_ingest(ws_id, sources[0])

        # 2) drop a stale manifest so a failed run can't look successful
        manifest = d / "spec" / "manifest.json"
        if manifest.exists():
            manifest.unlink()

        # 3) run the skill head-less
        prompt = build_refine_prompt(ws_id, meta)
        (d / "spec" / "_refine_prompt.md").write_text(prompt, encoding="utf-8")
        cmd = [CLAUDE, "-p", prompt,
               "--output-format", "json",
               "--permission-mode", "bypassPermissions",
               "--add-dir", str(SKILL_DIR)]
        if REFINE_MODEL:
            cmd += ["--model", REFINE_MODEL]
        job_log(ws_id, "$ claude -p (refine)  [usually 3-5 minutes: reads the KB, designs the spec]")
        p = subprocess.run(cmd, cwd=str(d), env=_child_env(), **_hidden_console(),
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=REFINE_TIMEOUT)
        tail = (p.stdout or "").strip()[-800:]
        if tail:
            job_log(ws_id, tail)
        if p.stderr.strip():
            job_log(ws_id, "stderr: " + p.stderr.strip()[-500:])

        # 4) verify the manifest exists + parses
        if not manifest.exists():
            raise RuntimeError("refine finished but spec/manifest.json was not written "
                               "(check the log; the model may have asked a question or errored)")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        n = len(data.get("diagrams", []))
        if n == 0:
            raise RuntimeError("manifest has no diagrams")
        set_status(ws_id, "refined", error="", n_diagrams=n)
        job_log(ws_id, f"OK refine -> {n} diagram(s)")
    except subprocess.TimeoutExpired:
        set_status(ws_id, "error", error=f"refine timed out after {REFINE_TIMEOUT}s")
        job_log(ws_id, "! refine timed out")
    except Exception as e:  # noqa: BLE001
        set_status(ws_id, "error", error=f"refine failed: {e}")
        job_log(ws_id, f"! {e}")
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


# --------------------------------------------------------- PROPOSAL (drives the tech-proposal skill)
def _fill_proposal_prompt(tmpl_path: Path, ws_id: str, meta: dict, output_dir: Path | None = None) -> str:
    d = WORKSPACES_DIR / ws_id
    fwd = lambda p: str(p).replace("\\", "/")
    return (tmpl_path.read_text(encoding="utf-8")
            .replace("{{WORKSPACE_DIR}}", fwd(d))
            .replace("{{PROPOSAL_SKILL_DIR}}", fwd(PROPOSAL_SKILL_DIR))
            .replace("{{OUTPUT_DIR}}", fwd(output_dir) if output_dir else fwd(d / "output"))
            .replace("{{FOLDER}}", meta.get("folder", "") or "(none; use the uploaded inputs / digest)")
            .replace("{{PROMPT_TEXT}}", meta.get("prompt", "") or "(no extra context)"))


def _run_claude(ws_id: str, prompt: str, timeout: int, label: str) -> subprocess.CompletedProcess:
    d = WORKSPACES_DIR / ws_id
    cmd = [CLAUDE, "-p", prompt, "--output-format", "json",
           "--permission-mode", "bypassPermissions",
           "--add-dir", str(PROPOSAL_SKILL_DIR), "--add-dir", str(SKILL_DIR)]
    if REFINE_MODEL:
        cmd += ["--model", REFINE_MODEL]
    job_log(ws_id, f"$ claude -p ({label})")
    p = subprocess.run(cmd, cwd=str(d), env=_child_env(), **_hidden_console(),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    tail = (p.stdout or "").strip()[-800:]
    if tail:
        job_log(ws_id, tail)
    if p.stderr.strip():
        job_log(ws_id, "stderr: " + p.stderr.strip()[-500:])
    return p


def analyze_job(ws_id: str):
    """Proposal analyze: run the skill's Phase 0-3 head-less -> spec/plan.json, stop at the gate."""
    try:
        meta = read_meta(ws_id)
        d = WORKSPACES_DIR / ws_id
        (d / "spec").mkdir(parents=True, exist_ok=True)
        sources = []
        if (d / "inputs").exists() and any((d / "inputs").iterdir()):
            sources.append(d / "inputs")
        if meta.get("folder") and Path(meta["folder"]).exists():
            sources.append(Path(meta["folder"]))
        if sources:
            run_ingest(ws_id, sources[0])
        plan = d / "spec" / "plan.json"
        if plan.exists():
            plan.unlink()
        prompt = _fill_proposal_prompt(PROPOSAL_ANALYZE_TMPL, ws_id, meta)
        (d / "spec" / "_analyze_prompt.md").write_text(prompt, encoding="utf-8")
        job_log(ws_id, "  [analyzing the RFP + docs, proposing stack/architecture — a few minutes]")
        _run_claude(ws_id, prompt, PROPOSAL_ANALYZE_TIMEOUT, "proposal analyze")
        if not plan.exists():
            raise RuntimeError("analyze finished but spec/plan.json was not written (check the log)")
        data = json.loads(plan.read_text(encoding="utf-8"))
        set_status(ws_id, "refined", error="",
                   n_diagrams=len(data.get("diagrams", [])))
        job_log(ws_id, f"OK analyze -> plan with {len(data.get('diagrams', []))} diagram(s), "
                       f"{len(data.get('tech_stack', []))} stack layer(s)")
    except subprocess.TimeoutExpired:
        set_status(ws_id, "error", error=f"analyze timed out after {PROPOSAL_ANALYZE_TIMEOUT}s")
    except Exception as e:  # noqa: BLE001
        set_status(ws_id, "error", error=f"analyze failed: {e}")
        job_log(ws_id, f"! {e}")
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


def proposal_generate_job(ws_id: str):
    """Proposal generate: run the skill's Phase 4-6 head-less -> a .docx + diagrams in a version dir."""
    try:
        d = WORKSPACES_DIR / ws_id
        plan = d / "spec" / "plan.json"
        if not plan.exists():
            raise RuntimeError("no plan to generate from; analyze first")
        meta = read_meta(ws_id)
        vid = max((v["id"] for v in meta.get("versions", [])), default=0) + 1
        out = _versions_dir(ws_id) / str(vid)
        (out / "diagrams").mkdir(parents=True, exist_ok=True)
        prompt = _fill_proposal_prompt(PROPOSAL_GENERATE_TMPL, ws_id, meta, output_dir=out)
        (d / "spec" / "_generate_prompt.md").write_text(prompt, encoding="utf-8")
        job_log(ws_id, "  [drawing diagrams + assembling the .docx + strict format review — this can take 10-30 min]")
        _run_claude(ws_id, prompt, PROPOSAL_GENERATE_TIMEOUT, "proposal generate")

        docx = next(iter(sorted(out.glob("*.docx"))), None)
        if not docx:
            # robustness: the skill may have written to the workspace output/ (its natural
            # location) instead of the version dir — adopt it into the version snapshot.
            stray = d / "output"
            if any(stray.glob("*.docx")):
                for p in list(stray.glob("*")):
                    if p.name == "versions":            # never fold the versions tree into itself
                        continue
                    dest = out / p.name
                    if p.is_dir():
                        shutil.copytree(p, dest, dirs_exist_ok=True); shutil.rmtree(p, ignore_errors=True)
                    else:
                        shutil.move(str(p), str(dest))
                docx = next(iter(sorted(out.glob("*.docx"))), None)
        pngs = sorted(p.name for p in (out / "diagrams").glob("*.png"))
        if not docx:
            raise RuntimeError("generate finished but no .docx was produced (check the log)")
        report = ""
        rp = out / "_report.md"
        if rp.exists():
            report = rp.read_text(encoding="utf-8")[:2000]

        meta = read_meta(ws_id)
        prev = (meta.get("versions") or [])[-1] if meta.get("versions") else None
        source = "Initial" if not prev else (
            "Re-analyzed inputs" if (prev.get("prompt", "") != meta.get("prompt", "")
                                     or prev.get("folder", "") != meta.get("folder", "")) else "Regenerated")
        record = {"id": vid, "created": _now(), "source": source, "kind": "proposal",
                  "prompt": meta.get("prompt", ""), "folder": meta.get("folder", ""),
                  "docx": docx.name, "diagrams": pngs, "n_diagrams": len(pngs),
                  "report": report, "label": ""}
        meta.setdefault("versions", []).append(record)
        meta["current_version"] = vid
        meta["status"] = "generated"
        meta["error"] = ""
        write_meta(ws_id, meta)
        job_log(ws_id, f"OK proposal v{vid} -> {docx.name}, {len(pngs)} diagram(s)")
    except subprocess.TimeoutExpired:
        set_status(ws_id, "error", error=f"generate timed out after {PROPOSAL_GENERATE_TIMEOUT}s")
    except Exception as e:  # noqa: BLE001
        set_status(ws_id, "error", error=f"generate failed: {e}")
        job_log(ws_id, f"! {e}")
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


# --------------------------------------------------------------------------- GENERATE
def _run_renderer(ws_id: str, script: str, spec_path: Path, png_path: Path) -> tuple[bool, str]:
    cmd = [sys.executable, str(SCRIPTS_DIR / script),
           "--spec", str(spec_path), "--out", str(png_path)]
    p = subprocess.run(cmd, cwd=str(SCRIPTS_DIR), env=_child_env(), creationflags=_NO_WINDOW,
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=RENDER_TIMEOUT)
    ok = p.returncode == 0 and png_path.exists()
    msg = (p.stderr or p.stdout or "").strip()[-600:]
    return ok, msg


def _versions_dir(ws_id: str) -> Path:
    return WORKSPACES_DIR / ws_id / "output" / "versions"


def _version_source(ws_id: str, prev: dict | None, prompt: str, folder: str, data: dict) -> str:
    """Label WHY this version was produced, by diffing against the previous one."""
    if not prev:
        return "Initial"
    if prev.get("prompt", "") != prompt or prev.get("folder", "") != folder:
        return "Re-refined inputs"
    prev_mf = _versions_dir(ws_id) / str(prev["id"]) / "manifest.json"
    try:
        pj = json.loads(prev_mf.read_text(encoding="utf-8"))
        if (json.dumps(pj, sort_keys=True, ensure_ascii=False)
                != json.dumps(data, sort_keys=True, ensure_ascii=False)):
            return "Edited spec"
    except Exception:  # noqa: BLE001
        pass
    return "Regenerated"


def generate_job(ws_id: str):
    try:
        d = WORKSPACES_DIR / ws_id
        manifest = d / "spec" / "manifest.json"
        if not manifest.exists():
            raise RuntimeError("no manifest to generate from; refine first")
        data = json.loads(manifest.read_text(encoding="utf-8"))
        diagrams = data.get("diagrams", [])
        meta0 = read_meta(ws_id)
        vid = max((v["id"] for v in meta0.get("versions", [])), default=0) + 1
        out = _versions_dir(ws_id) / str(vid)          # each run = its own version snapshot
        out.mkdir(parents=True, exist_ok=True)

        results = []
        dj_entries = []          # -> output/diagrams/diagrams.json (skill's sidecar format)
        for i, dg in enumerate(diagrams):
            kind = (dg.get("kind") or "graph").lower()
            slug = slugify(dg.get("slug") or dg.get("title") or f"diagram_{i+1}")
            title = dg.get("title") or slug
            script = RENDERER.get(kind)
            entry = {"slug": slug, "title": title, "kind": kind,
                     "ok": False, "png": None, "docx": None, "error": ""}
            if not script:
                entry["error"] = f"unknown kind '{kind}'"
                results.append(entry); continue

            spec = dg.get("spec") or {}
            spec.setdefault("slug", slug)
            spec.setdefault("title", title)
            spec_path = out / f"{slug}.spec.json"
            spec_path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")
            png_path = out / f"{slug}.png"

            job_log(ws_id, f"$ render [{kind}] {slug}")
            ok, msg = _run_renderer(ws_id, script, spec_path, png_path)
            entry["ok"] = ok
            if not ok:
                entry["error"] = msg or "renderer failed"
                job_log(ws_id, f"! {slug}: {entry['error'][:300]}")
                results.append(entry); continue
            entry["png"] = png_path.name
            for ext in (".svg", ".drawio"):
                if (out / f"{slug}{ext}").exists():
                    entry[ext.lstrip(".")] = f"{slug}{ext}"

            # per-diagram .docx from the descriptor
            desc = dg.get("descriptor") or {}
            desc.setdefault("slug", slug)
            desc.setdefault("subheading", dg.get("title") or slug)
            dj_entries.append({**desc, "slug": slug, "png": png_path.name})
            meta_path = out / f"{slug}.meta.json"
            meta_path.write_text(json.dumps(desc, indent=2, ensure_ascii=False), encoding="utf-8")
            docx_path = out / f"{slug}.docx"
            dp = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "build_diagram_doc.py"),
                 "--meta", str(meta_path), "--png", str(png_path),
                 "--out", str(docx_path), "--kind", kind],
                cwd=str(SCRIPTS_DIR), env=_child_env(), creationflags=_NO_WINDOW, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=RENDER_TIMEOUT)
            if dp.returncode == 0 and docx_path.exists():
                entry["docx"] = docx_path.name
            else:
                job_log(ws_id, f"! {slug} docx: {(dp.stderr or dp.stdout).strip()[:200]}")
            results.append(entry)

        # write the skill's diagrams.json sidecar (self-describing output; also lets
        # diagram_check validate captions/intros/bullets instead of warning they are absent)
        (out / "diagrams.json").write_text(
            json.dumps(dj_entries, indent=2, ensure_ascii=False), encoding="utf-8")

        # self-check the whole folder
        check = {"blockers": 0, "warnings": 0, "diagrams": []}
        try:
            report = out / "_check.json"
            subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "diagram_check.py"),
                 "--dir", str(out), "--json", str(report)],
                cwd=str(SCRIPTS_DIR), env=_child_env(), creationflags=_NO_WINDOW, capture_output=True,
                text=True, encoding="utf-8", errors="replace", timeout=120)
            if report.exists():
                check = json.loads(report.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            job_log(ws_id, f"! self-check skipped: {e}")

        # snapshot the exact manifest that produced this version (for restore/compare)
        (out / "manifest.json").write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

        meta = read_meta(ws_id)
        chk = {"blockers": check.get("blockers", 0), "warnings": check.get("warnings", 0)}
        prev = (meta.get("versions") or [])[-1] if meta.get("versions") else None
        record = {
            "id": vid, "created": _now(),
            "source": _version_source(ws_id, prev, meta.get("prompt", ""), meta.get("folder", ""), data),
            "prompt": meta.get("prompt", ""), "folder": meta.get("folder", ""),
            "summary": data.get("summary", ""), "label": "",
            "n_diagrams": len(results), "check": chk, "results": results,
        }
        meta.setdefault("versions", []).append(record)
        meta["current_version"] = vid
        meta["results"] = results          # mirror current for convenience
        meta["check"] = chk
        meta["status"] = "generated"
        n_ok = sum(1 for r in results if r["ok"])
        meta["error"] = "" if n_ok == len(results) else f"{len(results)-n_ok} diagram(s) failed to render"
        write_meta(ws_id, meta)
        job_log(ws_id, f"OK generate v{vid} -> {n_ok}/{len(results)} rendered, "
                       f"{check.get('blockers',0)} blocker(s)")
    except Exception as e:  # noqa: BLE001
        set_status(ws_id, "error", error=f"generate failed: {e}")
        job_log(ws_id, f"! {e}")
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


def start_job(ws_id: str, phase: str, target):
    with JOBS_LOCK:
        cur = JOBS.get(ws_id)
        if cur and cur.get("running"):
            raise HTTPException(409, f"a {cur.get('phase')} job is already running")
        JOBS[ws_id] = {"phase": phase, "running": True, "log": []}
    set_status(ws_id, "refining" if phase == "refine" else "generating", error="")
    threading.Thread(target=target, args=(ws_id,), daemon=True).start()


# --------------------------------------------------------------------------- app
app = FastAPI(title="Diagram-WorkFlow")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


def _claude_health() -> dict:
    """Is the claude CLI installed AND signed in? The Refine step needs both."""
    exe = shutil.which("claude")
    info = {"claude_installed": bool(exe), "logged_in": False, "email": None}
    if exe:
        try:
            r = subprocess.run([exe, "auth", "status", "--json"], capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=30, creationflags=_NO_WINDOW)
            d = json.loads(r.stdout or "{}")
            info["logged_in"] = bool(d.get("loggedIn"))
            info["email"] = d.get("email")
        except Exception:  # noqa: BLE001
            pass
    return info


@app.get("/api/health")
def health():
    return _claude_health()


@app.get("/api/workspaces")
def list_workspaces():
    items = []
    for d in sorted(WORKSPACES_DIR.iterdir() if WORKSPACES_DIR.exists() else []):
        mf = d / "meta.json"
        if not mf.exists():
            continue
        m = json.loads(mf.read_text(encoding="utf-8"))
        items.append({"id": m["id"], "name": m.get("name", m["id"]),
                      "type": m.get("type", "diagram"),
                      "status": m.get("status", "new"), "mode": m.get("mode", "text"),
                      "created": m.get("created"), "updated": m.get("updated"),
                      "n_diagrams": m.get("n_diagrams", 0)})
    items.sort(key=lambda x: x.get("updated") or "", reverse=True)
    return items


@app.post("/api/workspaces")
async def create_workspace(payload: dict):
    name = (payload.get("name") or "Untitled").strip()[:80]
    wtype = (payload.get("type") or "diagram").strip().lower()
    if wtype not in ("diagram", "proposal"):
        raise HTTPException(400, "type must be 'diagram' or 'proposal'")
    ws_id = uuid.uuid4().hex[:12]
    d = WORKSPACES_DIR / ws_id
    (d / "inputs").mkdir(parents=True, exist_ok=True)
    (d / "spec").mkdir(parents=True, exist_ok=True)
    (d / "output" / "diagrams").mkdir(parents=True, exist_ok=True)
    meta = {"id": ws_id, "name": name, "type": wtype, "created": _now(),
            "mode": "folder" if wtype == "proposal" else "text",
            "prompt": "", "folder": "", "status": "new", "error": ""}
    write_meta(ws_id, meta)
    return meta


def _detail(ws_id: str) -> dict:
    meta = read_meta(ws_id)
    d = WORKSPACES_DIR / ws_id
    inputs = sorted(p.name for p in (d / "inputs").glob("*") if p.is_file()) if (d / "inputs").exists() else []
    manifest = d / "spec" / "manifest.json"
    meta["inputs"] = inputs
    meta["has_manifest"] = manifest.exists()
    meta["has_digest"] = (d / "spec" / "_ingest_digest.md").exists()
    with JOBS_LOCK:
        job = JOBS.get(ws_id, {})
        meta["job"] = {"phase": job.get("phase"), "running": job.get("running", False),
                       "log": job.get("log", [])[-40:]}
    return meta


@app.get("/api/workspaces/{ws_id}")
def get_workspace(ws_id: str):
    return _detail(ws_id)


@app.delete("/api/workspaces/{ws_id}")
def delete_workspace(ws_id: str):
    d = ws_dir(ws_id)
    shutil.rmtree(d)
    with JOBS_LOCK:
        JOBS.pop(ws_id, None)
    return {"deleted": ws_id}


@app.post("/api/workspaces/{ws_id}/inputs")
async def set_inputs(ws_id: str,
                     prompt: str = Form(""),
                     folder: str = Form(""),
                     files: list[UploadFile] = File(default=[])):
    meta = read_meta(ws_id)
    d = WORKSPACES_DIR / ws_id
    meta["prompt"] = prompt or ""
    meta["folder"] = folder.strip().strip('"') or ""
    saved = []
    for f in files or []:
        if not f.filename:
            continue
        safe = Path(f.filename).name
        dest = d / "inputs" / safe
        dest.write_bytes(await f.read())
        saved.append(safe)
    has_docs = bool(meta["folder"]) or bool(list((d / "inputs").glob("*")))
    meta["mode"] = "folder" if has_docs else "text"
    meta["status"] = "new"
    write_meta(ws_id, meta)
    return {"saved": saved, **_detail(ws_id)}


_PICK_FOLDER_CODE = """
import sys, tkinter as tk
from tkinter import filedialog
sys.stdout.reconfigure(encoding='utf-8')
root = tk.Tk(); root.withdraw()
try:
    root.attributes('-topmost', True)
except Exception:
    pass
print(filedialog.askdirectory(title='Select a project-docs folder') or '')
"""


@app.get("/api/pick-folder")
def pick_folder():
    """Open the OS native folder dialog on the machine running the server (this is a
    local tool) and return the chosen absolute path. The browser cannot read a real
    folder path itself, so we ask the server-side OS."""
    try:
        r = subprocess.run([sys.executable, "-c", _PICK_FOLDER_CODE],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", timeout=180, creationflags=_NO_WINDOW)
        return {"path": (r.stdout or "").strip()}
    except Exception as e:  # noqa: BLE001
        raise HTTPException(500, f"native folder picker unavailable: {e}")


@app.post("/api/workspaces/{ws_id}/refine")
def refine(ws_id: str):
    meta = read_meta(ws_id)
    is_proposal = meta.get("type") == "proposal"
    has_folder = bool(meta.get("folder")) or bool(list((WORKSPACES_DIR / ws_id / "inputs").glob("*")))
    if is_proposal and not has_folder:
        raise HTTPException(400, "A technical proposal needs source docs: upload a folder of RFP + "
                                 "supporting docs, or point at a folder on this machine.")
    if not is_proposal and not (meta.get("prompt") or has_folder):
        raise HTTPException(400, "nothing to refine: add a prompt, upload files, or set a folder")
    h = _claude_health()
    if not h["claude_installed"]:
        raise HTTPException(400, "The 'claude' CLI is not installed. Install Claude Code, then reload. "
                                 "(Generate / Preview / Export work without it.)")
    if not h["logged_in"]:
        raise HTTPException(400, "You're not signed in to 'claude'. Run `claude auth login` in a terminal, "
                                 "then reload and try again.")
    start_job(ws_id, "refine", analyze_job if is_proposal else refine_job)
    return {"status": "refining"}


@app.get("/api/workspaces/{ws_id}/manifest")
def get_manifest(ws_id: str):
    mf = ws_dir(ws_id) / "spec" / "manifest.json"
    if not mf.exists():
        raise HTTPException(404, "no manifest yet")
    return JSONResponse(json.loads(mf.read_text(encoding="utf-8")))


@app.put("/api/workspaces/{ws_id}/manifest")
async def put_manifest(ws_id: str, payload: dict):
    ws_dir(ws_id)
    mf = WORKSPACES_DIR / ws_id / "spec" / "manifest.json"
    if "diagrams" not in payload or not isinstance(payload["diagrams"], list):
        raise HTTPException(400, "manifest must have a 'diagrams' array")
    mf.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    set_status(ws_id, "refined", n_diagrams=len(payload["diagrams"]))
    return {"ok": True, "n_diagrams": len(payload["diagrams"])}


@app.post("/api/workspaces/{ws_id}/generate")
def generate(ws_id: str):
    meta = read_meta(ws_id)
    if meta.get("type") == "proposal":
        if not (ws_dir(ws_id) / "spec" / "plan.json").exists():
            raise HTTPException(400, "analyze first (no plan)")
        h = _claude_health()
        if not h["claude_installed"] or not h["logged_in"]:
            raise HTTPException(400, "Generating a proposal needs the signed-in 'claude' CLI "
                                     "(run `claude auth login`), then reload.")
        start_job(ws_id, "generate", proposal_generate_job)
        return {"status": "generating"}
    if not (ws_dir(ws_id) / "spec" / "manifest.json").exists():
        raise HTTPException(400, "refine first (no manifest)")
    start_job(ws_id, "generate", generate_job)
    return {"status": "generating"}


@app.get("/api/workspaces/{ws_id}/plan")
def get_plan(ws_id: str):
    pf = ws_dir(ws_id) / "spec" / "plan.json"
    if not pf.exists():
        raise HTTPException(404, "no plan yet")
    return JSONResponse(json.loads(pf.read_text(encoding="utf-8")))


@app.put("/api/workspaces/{ws_id}/plan")
async def put_plan(ws_id: str, payload: dict):
    ws_dir(ws_id)
    (WORKSPACES_DIR / ws_id / "spec" / "plan.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    set_status(ws_id, "refined", n_diagrams=len(payload.get("diagrams", [])))
    return {"ok": True}


_MEDIA = {"png": "image/png", "svg": "image/svg+xml", "drawio": "application/xml",
          "json": "application/json",
          "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"}


def _current_vid(meta: dict) -> int | None:
    v = meta.get("current_version")
    if v is not None:
        return v
    vs = meta.get("versions") or []
    return vs[-1]["id"] if vs else None


@app.get("/api/workspaces/{ws_id}/versions/{vid}/preview/{name}")
def preview_version(ws_id: str, vid: int, name: str):
    ws_dir(ws_id)
    safe = Path(name).name
    base = _versions_dir(ws_id) / str(vid)
    f = base / safe
    if not f.exists():                       # proposal diagrams live in a diagrams/ subdir
        f = base / "diagrams" / safe
    if not f.exists():
        raise HTTPException(404, f"not found: v{vid}/{safe}")
    media = _MEDIA.get(safe.rsplit(".", 1)[-1].lower(), "application/octet-stream")
    return FileResponse(str(f), media_type=media, filename=safe)


@app.get("/api/workspaces/{ws_id}/preview/{name}")
def preview(ws_id: str, name: str):
    """Back-compat: serve from the current version."""
    vid = _current_vid(read_meta(ws_id))
    if vid is None:
        raise HTTPException(404, "no versions yet")
    return preview_version(ws_id, vid, name)


@app.post("/api/workspaces/{ws_id}/versions/{vid}/restore")
def restore_version(ws_id: str, vid: int):
    """Load a version's manifest back as the working spec so the user can iterate from it."""
    mf = _versions_dir(ws_id) / str(vid) / "manifest.json"
    if not mf.exists():
        raise HTTPException(404, f"version {vid} has no manifest")
    (WORKSPACES_DIR / ws_id / "spec" / "manifest.json").write_text(
        mf.read_text(encoding="utf-8"), encoding="utf-8")
    data = json.loads(mf.read_text(encoding="utf-8"))
    set_status(ws_id, "refined", n_diagrams=len(data.get("diagrams", [])))
    return {"ok": True, "from_version": vid}


@app.post("/api/workspaces/{ws_id}/versions/{vid}/label")
async def label_version(ws_id: str, vid: int, payload: dict):
    meta = read_meta(ws_id)
    hit = next((v for v in meta.get("versions", []) if v["id"] == vid), None)
    if not hit:
        raise HTTPException(404, f"version {vid} not found")
    hit["label"] = (payload.get("label") or "").strip()[:60]
    write_meta(ws_id, meta)
    return {"ok": True}


@app.get("/api/workspaces/{ws_id}/export")
def export(ws_id: str, version: int | None = None):
    d = ws_dir(ws_id)
    meta = read_meta(ws_id)
    vid = version if version is not None else _current_vid(meta)
    if vid is None:
        raise HTTPException(400, "nothing to export yet")
    out = _versions_dir(ws_id) / str(vid)
    zpath = d / "output" / f"{slugify(meta.get('name','diagrams'))}_v{vid}.zip"
    if zpath.exists():
        zpath.unlink()
    keep = (".png", ".svg", ".drawio", ".docx", ".json", ".md")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        for p in sorted(out.rglob("*")):     # recursive: covers proposal's diagrams/ subdir + docx
            if p.is_file() and (p.suffix.lower() in keep) and not p.name.endswith(".spec.json") \
                    and not p.name.endswith(".meta.json") and not p.name.endswith(".lint.json"):
                z.write(p, str(p.relative_to(out)))
    return FileResponse(str(zpath), media_type="application/zip", filename=zpath.name)


if __name__ == "__main__":
    import uvicorn
    host = os.environ.get("DIAGRAM_HOST", "127.0.0.1")
    port = int(os.environ.get("DIAGRAM_PORT", "8000"))
    print(f"Diagram-WorkFlow web app -> http://{host}:{port}")
    print(f"  skill: {SKILL_DIR}")
    print(f"  claude: {CLAUDE}  (model: {REFINE_MODEL or 'default'})")
    uvicorn.run(app, host=host, port=port, log_level="info")
