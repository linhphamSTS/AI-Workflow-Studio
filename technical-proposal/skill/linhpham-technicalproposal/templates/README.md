# Templates

## `proposal_template.docx`

Reusable Word template for STS High-Level Technical Proposals. All
project-specific text in Sections 1–2 has been stripped and replaced with
`{{KEY}}` placeholders; the structural sections (`PROPOSED DEVELOPMENT
MANAGEMENT` onwards) are kept verbatim because they're common across STS
bids.

- **Size:** ~3 MB · ~330 paragraphs · 11 tables
- **Heading levels in use:** H1 (cover / TOC) · H3 (top-level sections) · H5/H6 (sub-sections)

### Origin

Bootstrapped once from a prior STS deliverable via `tools/strip_template.py`,
then genericised via `tools/genericize_template.py` (cover strings replaced
with placeholders, customer-specific 2.1.x sub-headings removed, optional
tech-stack rows added). Both scripts are one-shot bootstrap tools — they do
not need to run again in normal use.

### Top-level structure (H3)

| # | Heading | Per-project? | Notes |
|---|---|---|---|
| Cover | `Technical Proposal - High Level` | Verbatim title; cover text is placeholder-driven | See cover placeholders below |
| TOC | `Content` | Verbatim | Auto-refreshes on open (build_docx sets `updateFields=true`) |
| 1 | `INTRODUCTION` | **Fill per project** | H5 markers: Executive Summary · Problems & Solutions · Purpose |
| 2 | `PROPOSED TECHNOLOGY` | **Fill per project** | See Section 2 notes below |
| 3 | `PROPOSED DEVELOPMENT MANAGEMENT` | **Verbatim** | Common across STS: Methodology · Dev Flow · CI/CD · Branch Model · Environments · QA · Testing |
| 4 | `CASE STUDY` | Replace per project | Swap in a relevant client case study |
| 5 | `SUMMARY` | Fill per project | Added per PL03 v01 standard |

### Section 2 structure

```
PROPOSED TECHNOLOGY  (H3)
├── System Overview  (H5)
│   └── 2.1.1 System Context  (H6)   ← anchor only
│       [build_docx injects one H6 per diagram in diagrams.json here,
│        in order: 2.1.2, 2.1.3, ... based on the project's inventory]
├── Technology Stack  (H5)
│   ├── Back-end · Front-end · Database · Server & Hosting  (H6)
│   ├── {{TECHSTACK_DATA}}  (H6, dropped if null)
│   └── {{TECHSTACK_AI}}    (H6, dropped if null)
└── Mobile App Strategy  (H5, dropped if mobile_strategy is null)
```

### Cover-page placeholders

The cover paragraph carries `{{CLIENT_NAME}}`, `{{PROJECT_TITLE}}`,
`{{VERSION}}`, and `{{PROPOSAL_DATE}}`. `build_docx.py` substitutes them
from `replacements.json` at build time — no client- or project-specific
text lives in the template itself.

### Body placeholders

Anywhere in body text, `{{KEY}}` tokens (uppercase, snake_case) are
substituted at build time from `replacements.json`. Any token still
present at format-review time is reported as `unfilled_placeholder`
(blocker) by `scripts/format_reviewer.py`.

### Optional sections

`build_docx.py` drops a heading and its body when the corresponding
replacement value is `null` (or absent). Currently treated as optional:

- `Mobile App Strategy` — drop if `mobile_strategy` is null
- `{{TECHSTACK_DATA}}` — drop if `techstack_data_pipeline` is null
- `{{TECHSTACK_AI}}` — drop if `techstack_ai` is null

### Auto-refresh of the Table of Contents

`build_docx.py` injects `<w:updateFields w:val="true"/>` into
`word/settings.xml` so Word (and SharePoint's web viewer) refresh the TOC
the first time the document is opened. Page numbers and the injected H6
sub-headings appear automatically.

### Re-deriving from a different source (rare)

Only needed if a better source proposal turns up:

```
python tools/strip_template.py --src "C:\path\to\better_prior_proposal.docx"
python tools/genericize_template.py
```
