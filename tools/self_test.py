#!/usr/bin/env python3
"""Autonomous end-to-end self-test of the proposal workflow.

Simulates Phase 4 outputs (replacements.json + diagrams.json + diagram PNGs),
runs build_docx, runs format_reviewer, renders the output docx to per-page
PNGs via LibreOffice + pdf2image, and reports everything.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TPL = REPO / "skill/linhpham-technicalproposal/templates/proposal_template.docx"
BUILD = REPO / "skill/linhpham-technicalproposal/scripts/build_docx.py"
REVIEW = REPO / "skill/linhpham-technicalproposal/scripts/format_reviewer.py"
RENDER = REPO / "skill/linhpham-technicalproposal/scripts/render_pages.py"
BUILD_DIAG = REPO / "skill/linhpham-technicalproposal/scripts/build_diagram.py"


def header(t):
    print()
    print("=" * 70)
    print(" " + t)
    print("=" * 70)


def make_synthetic_diagram(out_png: Path, title: str) -> bool:
    """Render a simple 300-DPI test PNG using PIL — proves the diagram
    pipeline works even when the bundled icon packs are empty."""
    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError:
        return False
    W, H = 2400, 1500
    img = Image.new("RGB", (W, H), "white")
    draw = ImageDraw.Draw(img)
    try:
        font_title = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 80)
        font_box = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 56)
    except Exception:
        font_title = ImageFont.load_default()
        font_box = ImageFont.load_default()
    # Title
    draw.text((100, 60), title, fill="black", font=font_title)
    # Simple 3-box flow
    boxes = [("User", "#E0F0FF"), ("API Gateway", "#FFE8C0"), ("Service", "#C8FFD4")]
    box_w, box_h = 500, 300
    y = 600
    for i, (label, color) in enumerate(boxes):
        x = 200 + i * 750
        draw.rounded_rectangle([x, y, x + box_w, y + box_h], radius=20,
                                fill=color, outline="#333", width=4)
        bb = draw.textbbox((0, 0), label, font=font_box)
        tw, th = bb[2] - bb[0], bb[3] - bb[1]
        draw.text((x + (box_w - tw) // 2, y + (box_h - th) // 2 - bb[1]),
                  label, fill="black", font=font_box)
        if i < len(boxes) - 1:
            arrow_y = y + box_h // 2
            draw.line([(x + box_w + 20, arrow_y), (x + 750 - 20, arrow_y)],
                      fill="#333", width=6)
            draw.polygon([(x + 750 - 20, arrow_y),
                          (x + 750 - 60, arrow_y - 25),
                          (x + 750 - 60, arrow_y + 25)], fill="#333")
    out_png.parent.mkdir(parents=True, exist_ok=True)
    img.save(out_png, format="PNG", optimize=False, dpi=(300, 300))
    return True


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    td = Path(tempfile.mkdtemp(prefix="proposal_selftest_"))
    print(f"Test workspace: {td}")

    # Synthetic project: a generic loyalty platform modernization bid
    diagrams_dir = td / "diagrams"
    diagrams_dir.mkdir()

    header("1. RENDER 3 synthetic diagrams")
    diag_specs = [
        ("system_context", "System Context — Loyalty Platform"),
        ("container_diagram", "Container Diagram — Core Services"),
        ("cicd_pipeline", "CI/CD Pipeline — GitOps Delivery"),
    ]
    for slug, title in diag_specs:
        out_png = diagrams_dir / f"{slug}.png"
        ok = make_synthetic_diagram(out_png, title)
        size = out_png.stat().st_size if out_png.exists() else 0
        print(f"  [{'OK ' if ok else 'FAIL'}] {slug}.png ({size:,} bytes)")

    header("2. WRITE realistic replacements + diagrams JSON")
    replacements = {
        "client_name": "Norden Retail Group",
        "client_contact_email": "platform@norden.example",
        "project_title": "Loyalty Platform Modernization",
        "version": "1.0",
        "proposal_date": "24 May 2026",
        "vendor_partner_name": "the existing point-of-sale provider",
        "executive_summary": (
            "Norden Retail's current loyalty engine cannot keep up with seasonal "
            "burst traffic; we propose a cloud-native rebuild on AWS managed "
            "services that halves end-to-end latency and triples throughput, "
            "delivered in 22 weeks with a 12-week post-go-live warranty."
        ),
        "purpose": (
            "This proposal scopes the high-level technical approach for the "
            "Norden loyalty platform rebuild and identifies the architectural "
            "decisions the client needs to confirm before detailed design."
        ),
        "system_overview_intro": (
            "The platform is decomposed into four bounded contexts behind an "
            "API gateway, with event-driven side-effects on Kafka and a "
            "managed Postgres data tier."
        ),
        "techstack_backend": (
            ".NET 10 / ASP.NET Core 10 with MediatR, FluentValidation, "
            "MassTransit on top of Amazon MSK (Kafka)."
        ),
        "techstack_frontend": (
            "React 18 + Vite 5 + TypeScript with TanStack Query and Tailwind."
        ),
        "techstack_database": (
            "Amazon Aurora PostgreSQL 16 (writer + 2 readers), "
            "ElastiCache Redis 7 for session + hot-key cache."
        ),
        "techstack_server_hosting": (
            "Amazon EKS multi-AZ with HPA + Cluster Autoscaler; "
            "ALB + CloudFront at the edge."
        ),
        "techstack_data": None,           # no data pipeline in scope -> drop
        "techstack_ai": None,             # no AI in scope -> drop
        "mobile_app_strategy": None,      # web-only -> drop
        "case_study_title": "FruPro multi-tenant B2B platform",
        "summary_body": (
            "Adopting AWS managed services for the loyalty platform is "
            "fundamentally an availability and throughput problem rather than "
            "a code-optimisation one. EKS plus Aurora plus MSK gives Norden "
            "headroom for the next three peak cycles without re-architecting. "
            "The proposal commits to four outcomes: sub-second P95 page loads, "
            "five-nines on the public API, a 12-week warranty after go-live, "
            "and full IP/source handover from day one."
        ),
    }
    diagrams = [
        {"slug": "system_context",
         "subheading": "2.1.2 System Context",
         "target_heading": "System Context",
         "png": str(diagrams_dir / "system_context.png"),
         "caption": "System Context — Loyalty Platform"},
        {"slug": "container_diagram",
         "subheading": "2.1.3 Container Diagram",
         "target_heading": "Container Diagram",
         "png": str(diagrams_dir / "container_diagram.png"),
         "caption": "Container Diagram — Core Services"},
        {"slug": "cicd_pipeline",
         "subheading": "2.1.4 CI/CD Pipeline",
         "target_heading": "CI/CD Pipeline",
         "png": str(diagrams_dir / "cicd_pipeline.png"),
         "caption": "CI/CD Pipeline — GitOps Delivery"},
    ]
    repl_p = td / "replacements.json"
    diag_p = td / "diagrams.json"
    repl_p.write_text(json.dumps(replacements, indent=2), encoding="utf-8")
    diag_p.write_text(json.dumps(diagrams, indent=2), encoding="utf-8")
    print(f"  [OK] replacements.json ({repl_p.stat().st_size:,} bytes)")
    print(f"  [OK] diagrams.json ({diag_p.stat().st_size:,} bytes)")

    header("3. RUN build_docx")
    out_docx = td / "Norden Loyalty Platform - High Level Technical Proposal.docx"
    r = subprocess.run(
        [sys.executable, str(BUILD),
         "--template", str(TPL),
         "--replacements", str(repl_p),
         "--diagrams", str(diag_p),
         "--out", str(out_docx)],
        capture_output=True, text=True,
    )
    print(r.stdout)
    if r.returncode != 0:
        print("STDERR:", r.stderr)
        return 1
    print(f"  Built: {out_docx.name} ({out_docx.stat().st_size:,} bytes)")

    header("4. RUN format_reviewer (strict)")
    review_json = td / "review.json"
    review_md = td / "review.md"
    r2 = subprocess.run(
        [sys.executable, str(REVIEW),
         "--docx", str(out_docx),
         "--json", str(review_json),
         "--md", str(review_md)],
        capture_output=True, text=True,
    )
    print(r2.stdout)
    rep = json.loads(review_json.read_text(encoding="utf-8"))
    blockers = [i for i in rep["issues"] if i["severity"] == "blocker"]
    print(f"  Blockers: {len(blockers)} | Total issues: {len(rep['issues'])}")
    if blockers:
        for i in blockers:
            print(f"    BLOCKER: {i['id']} — {i['summary']}")
            return 1

    header("5. RENDER docx to PDF + per-page PNG (LibreOffice)")
    pages_dir = td / "pages"
    r3 = subprocess.run(
        [sys.executable, str(RENDER),
         "--in", str(out_docx),
         "--out", str(pages_dir),
         "--dpi", "150"],   # 150 DPI is enough for visual inspection
        capture_output=True, text=True,
    )
    print(r3.stdout)
    if r3.stderr and "warning" not in r3.stderr.lower():
        print("STDERR:", r3.stderr[:300])
    pages = sorted(pages_dir.glob("page_*.png")) if pages_dir.exists() else []
    print(f"  Pages rendered: {len(pages)}")
    for p in pages[:6]:
        print(f"    - {p.name} ({p.stat().st_size:,} bytes)")
    if len(pages) > 6:
        print(f"    ... ({len(pages) - 6} more)")

    header("6. FINAL OUTPUT SUMMARY")
    print(f"  Output docx:     {out_docx}")
    print(f"  Format review:   {review_md}")
    print(f"  Rendered pages:  {pages_dir} ({len(pages)} pages)")
    print()
    if not pages:
        print("  NOTE: LibreOffice render failed — install or check tools/render_pages.py.")
    else:
        print("  >>> PIPELINE COMPLETE — open the docx + pages dir to inspect <<<")

    # Move artifacts into the repo so user can inspect after script exits
    artifact_dir = REPO / "selftest_output"
    if artifact_dir.exists():
        shutil.rmtree(artifact_dir)
    shutil.copytree(td, artifact_dir)
    print(f"\n  Artifacts copied to: {artifact_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
