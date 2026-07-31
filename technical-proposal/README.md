# Technical Proposal — `/linhpham-technicalproposal`

A Claude Code skill that turns a folder of RFP / brief / reference docs into a polished,
SharePoint-Online-compatible **High-Level Technical Proposal .docx** — with senior-SA-grade
architecture diagrams.

This skill lives inside the [AI Workflow Studio](../README.md) monorepo, alongside sibling skills
such as `/linhpham-diagram` and `/linhpham-wbs`, and a shared web app that drives them.

```
/linhpham-technicalproposal <projectname>
```

Auto-scans the local filesystem for the project folder, ingests every supported input file,
proposes a tech stack, asks the user to confirm, then orchestrates parallel agents to draw
diagrams and assemble the document. A strict format-review agent verifies layout, sharpness,
and SharePoint compatibility before delivery.

## Install

Most people should install the whole monorepo in one step, which deploys this skill
along with the other two and prepares the web app — see the
[root README](../README.md#install-once-per-machine).

To deploy **only this skill**:

```bash
# 1. Clone anywhere on your machine.
git clone https://github.com/linhphamSTS/AI-Workflow-Studio.git
cd AI-Workflow-Studio/technical-proposal

# 2. Run the platform-appropriate deploy script.
#    Windows:  double-click deploy.bat
#    macOS:    double-click deploy.command
#    Linux:    ./deploy.sh
```

The deploy script:

1. Scans your home directory for every Claude Code profile (`.claude`, `.claude-account2`, ...).
2. Verifies each candidate is **actually** a Claude profile by checking for known signature files
   (`.credentials.json`, `history.jsonl`, `.claude.json`, `projects/`, `plugins/`) — folders that
   merely share the `.claude*` prefix but are not real profiles are skipped.
3. Creates a junction (Windows) or symlink (macOS/Linux) from each profile's `skills/` folder to
   this repo's `skill/linhpham-technicalproposal/`. **Editing in the repo updates every profile
   instantly — no re-deploy needed.**

Re-running the deploy script is idempotent and safe; pass `--mode copy` if you prefer hard copies
over symlinks.

## Updating

```bash
git pull
# Existing links keep working. Re-run deploy.* only if you switched between link/copy modes
# or if a new Claude profile was added since the last deploy.
```

## Folder layout

```
technical-proposal/
├── skill/
│   └── linhpham-technicalproposal/      # source of truth for the skill
│       ├── SKILL.md
│       ├── LESSONS_LEARNED.md           # self-learning diary; read at phase 0, appended at phase 6
│       ├── prompts/                     # phase 0..6 instruction files
│       ├── scripts/                     # renderers + build + review (see below)
│       ├── templates/                   # proposal_template.docx
│       ├── assets/icons/                # 8 icon packs (ai aws azure container data gcp generic network)
│       └── tools/fetch_tech_logos.mjs   # node: fetch technology logos for the stack tables
├── tools/
│   ├── deploy.py                        # main cross-platform deploy
│   ├── fetch_icons.py                   # download official icon sets
│   ├── prerender_icons.py               # SVG -> PNG @200/300 DPI
│   ├── strip_template.py                # turn a delivered .docx back into a reusable template
│   ├── finalize_template.py             # apply the template's SharePoint fixes
│   ├── self_test.py                     # smoke-test the skill end to end
│   └── verify_all.py, verify_workflow.py
├── deploy.bat                           # Windows wrapper
├── deploy.command                       # macOS double-clickable wrapper
└── deploy.sh                            # Linux wrapper
```

The rendering scripts (`build_cloud`, `build_graph`, `build_sequence`, `cloud_specs`,
`diagram_check`, `diagram_templates`, `diagrams_runtime`, `drawio_export`, `svg_util`,
`build_diagram`) are **shared byte for byte** with the `/linhpham-diagram` skill and are
gated by `tools/check_skill_parity.py` at the repo root. Edit one, copy it to the other in
the same change, then run the gate. The document scripts (`build_docx`, `format_reviewer`,
`check_consistency`, `auto_fix`, `render_pages`) belong to this skill alone.

## License

MIT (skill code). Icon packs retain their upstream licenses — see
`skill/linhpham-technicalproposal/assets/icons/README.md`.
