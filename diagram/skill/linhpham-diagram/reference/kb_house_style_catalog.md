# Knowledge Base — House Style + Suggestion Catalog

> Distilled from professional, production-grade architecture diagrams. These are neutral conventions —
> apply them to whatever the CURRENT project needs; never copy another project's names, wording, or scope.
> The **house style** is: mingrammer/Graphviz renders + a `diagrams.json` sidecar.

## House style

- **Background** white. Rendered PNG @300 DPI + a matching editable `.drawio` per diagram.
- **Iconography:** own/platform services = one accent glyph/colour; managed/cloud services = official vendor icons in their category colours (AWS: network purple `#8C4FFF`, storage green `#7AA116`, database blue, app-integration magenta `#E7157B`, security red `#DD344C`, compute orange `#ED7100`). Actors = line-art device/person glyphs.
- **Trust boundaries NEST and are colour-coded** with pale tinted fills + thin borders: grey-blue for Actors/Clients, red-bordered pink for External Systems, dashed blue for the VPC/platform boundary, cream for public subnet, pink for private subnets. Cross-cutting concerns (Shared Identity/Audit/Ops) drawn OUTSIDE the subnet groups to signal platform-wide scope.
- **Legend = a first-class boxed cluster** on every architecture/context diagram: white box, thin grey border, showing **solid = synchronous (req/resp), dashed = asynchronous (event)**. Security/PDPA view adds **orange edge = PII / sensitive-data path**.
- **Edges** dark slate-grey; solid vs dashed = sync vs async. Sequence diagrams use **numbered step labels** ("1 trip request", "2 GEO RADIUS", ...).
- **Data-classification tags** in node labels + bullet headers: `[SoR]`, `[PII]`, `[PCI]`.
- **Title** centred, dark-navy, top of canvas.
- **Caption format = `<Type> — <Scope>`** with an em-dash, where `<Scope>` is THIS project's subject (e.g. `System Context Diagram — <the system being proposed>`, `CI/CD Pipeline — Commit to Production`). No "Figure N:" in the stored caption; numbering is prepended at doc-assembly time.

## The `diagrams.json` metadata contract (reuse this shape)

Each entry: `slug`, `subheading`, `target_heading`, `png` (path), `caption`, `intro_paragraph`, `explanation_bullets[]`.
- **`intro_paragraph`** = 2–4 sentences framing what the view shows and why (altitude/purpose), no bullets.
- **`explanation_bullets`** = `**Component** — one-sentence description` (bold name, em-dash, rationale). Sequence diagrams use `**Step — <label>** — description`. Bullets map 1:1 to nodes/clusters in the image (orphan bullets are flagged).

## Suggestion catalog — recurring diagram types worth offering the user

Grouped by intent. When the user's description is fuzzy, offer the 2–4 most relevant of these.

**Core architecture (almost every proposal):**
- **System Context** — one trust boundary; actors + external systems + integration protocols.
- **Cloud Reference Architecture (AWS / Azure / GCP)** — nested VPC/VNet → subnet → compute cluster (EKS/AKS/GKE) → data tier; optional multi-region DR; legend + category colours.
- **Microservices Decomposition** — bounded-context clusters, datastore-per-service, sync-HTTP vs async-event edges.
- **Database ERD** — entities + attributes (PK/FK) + relationships.

**Critical-flow sequences (per key business flow):**
- **Sequence — <flow>** — numbered step flow for the latency/money-critical path (Dispatch & Matching, Ordering, Auth/Login).
- **Payment / Settlement flow** — charge → ledger → split → reconciliation; gateway ACL + idempotency.
- **Saga / Orchestration with Compensation** — happy path + compensation/rollback paths + saga-properties panel.
- **Real-time / Event Fan-out** — WebSocket gateway + pub/sub + event firehose to analytics.

**Integration & API patterns:**
- **Anti-Corruption Layer / Integration Pattern** — 3-column Portal | ACL (retry/circuit-breaker/bulkhead/DLQ) | external vendor.
- **Public API Hub** — consumers → gateway (protocols, OAuth2, rate limit, mTLS, webhooks, dev portal) → internal services.
- **Device/hardware integration** — POS integration, QR dual-mode camera flow, device-feature flows.

**Cross-cutting & non-functional:**
- **Security / PDPA-GDPR & Audit View** — TLS, RBAC, encryption-at-rest, signed-URL access, consent/deletion workflow, tamper-evident audit log; PII edges highlighted.
- **CI/CD Pipeline** — commit → build/test/scan → registry → GitOps rollout (blue/green) + parallel mobile lane; CI runner vendor-neutral.
- **Multi-tenant / Multi-outlet Architecture** — tenant isolation topology.
- **Notification System** — multi-channel (push/SMS/email) delivery.

**Delivery / project-management (when the proposal has a delivery-methodology section):**
- **Scrum methodology**, **Development flow**, **Git branch model**, **Environments (Dev/Staging/Prod)**, **Testing pyramid**, **Testing process**.

## Renderer routing (this skill)
| Family | Renderer |
|---|---|
| Cloud/infra reference arch, K8s topology, deployment | mingrammer `diagrams` (vendor icons) — author a Python script |
| System context, microservices, C4, ERD, DFD, flowchart, workflow, DevOps/CI-CD, state, class, org chart, mind map, network, business context | `build_graph.py` (Graphviz spec) |
| Sequence / interaction | `build_sequence.py` (PIL) |
