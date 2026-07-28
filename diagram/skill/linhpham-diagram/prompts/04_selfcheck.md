# Phase 4 — Self-check (quality gate: "would a 20-year Solution Architect ship this?")

Every generated diagram MUST pass this gate before delivery. The bar is not "it renders" — it is
**correct, professional, and beautiful, as if drawn by a Solution Architect with 20 years'
experience**, AND **sharp and sized to drop cleanly into a Word document, one page**. Fix, re-render,
re-check until it passes. Never deliver a diagram that fails.

## 1. Automated check (run for EVERY diagram)
```bash
python scripts/diagram_check.py --dir output/diagrams --json output/diagrams/diagram_check.json
```
It verifies:
- **Sharp / clear at the real embed size:** a document embeds the figure at **6.5in wide**, so what
  matters is `width_px / 6.5` — the effective DPI on the page, not the long side. Below 220 DPI
  (< 1430 px wide) is a BLOCKER (`png_soft_for_embed`); below the 300 DPI crisp target
  (< 1950 px wide) is a warning (`png_below_crisp`). The renderers already up-render to clear this,
  so a hit here means something bypassed them. Save with 300-dpi metadata.
- **Fits one Word page:** rendered height at 6.5in embed width must be <= 9.0in (BLOCKER `png_too_tall`);
  a warning (`png_tight_for_word`) fires above 8.5in so you leave room for the caption. Aim <= 8.5in.
- **.drawio hygiene:** well-formed, has nodes/edges, no blank boxes, no label line ending on "(",
  line breaks preserved, and nested boundaries for VPC/subnet network diagrams.
- **Layout lint (text overflow / label overlap) — BLOCKER.** For cloud/infra diagrams (`build_cloud`),
  the renderer self-checks with the REAL fonts + coordinates it drew with and writes a `<slug>.lint.json`
  ONLY when it finds a defect: `header_overflow` (a boundary/subnet title crossing its box edge) or
  `label_overlap` (an edge label landing on a node/header label). `diagram_check` promotes each to a
  blocker. This is automatic and applies to EVERY diagram — so "text must not overflow a border and no
  two labels may overlap" is enforced, not just reviewed. Zero tolerance: fix and re-render until gone.

**Fix every BLOCKER and re-render until 0 blockers.** For `png_too_tall`/`png_tight_for_word`: flip
direction (TB<->LR), group nodes, or split into two figures — NEVER shrink to illegibility.

## 2. SA-grade visual review (`Read` the PNG with vision — mandatory)
Open the rendered PNG and judge it against the 20-year-SA rubric. Every item must hold:

**Correctness**
- The diagram TYPE and notation match what was requested and the KB convention (flowchart ISO shapes,
  ERD crow's-foot, C4 boundaries, cloud nested VPC/VNet, sequence lifelines, etc.).
- Every element the brief promised is present and correctly connected; every edge is labelled with a
  real mechanism (HTTPS/gRPC/event/SQL), not generic "uses"/"calls".
- No wrong-cloud icons; no invented components; no component drawn twice.

**Professional structure (the senior signal)**
- Trust boundaries NEST (VPC ⊃ subnet ⊃ pool), not flat siblings. Edge/CDN/WAF outside the network
  boundary; data tier innermost; identity/observability as a side rail.
- Consistent reading order (top→bottom or left→right, not mixed); users top/left, data bottom/inner.
- A LEGEND is present when there are >2 colours or line styles; sync=solid, async=dashed is honoured.
- Per-tier colour hierarchy; no cluster floating unconnected; <= ~9 elements per group.

**Beauty / polish**
- No text overflows its box; no label touches an icon; no arrow cuts through a title chip or a box.
- **Every boundary/subnet header sits INSIDE its box** (the manual-grid renderer widens the box or
  wraps the header to guarantee this — if a title still crosses an edge, the box needs widening).
- **No edge label overlaps a node label or another label.** A same-column (stacked) edge label
  belongs in the clear side gutter, never on the centred node label beneath the icon.
- Labels wrapped cleanly (no dangling "("); no overlapping nodes/edges; balanced whitespace.
- Caption reads `<Type> — <Scope>`.

Crop the densest region — and specifically crop each boundary header and every edge label — then
`Read` the crop to confirm nothing overflows a border or overlaps. The automated lint (§1) catches
these for `build_cloud` diagrams, but confirm visually for Graphviz/sequence diagrams too. **If any item fails, fix the
spec/script and re-render — do not rationalise a mediocre diagram.** Ask yourself literally: *would a
principal SA put this in front of a paying client?* If not, redo it.

## 3. Word-embed confirmation
Confirm the final PNG embeds cleanly at 6.5in wide on a single Word page: `rendered_h_in = 6.5 * h/w`
should be <= 8.5in (hard max 9.0in), and `width_px >= 1950` (= 300 DPI at that embed width). State
the computed height AND the effective embed DPI in the Phase-5 report so the user knows it will both
fit and look crisp.

Only when `diagram_check` reports 0 blockers AND the SA-grade visual review passes, proceed to
Phase 5.
