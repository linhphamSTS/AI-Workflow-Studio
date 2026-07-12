# Knowledge Base — Data & Process/Business Diagrams

> Notation + layout + Graphviz mapping for data and process/business diagram families.
> Graphviz shape vocab: `box ellipse diamond parallelogram hexagon trapezium invtrapezium house cds cylinder circle doublecircle note component terminator folder box3d record/Mrecord plaintext(HTML table)`. Engines: `dot` (hierarchical), `twopi` (radial), `neato` (spring), `circo` (circular).

## PART A — DATA

### 1. ERD (Entity-Relationship)
Models the data schema — entities/tables, attributes, relationships + cardinality.
- **Modern table style:** rectangle of rows; shaded title band (entity name, singular); attribute rows `name datatype flags`; **PK bold/underlined or `PK` badge; FK = `FK`; unique = `U`**.
- **Crow's foot cardinality** = a pair of symbols at each line end (inner = min/modality, outer = max): tick `|` = one, ring `O` = zero, crow's foot `<` = many. Combos: zero-or-one `O|`, exactly-one `||`, zero-or-many `O<`, one-or-many `|<`.
- **Chen (classic alt):** entities=rectangles, attributes=ovals, relationships=diamonds (can hold attributes), cardinality `1/N/M`.
- **Graphviz (pure `dot`):** entities `shape=plaintext` HTML `<TABLE>` with a `PORT` per attribute row so edges anchor to PK/FK. Crow's foot is NATIVE via arrowhead tokens on `arrowhead`/`arrowtail` + `dir=both`: `crow`(many) `tee`(one-bar) `odot`(ring), concatenated — `crowtee`=one-or-many, `crowodot`=zero-or-many, `teetee`=exactly-one, `teeodot`=zero-or-one.

### 2. DFD (Data Flow Diagram)
How data moves (independent of control/timing). 4 elements:
| Element | Yourdon/DeMarco | Gane-Sarson |
|---|---|---|
| Process (≥1 in AND ≥1 out) | circle | rounded rect + ID sub-box |
| Data store | two parallel lines | open-ended rect + `D1` cell |
| External entity | rectangle (edges) | rectangle |
| Data flow | labelled arrow | labelled arrow |
- **Leveling:** Context (L0) = whole system as one process `0` + externals, no stores; L1 = sub-processes `1,2,3`; L2+ dotted-decimal (`2`→`2.1`). Balancing: child net I/O = parent boundary flows.
- **Layout LR** (inputs left, outputs right); externals on perimeter.
- **Graphviz:** process `circle`/`box,rounded`; external `box`(shadow≈`box3d`); flows = labelled edges. Data stores need HTML-table or custom SVG (no native shape).

### 3. Data Pipeline / Lineage
Spine LR: `SOURCE → INGEST → TRANSFORM → STORE → SERVE`. ETL (transform-then-load) vs ELT (load-then-transform). Batch (scheduled bulk) vs streaming (continuous via Kafka) — make visually distinct (edge style/colour). Lineage = DAG: nodes=datasets/tables/columns, edges=derivation, upstream LEFT → downstream RIGHT; medallion bronze/silver/gold zones.
- **Graphviz (`dot`, `rankdir=LR`):** stage/zone `subgraph cluster_*`; stores/warehouses `cylinder`; files/object `folder`/`note`; queues/streams `box`/`cds`; product icons via `shape=none,image=...`. Column-level lineage = ERD-style HTML tables with per-column PORTs.

## PART B — PROCESS / BUSINESS

### 4. Flowchart (ANSI / ISO 5807) — shape-based, not colour
| Symbol | Shape | Use | Graphviz |
|---|---|---|---|
| Terminator | oval/stadium | start/end | `terminator`/`oval` |
| Process | rectangle | action (most common) | `box` |
| Decision | diamond | branch, ≥2 labelled exits | `diamond` |
| Input/Output | parallelogram | data I/O | `parallelogram` |
| Predefined process | rect w/ double bars | named subroutine | special (`component` approx) |
| Document | rect wavy bottom | a document | special (`note` proxy) |
| Manual input | sloped-top quad | runtime hand entry | `trapezium` |
| Manual operation | trapezoid | human step | `invtrapezium` |
| Preparation | hexagon | init/setup | `hexagon` |
| On-page connector | small circle | same-page continue | `circle` |
| Off-page connector | pentagon | other-page continue | `cds`/`house` |
| Database | cylinder | DB data | `cylinder` |
| Annotation | bracket, dashed link | note | `note`+`style=dashed` |
Primary axis TB, secondary LR. One start, marked end(s). document/predefined/stored-data/delay/display have no faithful native shape → custom SVG if fidelity needed.

