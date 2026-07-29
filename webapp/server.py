#!/usr/bin/env python3
"""
AI Workflow Studio — a local UI that drives the `linhpham-diagram` and
`linhpham-technicalproposal` skills.

Flow (one workspace per project; the type is chosen at creation):
    inputs (prompt / uploaded docs / a folder)
      -> REFINE / ANALYZE : `claude -p` runs the skill head-less -> spec/  (GATE)
      -> confirm / edit the spec or plan in the browser
      -> GENERATE : diagram = deterministic Python renderers; proposal = the skill's Phase 4-6
      -> PREVIEW  : view the output; iterate (edit + re-run) until happy
      -> EXPORT   : download a zip of the version folder

Refine/Analyze is an LLM step (the real skill via the installed `claude` CLI, no API key).
Diagram generate is pure Python (fast, no LLM) using the skill's build_cloud / build_graph /
build_sequence / build_diagram_doc / diagram_check scripts; proposal generate runs the
technical-proposal skill head-less and is read-only against that skill.

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
import time
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
WBS_SKILL_DIR = REPO_ROOT / "wbs-estimate" / "skill" / "linhpham-wbs"
# Where a user's workspaces (their inputs + generated output) live. Override with
# DIAGRAM_WORKSPACES_DIR to keep data outside the repo, or to point tests elsewhere
# so they never touch real data.
WORKSPACES_DIR = Path(os.environ.get("DIAGRAM_WORKSPACES_DIR", str(WEBAPP_DIR / "workspaces"))).resolve()
STATIC_DIR = WEBAPP_DIR / "static"
REFINE_PROMPT_TMPL = WEBAPP_DIR / "refine_prompt.md"
PROPOSAL_ANALYZE_TMPL = WEBAPP_DIR / "proposal_analyze_prompt.md"
PROPOSAL_GENERATE_TMPL = WEBAPP_DIR / "proposal_generate_prompt.md"
WBS_ANALYZE_TMPL = WEBAPP_DIR / "wbs_analyze_prompt.md"
WBS_GENERATE_TMPL = WEBAPP_DIR / "wbs_generate_prompt.md"
DIAGRAM_SELFLEARN_TMPL = WEBAPP_DIR / "diagram_selflearn_prompt.md"

WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)

CLAUDE = shutil.which("claude") or "claude"
REFINE_MODEL = os.environ.get("DIAGRAM_REFINE_MODEL", "").strip()
REFINE_TIMEOUT = int(os.environ.get("DIAGRAM_REFINE_TIMEOUT", "900"))   # seconds
DIAGRAM_SELFLEARN = os.environ.get("DIAGRAM_SELFLEARN", "1") == "1"     # skill self-learns after a web render
DIAGRAM_SELFLEARN_TIMEOUT = int(os.environ.get("DIAGRAM_SELFLEARN_TIMEOUT", "600"))
PROPOSAL_ANALYZE_TIMEOUT = int(os.environ.get("PROPOSAL_ANALYZE_TIMEOUT", "1200"))    # 20 min
PROPOSAL_GENERATE_TIMEOUT = int(os.environ.get("PROPOSAL_GENERATE_TIMEOUT", "3600"))  # 60 min (heavy)
WBS_ANALYZE_TIMEOUT = int(os.environ.get("WBS_ANALYZE_TIMEOUT", "1200"))              # 20 min
# Estimating every leaf task, fetching real prices and gating two workbooks on a verifier
# is the longest job in the app.
WBS_GENERATE_TIMEOUT = int(os.environ.get("WBS_GENERATE_TIMEOUT", "4200"))             # 70 min
RENDER_TIMEOUT = int(os.environ.get("DIAGRAM_RENDER_TIMEOUT", "180"))   # per diagram
# ingest.py's own default is 20k chars/file, which truncates a real RFP and most of a
# WBS spreadsheet. Requirements the analysis never sees cannot end up in the proposal.
INGEST_MAX_CHARS = int(os.environ.get("INGEST_MAX_CHARS", "250000"))

RENDERER = {"cloud": "build_cloud.py", "graph": "build_graph.py", "sequence": "build_sequence.py"}

# The bid sections the proposal template can render beyond the technical solution.
# Not every RFP asks for these, so each is opt-in: the analyze step pre-ticks the ones
# the RFP actually requires, the user adjusts them at the plan gate, and generate fills
# only what is ticked. Anything unticked is written as null and the build drops the
# heading entirely. Keys MUST match build_docx.OPTIONAL_SECTION_GROUPS.
OPTIONAL_SECTIONS = [
    {"key": "security_data_protection", "group": "Security & Data Protection",
     "label": "Security & Data Protection",
     "hint": "Residency, encryption, access control, consent and secure SDLC as its own narrative."},
    {"key": "team_structure", "group": "Project Team", "label": "Team Structure",
     "hint": "Squads, how many, what each owns."},
    {"key": "team_roles", "group": "Project Team", "label": "Roles & Responsibilities",
     "hint": "The roles and what each is accountable for. Roles only, never invented people."},
    {"key": "team_engagement_model", "group": "Project Team", "label": "Engagement Model",
     "hint": "Onshore/offshore split, hours overlap, how the client works with the team."},
    {"key": "delivery_roadmap", "group": "Delivery Plan & Governance", "label": "Delivery Roadmap",
     "hint": "Phased roadmap or sequencing proposal."},
    {"key": "delivery_milestones", "group": "Delivery Plan & Governance",
     "label": "Milestones & Acceptance", "hint": "Milestones and what acceptance means at each."},
    {"key": "delivery_governance", "group": "Delivery Plan & Governance",
     "label": "Governance & Reporting",
     "hint": "Steering, escalation, change control, reporting cadence."},
    {"key": "support_model", "group": "Support & Service Levels", "label": "Support Model",
     "hint": "Run phase coverage, tiers and tooling."},
    {"key": "service_levels", "group": "Support & Service Levels", "label": "Service Level Targets",
     "hint": "Availability and severity-based response and resolution targets."},
    {"key": "assumptions_dependencies", "group": "Assumptions, Dependencies & Risks",
     "label": "Assumptions & Dependencies", "hint": "What was assumed and what the client must provide."},
    {"key": "risk_register", "group": "Assumptions, Dependencies & Risks",
     "label": "Key Risks & Mitigations", "hint": "Risk, impact, and the mitigation built into the approach."},
    {"key": "references", "group": "Case Study", "label": "References",
     "hint": "Client references. Never invented; supplied by the bid owner."},
    {"key": "contractual_exceptions", "group": "Contractual Exceptions",
     "label": "Contractual Exceptions",
     "hint": "Exceptions to the client's contract terms. A legal position, so leave off unless instructed."},
]
OPTIONAL_SECTION_KEYS = [s["key"] for s in OPTIONAL_SECTIONS]

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


def _cancelled(ws_id: str) -> bool:
    with JOBS_LOCK:
        return bool((JOBS.get(ws_id) or {}).get("cancel"))


def _finish_job(ws_id: str, phase: str, exc: BaseException) -> None:
    """Common failure handling: a user cancel is not an error, it is a stop."""
    if _cancelled(ws_id) or "cancelled by user" in str(exc):
        set_status(ws_id, "error", error=f"{phase} stopped by you")
        job_log(ws_id, "! stopped")
    elif isinstance(exc, subprocess.TimeoutExpired):
        set_status(ws_id, "error", error=f"{phase} timed out")
        job_log(ws_id, "! timed out")
    else:
        set_status(ws_id, "error", error=f"{phase} failed: {exc}")
        job_log(ws_id, f"! {exc}")


def slugify(s: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "_", (s or "").lower()).strip("_")
    return s or "diagram"


# --------------------------------------------------------------------------- ingest
def run_ingest(ws_id: str, source_dir: Path) -> Path | None:
    """Build spec/_ingest_digest.md from a folder of docs. Returns digest path or None.

    ingest.py defaults to 20k chars per file, which silently drops the tail of a real
    RFP (and most of a WBS spreadsheet) — exactly the requirements a proposal must not
    miss. Modern context windows make that cap unnecessary, so raise it here; the
    per-file limit still guards against one pathological file swamping the digest.
    """
    d = WORKSPACES_DIR / ws_id
    digest = d / "spec" / "_ingest_digest.md"
    digest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(SCRIPTS_DIR / "ingest.py"),
           "--dir", str(source_dir), "--out", str(digest),
           "--max-chars-per-file", str(INGEST_MAX_CHARS)]
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
        job_log(ws_id, "  [usually 3-5 minutes: reads the KB, designs the spec]")
        # Same streamed + cancellable runner as the proposal phases, so every LLM step
        # in the app reports progress live and can be stopped from the UI.
        _run_claude(ws_id, prompt, REFINE_TIMEOUT, "refine", add_dirs=[SKILL_DIR])

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
        _finish_job(ws_id, "refine", e)
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


# --------------------------------------------------------- PROPOSAL (drives the tech-proposal skill)
def _prior_version_block(ws_id: str, meta: dict) -> str:
    """Tell the skill exactly what a re-run may reuse — and what it must re-derive.

    A prior version is a source of CONTENT stability, never of rendering. Carrying a
    previous run's build script forward freezes the renderer at whatever the skill
    could do that day, so every later improvement becomes invisible. The skill's own
    `04_generate.md` states this rule; repeating it here means the run does not depend
    on the lessons diary being read carefully.
    """
    versions = meta.get("versions") or []
    if not versions:
        return ("This is the FIRST run for this workspace — there is no previous version.\n"
                "Derive everything from `plan.json` and the source documents.")
    prev = versions[-1]
    pdir = str(_versions_dir(ws_id) / str(prev["id"])).replace("\\", "/")
    return (
        f"This is a RE-RUN. The previous output is version **{prev['id']}** at `{pdir}`\n"
        f"(`{prev.get('docx', '?')}`, {prev.get('n_diagrams', 0)} diagram(s)).\n"
        "\n"
        "**Reuse its CONTENT so the proposal stays stable across iterations:**\n"
        f"- `{pdir}/replacements.json` — the written prose the user already accepted\n"
        f"- `{pdir}/diagrams/diagrams.json` — each diagram's slug, `target_heading`, `caption`,\n"
        "  `intro_paragraph` and `explanation_bullets`\n"
        "- the diagram set and section structure implied by `plan.json`\n"
        "\n"
        "**Re-derive the RENDERING from scratch — do NOT copy it forward:**\n"
        "- re-select each diagram's renderer from the PRIMARY list in `04_generate.md`\n"
        "  (`build_cloud` / `build_graph` / `build_sequence`; mingrammer only as a genuine fallback)\n"
        "- author a fresh `spec.json` per diagram and re-render the PNG / SVG / `.drawio`\n"
        "- re-assemble the `.docx` with the skill's current `build_docx.py`\n"
        "\n"
        f"**Never copy `{pdir}`'s build script, renderer choice or rendered images into the new\n"
        "version.** They were produced by whatever the skill could do on that date; re-rendering is\n"
        "what lets this run pick up the current renderers, DPI rules and SA-grade structure. If a\n"
        "re-render is genuinely worse than the previous version, say so in the Phase 6 report rather\n"
        "than silently reinstating the old images.\n"
        "\n"
        "**REUSE IS SUBORDINATE TO TWO THINGS, AND THIS OVERRIDES EVERYTHING ABOVE.** Reuse exists\n"
        "to stop the wording drifting between iterations, not to freeze a decision the user has since\n"
        "changed. Before reusing any prose value, check it against:\n"
        "\n"
        f"1. **`plan.json` as it stands right now.** It may have been edited at the gate since\n"
        f"   version {prev['id']} was written. For EVERY prose value, verify that what it asserts\n"
        "   still matches the current plan: the stack choices, the cloud and region, the\n"
        "   architecture, the assumptions and the open questions. Any sentence that contradicts the\n"
        "   current plan, or that names a technology, vendor, region or option the current plan no\n"
        "   longer carries, must be REWRITTEN from the current plan. Do not soften it and do not\n"
        "   keep it as an aside. A proposal that recommends one thing while a sentence elsewhere\n"
        "   still offers the thing it replaced is a bid-level defect, and it is the single most\n"
        "   likely way a re-run ships a contradiction.\n"
        "2. **The phase prompts as they stand right now.** `04_generate.md` may have gained or\n"
        "   tightened a rule since the last run: a length ceiling, a required shape (an array where\n"
        "   there used to be prose), a mandatory field, a banned construction. Re-read it and bring\n"
        "   every reused value into line. A reused value that breaches a current rule is a defect,\n"
        "   not a stable choice, and the reviewer will reject it.\n"
        "\n"
        "State in the Phase 6 report which reused values you had to rewrite and why, so the diff\n"
        "between versions is explained rather than mysterious."
    )


def _sections_block(ws_id: str) -> str:
    """Tell the generate step exactly which optional bid sections to write.

    The choice belongs to the user, not the model: an RFP that never asked for a
    delivery roadmap does not want one invented, and a section the client DID ask for
    must not be silently skipped. So the plan gate records an explicit include flag per
    section and this block turns it into an instruction with no room to improvise.
    """
    plan_path = WORKSPACES_DIR / ws_id / "spec" / "plan.json"
    chosen = {}
    try:
        plan = json.loads(plan_path.read_text(encoding="utf-8"))
        raw = plan.get("optional_sections") or {}
        for key, val in raw.items():
            chosen[key] = bool(val.get("include")) if isinstance(val, dict) else bool(val)
    except Exception:  # noqa: BLE001
        pass

    if not chosen:
        return ("The plan records no per-section choice, so decide each optional section from the\n"
                "RFP itself: fill the ones its required-contents list asks for and set every other\n"
                "one to `null`. Never invent a section the client did not ask for.")

    on = [s for s in OPTIONAL_SECTIONS if chosen.get(s["key"])]
    off = [s for s in OPTIONAL_SECTIONS if not chosen.get(s["key"])]
    lines = ["The user has chosen exactly which optional bid sections this proposal contains.",
             "This is a decision, not a suggestion.", ""]
    if on:
        lines.append("**WRITE these (a real, grounded value):**")
        lines += [f"- `{s['key']}` — {s['group']} › {s['label']}. {s['hint']}" for s in on]
    else:
        lines.append("**WRITE these:** none. Every optional section is switched off.")
    lines.append("")
    if off:
        lines.append("**Set these to `null`** (the build removes the heading; do not write them):")
        lines.append("  " + ", ".join(f"`{s['key']}`" for s in off))
    lines.append("")
    lines.append("Emit every key listed above in `replacements.json`, using `null` for the off ones, "
                 "so the choice is explicit in the artefact rather than implied by omission.")
    return "\n".join(lines)


def _wbs_mode_block(meta: dict) -> str:
    """State the mode the user chose, so the run does not have to guess it.

    The skill can detect the situation on its own, and it still should as a cross-check, but
    the user was asked at creation time and their answer is the authority. A run that decides
    for itself can decide differently from what the person expects, and the difference is not
    a detail: one job leaves the client's workbook alone, the other writes a new one.
    """
    mode = (meta.get("wbs_mode") or "").strip().lower()
    if mode == "fill":
        return ("MODE: **FILL**. The user has stated that the client supplied a WBS. Find it in "
                "the inputs, treat its structure, wording and styling as the deliverable, and "
                "write only the effort columns, with `scripts/fill_wbs.py`. Do not author a "
                "breakdown. If no client workbook is in the inputs, stop and say so rather "
                "than switching to author mode: the user asked for one job, not the other.")
    if mode == "author":
        return ("MODE: **AUTHOR**. The user has stated that there is no client WBS. Design the "
                "breakdown from the documents, then estimate it, then build it with "
                "`scripts/build_wbs.py`. If the inputs do turn out to contain a client "
                "workbook, say so in the plan before building, because filling theirs is "
                "usually what a client wants.")
    return ("MODE: not stated. Detect it from the inputs and say in the plan which one you "
            "found and why, before building anything.")


def _fill_proposal_prompt(tmpl_path: Path, ws_id: str, meta: dict, output_dir: Path | None = None) -> str:
    d = WORKSPACES_DIR / ws_id
    fwd = lambda p: str(p).replace("\\", "/")
    filled = (tmpl_path.read_text(encoding="utf-8")
              .replace("{{WORKSPACE_DIR}}", fwd(d))
              .replace("{{PROPOSAL_SKILL_DIR}}", fwd(PROPOSAL_SKILL_DIR))
              .replace("{{WBS_SKILL_DIR}}", fwd(WBS_SKILL_DIR))
              .replace("{{OUTPUT_DIR}}", fwd(output_dir) if output_dir else fwd(d / "output"))
              .replace("{{PRIOR_VERSION}}", _prior_version_block(ws_id, meta))
              .replace("{{SECTIONS}}", _sections_block(ws_id))
              .replace("{{FOLDER}}", meta.get("folder", "") or "(none; use the uploaded inputs / digest)")
              .replace("{{PROMPT_TEXT}}", meta.get("prompt", "") or "(no extra context)")
              .replace("{{WBS_MODE}}", _wbs_mode_block(meta)))
    # A placeholder that survives substitution reaches the model as literal "{{KEY}}" and is
    # silently ignored — the run then quietly loses whatever that block was meant to say.
    leftover = sorted(set(re.findall(r"\{\{[A-Z_]+\}\}", filled)))
    if leftover:
        raise RuntimeError(
            f"{tmpl_path.name}: unfilled placeholder(s) {', '.join(leftover)} — "
            "add the substitution in _fill_proposal_prompt()")
    return filled


def _kill_tree(proc: subprocess.Popen) -> None:
    """Kill the claude process AND its children (it spawns python / dot / bash)."""
    if proc.poll() is not None:
        return
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                           capture_output=True, creationflags=_NO_WINDOW, timeout=30)
        else:
            os.killpg(os.getpgid(proc.pid), 15)
    except Exception:  # noqa: BLE001
        pass
    try:
        proc.wait(timeout=15)
    except Exception:  # noqa: BLE001
        try:
            proc.kill()
        except Exception:  # noqa: BLE001
            pass


def _short(s: str, n: int = 150) -> str:
    s = " ".join((s or "").split())
    return s if len(s) <= n else s[: n - 1] + "…"


def _describe_event(evt: dict) -> str | None:
    """Turn one stream-json event into a readable progress line (or None to skip)."""
    kind = evt.get("type")
    if kind == "system" and evt.get("subtype") == "init":
        return f"  session started (model: {evt.get('model', '?')})"
    if kind == "assistant":
        out = []
        for block in (evt.get("message") or {}).get("content") or []:
            btype = block.get("type")
            if btype == "text":
                first = next((ln for ln in (block.get("text") or "").splitlines() if ln.strip()), "")
                if first:
                    out.append("  " + _short(first, 180))
            elif btype == "tool_use":
                name = block.get("name", "tool")
                inp = block.get("input") or {}
                if name == "Bash":
                    detail = inp.get("command", "")
                elif name in ("Read", "Write", "Edit", "NotebookEdit"):
                    detail = str(inp.get("file_path", ""))
                elif name == "Task":
                    detail = inp.get("description", "") or inp.get("subagent_type", "")
                elif name in ("Grep", "Glob"):
                    detail = inp.get("pattern", "")
                else:
                    detail = ""
                out.append(f"  -> {name}: {_short(detail, 140)}" if detail else f"  -> {name}")
        return "\n".join(out) or None
    if kind == "result":
        cost = evt.get("total_cost_usd")
        turns = evt.get("num_turns")
        bits = [f"finished ({evt.get('subtype', 'done')})"]
        if turns:
            bits.append(f"{turns} turns")
        if isinstance(cost, (int, float)):
            bits.append(f"${cost:.2f}")
        return "  " + ", ".join(bits)
    return None


def _run_claude(ws_id: str, prompt: str, timeout: int, label: str,
                add_dirs: list[Path] | None = None) -> str:
    """Run the skill head-less, streaming progress into the job log.

    Uses `--output-format stream-json` so a 20-30 minute proposal run is observable
    instead of a silent black box, and keeps the Popen handle in the job registry so
    the run can be cancelled from the UI. Returns the final result text.
    """
    d = WORKSPACES_DIR / ws_id
    cmd = [CLAUDE, "-p", prompt, "--output-format", "stream-json", "--verbose",
           "--permission-mode", "bypassPermissions"]
    for extra in (add_dirs if add_dirs is not None
                  else [PROPOSAL_SKILL_DIR, WBS_SKILL_DIR, SKILL_DIR]):
        cmd += ["--add-dir", str(extra)]
    if REFINE_MODEL:
        cmd += ["--model", REFINE_MODEL]
    job_log(ws_id, f"$ claude -p ({label})")

    popen_kwargs = dict(_hidden_console())
    if os.name != "nt":
        popen_kwargs["start_new_session"] = True   # so we can kill the whole group
    proc = subprocess.Popen(cmd, cwd=str(d), env=_child_env(),
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            text=True, encoding="utf-8", errors="replace",
                            bufsize=1, **popen_kwargs)
    with JOBS_LOCK:
        JOBS.setdefault(ws_id, {"log": []})["proc"] = proc

    state = {"timed_out": False}

    def _on_timeout():
        state["timed_out"] = True
        _kill_tree(proc)

    timer = threading.Timer(timeout, _on_timeout)
    timer.daemon = True
    timer.start()

    final, saw_result = "", False
    try:
        for line in proc.stdout:                    # streams as the model works
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                job_log(ws_id, "  " + _short(line, 200))
                continue
            if evt.get("type") == "result":
                saw_result = True
                final = evt.get("result") or ""
            msg = _describe_event(evt)
            if msg:
                job_log(ws_id, msg)
                with JOBS_LOCK:
                    JOBS.setdefault(ws_id, {"log": []})["activity"] = msg.strip()
        proc.wait()
    finally:
        timer.cancel()
        with JOBS_LOCK:
            job = JOBS.get(ws_id, {})
            job.pop("proc", None)
            cancelled = job.get("cancel", False)

    err = (proc.stderr.read() or "").strip() if proc.stderr else ""
    if err:
        job_log(ws_id, "stderr: " + err[-500:])
    if cancelled:
        raise RuntimeError("cancelled by user")
    if state["timed_out"]:
        raise subprocess.TimeoutExpired(cmd[0], timeout)
    if not saw_result and proc.returncode not in (0, None):
        raise RuntimeError(f"{label} exited with code {proc.returncode}"
                           + (f": {err[-300:]}" if err else ""))
    return final


def analyze_job(ws_id: str):
    """Proposal analyze: run the skill's Phase 0-3 head-less -> spec/plan.json, stop at the gate."""
    try:
        meta = read_meta(ws_id)
        d = WORKSPACES_DIR / ws_id
        (d / "spec").mkdir(parents=True, exist_ok=True)
        inp = d / "inputs"
        has_docs = (inp.exists() and any(inp.iterdir())) or (meta.get("folder") and Path(meta["folder"]).exists())
        # WORKAROUND (skill is read-only + needs a doc folder to ingest): if the user gave only a
        # prompt and no docs, capture the prompt as a requirements doc so the skill has something to
        # analyse. This is entirely webapp-side — the tech-proposal skill is never modified.
        if not has_docs and (meta.get("prompt") or "").strip():
            inp.mkdir(parents=True, exist_ok=True)
            (inp / "requirements.md").write_text(
                "# Project requirements\n\n"
                "_(Provided directly as a prompt; no source RFP documents were supplied.)_\n\n"
                + meta["prompt"].strip() + "\n", encoding="utf-8")
            job_log(ws_id, "  (no docs supplied — captured your prompt as inputs/requirements.md for the skill to analyse)")
        sources = []
        if inp.exists() and any(inp.iterdir()):
            sources.append(inp)
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
        _finish_job(ws_id, "analyze", e)
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False



