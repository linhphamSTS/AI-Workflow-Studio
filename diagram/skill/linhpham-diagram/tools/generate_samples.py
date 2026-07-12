#!/usr/bin/env python3
"""Render the samples/ showcase — a DEMONSTRATION of what the SKILL produces.

The cloud/infra/tech diagrams are rendered by the SKILL's own reusable clean-layout
builders in `scripts/diagram_templates.py` (the SAME code a real /linhpham-diagram
run uses), so the samples are literally the skill's output, not a separate script.
The abstract/notation diagrams go through `scripts/build_graph.py` and sequences
through `scripts/build_sequence.py` — again the skill's own renderers.

Run: python skill/linhpham-diagram/tools/generate_samples.py
"""
import sys
from pathlib import Path

SK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SK / "scripts"))
import build_graph, build_sequence                 # noqa: E402
import build_diagram_doc, cloud_specs              # noqa: E402
from svg_util import png_to_drawio                 # noqa: E402
from diagram_templates import TEMPLATES            # noqa: E402  (skill's clean cloud/infra/tech builders)
from PIL import Image, ImageDraw, ImageFont         # noqa: E402

S = SK.parent.parent / "samples"
S.mkdir(exist_ok=True)
for f in S.glob("*"):
    if f.suffix in (".png", ".svg", ".drawio", ".docx") or f.name.endswith(".lint.json"):
        f.unlink()


def _doc(spec, kind, slug):
    """Emit the per-diagram explainer .docx (skips cleanly if the PNG is missing)."""
    png = S / f"{slug}.png"
    if not png.exists():
        return
    try:
        build_diagram_doc.build_doc(build_diagram_doc.describe(spec, kind, slug), png, S / f"{slug}.docx")
    except Exception as e:  # noqa: BLE001
        print(f"! doc {slug}: {e}")

