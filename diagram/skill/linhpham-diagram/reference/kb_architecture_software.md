# Knowledge Base — Architecture-Style & Software-Structure Diagrams

> Renderer for these = Graphviz `dot` (via `build_graph.py`). Universal rules + per-type notation + a Graphviz cheat-sheet.

## 0. Universal rules (every diagram)
- **Title** every diagram with type + scope (`label=...; labelloc=t`).
- **Always include a legend/key** — explain colours, shapes, line styles, acronyms. Notation-independent models (C4) rely on it. Graphviz: `subgraph cluster_legend`.
- **Every line is a labelled, unidirectional relationship** — state intent + protocol (`Makes API calls to [JSON/HTTPS]`), prefer specific verbs over "Uses".
- **Name the type** of every element (`[Container: React SPA]`, `[Component]`) + a one-line responsibility. Don't rely on shape alone.
- **Colour not prescribed** — pick a consistent, colour-blind-safe palette; never encode meaning in colour alone.
- **Reading direction:** TB for hierarchies/layered stacks; LR for pipelines/request/event flows (and to cure vertical overflow). Users/entry top or left; datastores/sinks bottom or right.
- **Group with boundaries** — dashed clusters for logical/ownership boundaries; NEST clusters (region→VPC→subnet, service→its-DB) to read "designed" not "auto-laid-out".

## 1. C4 model (four levels + supplements)
Hierarchical zoom set; **Context + Container are enough for most**. Abstractions: **Person** (human), **Software System** (highest-level value unit), **Container** (a separately runnable app OR data store — NOT a Docker container; has an explicit technology), **Component** (grouping behind an interface inside a container).
- **L1 System Context** — in-scope system as one box + Persons + external systems; no tech detail; in-scope box centred/distinct, externals greyed.
- **L2 Container** — the single most-recommended diagram; containers (each with tech label) inside a dashed system boundary; entry points top/left → API/services → datastores bottom/right.
- **L3 Component** — decompose ONE container into components inside a dashed container boundary.
- **L4 Code** — classes inside a component (= UML class diagram); rarely, usually generated.
- **Supplements:** System Landscape (zoom out), Dynamic (numbered runtime steps), Deployment (containers onto infra nodes; nested clusters for regions/AZs).
- **Graphviz:** system/container/component → `box` (HTML label: name / [Type: tech] / description); Person → box+circle composite or clearly-labelled filled box; DB container → `cylinder`; boundary → `subgraph cluster { style=dashed }`; relationship → labelled edge with `[protocol]`.

## 2. Microservices decomposition
Independently deployable services partitioned by business capability, each owning its data, behind a gateway, sync + async comms.
- **Bounded contexts (DDD):** cluster VERTICALLY by business capability (Orders, Payments, Inventory), NOT horizontally by tech layer. Each service box encloses **its own datastore**.
- **Database per service:** private data, reachable only via the service API. Never a shared DB touched by many services (the anti-pattern the diagram should expose). Cross-service: Saga (writes), API Composition/CQRS (reads).
- **API Gateway / BFF:** single client entry point; BFF = one gateway per client type (Web/Mobile/3rd-party) when needs differ. Clients top/left → Gateway → services.
- **Sync vs async:** solid edges = sync (REST/gRPC); **dashed edges = async/event** (routed through a broker/topic node), labelled with protocol/event name. This split is the #1 readability cue.
- **Saga:** Choreography (no coordinator; each service publishes an event triggering the next — dashed edges via broker, no hub) vs Orchestration (central orchestrator sends commands/receives replies — hub-and-spoke). 
- **Graphviz:** service `box,rounded` + its DB `cylinder` in one cluster; gateway `box`/`component`; broker `box3d`; sync solid / async dashed+event label; orchestrator = central node with paired directed edges.