def wbs_analyze_job(ws_id: str):
    """WBS analyze: run the skill's Phase 0-3 head-less -> spec/wbs_plan.json, stop at the gate.

    The gate exists because the module structure, the column set and the factor stack are
    cheap to change now and expensive once 250 rows carry numbers.
    """
    try:
        meta = read_meta(ws_id)
        d = WORKSPACES_DIR / ws_id
        (d / "spec").mkdir(parents=True, exist_ok=True)
        inp = d / "inputs"
        has_docs = (inp.exists() and any(inp.iterdir())) or (
            meta.get("folder") and Path(meta["folder"]).exists())
        # Same webapp-side workaround as the proposal type: the skill needs documents to
        # ingest, so a prompt-only workspace gets its prompt captured as one.
        if not has_docs and (meta.get("prompt") or "").strip():
            inp.mkdir(parents=True, exist_ok=True)
            (inp / "requirements.md").write_text(
                "# Project requirements\n\n"
                "_(Provided directly as a prompt; no source bid documents were supplied.)_\n\n"
                + meta["prompt"].strip() + "\n", encoding="utf-8")
            job_log(ws_id, "  (no docs supplied - captured your prompt as inputs/requirements.md)")
        sources = []
        if inp.exists() and any(inp.iterdir()):
            sources.append(inp)
        if meta.get("folder") and Path(meta["folder"]).exists():
            sources.append(Path(meta["folder"]))
        if sources:
            run_ingest(ws_id, sources[0])
        plan = d / "spec" / "wbs_plan.json"
        if plan.exists():
            plan.unlink()
        prompt = _fill_proposal_prompt(WBS_ANALYZE_TMPL, ws_id, meta)
        (d / "spec" / "_wbs_analyze_prompt.md").write_text(prompt, encoding="utf-8")
        job_log(ws_id, "  [reading the bid folder, detecting fill or author mode, designing the "
                       "breakdown and the factor stack - a few minutes]")
        _run_claude(ws_id, prompt, WBS_ANALYZE_TIMEOUT, "wbs analyze")
        if not plan.exists():
            raise RuntimeError("analyze finished but spec/wbs_plan.json was not written "
                               "(check the log)")
        data = json.loads(plan.read_text(encoding="utf-8"))
        mods = data.get("modules") or []
        set_status(ws_id, "refined", error="", n_diagrams=len(mods))
        cloud = (data.get("cloud") or {})
        job_log(ws_id, "OK analyze -> %s mode, %d module(s), cloud %s/%s"
                % (data.get("mode", "?"), len(mods),
                   cloud.get("provider", "?"), cloud.get("region", "?")))
    except subprocess.TimeoutExpired:
        set_status(ws_id, "error", error=f"analyze timed out after {WBS_ANALYZE_TIMEOUT}s")
    except Exception as e:  # noqa: BLE001
        _finish_job(ws_id, "analyze", e)
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