# ===== Abstract / notation diagrams — rendered by the skill's build_graph.py =====
GRAPH = [
 {"slug":"c4_context","title":"System Context — Internet Banking","diagram_type":"c4","engine":"dot","direction":"TB",
  "nodes":[{"id":"cust","label":"Customer","role":"person","subtitle":"Bank customer"},{"id":"sys","label":"Internet Banking","role":"system","tech":"in scope"},
    {"id":"mail","label":"Email System","role":"external"},{"id":"core","label":"Mainframe Banking","role":"external"}],
  "edges":[{"from":"cust","to":"sys","label":"views balances [HTTPS]"},{"from":"sys","to":"mail","label":"sends email [SMTP]","kind":"async"},{"from":"sys","to":"core","label":"gets account data [XML/HTTPS]"}]},
 {"slug":"class_diagram","title":"Class Diagram — Domain Model","diagram_type":"class","engine":"dot","direction":"TB",
  "nodes":[{"id":"animal","type":"class","label":"Animal","fields":["+name: str","#age: int"],"methods":["+speak()"]},
    {"id":"dog","type":"class","label":"Dog","fields":["+breed: str"],"methods":["+speak()","+fetch()"]},{"id":"cat","type":"class","label":"Cat","methods":["+speak()"]},
    {"id":"owner","type":"class","label":"Owner","fields":["+name: str"],"methods":["+adopt()"]}],
  "edges":[{"from":"dog","to":"animal","kind":"inheritance"},{"from":"cat","to":"animal","kind":"inheritance"},{"from":"owner","to":"animal","kind":"aggregation","label":"owns 0..*"}]},
 {"slug":"erd","title":"ERD — Shop Data Model","diagram_type":"erd","engine":"dot","direction":"LR",
  "nodes":[{"id":"u","type":"entity","label":"User","attributes":["id  PK","email  UQ","name"]},{"id":"o","type":"entity","label":"Order","attributes":["id  PK","user_id  FK","total","status"]},
    {"id":"i","type":"entity","label":"OrderItem","attributes":["id  PK","order_id  FK","sku","qty"]},{"id":"p","type":"entity","label":"Product","attributes":["sku  PK","name","price"]}],
  "edges":[{"from":"u","to":"o","label":"1 : N places"},{"from":"o","to":"i","label":"1 : N contains"},{"from":"p","to":"i","label":"1 : N in"}]},
 {"slug":"dfd","title":"Data Flow Diagram — Order Processing (L1)","diagram_type":"dfd","engine":"dot","direction":"LR",
  "nodes":[{"id":"cust","label":"Customer","role":"external"},{"id":"p1","label":"1. Validate Order","role":"process"},{"id":"p2","label":"2. Fulfil Order","role":"process"},
    {"id":"d1","label":"Orders","role":"datastore"},{"id":"wh","label":"Warehouse","role":"external"}],
  "edges":[{"from":"cust","to":"p1","label":"order"},{"from":"p1","to":"d1","label":"validated order"},{"from":"d1","to":"p2","label":"order record"},{"from":"p2","to":"wh","label":"pick list"}]},
 {"slug":"bpmn","title":"BPMN — Order Fulfilment","diagram_type":"bpmn","engine":"dot","direction":"LR",
  "nodes":[{"id":"s","label":"Order received","role":"start"},{"id":"t1","label":"Validate order","role":"task"},{"id":"g1","label":"In stock?","role":"gateway"},
    {"id":"t2","label":"Reserve stock","role":"task"},{"id":"t3","label":"Create backorder","role":"task"},{"id":"t4","label":"Ship order","role":"task"},{"id":"e","label":"Order complete","role":"end"}],
  "edges":[{"from":"s","to":"t1"},{"from":"t1","to":"g1"},{"from":"g1","to":"t2","label":"yes"},{"from":"g1","to":"t3","label":"no"},{"from":"t2","to":"t4"},{"from":"t3","to":"t4"},{"from":"t4","to":"e"}]},
 {"slug":"swimlane","title":"Swimlane — Purchase Approval","diagram_type":"swimlane","engine":"dot","direction":"LR",
  "nodes":[{"id":"a1","label":"Submit request","role":"process"},{"id":"m1","label":"Review request","role":"process"},{"id":"g1","label":"Approved?","role":"decision"},
    {"id":"f1","label":"Create PO","role":"process"},{"id":"f2","label":"Notify rejection","role":"process"}],
  "edges":[{"from":"a1","to":"m1"},{"from":"m1","to":"g1"},{"from":"g1","to":"f1","label":"yes"},{"from":"g1","to":"f2","label":"no"}],
  "clusters":[{"id":"emp","label":"Employee","members":["a1"]},{"id":"mgr","label":"Manager","members":["m1","g1"]},{"id":"fin","label":"Finance","members":["f1","f2"]}]},
 {"slug":"decision_tree","title":"Decision Tree — Loan Approval","diagram_type":"flowchart","engine":"dot","direction":"TB",
  "nodes":[{"id":"q1","label":"Credit score > 700?","role":"decision"},{"id":"q2","label":"Income > 50k?","role":"decision"},{"id":"q3","label":"Has collateral?","role":"decision"},
    {"id":"a1","label":"Approve","role":"end"},{"id":"a2","label":"Approve (review)","role":"end"},{"id":"r1","label":"Reject","role":"end"}],
  "edges":[{"from":"q1","to":"a1","label":"yes"},{"from":"q1","to":"q2","label":"no"},{"from":"q2","to":"q3","label":"yes"},{"from":"q2","to":"r1","label":"no"},{"from":"q3","to":"a2","label":"yes"},{"from":"q3","to":"r1","label":"no"}]},
 {"slug":"order_state","title":"Order Lifecycle — State Machine","diagram_type":"state","engine":"dot","direction":"LR",
  "nodes":[{"id":"i","role":"initial"},{"id":"pending","label":"Pending","role":"state"},{"id":"paid","label":"Paid","role":"state"},{"id":"fulfilled","label":"Fulfilled","role":"state"},
    {"id":"shipped","label":"Shipped","role":"state"},{"id":"delivered","label":"Delivered","role":"state"},{"id":"cancelled","label":"Cancelled","role":"state"},{"id":"f","role":"final"}],
  "edges":[{"from":"i","to":"pending"},{"from":"pending","to":"paid","label":"payment ok"},{"from":"pending","to":"cancelled","label":"timeout / cancel"},{"from":"paid","to":"fulfilled","label":"stock reserved"},
    {"from":"fulfilled","to":"shipped","label":"dispatch"},{"from":"shipped","to":"delivered","label":"POD"},{"from":"delivered","to":"f"},{"from":"cancelled","to":"f"}]},
 {"slug":"org_chart","title":"Org Chart — Engineering","diagram_type":"orgchart","engine":"dot","direction":"TB",
  "nodes":[{"id":"ceo","label":"CEO","role":"process"},{"id":"cto","label":"CTO","role":"process"},{"id":"cfo","label":"CFO","role":"process"},{"id":"em","label":"Eng Manager","role":"process"},
    {"id":"d1","label":"Backend Dev","role":"process"},{"id":"d2","label":"Frontend Dev","role":"process"},{"id":"qa","label":"QA Lead","role":"process"}],
  "edges":[{"from":"ceo","to":"cto"},{"from":"ceo","to":"cfo"},{"from":"cto","to":"em"},{"from":"em","to":"d1"},{"from":"em","to":"d2"},{"from":"cto","to":"qa","kind":"dashed","label":"dotted line"}]},
 {"slug":"mindmap","title":"Mind Map — Product Launch","diagram_type":"mindmap","engine":"twopi","direction":"TB",
  "nodes":[{"id":"root","label":"Product Launch","role":"process"},{"id":"mkt","label":"Marketing","role":"process"},{"id":"eng","label":"Engineering","role":"process"},{"id":"sales","label":"Sales","role":"process"},{"id":"sup","label":"Support","role":"process"},
    {"id":"m1","label":"Campaign","role":"process"},{"id":"m2","label":"PR","role":"process"},{"id":"e1","label":"MVP","role":"process"},{"id":"e2","label":"Beta","role":"process"},{"id":"s1","label":"Pricing","role":"process"},{"id":"p1","label":"Docs","role":"process"}],
  "edges":[{"from":"root","to":"mkt"},{"from":"root","to":"eng"},{"from":"root","to":"sales"},{"from":"root","to":"sup"},{"from":"mkt","to":"m1"},{"from":"mkt","to":"m2"},{"from":"eng","to":"e1"},{"from":"eng","to":"e2"},{"from":"sales","to":"s1"},{"from":"sup","to":"p1"}]},
 {"slug":"network_topology","title":"Network Topology — DMZ + LAN","diagram_type":"network","engine":"dot","direction":"LR",
  "nodes":[{"id":"net","label":"Internet","role":"external"},{"id":"fw","label":"Perimeter Firewall","role":"process"},{"id":"lb","label":"Load Balancer","role":"service"},
    {"id":"w1","label":"Web 1","role":"service"},{"id":"w2","label":"Web 2","role":"service"},{"id":"db","label":"Database","role":"datastore"}],
  "edges":[{"from":"net","to":"fw","label":"443"},{"from":"fw","to":"lb"},{"from":"lb","to":"w1"},{"from":"lb","to":"w2"},{"from":"w1","to":"db","label":"5432"},{"from":"w2","to":"db","label":"5432"}],
  "clusters":[{"id":"dmz","label":"DMZ","members":["lb","w1","w2"]},{"id":"lan","label":"Trusted LAN","members":["db"]}]},
]
for s in GRAPH:
    try: build_graph.render(s, S/f"{s['slug']}.png", emit_drawio=True)
    except Exception as e: print(f"! {s['slug']}: {e}")
