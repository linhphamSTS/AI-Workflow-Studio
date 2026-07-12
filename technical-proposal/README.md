# TechnicalProposal-WorkFlow

A Claude Code skill that turns a folder of RFP / brief / reference docs into a polished,
SharePoint-Online-compatible **High-Level Technical Proposal .docx** — with senior-SA-grade
architecture diagrams.

```
/linhpham-technicalproposal <projectname>
```

Auto-scans the local filesystem for the project folder, ingests every supported input file,
proposes a tech stack, asks the user to confirm, then orchestrates parallel agents to draw
diagrams and assemble the document. A strict format-review agent verifies layout, sharpness,
and SharePoint compatibility before delivery.

## Install

```bash
# 1. Clone anywhere on your machine.
git clone https://github.com/linhphamSTS/TechnicalProposal-WorkFlow.git
cd TechnicalProposal-WorkFlow

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

## Repo layout

```
TechnicalProposal-WorkFlow/
├── skill/
│   └── linhpham-technicalproposal/      # source of truth for the skill
│       ├── SKILL.md
│       ├── prompts/                     # phase 0..6 instruction files
│       ├── scripts/                     # python helpers (build, diagram, review)
│       ├── templates/                   # proposal_template.docx
│       └── assets/icons/                # 8 icon packs (SVG; PNG generated at deploy time)
├── tools/
│   ├── deploy.py                        # main cross-platform deploy
│   ├── fetch_icons.py                   # (todo) download official icon sets
│   └── prerender_icons.py               # (todo) SVG -> PNG @200/300 DPI
├── docs/
├── deploy.bat                           # Windows wrapper
├── deploy.command                       # macOS double-clickable wrapper
└── deploy.sh                            # Linux wrapper
```

## License

MIT (skill code). Icon packs retain their upstream licenses — see
`skill/linhpham-technicalproposal/assets/icons/README.md`.