def wbs_generate_job(ws_id: str):
    """WBS generate: Phase 4-7 head-less -> the work breakdown AND the cost estimation.

    Two workbooks, not one. A bid needs the hours and the running cost, and the cost sheet is
    the one that must never carry an invented price, so the wrapper prompt makes the fetch
    sequence mandatory.
    """
    try:
        d = WORKSPACES_DIR / ws_id
        plan = d / "spec" / "wbs_plan.json"
        if not plan.exists():
            raise RuntimeError("no plan to estimate from; analyze first")
        meta = read_meta(ws_id)
        vid = max((v["id"] for v in meta.get("versions", [])), default=0) + 1
        out = _versions_dir(ws_id) / str(vid)
        out.mkdir(parents=True, exist_ok=True)
        prompt = _fill_proposal_prompt(WBS_GENERATE_TMPL, ws_id, meta, output_dir=out)
        (d / "spec" / "_wbs_generate_prompt.md").write_text(prompt, encoding="utf-8")
        job_log(ws_id, "  [estimating every leaf task, fetching real cloud prices, building and "
                       "verifying both workbooks - this can take 20-60 min]")
        _run_claude(ws_id, prompt, WBS_GENERATE_TIMEOUT, "wbs generate")

        books = sorted(out.glob("*.xlsx"))
        if not books:
            # The skill may have written to its natural output/ location; adopt it.
            stray = d / "output"
            if any(stray.glob("*.xlsx")):
                for p in list(stray.glob("*")):
                    if p.name == "versions":
                        continue
                    dest = out / p.name
                    if p.is_dir():
                        shutil.copytree(p, dest, dirs_exist_ok=True)
                        shutil.rmtree(p, ignore_errors=True)
                    else:
                        shutil.move(str(p), str(dest))
                books = sorted(out.glob("*.xlsx"))
        if not books:
            raise RuntimeError("generate finished but no .xlsx was produced (check the log)")

        def pick(*needles):
            for b in books:
                low = b.name.lower()
                if all(n in low for n in needles):
                    return b.name
            return None

        wbs_name = pick("wbs") or books[0].name
        cost_name = pick("cost") or (books[1].name if len(books) > 1 else None)
        if not cost_name:
            # Not fatal, but it is half a deliverable and the report must say so.
            job_log(ws_id, "  ! no cost estimation workbook was produced - the run is incomplete")

        report = ""
        rp = out / "_report.md"
        if rp.exists():
            report = rp.read_text(encoding="utf-8")[:2000]

        meta = read_meta(ws_id)
        prev = (meta.get("versions") or [])[-1] if meta.get("versions") else None
        source = "Initial" if not prev else (
            "Re-analyzed inputs" if (prev.get("prompt", "") != meta.get("prompt", "")
                                     or prev.get("folder", "") != meta.get("folder", ""))
            else "Regenerated")
        record = {"id": vid, "created": _now(), "source": source, "kind": "wbs",
                  "prompt": meta.get("prompt", ""), "folder": meta.get("folder", ""),
                  "wbs": wbs_name, "cost": cost_name,
                  "workbooks": [b.name for b in books], "report": report}
        versions = meta.get("versions") or []
        versions.append(record)
        set_status(ws_id, "generated", error="", versions=versions,
                   current_version=vid, n_diagrams=len(books))
        job_log(ws_id, "OK wbs v%d -> %s%s" % (vid, wbs_name,
                                               (" + " + cost_name) if cost_name else ""))
    except subprocess.TimeoutExpired:
        set_status(ws_id, "error", error=f"generate timed out after {WBS_GENERATE_TIMEOUT}s")
    except Exception as e:  # noqa: BLE001
        _finish_job(ws_id, "generate", e)
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
        _finish_job(ws_id, "generate", e)
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
            if _cancelled(ws_id):     # honour Stop between diagrams (a renderer is short)
                raise RuntimeError("cancelled by user")
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
        # skill self-learning (best-effort): the diagram is already delivered above; now let the
        # skill run its OWN Phase 4-5 self-learn over the render so it improves over time. Never
        # fails the generate. Off with DIAGRAM_SELFLEARN=0.
        _diagram_selflearn(ws_id, out)
    except Exception as e:  # noqa: BLE001
        _finish_job(ws_id, "generate", e)
    finally:
        with JOBS_LOCK:
            JOBS.get(ws_id, {})["running"] = False


