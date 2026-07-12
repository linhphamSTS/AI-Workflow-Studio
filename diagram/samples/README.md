# samples/

Diagrams produced by the `/linhpham-diagram` self-test — one per major type, across all three
renderers. Open `gallery_1.png` … `gallery_3.png` for contact sheets of everything (26 diagrams).
Regenerate the whole set anytime with `python skill/linhpham-diagram/tools/generate_samples.py`.

**Every diagram ships a `.png` AND a `.drawio`.** Formats per renderer:
- **Graphviz** (structural/process/data/hierarchy): `.png` + `.svg` + **native `.drawio`** (per-node editable shapes).
- **Cloud/infra & tech diagrams** (mingrammer real icons): `.png` + self-contained `.svg` + an **image-backed `.drawio`** (opens in draw.io showing the diagram exactly; move/resize/annotate — for structural edits use the SVG).
- **Sequence** (PIL): `.png` + image-backed `.drawio` (lifeline layout doesn't round-trip to vector).

The **`.svg`** looks exactly like the PNG, stays sharp at any zoom, and opens/edits in draw.io.
Regenerate everything: `python skill/linhpham-diagram/tools/generate_samples.py`.

## Cloud & Infrastructure (mingrammer — real vendor icons)
| File | Type |
|---|---|
| `aws_ref` | AWS reference architecture (VPC → subnets → EKS → Aurora/ElastiCache, shared IAM/S3) |
| `azure_ref` | Azure reference architecture (VNet nesting, App Gateway/AKS, SQL via private endpoint) |
| `gcp_ref` | GCP reference architecture (global VPC over regions, Cloud Run/SQL/Memorystore) |
| `k8s_topology` | Kubernetes workload topology (Ingress → Service → Pods, ConfigMap/Secret) |
| `docker_compose` | Docker Compose service topology (services, networks, volumes) |
| `onprem_hybrid` | Hybrid cloud (on-prem DC → Direct Connect + VPN failover → AWS VPC) |
| `uml_deployment` | UML deployment diagram (device/exec-env nodes + comms) |

## System & Software Architecture (Graphviz)
| File | Type |
|---|---|
| `c4_context` | C4 System Context |
| `c4_container` | C4 Container diagram |
| `microservices` | Microservices decomposition (bounded contexts, DB-per-service, sync/async) |
| `class_diagram` | UML class diagram (inheritance / aggregation) |

## Data (Graphviz)
| File | Type |
|---|---|
| `erd` | Entity-Relationship diagram (PK/FK, cardinality) |
| `dfd` | Data Flow Diagram |
| `data_pipeline` | Data pipeline / lineage (batch + streaming) |

## Process & Business (Graphviz)
| File | Type |
|---|---|
| `cicd` | CI/CD pipeline |
| `gitops` | GitOps flow (Argo CD pull/reconcile) |
| `bpmn` | BPMN-lite (events / tasks / gateways) |
| `swimlane` | Cross-functional swimlane (Employee / Manager / Finance) |
| `decision_tree` | Decision tree |
| `order_state` | State machine (order lifecycle) |

## Interaction & Hierarchy
| File | Type | Renderer |
|---|---|---|
| `oauth_login` | UML sequence (OAuth 2.0) | PIL sequence |
| `saga_orchestration` | Saga orchestration + compensation (sequence) | PIL sequence |
| `org_chart` | Org chart (line + dotted-line) | Graphviz dot |
| `mindmap` | Mind map (radial) | Graphviz twopi |
| `network_topology` | Network topology (DMZ / LAN) | Graphviz dot |
| `ai_rag` | AI RAG + multi-model gateway (OpenAI/Claude/Gemini/DeepSeek/Qdrant) | mingrammer (Custom AI logos) |
