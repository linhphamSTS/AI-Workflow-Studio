# Phase 0 — Intake

Goal: capture the user's request and load the knowledge needed to refine it well.

1. **Load the skill's learned rules.** The durable lessons are already ENFORCED in the prompts,
   `reference/kb_*.md`, and `scripts/*.py` you use this run (Phase 5 promotes every reusable lesson
   into those), so the skill applies them automatically — you do not have to memorise them. ALSO
   skim `LESSONS_LEARNED.md`: it is the DIARY of past runs. Scan it for anything relevant to THIS
   request (classification, notation, renderer gotchas) and for any lesson not yet promoted. Do not
   skip it — but note you do NOT need to hold all of it in mind: the promoted rules do the enforcing,
   so the diary can grow without slowing you down.

2. **Read the taxonomy** `reference/diagram_types.md`. It is the master list of what this skill can
   draw and how requests map to types + renderers. Keep it in mind for Phase 1.

3. **Detect the input MODE — free-text vs a project FOLDER.** The argument after
   `/linhpham-diagram` may be either a plain description OR a path to a folder of project docs (or the
   user may say "phân tích folder X", "từ tài liệu trong …", "ingest this folder", etc.).
   - **If it names/points at a folder** (an existing directory, or the user clearly asks to analyse a
     folder of documents) → **FOLDER MODE**: ingest the documents and derive the diagrams from them,
     the same way the technical-proposal skill starts from an RFP folder. Run:
     ```bash
     python scripts/ingest.py --dir "<folder>" --out "<folder>/output/diagrams/_ingest_digest.md"
     ```
     It extracts text from `.txt/.md/.csv/.json/.yaml/.docx/.xlsx/.xlsm/.pdf` (recursively, skipping
     noise dirs) into ONE digest. **Read the digest**, then analyse it: what system is described, its
     components/tiers/integrations/data model/flows, named tech/cloud, compliance, actors. This
     analysis feeds Phase 1, where you will propose a SET of diagrams that fit the material.
   - **Otherwise** → **TEXT MODE**: the free text is the raw description (often vague/partial — that
     is expected, do NOT reject it).
   Either way, note: the subject/domain; what to SHOW (structure / a flow over time / the cloud setup
   / a data model); any named technology (AWS/Azure/GCP, tools, frameworks); the likely audience.
   If the user gave no description AND no folder, ask one short question: "What do you want the diagram
   to show, or point me at a folder of project docs?" — then continue.

4. **Decide output location.** Default `./output/diagrams/` under the current working directory. In
   FOLDER MODE use `<that folder>/output/diagrams/`. If the user named a project folder/path, use
   `<that>/output/diagrams/`.

Do not draw anything yet. Proceed to Phase 1 (Refine).
