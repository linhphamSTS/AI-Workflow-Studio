# Phase 5 — Deliver + self-learn (mandatory)

## 0. Per-diagram description .docx (one Word file per diagram — ALWAYS)
For EVERY diagram rendered, emit a standalone `output/diagrams/<slug>.docx` laid out **exactly like a
figure block in a professional technical proposal**: a short heading, then one
justified **intro paragraph** above the image, the **image** centered, a **"Figure N: <caption>"** line
below it, then the **explanation bullets** — each `**Bold name** — description` that folds in what the
component is AND how it connects. That is the whole document: NO "how it was generated" / "how to
reproduce" / engine notes (a proposal figure never shows those). Derive the content from the SPEC so it
can never drift from the picture:
```bash
python scripts/build_diagram_doc.py --spec output/diagrams/<slug>.spec.json --kind cloud|graph|sequence \
       --png output/diagrams/<slug>.png --out output/diagrams/<slug>.docx
```
If Phase 3 wrote a richer `diagrams.json` entry (caption / intro_paragraph / explanation_bullets), pass
it via `--meta` for the fuller, agent-written narrative — that is preferred for real projects (the
auto-derived text is only a fallback). Either way: one `.docx` per diagram, always, in proposal format.

## 1. Deliver
Report to the user:
- the **PNG** path, the **SVG** path (vector twin — looks exactly like the PNG, opens/edits in
  draw.io), the **`.drawio`** path if emitted, and the per-diagram **`.docx`** explainer, plus the
  `diagrams.json` entry,
- point out that for pixel-faithful editing the **SVG** is the one to use (the `.drawio` is a
  structural twin, not a pixel copy — that is inherent, not a defect),
- a one-line description of what was drawn and the key elements,
- any **caveats/assumptions** (things you filled that the user didn't specify; anything the renderer
  approximated — e.g. sequence has no `.drawio`; a BPMN gateway marker was put in the label),
- how to edit it (open the `.drawio` in app.diagrams.net, or ask for a spec change and re-run).

## 2. Self-learn — append a lesson (NOT optional, EVERY run)
This is the self-learning loop's write side. After delivering, append an entry to
`LESSONS_LEARNED.md` (see its header for the required fields):
- **Title** (what + type + absolute date), **Request → chosen type**, **What went wrong / friction**
  (classification miss, missing icon, overflow, label defect, wrong notation, `.drawio` issue,
  self-check blocker, or an explicit user correction — be concrete; "nothing went wrong" is rare,
  record what was subtly hard or what the user tweaked), **Fix applied + where promoted**,
  **Reusable rule**.

## 3. Promote universal lessons (so the mistake can't recur)
If the lesson is general (not one-off), edit the RIGHT place immediately, and say you did:
- a **diagram-convention fact** → the matching `reference/kb_*.md`,
- a **renderer bug/gotcha** → fix `scripts/*.py` (or a note at its top),
- a **classification / suggestion miss** → `reference/diagram_types.md` (classification hints),
- a **spec / notation mistake** → `prompts/01_refine.md` or `prompts/03_generate.md`.

This keeps the knowledge base and prompts improving every run — the point of the skill's
self-learning contract. If skill files are junction-linked into Claude profiles, the edit is live
immediately; offer to git-commit the repo so it syncs across machines.
