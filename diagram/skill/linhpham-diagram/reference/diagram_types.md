# Master Diagram Taxonomy — what this skill can draw

> Phase 1 (Refine) reads this to classify the user's request, SUGGEST the most fitting types, and
> pick the renderer. Each row: **type → category → renderer/engine → when to use → KB file** for
> the detailed notation. Never invent a type outside this table without saying so.

## Renderers
- **mingrammer** — the `diagrams` Python package (real vendor icons) + Graphviz. Author a small Python script (`03_generate.md`). Use for cloud/infra with branded icons.
- **graphviz** — `scripts/build_graph.py` from a JSON spec; engine `dot` (default) / `twopi` (radial) / `neato` (spring) / `circo` (circular).
- **sequence** — `scripts/build_sequence.py` (PIL lifelines) from a JSON spec.

## Taxonomy

### A. Cloud & Infrastructure  → renderer: **mingrammer**
| Type | When to use | KB |
|---|---|---|
| AWS / Azure / GCP Reference Architecture | "our cloud setup", deployment on a named cloud; nested VPC/VNet→subnet→compute→data + legend | kb_cloud_refarch, kb_house_style_catalog |
| Kubernetes Topology | K8s cluster: control-plane vs workers, OR workload view (Ingress→Service→Deployment→Pod) | kb_infra_container_onprem §1 |
| Docker / Container Composition | docker engine or docker-compose service+network+volume graph | kb_infra_container_onprem §2 |
| On-Prem / Hybrid Deployment | data-center zones (DMZ/LAN/data) or hybrid link (VPN / DirectConnect / ExpressRoute) | kb_infra_container_onprem §3 |
| Network Topology | routers/firewalls/subnets/hosts connectivity | kb_infra_container_onprem, kb_data_process |
| Deployment Diagram (UML) | artifacts onto infra nodes (device→runtime) | kb_architecture_software §4.3 |

### B. System & Software Architecture  → renderer: **graphviz (dot)**
| Type | When to use | KB |
|---|---|---|
| System Context (C4 L1) | the system as one box + actors + external systems; big-picture start | kb_architecture_software §1, kb_house_style_catalog |
| Container Diagram (C4 L2) | apps/data stores inside the system + tech + how they talk (most-recommended) | kb_architecture_software §1 |
| Component Diagram (C4 L3) | decompose one container into components | kb_architecture_software §1 |
| Microservices Decomposition | bounded-context clusters, DB-per-service, sync vs async edges, gateway/BFF, saga | kb_architecture_software §2 |
| Event-Driven / Serverless | producers → router/broker/stream → consumers; fan-out; choreography vs orchestration | kb_architecture_software §3 |
| Layered / Hexagonal / Clean | n-tier bands, ports&adapters, concentric dependency rule | kb_architecture_software §5 |
| UML Class Diagram | classes + attributes/methods + inheritance/composition/dependency | kb_architecture_software §4.1 |
| UML Component Diagram | components + provided/required interfaces | kb_architecture_software §4.2 |
| Package / Module Dependency | package folders + dependency arrows; expose cycles | kb_architecture_software §4.4 |

### C. Data  → renderer: **graphviz (dot)**
| Type | When to use | KB |
|---|---|---|
| ERD (Entity-Relationship) | data schema: entities/attributes/PK-FK + crow's-foot cardinality | kb_data_process §1 |
| Data Flow Diagram (DFD) | how data moves: process/store/external/flow; leveled | kb_data_process §2 |
| Data Pipeline / Lineage | source→ingest→transform→store→serve (LR); batch vs streaming; lineage DAG | kb_data_process §3 |

### D. Process & Business  → renderer: **graphviz (dot)**
| Type | When to use | KB |
|---|---|---|
| Flowchart | single-actor step-by-step algorithm/procedure (ISO 5807 shapes) | kb_data_process §4 |
| Workflow | a business/process workflow (= flowchart with process/decision emphasis) | kb_data_process §4 |
| BPMN-lite | events(circles)/tasks(rounded)/gateways(diamonds), pools/lanes, sequence vs message flow | kb_data_process §5 |
| Swimlane / Cross-functional | who-does-what: ANSI shapes in actor lanes; hand-offs cross lanes | kb_data_process §6 |
| State Machine | object lifecycle: states + event[guard]/action transitions | kb_data_process §7 |
| Decision Tree | branching decisions → outcomes (also ML classification) | kb_data_process §8b |
| Business Context Diagram | the business/organisation in its environment: capabilities + external parties (context-level) | kb_architecture_software §1, kb_data_process |

### E. Interaction  → renderer: **sequence (PIL)**
| Type | When to use | KB |
|---|---|---|
| Sequence Diagram | time-ordered messages between participants for one scenario (login, checkout, dispatch) | kb_data_process §9 |

### F. Hierarchy  → renderer: **graphviz (dot / twopi)**
| Type | When to use | KB |
|---|---|---|
| Org Chart | reporting structure; solid=line authority, dashed=dotted-line | kb_data_process §10a |
| Mind Map | radiant brainstorming from a central topic (engine `twopi`) | kb_data_process §10b |
| Sitemap / Tree | site or content hierarchy | kb_data_process §10 |

### G. DevOps & Delivery  → renderer: **graphviz (dot)** (mingrammer if tool icons wanted)
| Type | When to use | KB |
|---|---|---|
| CI/CD Pipeline | source→build→test→registry→deploy (LR); gates between envs; CI runner vendor-neutral | kb_infra_container_onprem §4A, kb_house_style_catalog |
| GitOps Flow | Argo CD pull/reconcile loop (cluster→Git, never CI→cluster) | kb_infra_container_onprem §4B |
| Git Branch Model / Environments / Testing Pyramid / Scrum flow | delivery-methodology diagrams | kb_house_style_catalog |

### H. Cross-cutting  → renderer: **graphviz (dot)** or mingrammer
| Type | When to use | KB |
|---|---|---|
| Security / Compliance (PDPA-GDPR) & Audit View | TLS/RBAC/encryption/consent-deletion/audit-log; PII edges highlighted | kb_house_style_catalog |

## Classification hints for fuzzy requests
- "flow / steps / process / how X happens / workflow" → Flowchart/Workflow (single actor) OR Sequence (if it names who-calls-whom over time).
- "who calls whom / request/response / login flow / API call order" → **Sequence**.
- "our AWS/Azure/GCP / cloud setup / infrastructure / deployment" → **Cloud Reference Architecture** (name the cloud).
- "services / microservices / how the backend is split" → **Microservices Decomposition** (or C4 Container).
- "the big picture / system and its users/externals" → **System Context** (or **Business Context** if the framing is organisational, not technical).
- "data model / tables / schema / entities" → **ERD**.
- "pipeline / ETL / data moving / lineage" → **Data Pipeline / Lineage**.
- "states / lifecycle / statuses" → **State Machine**.
- "org / team / reporting" → **Org Chart**; "brainstorm / ideas around X" → **Mind Map**.
- "CI/CD / build and deploy / pipeline (code)" → **CI/CD Pipeline** (or GitOps if Argo/Flux named).
- "kubernetes / k8s / pods / cluster" → **Kubernetes Topology**; "docker / compose / containers" → **Docker Composition**.
When two types both fit, SUGGEST both (with a one-line reason each) and let the user pick — do not silently choose.