for s in GRAPH:
    _doc(s, "graph", s["slug"])

# ===== Sequences — rendered by the skill's build_sequence.py =====
SEQ = [
 {"slug":"oauth_login","title":"OAuth 2.0 Login — Authorization Code Flow","diagram_type":"sequence",
  "participants":[{"id":"user","label":"User","role":"actor"},{"id":"spa","label":"Web App (SPA)"},{"id":"idp","label":"OAuth Provider","role":"external"},{"id":"api","label":"Backend API"}],
  "messages":[{"from":"user","to":"spa","label":"Click 'Sign in'","kind":"sync"},{"from":"spa","to":"idp","label":"redirect /authorize","kind":"sync"},{"from":"user","to":"idp","label":"authenticate + consent","kind":"sync"},
    {"from":"idp","to":"spa","label":"redirect back + code","kind":"return"},{"from":"spa","to":"api","label":"POST /token (code)","kind":"sync"},{"from":"api","to":"idp","label":"exchange code","kind":"sync"},
    {"from":"idp","to":"api","label":"access + refresh token","kind":"return"},{"from":"api","to":"spa","label":"session cookie","kind":"return"}]},
 {"slug":"saga_orchestration","title":"Saga — Order Orchestration with Compensation","diagram_type":"sequence",
  "participants":[{"id":"orch","label":"Saga Orchestrator"},{"id":"ord","label":"Order Svc"},{"id":"inv","label":"Inventory Svc"},{"id":"pay","label":"Payment Svc","role":"external"}],
  "messages":[{"from":"orch","to":"ord","label":"create order","kind":"sync"},{"from":"ord","to":"orch","label":"created","kind":"return"},
    {"from":"orch","to":"inv","label":"reserve stock","kind":"sync"},{"from":"inv","to":"orch","label":"reserved","kind":"return"},
    {"from":"orch","to":"pay","label":"charge card","kind":"sync"},{"from":"pay","to":"orch","label":"payment FAILED","kind":"return"},
    {"from":"orch","to":"inv","label":"compensate: release stock","kind":"async"},{"from":"orch","to":"ord","label":"compensate: cancel order","kind":"async"}],
  "fragments":[{"type":"alt","label":"payment failed → run compensations","from":5,"to":8}]},
]
for s in SEQ:
    try:
        build_sequence.render(s, S/f"{s['slug']}.png"); png_to_drawio(S/f"{s['slug']}.png", s["title"])
    except Exception as e: print(f"! {s['slug']}: {e}")
