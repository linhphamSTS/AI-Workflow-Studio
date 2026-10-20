# -*- coding: utf-8 -*-
"""Cross-check the proposal against the WBS that ships beside it.

Each document has its own gate, and neither gate can see the other. That is how a proposal put a
self-built option into "Phase 2" while the WBS priced it as an option of Phase 1, and how a
proposal recommending one cloud shipped beside an estimate whose infrastructure tasks named
another. Both were found by reading, after every gate had passed.

Hard checks (exit 1):
  * a total of hours or man-days quoted in the proposal that is close to the WBS total but not
    equal to it (a stale figure from an earlier round);
  * the cloud the proposal names most is not the cloud the WBS names most.
Review list (printed, not failed, because wording varies too much to decide automatically):
  * every paragraph of the proposal that mentions an Out of Scope item of the WBS, with the
    heading it sits under, flagged when that heading reads as in-scope or Phase 1.

Usage: python check_crossdoc.py --docx <proposal.docx> --wbs <WBS.xlsx>
The WBS is read in the house layout (ID in A, Module in B, Feature in C, Description in D,
effort columns from F to the Total column) with an "Out of Scope" sheet.
"""
import argparse
import re
import sys

import openpyxl
from docx import Document

CLOUDS = {
    "AWS": r"\b(AWS|Amazon Web Services|EC2|EKS|S3|RDS|Aurora|Lambda|CloudFront)\b",
    "Azure": r"\b(Azure|AKS|Cosmos DB|Entra ID|App Service)\b",
    "GCP": r"\b(GCP|Google Cloud|Cloud Run|GKE|BigQuery|Cloud SQL|Pub/Sub|Memorystore)\b",
}
HOURS = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d{3,6})\s*(giờ công|giờ|man-hours?|hours?|h\b)", re.I)
DAYS = re.compile(r"(\d{1,3}(?:[.,]\d{3})+|\d{2,5})\s*(ngày công|man-days?|person-days?)", re.I)
IN_SCOPE = re.compile(r"(phase 1|giai đoạn 1|in scope|scope of work|phạm vi công việc|"
                      r"phạm vi giai đoạn 1|mvp)", re.I)
OUT_SCOPE = re.compile(r"(out of scope|ngoài phạm vi|phase 2|phase 3|giai đoạn 2|giai đoạn 3|"
                       r"optional|tùy chọn|future|sau này)", re.I)
STOP = {"and", "the", "for", "with", "from", "this", "that", "của", "cho", "các", "những", "được",
        "trong", "theo", "không", "một", "riêng"}


def num(s):
    return int(re.sub(r"[.,]", "", s))


def cell_value(ws, ref, memo):
    """Evaluate a cell the way Excel would for the formulas a WBS uses (`=A1+B2`,
    `=SUM(F5:K5)`, `=SUM(F3,F54,...)`). openpyxl writes no cached values, so a generated
    workbook has no number in its TOTAL cell until something computes it."""
    if ref in memo:
        return memo[ref]
    v = ws[ref].value
    if isinstance(v, (int, float)):
        out = v
    elif isinstance(v, str) and v.startswith("="):
        out = eval_expr(ws, v[1:], memo)
    else:
        out = 0
    memo[ref] = out
    return out


def eval_expr(ws, expr, memo):
    expr = expr.replace("$", "").strip()
    m = re.fullmatch(r"SUM\((.*)\)", expr, re.I)
    if m:
        return sum(eval_expr(ws, part, memo) for part in m.group(1).split(","))
    if "+" in expr:
        return sum(eval_expr(ws, part, memo) for part in expr.split("+"))
    if ":" in expr:
        return sum(cell_value(ws, c.coordinate, memo) for row in ws[expr] for c in row)
    if re.fullmatch(r"[A-Z]{1,3}\d+", expr):
        return cell_value(ws, expr, memo)
    try:
        return float(expr)
    except ValueError:
        return 0