## 3. Serverless / event-driven (EDA)
Producers emit events → router/broker/stream → consumers react; decoupled. Use when many subsystems react to the same events / real-time / high volume; avoid for simple request-response or strong cross-service consistency.
- **Flow (LR):** event producers → event channel/router → consumers (drawn as MULTIPLE instances, not one box).
- **Channel models:** pub-sub (Event Grid / SNS — push to all subscribers, no replay) vs event streaming (Event Hubs/Kafka / Kinesis/MSK — durable ordered log, replay by offset) vs competing consumers (Service Bus / SQS — pull, once each).
- **Topologies:** broker (broadcast, choreography, no coordinator) vs mediator (central orchestrator owns state — orchestration).
- **Fan-out:** SNS→multiple SQS so each consumer gets a durable copy. **Orchestration:** Step Functions / Durable Functions (hub with numbered steps).
- **Correct EDA diagram shows:** correlation/tracing across hops, a **DLQ** off consumers, multiple consumer instances.
- **Graphviz:** `rankdir=LR`; functions `box`; queue/topic/stream distinct node; router = central node with rule-labelled out-edges; async `style=dashed`+event label; DLQ = side node via `style=dashed,label="on error"`.

## 4. Classic UML software diagrams
- **Class diagram:** 3-compartment box (name / attributes / operations) with visibility `+ - #`. Relationship arrowheads (Graphviz edge attrs):
  | Relationship | Line | Head | Graphviz |
  |---|---|---|---|
  | Association (navigable) | solid | open arrow | `arrowhead=vee` (`dir=none` if bidir) |
  | Generalization/Inheritance | solid | hollow triangle→parent | `arrowhead=empty` (child→parent) |
  | Realization/Implements | dashed | hollow triangle→iface | `arrowhead=empty,style=dashed` |
  | Dependency ("uses") | dashed | open arrow | `arrowhead=vee,style=dashed` |
  | Aggregation (shared) | solid | hollow diamond at whole | `arrowhead=odiamond` (part→whole) |
  | Composition (owned) | solid | filled diamond at whole | `arrowhead=diamond` (part→whole) |
  Node: `shape=record` `{Class|+attr: T\l|+op(): R\l}`. Diamond sits on the WHOLE end → draw edge part→whole so arrowhead lands right.
- **Component diagram:** component = rectangle with `«component»` + two-tab icon (`shape=component`); provided iface = lollipop, required = socket (approximate + document in legend); dependency `style=dashed,arrowhead=vee`.
- **Deployment diagram:** node = 3-D cube (`shape=box3d`); artifact = `«artifact»` doc (`shape=note`); nodes nest (device→OS→runtime); comm paths = plain solid edges.
- **Package/module dependency:** package = folder (`shape=tab`/`folder`); dependency = dashed arrow client→supplier; healthy graph is a DAG — highlight cycles (back-edges) in a warning colour.

## 5. Layered / hexagonal / clean
- **Layered (n-tier):** Presentation → Business (BLL) → Persistence (DAL) → Database; horizontal bands stacked TB, dependency arrows DOWNWARD only. `rankdir=TB`, one cluster per band.
- **Hexagonal (ports & adapters):** hexagon = app core; ports on its edges; adapters outside. Primary/driving adapters (UI, tests) left/top; secondary/driven (DB, services) right/bottom. Core `shape=hexagon`; `rankdir=LR`, driving `rank=source`, driven `rank=sink`.
- **Clean architecture:** concentric rings Entities → Use Cases → Interface Adapters → Frameworks&Drivers; **Dependency Rule = source dependencies point INWARDS only**. Graphviz substitute: NESTED clusters (Frameworks ⊃ Adapters ⊃ UseCases ⊃ Entities) with every cross-boundary edge pointing inward + a legend note; or `circo`/`neato` for a radial look.

## 6. Graphviz cheat-sheet
**Node shapes:** generic system/service/function → `box` (often `rounded,filled`); UML component → `component`; DB/datastore → `cylinder`; deployment node → `box3d`; artifact/note → `note`; package → `tab`/`folder`; class → `record` or HTML `<table>`; hexagonal core → `hexagon`; person → box+circle composite.
**Layout:** `rankdir=TB` for hierarchy/class-inheritance/layered; `rankdir=LR` for pipelines/request/event flows + overflow cure. Boundaries → `subgraph cluster_x { style=dashed; label=... }`, NEST for SA-grade. `rank=same` to align tiers; `rank=source`/`sink` to pin driving/driven. Always a `cluster_legend` + top `label` title.