for s in SEQ:
    _doc(s, "sequence", s["slug"])

# ===== Cloud / infra / tech — the SKILL's clean-layout templates =====
for name, fn in TEMPLATES.items():
    try: fn(S); print(f"{name} ok")
    except Exception as e: print(f"! {name}: {e}")
for name in TEMPLATES:
    if name in cloud_specs.SPECS:
        _doc(cloud_specs.SPECS[name], "cloud", name)

# stray graphviz source cleanup (keep the deliverable formats + per-diagram .docx +
# any .lint.json the renderer wrote for a real layout defect, so a later
# diagram_check on samples/ still catches it)
for f in S.iterdir():
    if f.suffix not in (".png", ".svg", ".drawio", ".md", ".docx") and not f.name.endswith(".lint.json"):
        try: f.unlink()
        except OSError: pass

# ===== gallery =====
pngs = sorted(p for p in S.glob("*.png") if not p.name.startswith("gallery"))
COLS, CW, CH, PAD, LH, PP = 4, 680, 560, 24, 46, 12
F = ImageFont.truetype("C:/Windows/Fonts/segoeui.ttf", 26) if Path("C:/Windows/Fonts/segoeui.ttf").exists() else ImageFont.load_default()
pages = [pngs[i:i+PP] for i in range(0, len(pngs), PP)]
for pi, page in enumerate(pages):
    rows = (len(page)+COLS-1)//COLS; W = COLS*(CW+PAD)+PAD; H = rows*(CH+LH+PAD)+PAD
    cv = Image.new("RGB", (W, H), "#f4f5f7"); d = ImageDraw.Draw(cv)
    for idx, p in enumerate(page):
        r, c = divmod(idx, COLS); x = PAD+c*(CW+PAD); y = PAD+r*(CH+LH+PAD)
        d.rectangle([x, y, x+CW, y+CH+LH], fill="white", outline="#d0d3d8", width=2)
        d.rectangle([x, y, x+CW, y+LH], fill="#1f2937"); d.text((x+14, y+10), p.stem, font=F, fill="white")
        im = Image.open(p).convert("RGB"); im.thumbnail((CW-20, CH-20), Image.LANCZOS)
        cv.paste(im, (x+(CW-im.width)//2, y+LH+(CH-im.height)//2))
    cv.save(S/f"gallery_{pi+1}.png")
print(f"TOTAL {len(pngs)} diagrams, {len(pages)} gallery page(s)")