def _diagram_selflearn(ws_id: str, out_dir: Path) -> None:
    """Run the diagram skill's OWN Phase 4-5 (self-check + self-learn) over a finished render,
    so it appends a lesson to its LESSONS_LEARNED via its native mechanism. Best-effort."""
    if not DIAGRAM_SELFLEARN:
        return
    if not (shutil.which("claude") and _claude_health()["logged_in"]):
        return
    try:
        d = WORKSPACES_DIR / ws_id
        fwd = lambda p: str(p).replace("\\", "/")
        prompt = (DIAGRAM_SELFLEARN_TMPL.read_text(encoding="utf-8")
                  .replace("{{SKILL_DIR}}", fwd(SKILL_DIR))
                  .replace("{{OUTPUT_DIR}}", fwd(out_dir))
                  .replace("{{WORKSPACE_DIR}}", fwd(d)))
        job_log(ws_id, "  [skill self-learn: running the diagram skill's own Phase 4-5 over the render]")
        subprocess.run([CLAUDE, "-p", prompt, "--output-format", "json",
                        "--permission-mode", "bypassPermissions", "--add-dir", str(SKILL_DIR)],
                       cwd=str(d), env=_child_env(), **_hidden_console(),
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       timeout=DIAGRAM_SELFLEARN_TIMEOUT)
        job_log(ws_id, "  [skill self-learn: done]")
    except Exception as e:  # noqa: BLE001
        job_log(ws_id, f"  (self-learn skipped: {e})")