def read_wbs(path):
    """Total hours from the sheet's own TOTAL row (rows the WBS keeps outside its total, such
    as a priced option, stay outside), the task text, and the Out of Scope items."""
    wb = openpyxl.load_workbook(path, data_only=False)
    total, desc, oos = 0, [], []
    for ws in wb.worksheets:
        title = ws.title.lower()
        if "out of scope" in title or "ngoài phạm vi" in title:
            col, start = None, None
            for r in range(1, min(ws.max_row, 6) + 1):
                for c in range(1, ws.max_column + 1):
                    if str(ws.cell(r, c).value or "").strip().lower() in ("item", "hạng mục"):
                        col, start = c, r + 1
            for r in range(start or 2, ws.max_row + 1):
                item = ws.cell(r, col or 2).value
                if item:
                    oos.append(str(item))
            continue
        tcol = None
        for r in (1, 2):
            for c in range(1, ws.max_column + 1):
                if str(ws.cell(r, c).value or "").lower().startswith(("total effort", "tổng nỗ lực")):
                    tcol = c
        if not tcol:
            continue
        memo, sheet_total = {}, None
        for r in range(3, ws.max_row + 1):
            labels = {str(ws.cell(r, c).value or "").strip().upper() for c in (1, 2)}
            if labels & {"TOTAL", "TỔNG CỘNG"}:
                sheet_total = cell_value(ws, ws.cell(r, tcol).coordinate, memo)
            rid = str(ws.cell(r, 1).value or "").strip()
            if re.fullmatch(r"\d+(\.\d+)+", rid) and ws.cell(r, 3).value:
                desc.append(" ".join(str(ws.cell(r, c).value or "") for c in (3, 4, 5)))
        total += int(round(sheet_total or 0))
    return total, " ".join(desc), oos


def proposal_paragraphs(path):
    d = Document(path)
    heading, out = "", []
    for p in d.paragraphs:
        t = (p.text or "").strip()
        if not t:
            continue
        if (p.style.name or "").startswith("Heading"):
            heading = t
            continue
        out.append((heading, t))
    for tb in d.tables:
        for row in tb.rows:
            for cell in row.cells:
                t = cell.text.strip()
                if t:
                    out.append(("(table)", t))
    return out


def dominant_cloud(text):
    counts = {k: len(re.findall(rx, text)) for k, rx in CLOUDS.items()}
    best = max(counts, key=lambda k: counts[k])
    return (best if counts[best] else None), counts


def phrases(item):
    """Two-word phrases of the item name. Single words match everywhere in Vietnamese, where a
    word is one syllable ("vé", "người", "mua"); a phrase ("chuyển nhượng", "lịch sử") does not."""
    head = re.split(r"[:(–]", item)[0].lower()
    words = [w for w in re.findall(r"\w+", head) if w not in STOP and not w.isdigit()]
    return [" ".join(words[i:i + 2]) for i in range(len(words) - 1)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docx", required=True)
    ap.add_argument("--wbs", required=True)
    a = ap.parse_args()

    total, wbs_text, oos = read_wbs(a.wbs)
    paras = proposal_paragraphs(a.docx)
    prop_text = " ".join(t for _h, t in paras)
    fails = []

    print("WBS total: %d h  (%d man-days at 8 h)" % (total, round(total / 8)))
    for rx, unit, want in ((HOURS, "h", total), (DAYS, "man-days", round(total / 8))):
        for m in rx.finditer(prop_text):
            n = num(m.group(1))
            if want and n != want and abs(n - want) <= 0.3 * want:
                fails.append("proposal quotes %s %s, the WBS total is %d %s (stale figure?)"
                             % (m.group(1), m.group(2), want, unit))

    pc, pcounts = dominant_cloud(prop_text)
    wc, wcounts = dominant_cloud(wbs_text)
    print("Cloud named most: proposal %s %s | WBS %s %s" % (pc, pcounts, wc, wcounts))
    if pc and wc and pc != wc:
        fails.append("the proposal is about %s but the WBS tasks name %s most" % (pc, wc))

    print("\nOut of Scope items mentioned in the proposal (read each one):")
    flagged = 0
    for item in oos:
        ph = phrases(item)
        if not ph:
            continue
        need = len(ph) if len(ph) <= 2 else max(2, int(len(ph) * 0.6 + 0.5))
        for heading, t in paras:
            low = re.sub(r"\s+", " ", t.lower())
            if sum(1 for x in ph if x in low) >= need:
                risky = IN_SCOPE.search(heading) and not OUT_SCOPE.search(heading + " " + t)
                flagged += bool(risky)
                print("  %s %s\n      under '%s': %s"
                      % ("!! IN-SCOPE HEADING" if risky else "  ", item[:70], heading[:60], t[:140]))
                break
    if flagged:
        print("\n%d Out of Scope item(s) appear under an in-scope or Phase 1 heading: confirm the "
              "proposal and the WBS put each one in the same phase." % flagged)

    print()
    for f in fails:
        print("[FAIL] " + f)
    print("RESULT: %s" % ("CONSISTENT" if not fails else "%d FAILURE(S)" % len(fails)))
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
