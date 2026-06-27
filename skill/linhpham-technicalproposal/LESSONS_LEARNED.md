# Lessons Learned — /linhpham-technicalproposal

> **Self-learning store for this skill.** This file travels with the skill (git +
> profile junctions), so lessons recorded here apply to **every** run on **every**
> machine where the skill is deployed.
>
> - **Phase 0** reads this file at the start of every run and treats each entry as a
>   hard constraint / preference for the current proposal.
> - **Phase 6** appends a new entry at the end of every run.
>
> Goal: each proposal is more accurate, sharper, and freer of repeated mistakes than
> the last.

## How to read this (Phase 0)

Before doing anything else, internalise every entry below. If an entry names a
concrete fix (a format setting, a diagram rule, a content gap, a forbidden phrase),
apply it proactively this run — do not wait to rediscover the problem.

## How to write an entry (Phase 6)

Append to the **Entries** section, newest on top, using this shape:

```
### <Project> — <proposal type> — <YYYY-MM-DD>
- **Stack/architecture proposed:** … (+ why)
- **Format/layout issues hit & fix:** … (SharePoint compat, >=300 DPI, overflow, template structure, font/spacing drift, widow/orphan)
- **Diagram-quality issues & fix:** … (icon missing, chip/arrow collision, midline centring, label overflow)
- **Content gaps / client feedback:** … (what was missing or wrong, how corrected)
- **Do better next time (reusable):** … (checklist items future runs should apply up-front)
- **Generalisable rule?:** if a lesson is broadly true, also fold it into the relevant phase prompt (04_generate / 05b_format_review) — note here that you did.
```

Keep entries concrete and reusable. If a lesson is universal, promote it into the
phase prompts so it is enforced, and note the promotion here.

---

## Entries

<!-- Newest entry directly below this line. -->

### Kenneth & Co Ride-Hailing & Food-Delivery Super App — High-Level Technical Proposal — 2026-06-27
- **Stack/architecture proposed:** microservices on AWS EKS (honoured the client's stated microservices requirement); Go-primary disciplined-polyglot (Node BFF; JVM only if in-house stream tier; no Python — no ML feature); Redis GEO dispatch + self-managed Go WebSocket gateway; two-tier messaging MSK(Kafka) firehose + SQS/SNS commands; polyglot persistence Aurora PG+PostGIS / ElastiCache Redis / TimescaleDB; per-gateway payment ACL + append-only ledger; Flutter; React; GitHub Actions→ECR→Argo CD; Terraform. Derived impartially from features + domain + comparable products (Grab/Gojek/Uber/DoorDash), rejecting the WBS's .NET/Azure assumption on merit; staffing left to HR.
- **Format/layout issues hit & fix:** (1) `build_docx --diagrams` must point to `output/diagrams/diagrams.json` (Agent A writes it inside the `diagrams/` subfolder) — first run failed because 05a's example shows `output/diagrams.json`. (2) Auto-fix cleared `image_text_crush` (8) + `heading_section_spacing_tight` (38). (3) **`build_docx.py boost_heading_spacing()` clamps heading space-before to an 8-10pt ceiling, below the reviewer's 24pt floor → a rebuild after auto_fix re-introduces the defect.**
- **Diagram-quality issues & fix:** only `pdpa_security_audit` needed TB→LR (11.73"→3.74"). Cosmetic trailing "(" from the label-wrapper. `image_low_resolution` 42× is mostly 143px AWS sub-icons inside large sharp diagrams (false-positive).
- **Content gaps / client feedback:** `case_study_title` placeholdered (no real STS case-study list) — must be swapped by the user; `client_contact_email` placeholdered; output language assumed English.
- **Do better next time (reusable):** point `--diagrams` at `output/diagrams/diagrams.json`; reconcile build_docx heading ceiling with reviewer floor; keep a real STS case-study list; exclude composited sub-icons from the image-resolution check.
- **Generalisable rule? — PROMOTED:** (a) fixed `_HEADING_MAX_SPACE_BEFORE` in `scripts/build_docx.py` to respect the reviewer H1-H6 floors so post-auto-fix rebuilds don't regress; (b) added a path note in `04_generate.md`/`05a_assemble.md` that `diagrams.json` lives in `output/diagrams/`.
- **Round 2 — Tay-Ho format conformance (all PROMOTED to skill):**
  - **Technology Stack renders as 2-col `Technology | Advantages` tables, never prose.** `techstack_*` MUST be arrays of `{name, description}` (04_generate schema + mandatory rule); `render_techstack_tables` only fires on arrays. Template Data/AI fixed to "label heading + body placeholder"; `drop_section_if_empty` gained `content_key`; new zero-tolerance reviewer check `techstack_not_table`. The renderer + tables already existed — the bug was the content schema being prose.
  - **.drawio AWS shapes need `shape=mxgraph.aws4.resourceIcon;resIcon=mxgraph.aws4.<name>`** (bare `shape=mxgraph.aws4.<name>` = empty boxes). Fixed `_aws()` + eks/ecs names + Azure fallback fill. Per-cloud glyph fidelity needs a draw.io visual check (cannot render headlessly).
  - **`image_text_crush` regresses on every rebuild** — re-run `auto_fix --issue image_text_crush` after a rebuild and don't rebuild again; candidate fix is to set image-paragraph spacing to the reviewer floor during build.