### 5. BPMN (lite)
- **Events = circles** (Start thin / Intermediate double / End thick) with an inner marker icon (message/timer/error); hollow=catching, filled=throwing.
- **Activities/Tasks = rounded rectangles** (sub-process has `+`).
- **Gateways = diamonds** with marker: XOR=`X` (exactly one), AND=`+` (all parallel), OR=`O` (one+), event-based.
- **Pools** = participant; **Lanes** = role/dept subdivision.
- **Connections:** Sequence flow = solid line + solid arrow (within a pool); **Message flow = dashed line, open circle source + open arrow target (between pools)**; Association = dotted.
- **Graphviz (approx):** task `box,rounded`; start `circle,penwidth=1`, end `circle,penwidth=3`, intermediate `doublecircle`; gateway `diamond`; sequence = default edge; message = `style=dashed,dir=both,arrowtail=odot,arrowhead=open`; association = `style=dotted,arrowhead=none`; pools/lanes = clusters (approx). Event/gateway marker icons need a BPMN-aware renderer.

### 6. Swimlane / cross-functional
Same ANSI/ISO shapes placed in labelled lane bands (one lane = one actor/role/dept/system). Horizontal lanes (rows) most common: x=sequence, y=actor. Placement assigns responsibility; a flowline crossing a lane = a hand-off. Rummler-Brache matrix: rows=roles, columns=phases. The load-bearing convention is SPATIAL (position), not colour. **Graphviz: approximation only** (`cluster` per actor + `rankdir`); faithful uniform bands + phase×role matrix need a grid/SVG lane renderer.

### 7. State machine (UML)
| Element | Notation | Graphviz |
|---|---|---|
| Simple state | rounded rect (+ entry/exit/do) | `box,rounded` (`Mrecord` for actions) |
| Initial | solid black circle | `circle,style=filled,fillcolor=black,label=""` |
| Final | ringed filled circle | `doublecircle,style=filled,fillcolor=black,label=""` |
| Transition | solid line, open arrow, label `event [guard] / action` | edge with label |
| Self-transition | loop arrow to same state | edge to itself |
| Composite/nested | enlarged rect w/ substates (regions dashed) | `subgraph cluster` |
| Choice / Junction | diamond / small circle | `diamond` / `circle,filled` |
| Fork/Join | heavy bar | thin filled `box` |
Renders well in `dot` (TB or LR).

### 8a. User journey map — NEEDS special renderer
A table/matrix, NOT a node graph. Zones: Head (actor, scenario) / Body grid (phases as columns; rows = Actions, Touchpoints, Thoughts, **Emotion curve** (continuous ups/downs line), Pain points) / Footer (opportunities). LR by phase, TB by info type. Render with HTML/CSS grid or PIL/SVG (columns + row bands + polyline emotion curve). Graphviz cannot draw the curve.

### 8b. Decision tree — renders excellently in `dot`
Root (top/left) → decision nodes (square) → chance nodes (circle, EV trees) → leaves (triangle/endpoint). Conditions on edge labels. No cycles. `rankdir=TB`/`LR`; internal `box`/`diamond`, chance `circle`, leaves `ellipse`/`box` filled by class.

### 9. Sequence diagram (UML) — ⚠ NEEDS dedicated lifeline renderer (`build_sequence.py`)
Participant heads in a row; **dashed vertical lifelines**; **activation bars** (thin rects) = active execution; **sync** = solid line + solid filled arrow; **async** = solid + open arrow; **reply/return** = dashed + open arrow; **self-message** = loop; **destruction** = X at lifeline bottom; **combined fragment** = frame with operator in a folded-corner pentagon top-left + guard `[cond]` (operators: `alt opt loop par break ref`). Two axes: LR = participants (by first involvement), TB = time. `dot` CANNOT draw this (no persistent lifelines / time axis / activation bars). Use `build_sequence.py` (PIL) or PlantUML/Mermaid.

### 10a. Org chart — `dot`
Box per POSITION (title above name); uniform boxes; **solid = direct/line authority; dashed/dotted = secondary/functional reporting**. Top-down (apex = CEO). Color-code by department. `rankdir=TB`; `box`/`record`; dashed matrix edges use `constraint=false` so they don't distort ranks.

### 10b. Mind map — `twopi` (radial approx)
Central topic → main branches (Basic Ordering Ideas) radiate → sub-branches; one keyword per branch; **each main branch a distinct colour cascaded to its sub-branches**. Read center-outward. `twopi` with a designated `root`, tune `ranksep`; `neato` alt. True Buzan curved/tapering branches need a dedicated renderer.

## Which engine per family
| Family | Engine |
|---|---|
| flowchart, state, ERD, DFD, org chart, decision tree, pipeline/lineage, workflow, DevOps/CI-CD, C4, microservices, business context | `dot` |
| mind map, hub-and-spoke | `twopi` |
| relationship/knowledge maps | `neato` |
| ring/cyclic topologies | `circo` |
| **sequence** | dedicated PIL renderer (`build_sequence.py`) |
| **user journey map** | table+chart renderer (HTML/CSS or PIL/SVG) |
Rule of thumb: `dot` when the story is hierarchy/flow; `twopi`/`neato`/`circo` when it is radiation-from-center / a cycle; hand sequence + journey maps to purpose-built renderers.