def start_job(ws_id: str, phase: str, target):
    with JOBS_LOCK:
        cur = JOBS.get(ws_id)
        if cur and cur.get("running"):
            raise HTTPException(409, f"a {cur.get('phase')} job is already running")
        JOBS[ws_id] = {"phase": phase, "running": True, "log": [],
                       "started": time.time(), "cancel": False, "activity": ""}
    set_status(ws_id, "refining" if phase == "refine" else "generating", error="")
    threading.Thread(target=target, args=(ws_id,), daemon=True).start()


# --------------------------------------------------------------------------- app
app = FastAPI(title="AI Workflow Studio")
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    """Serve the shell with a cache-busting stamp on app.js and style.css.

    Without this, a browser holding an older app.js keeps serving it after the
    app is updated, and the user sees a stale UI with no way to tell. That is
    indistinguishable from a missing feature, so the stamp is not cosmetic.
    """
    html = (STATIC_DIR / "index.html").read_text(encoding="utf-8")
    for asset in ("app.js", "style.css"):
        f = STATIC_DIR / asset
        stamp = int(f.stat().st_mtime) if f.exists() else 0
        html = html.replace("/static/%s" % asset, "/static/%s?v=%d" % (asset, stamp))
    return html


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


@app.get("/api/optional-sections")
def optional_sections():
    """The catalogue the plan gate renders its checkboxes from, so the UI never
    hardcodes a list that could drift from the template."""
    return {"sections": OPTIONAL_SECTIONS}


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
    if wtype not in ("diagram", "proposal", "wbs"):
        raise HTTPException(400, "type must be 'diagram', 'proposal' or 'wbs'")
    # An estimate is one of two jobs and they are not interchangeable. FILL puts hours
    # into a workbook the client already wrote and leaves their structure alone; AUTHOR
    # designs the breakdown first. Asking up front avoids discovering halfway through
    # that the wrong one was assumed.
    wbs_mode = (payload.get("wbs_mode") or "").strip().lower()
    if wtype == "wbs":
        if wbs_mode not in ("fill", "author"):
            raise HTTPException(400, "wbs_mode must be 'fill' or 'author'")
    else:
        wbs_mode = ""
    ws_id = uuid.uuid4().hex[:12]
    d = WORKSPACES_DIR / ws_id
    (d / "inputs").mkdir(parents=True, exist_ok=True)
    (d / "spec").mkdir(parents=True, exist_ok=True)
    (d / "output" / "diagrams").mkdir(parents=True, exist_ok=True)
    meta = {"id": ws_id, "name": name, "type": wtype, "wbs_mode": wbs_mode,
            "created": _now(),
            # A WBS is estimated from bid documents, so it opens in folder mode like a proposal.
            "mode": "folder" if wtype in ("proposal", "wbs") else "text",
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
        started = job.get("started")
        meta["job"] = {"phase": job.get("phase"), "running": job.get("running", False),
                       "log": job.get("log", [])[-60:],
                       "activity": job.get("activity", ""),
                       "elapsed": int(time.time() - started) if started else 0,
                       "cancelling": bool(job.get("cancel")),
                       "cancellable": bool(job.get("proc"))}
    return meta


@app.get("/api/workspaces/{ws_id}")
def get_workspace(ws_id: str):
    return _detail(ws_id)


@app.post("/api/workspaces/{ws_id}/cancel")
def cancel_job(ws_id: str):
    """Stop a running refine / analyze / generate. Kills the claude process tree."""
    ws_dir(ws_id)
    with JOBS_LOCK:
        job = JOBS.get(ws_id) or {}
        if not job.get("running"):
            raise HTTPException(409, "nothing is running for this workspace")
        job["cancel"] = True
        proc = job.get("proc")
    job_log(ws_id, "! cancelling — stopping the run …")
    if proc is not None:
        _kill_tree(proc)
        return {"ok": True, "stopped": True}
    # A pure-Python diagram generate has no claude process; it finishes its current
    # renderer and the flag is picked up by the job loop.
    return {"ok": True, "stopped": False,
            "note": "stop requested; the current step will finish first"}


@app.post("/api/workspaces/{ws_id}/rename")
def rename_workspace(ws_id: str, payload: dict):
    name = (payload or {}).get("name", "")
    name = " ".join(str(name).split())[:80]
    if not name:
        raise HTTPException(400, "name is required")
    meta = read_meta(ws_id)
    meta["name"] = name
    write_meta(ws_id, meta)
    return {"ok": True, "name": name}


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
    wtype = meta.get("type")
    is_proposal = wtype == "proposal"
    is_wbs = wtype == "wbs"
    has_docs = bool(meta.get("folder")) or bool(list((WORKSPACES_DIR / ws_id / "inputs").glob("*")))
    has_prompt = bool((meta.get("prompt") or "").strip())
    if not has_docs and not has_prompt:
        raise HTTPException(400, "Nothing to work from: add a prompt, upload files, or set a folder."
                                 + (" (A proposal is best with RFP docs, but a detailed prompt works too — "
                                    "we capture it as a requirements doc for the skill.)" if is_proposal else ""))
    h = _claude_health()
    if not h["claude_installed"]:
        raise HTTPException(400, "The 'claude' CLI is not installed. Install Claude Code, then reload. "
                                 "(Generate / Preview / Export work without it.)")
    if not h["logged_in"]:
        raise HTTPException(400, "You're not signed in to 'claude'. Run `claude auth login` in a terminal, "
                                 "then reload and try again.")
    start_job(ws_id, "refine",
              wbs_analyze_job if is_wbs else (analyze_job if is_proposal else refine_job))
    return {"status": "refining"}


@app.get("/api/workspaces/{ws_id}/wbs-plan")
def get_wbs_plan(ws_id: str):
    pf = ws_dir(ws_id) / "spec" / "wbs_plan.json"
    if not pf.exists():
        raise HTTPException(404, "no plan yet")
    return JSONResponse(json.loads(pf.read_text(encoding="utf-8")))


@app.put("/api/workspaces/{ws_id}/wbs-plan")
async def put_wbs_plan(ws_id: str, payload: dict):
    ws_dir(ws_id)
    (WORKSPACES_DIR / ws_id / "spec" / "wbs_plan.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    set_status(ws_id, "refined", n_diagrams=len(payload.get("modules") or []))
    return {"ok": True}


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
    if meta.get("type") == "wbs":
        if not (ws_dir(ws_id) / "spec" / "wbs_plan.json").exists():
            raise HTTPException(400, "analyze first (no plan)")
        h = _claude_health()
        if not h["claude_installed"] or not h["logged_in"]:
            raise HTTPException(400, "Estimating a WBS needs the signed-in 'claude' CLI "
                                     "(run `claude auth login`), then reload.")
        start_job(ws_id, "generate", wbs_generate_job)
        return {"status": "generating"}
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
          "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
          "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}


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
    print(f"AI Workflow Studio -> http://{host}:{port}")
    print(f"  skill: {SKILL_DIR}")
    print(f"  wbs skill: {WBS_SKILL_DIR}")
    print(f"  claude: {CLAUDE}  (model: {REFINE_MODEL or 'default'})")
    uvicorn.run(app, host=host, port=port, log_level="info")
