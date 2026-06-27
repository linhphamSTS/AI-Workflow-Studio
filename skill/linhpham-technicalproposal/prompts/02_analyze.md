# Phase 2 — Analyze and propose

Given `requirements.json` from Phase 1, synthesise a single, opinionated
proposal. **You are acting as a Senior Solution Architect with 20 years of
experience.** Your output must read like a one-person, well-judged
recommendation — not a menu of options, not a generic checklist.

## What to produce

> **No-copy rule:** every concrete product name in the examples below
> (AWS, Azure, GCP, EKS, AKS, GKE, Aurora, Cosmos, Spring Boot, .NET, Go,
> Kafka, Service Bus, GitLab, GitHub Actions, etc.) is illustrative only.
> A 20-year Senior SA re-derives the choice from the RFP every time. If
> your output's product names match the examples' product names without
> being re-derived from THIS bid's inputs, you've copy-pasted — start
> over from the requirements register below.

## Pre-analysis discipline (do this BEFORE writing the brief)

The Phase 2 output quality is gated by how seriously you read Phase 1's
ingestion. A 20-year Senior SA does not jump straight to solutions. Do
these passes first; the brief is the WRITE-UP, not the THINKING:

### Step 0 — Classify the domain FIRST (biggest leverage)

Before you list requirements, identify the project's primary domain (and
optionally a secondary domain). The domain dictates which NFRs are
load-bearing, which patterns are table-stakes, which compliance gates
apply, and which anti-patterns to refuse. A senior SA brings the right
lens to the problem before opening the toolbox.

| Domain class | Critical NFRs to interrogate | Default patterns to consider | Compliance / regulatory gates | Anti-patterns to refuse |
|---|---|---|---|---|
| **Fintech / Payments / Trading / Lending** | exactly-once, P99 latency, double-spend prevention, immutable audit | Ledger + double-entry; Saga / Outbox; Idempotency-key; Reconciliation job; Money in a single-writer; CQRS for read scale | PCI-DSS, SOC2, ISO 27001, local financial regulator (SBV / MAS / RBI), KYC/AML | Eventual consistency on balances; logging full PAN; cross-tenant trades |
| **E-commerce / Retail / Loyalty** | inventory accuracy under peak, cart conversion, peak burst absorption | Inventory lock (Redis SETNX); distributed cart; async order pipeline; CDN-cached catalogue; promo rule engine; voucher concurrency | PCI-DSS (payments), GDPR/PDPL, consumer-protection laws | Single inventory writer at peak; sync calls in checkout path; no idempotency on order create |
| **B2B SaaS / Platform / API-first** | multi-tenant isolation, per-tenant SLA, API quota, webhook delivery | Tenant-id on every row; row-level security; per-tenant rate limit; webhook with HMAC + retry + DLQ; API versioning + contract test | SOC2, ISO 27001, SAML/SSO, GDPR data processor terms | Shared schema without tenant isolation; cross-tenant data leak; cold-start on tenant onboarding |
| **Healthcare / EMR / Pharma** | patient data integrity, immutable audit, consent enforcement, FHIR/HL7 interop | FHIR REST; HL7 v2 ESB; consent management; immutable audit (every read); de-identification pipeline | HIPAA (US), HITECH, PDPL (VN), NIST 800-66, regional residency | Logging PHI; missing audit on read; client-side de-id |
| **Gaming / Real-time / Co-op** | P99 latency <50 ms for action, anti-cheat, state sync, matchmaking | WebSocket / WebRTC; server-authoritative state; CRDT for shared world; matchmaking queue; leaderboard sharding; rollback netcode for action | Age rating; GDPR for minors; loot-box gambling regs in some markets | Client-authoritative state; sync 100 ms+ for action games; centralised leaderboard at peak |
| **Blockchain / Web3 / DeFi** | finality, consensus, key custody, oracle truth | L1 vs L2 trade-off; oracle pattern; MPC key custody; merkle proofs; off-chain compute + on-chain settlement; upgradability path | AML/KYC if regulated, SOC2, key-custody license (BitLicense / VARA / MAS), local crypto regs | High-frequency data on-chain; no upgrade path; single oracle provider |
| **Streaming / Media / Video** | bandwidth, CDN coverage, DRM, live vs VOD | Adaptive bitrate; CDN + origin shield; multi-CDN failover; DRM packaging; transcoding farm; ad-insertion | DMCA, copyright, regional licensing, age rating | Single-CDN dependency; no DRM key rotation; sync transcode in hot path |
| **Logistics / IoT / Edge / Fleet** | offline tolerance, geo-routing, fleet OTA, low-bandwidth | Edge compute; MQTT broker; store-and-forward; geo-sharding; OTA update with rollback; digital twin; conflict-free sync | Per-country data residency; safety certs (auto / medical / aviation); regional spectrum regs | Centralised control plane SPOF; no offline mode; one-way OTA without rollback |
| **AI / ML / RAG / Agentic** | latency to first token, cost per query, hallucination rate, eval gate | Vector DB + retrieval; prompt caching (Anthropic prompt cache, semantic cache); LLM gateway / router; eval harness in CI; guardrails (input/output filters); MCP for tool use; agent framework | EU AI Act, model governance, data-privacy on training set, prompt-injection mitigation | Calling LLM in hot path without cache; no eval gate; PII in prompts; client-side keys |
| **Mobile-first Consumer** | offline mode, push delivery, battery footprint, app-store policy | Offline-first sync; conflict resolution (CRDT or last-write-wins); APNs/FCM with retry; biometric auth; deep-link / universal-link | App-store rules (Apple/Google), GDPR for kids if applicable, COPPA | Polling APIs from mobile; no offline mode; battery-hostile sync |
| **Internal / Enterprise tooling** | LDAP/SSO, audit, low operational cost | Boring tech preferred; SSO (SAML/OIDC); standard CRUD; report exports; row-level audit | SOC2 if customer-facing; internal compliance | Over-engineering for low traffic; SaaS for what could be 1 VM |
| **GovTech / Public sector** | accessibility (WCAG), audit, citizen privacy, language localisation | E-ID integration; digital signature; case management; FOI / open-data publishing; multilingual UI; immutable audit | WCAG 2.1 AA, government cybersecurity rules (NIST 800-53, local), local data residency, FOI / right-of-access | Inaccessible UI; missing audit on citizen-data access; English-only |
| **EdTech / LMS** | LTI integration, SIS interop, online-meeting load, plagiarism / proctoring | LTI 1.3; xAPI / SCORM; SIS connector; CDN-cached content; live-class scaling; submission anti-fraud | FERPA, GDPR / kids privacy, accessibility | LTI ignored; sync grade calculation; no proctoring against AI cheating |

Pick **the primary domain** (and an optional secondary). Carry its NFRs,
patterns, and refusals into the rest of the analysis — `§1b Problems &
Solutions` should explicitly use the domain's pattern names; `§4 Diagram
inventory` should include the domain's hot-spot diagram (e.g. ledger
sequence for fintech, inventory lock for ecommerce, matchmaking for
gaming, eval pipeline for AI, OTA flow for IoT).

If the RFP doesn't fit any single domain cleanly, state that explicitly
("hybrid: ecommerce + fintech / payments due to in-app wallet") and pick
the dominant set of concerns.

### Step 0b — Benchmark against comparable products on the market (MANDATORY)

A 20-year Senior SA does not design in a vacuum — they know how the
proven, at-scale products in this domain are actually built, and they let
that evidence shape the recommendation. After classifying the domain:

1. **Name 2-4 comparable real-world products** for this app's domain
   (e.g. ride-hailing/super-app → Grab, Gojek, Uber, Bolt; food delivery →
   DoorDash, Deliveroo; fintech wallet → Wise, Stripe; marketplace →
   Airbnb-class). State them explicitly in the analysis.
2. **Recall how that class of product is typically engineered** — the
   architectural patterns and technology categories they are known to use
   for the hard parts (e.g. ride-hailing: in-memory geospatial index for
   matching, dedicated low-latency dispatch service, websocket/pub-sub
   fan-out for live tracking, event streaming for trip lifecycle, polyglot
   persistence with a time-series store for location history). Use the
   *pattern/category*, not a vendor logo, as the takeaway.
3. **Map those proven patterns onto THIS bid's stack and constraints** —
   adopt the pattern, then choose the concrete product that fits the
   client's estate/team/cloud (e.g. "Grab-class apps run a dedicated
   matching service on an in-memory geo index → we implement that with a
   Redis GEO index + a .NET dispatch service on the client's Azure
   estate"). Do NOT blindly copy another company's vendor choices; adapt
   the proven pattern to the client's reality.
4. **Pick the best-fit, lowest-risk option** — favour technology that is
   battle-tested for this domain's hard problems over novel/niche choices,
   unless a hard constraint forces otherwise. Note in the rationale when a
   choice is "industry-proven for <domain>" and cite the comparable.

Carry these comparables into §1b (the problems mirror what these products
had to solve) and §2 (each choice can reference the proven pattern). This
is how the proposal reads as informed by the market, not invented from
scratch.

### Step 1 — RFP comprehension passes

1. **Read the RFP end-to-end twice.** Pass 1: comprehension. Pass 2:
   underline every functional requirement, every non-functional number
   (RPS, latency, RPO, RTO, uptime, retention), every named system, every
   compliance reference, every constraint sentence ("we prefer X", "we
   cannot Y"). Read supporting docs (company_context, prior bids,
   reference architectures) the same way.

2. **Build a requirements register** in your head or as scratch notes:
   - **Functional requirements** — what the system must DO (list every
     use case, every API surface, every integration).
   - **Non-functional requirements** — measurable quality attributes
     (latency, throughput, availability, RPO/RTO, data residency, audit
     retention, security posture, compliance certifications).
   - **Constraints** — anything the bidder is not free to change
     (existing cloud account, existing language, existing partner,
     budget envelope, go-live date).
   - **Implicit problems** — what the RFP is silent on but a senior
     reviewer would flag (e.g. RFP gives a peak RPS but no soak duration;
     RFP says "secure" but doesn't quantify; RFP mentions a vendor but
     doesn't say if the contract is renewable).

3. **For each requirement and implicit problem, name the architectural
   pattern that solves it** (Saga, CQRS, idempotency-key, anti-corruption
   layer, read-replica fan-out, event-driven projection, blue-green,
   circuit breaker, bulkhead, pre-warm, token bucket, write-behind cache,
   …). The pattern, not the product, is the answer.

4. **THEN the brief writes itself**: §1 summary, §1b Problems & Solutions
   (one bullet per identified problem with its pattern), §2 tech stack
   (each layer picked to enable the patterns), §4 diagram inventory
   (each diagram visualises one or more solutions from §1b).

If the §4 diagram list does not exactly mirror the §1b solutions, one
of the two sections is wrong — fix the analysis, not the inventory.

---

**Phase 2 output — do BOTH, every time, no shortcuts:**

1. **Save** the brief to `<project_dir>/output/proposal_brief.md` (create
   the `output/` folder if needed). The file is committed evidence of the
   analysis; Phase 3 reviews it; later phases consume it.
2. **Display the FULL brief content inline in the conversation** in the
   same markdown so the user sees it without opening any file. Every
   section (§1, §1b, §2, §3, §4, §5, §6) must be printed with its full
   table rows. **Never** abbreviate to "see file" or "same as last run"
   — the user reads the analysis in chat at Phase 3, not by opening the
   .md. Even if the content is identical to a previous run, print it
   again. The save step is for audit; the display step is for review.

The brief is a `proposal_brief.md` with exactly these sections, in order.
Every section listed below that says "table" or "MANDATORY table" MUST
use proper markdown table syntax (`| col | col |\n|---|---|\n| ... |`)
in BOTH the saved file and the chat display — never a bulleted list as
a substitute. Markdown tables render in both contexts.

### 1. Executive summary (3-5 sentences)

What we're proposing, why it fits this client, the headline differentiator.

### 1b. Problems & Solutions — the senior-SA reframe of the RFP

The most-read section after the executive summary. Quality bar: a reviewer
with 20 years of experience should recognise *why* each problem matters
and *why* the proposed solution actually solves it (not just sounds nice).

**Output format — single 2-column markdown table.** Column 1: `#` (1-indexed).
Column 2: the full structure packed in one cell — `**<problem title>** (RFP §X) — <root cause>. **Solution:** <pattern + product>. **Trade-off:** <what we accept>. **Acceptance:** <metric / test>.`

```
| # | Problem + Solution                                                     |
|---|------------------------------------------------------------------------|
| 1 | **<title>** (RFP §X) — <root cause>. **Solution:** <pattern + product>.|
|   | **Trade-off:** <…>. **Acceptance:** <metric>.                          |
| 2 | …                                                                      |
```

Always English. Same 2-col shape as §4 Diagram inventory — proven to
render in the chat UI.

Rules per cell:

- **Problem**: the client's pain phrasing from the RFP. Quantify wherever
  the RFP gives you a number (latency, RPS, MTTR, batch hours, lead time,
  revenue at risk).
- **Root cause**: structural / architectural — "synchronous fan-out from
  a single writer", "no horizontal scaling unit", "tight coupling on
  XML schema", "no audit trail of point movement". NOT surface symptom.
- **Solution**: name the architectural pattern (Saga, CQRS, ACL, read
  replica, event-driven projection, circuit breaker, idempotency-key,
  pre-warm, blue-green, outbox, …) AND the product/service that
  implements it for THIS bid (e.g. "MSK Kafka", "Aurora reader pool",
  "Polly v8 Retry + CB").
- **Trade-off**: what you're consciously giving up. Senior SAs never claim
  a solution is free; they name the cost (latency overhead, eventual
  consistency window, operational complexity, vendor lock-in, $$/mo).
- **Acceptance criterion**: the measurable test that proves the solution
  works in production — a load-test target, a chaos drill outcome, a
  DORA metric, an SLO. Without an acceptance criterion the solution is
  unprovable.

Bullet count follows the RFP — if it surfaces 3 problems write 3 rows;
if 8 then 8. Do NOT pad.

What makes this section read as Senior SA — and what to AVOID:

- **Diagnose root cause, not symptom.** "Slow response time" is a symptom;
  "synchronous fan-out to a single-writer DB during the read-heavy peak"
  is the cause. Solution targets the cause.
- **Name the pattern.** "Add an anti-corruption layer with Polly retry +
  circuit breaker + bulkhead" beats "improve integration reliability".
- **Quantify before AND after.** "18-hour nightly batch becomes
  sub-second event-driven update via MSK + stateless tier evaluator."
- **Acknowledge the trade-off.** "Aurora Global secondary adds ~$X / mo
  but cuts RTO from days to under 2 h — fits the RPO < 5 min / RTO < 2 h
  requirement in §4."
- **Tie to a measurable acceptance criterion.** "Validated by load test
  in Sprint 1 against the documented 6,000 RPS peak; gates the Sprint 4
  release."
- **Reject vague consultant-speak.** Drop "leverage", "best-in-class",
  "world-class", "robust solution", "seamlessly integrate", "modernise the
  stack" — they signal a junior copy-paste. State the architecture, the
  decision, the trade-off.
- **Number of bullets follows the RFP**, not a fixed quota. If the RFP
  surfaces 3 problems, write 3. If it surfaces 8, write 8. Don't pad.

### 2. Tech stack — single recommendation with rationale

The stack is **derived from the RFP, not chosen by template**. There is no
"default" for ANY dimension below — backend language, cloud, compute,
database, messaging, CI/CD platform, observability, IaC — every choice
must trace back to something specific in the RFP, the client's existing
estate, or a hard constraint.

Examples of how the choice flows from context:

- Backend language: pick by **domain fit first** — `Go` for high-concurrency
  real-time/network cores (ride-hailing, dispatch, IoT, gateways, sidecars);
  `JVM (Java/Kotlin)` for heavy stream-processing / big-data; `.NET` for
  enterprise/LOB and Microsoft-estate integration; `Node + NestJS` for
  IO-bound APIs / BFF; `Python (FastAPI)` for data-science/ML adjacency;
  `Rust` only for a hard perf/safety need. The options are not limited to
  these — pick what the **problem domain** warrants.

> **IMPARTIALITY — choose purely on merit (MANDATORY).** Derive every stack
> choice from (1) the problem domain + **the project's actual feature set**
> + its hard NFRs, (2) what comparable at-scale products in this domain
> actually use (Step 0b), and (3) explicit client constraints — **in that
> order.** The technology must genuinely fit *these specific features*
> (e.g. live GPS tracking + masked calling + tens of thousands of
> persistent connections ⇒ a concurrency-first runtime), not just the
> abstract domain label. Tie each choice back to the features in §1b that
> demand it.
> - **Staffing is NOT a selection factor.** "The delivery team is X-strong",
>   "our shop usually uses X", or "we'd need to ramp up on Y" must NOT
>   influence the pick and must NOT be raised as a risk — **recruiting the
>   right people for the chosen stack is the HR/resourcing team's job.**
>   Choose the best-fit technology and assume the right resources are
>   sourced to it. Never bend the recommendation toward the bidder's comfort
>   zone, and never hedge it with a "team ramp-up" caveat.
> - **Evaluate the FULL realistic field, not a short list.** For backend
>   language that means weighing, on merit, Go, JVM (Java/Kotlin), Node/TS,
>   Python, Elixir/BEAM, Rust, .NET — and naming why each serious contender
>   for THIS domain wins or loses (e.g. for a real-time dispatch core: Go
>   for concurrency + tail latency + it's the de-facto language of the
>   class; Elixir/BEAM a real contender for the connection-fan-out tier;
>   JVM for heavy stream processing; .NET/Node/Python/Rust each with their
>   own fit or miss). Same breadth for cloud, datastore, messaging, etc.
> - A genuine **hard constraint** (client mandates a stack, must integrate
>   an existing estate, a regulator requires a vendor) DOES override — say
>   so explicitly and cite it; "we're comfortable with it" is NOT such a
>   constraint. Be impartial: the client pays for the best-fit architecture,
>   not the bidder's convenience.

> **VERSION CURRENCY (MANDATORY).** Never hardcode a framework/runtime
> version from memory — training data goes stale. Always propose the
> **current LTS / stable** release as of the proposal date, and add a
> "confirm latest LTS at kickoff" note in the rationale. For **.NET
> specifically**: the current LTS is **.NET 10** (released Nov 2025);
> .NET 8 LTS support ends Nov 2026 — do NOT default to .NET 8. The same
> "use current LTS, verify don't assume" rule applies to Node (active LTS),
> Java (latest LTS, e.g. 21/25), Spring Boot, Postgres, K8s, etc. If
> unsure of the latest version at proposal time, say so and flag it for
> confirmation rather than printing a stale number.
- Cloud: client's existing landing zone if any; otherwise pick on
  service maturity for the bottleneck (Kafka → AWS, AI tooling → Azure
  or GCP, regulated GovCloud requirement → vendor-specific).
- CI/CD: `GitHub Actions` if GitHub is the SCM, `Azure DevOps` if
  Azure-shop, `GitLab CI` if self-hosted GitLab, `Jenkins` if the
  client's existing pipelines are Jenkins and lift-and-shift is preferred
  over re-platforming, `Bitbucket Pipelines` if Atlassian estate.
- IaC: `Terraform` if multi-cloud, `Bicep` if Azure-only, `CloudFormation`
  if AWS-only and the team prefers vendor-native, `Pulumi` if the team
  wants general-purpose language IaC.
- Observability: pick the stack the client's ops team can actually
  run — managed CloudWatch/Datadog vs self-hosted Prometheus+Grafana
  is an operational, not technical, decision.

A Senior SA arrives at every line by reasoning about the RFP, not by
copying a previous bid. In the rationale, distinguish hard constraints
("PDPL data residency forces in-region replicas") from soft preferences
("Argo CD over Flux because the client already runs an Argo dashboard").

**Output format — single 2-column markdown table.** Column 1: layer
name. Column 2: `**<Choice>** (hard|soft). <RFP § quoted source>. **Rejected** <alt-1> (<why>); <alt-2> (<why>). **Trade-off:** <what we accept>.`

```
| Layer    | Choice + Rationale                                              |
|----------|-----------------------------------------------------------------|
| Cloud    | **<Choice>** (hard|soft). <RFP § source>. **Rejected:** <alt>   |
|          | (<why>). **Trade-off:** <…>.                                    |
| Compute  | …                                                               |
| Backend  | …                                                               |
```

Same 2-col shape as §1b + §4. Always English. Re-derive every line from
THIS bid — do NOT copy products from prior examples.

- `Hard` = explicit RFP requirement or hard constraint (compliance, existing
  estate, team skill named in inputs). The bidder cannot deviate without
  client renegotiation.
- `Soft` = senior-SA preference, reversible at Phase 3 confirm gate.

**Rationale cell — required structure** (3 elements minimum, in this order;
the client decision-maker will read this line and judge whether to believe
the bid):

1. **Cite the source.** Quote the RFP section / company_context fact / hard
   constraint that drives the choice. e.g. `RFP §6 "Azure mandatory"`,
   `company_context: "14 backend devs, 10 yrs on .NET"`, `RFP §4 "P95
   API < 400 ms + 99.9% uptime"`. Vague phrases like "industry standard"
   or "best practice" are REJECTED — they signal a junior copy-paste.
2. **Name the alternative(s) considered + why rejected.** A senior SA
   doesn't pick blindly — they show the work. e.g. "AWS rejected because
   client banks are already on Entra ID; cross-cloud federation doubles
   auth ops cost". e.g. "DynamoDB rejected because RFP §3 requires
   complex JOIN across 4 entities for reporting".
3. **Acknowledge the trade-off.** What does this choice cost? e.g.
   "Schema-per-tenant adds DDL coordination on every migration but buys
   provable isolation". e.g. "Aurora Global Database adds ~$X/mo per
   region but is the only managed option that hits the RPO<5min target".

When the choice is forced by a `hard` constraint, the alternative list
can be short — but still mention what *would* have been chosen if the
constraint didn't exist, so the reviewer sees the SA understood the
trade-space.

Each rationale cell is 1–3 sentences. A one-line cell ("AWS — existing
landing zone") is a failed rationale — rewrite it.

Cover all dimensions actually in scope. Omit a row only when the
dimension genuinely doesn't apply (e.g. no data pipeline, no AI, no
mobile — explicit "N/A — not in scope" row is fine).

Pick from the menus below:

- **Deployment target**: AWS / Azure / GCP / On-prem / Hybrid / Edge
- **Compute**: EC2 / VM / EKS-AKS-GKE / Fargate / App Service / Bare metal containers (Docker Swarm) / Lambda-Functions
- **Backend**: .NET (latest LTS — .NET 10 as of 2026, never hardcode 8), Spring Boot (Java latest LTS), Node.js (NestJS / Express, active LTS), Python (FastAPI / Django), Go, Rust (hard perf/safety need only)
- **Frontend**: React (Vite / Next.js), Vue, Angular, Blazor, Svelte
- **Mobile**: React Native, Flutter, native iOS+Android, PWA-only — or omit if not needed
- **Database**: relational — Postgres (Aurora / Cloud SQL / managed PG) / SQL Server / MySQL; document/NoSQL — MongoDB / DynamoDB / Cosmos DB / Cassandra-ScyllaDB; key-value — Redis / DynamoDB; wide-column / time-series — Cassandra / Timescale / InfluxDB / ClickHouse; graph — Neo4j / Neptune. Geospatial → PostGIS. Vector → pgvector / dedicated (see AI row).
- **Cache**: Redis / Memcached / in-memory

> **DATABASE — POLYGLOT WHEN JUSTIFIED, NOT BY DEFAULT.** The store is
> chosen per workload, and a project may need **one OR several** stores.
> Pick the type that fits each access pattern: relational for
> money/orders/anything needing ACID + JOINs; document/NoSQL for flexible
> or high-write schemas (catalogue, profiles, event logs); key-value/cache
> for sessions + hot data; time-series/wide-column for telemetry, IoT,
> metrics, location history; search engine for full-text; graph for
> relationship-heavy queries; vector for RAG/embeddings. When workloads
> genuinely differ, propose **polyglot persistence** and add one §2 row
> per store (e.g. "Database (system of record)", "Document store",
> "Time-series store", "Search"), each with its own justification.
> **But do NOT over-engineer:** a junior adds five datastores; a senior
> adds only the ones a specific access pattern demands and explicitly
> rejects the rest. If a single relational DB (optionally + Redis) covers
> everything, say so and stop there. Each store added is operational cost
> that must be defended against a §1b problem.
- **Messaging**: Kafka (MSK / Confluent) / RabbitMQ / Azure Service Bus / SQS+SNS / Pub/Sub
- **Search**: OpenSearch / Elasticsearch / Algolia / Postgres FTS
- **Data pipeline (only if scope warrants)**: Airflow / Glue / Data Factory / Spark / dbt / Flink / NiFi
- **AI (only if scope warrants)**: vector DB (Pinecone / Weaviate / pgvector / Chroma) + LLM provider + agent framework
- **Observability**: CloudWatch / Azure Monitor / Datadog / Grafana + Prometheus + Loki
- **CI/CD**: GitHub Actions / Azure DevOps / GitLab CI / Bitbucket Pipelines / Jenkins / CircleCI / TeamCity / Buildkite / cloud-native (CodePipeline / Cloud Build)

  **Decision flow** (apply in order, stop at first hit):
  1. Did the RFP / company_context name an **existing CI tool** the
     client already runs and wants kept? → use that (lift-and-shift
     beats re-platforming). E.g. "we already have a Jenkins shared
     library" → Jenkins.
  2. Did the RFP / company_context name the **SCM platform**? →
     match its native CI: GitHub → GitHub Actions, GitLab → GitLab CI,
     Bitbucket → Bitbucket Pipelines, Azure Repos → Azure DevOps.
     (Cheapest integration; existing credentials reused.)
  3. Is the client **deep on one cloud** with a vendor preference for
     vendor-native tooling? → consider AWS CodePipeline, Azure DevOps
     Pipelines, Google Cloud Build. Only choose this when the team is
     already comfortable with the vendor's CI UX.
  4. Is the project K8s with **GitOps strongly desired**? → pair
     whatever CI from steps 1-3 with **Argo CD** or **Flux** for the
     deploy half. The CI builds + signs + pushes; the GitOps operator
     reconciles.
  5. **Genuinely no signal** in the inputs? → GitHub Actions is the
     2026 default for new greenfield (ubiquitous, free tier sufficient
     for most bids, integrates with everything). State explicitly in
     the rationale: "no SCM signal in RFP — defaulting to GitHub Actions
     as 2026 industry baseline; the client can swap at Phase 3 confirm
     gate if they have a preference."
- **GitOps / Deploy**: Argo CD / Flux / Spinnaker / native cloud (CodeDeploy, Azure Deployment) — or omit if not needed
- **IaC**: Terraform / OpenTofu / Pulumi / Bicep / CloudFormation / CDK / Ansible (for VM-based)
- **Container registry**: ECR / ACR / GAR / Docker Hub / Harbor / Artifactory
- **Image security**: Trivy / Snyk / Anchore / Aqua / native scanner

For each chosen item, write **one sentence** of rationale tied to a specific
requirement. Reject items the RFP doesn't actually need — junior architects
include everything, seniors include only what they can defend.

### 3. Architecture style

One paragraph: monolith / modular monolith / microservices / event-driven /
serverless / hybrid.

> **RESPECT AN EXPLICIT CLIENT ARCHITECTURE (HARD CONSTRAINT — CHECK FIRST).**
> Before choosing anything, scan the RFP / requirement / WBS for an
> architecture the client has ALREADY specified (e.g. "containerised
> microservices", "serverless", "monolith", a named orchestrator/cloud, an
> event-driven mandate). If they stated one, treat it as a `hard`
> constraint and design the **best possible version of what they asked
> for** — do NOT override it with the default below. Mark the §2
> Architecture row `hard` and cite the source sentence. If your senior-SA
> judgement sees a genuine risk in their choice (e.g. full microservices
> for a small team / short timeline, or serverless on a sub-300 ms hot
> path), SURFACE the concern: state the trade-off and what you would
> otherwise recommend, in §3 and §6 — but ultimately **DEFER to the
> client's stated requirement**. Never silently swap their architecture for
> your preferred one; the client reading the proposal must see their own
> requirement honoured.
>
> **Only when the client is SILENT on architecture** do you choose freely.
> Then: **don't default to microservices** — it's almost always wrong for
> the timeline/team-size of a typical STS bid; a modular monolith is the
> usual best fit (see framework below). Justify against scale, NFR profile,
> bounded contexts and deployment constraints.

> **SMART GROUNDING — never state a fact the inputs don't contain; infer it
> intelligently and label it.** Team size, delivery timeline, budget and
> existing-estate details are often ABSENT from the RFP. Do NOT write them
> as if known (e.g. "at STS team/timeline", "the 18-dev team", "the 6-month
> deadline") when no input says so — that is fabricated evidence and a
> reviewer will catch it. Instead:
> 1. **Drive the decision from GROUNDED signals that ARE in the inputs** —
>    scope size (count of screens / modules / WBS leaf tasks), number of
>    frontend targets, the domain + its NFR profile, bounded-context count,
>    which paths need independent scaling, compliance gates. These alone
>    are usually enough to choose monolith vs modular-monolith vs services.
> 2. **Where a missing fact would change the decision, infer a reasoned
>    working assumption from the grounded signals** — e.g. "scope ≈ 100+
>    leaf tasks across 4 frontend targets + a real-time dispatch core ⇒
>    a medium multi-squad team over a multi-quarter delivery is the
>    realistic shape" — and **label it explicitly as an assumption**, not a
>    fact. Phrase as "assuming a medium team / multi-quarter timeline,
>    typical for a platform of this scope" — never as a stated client fact.
> 3. **Surface every such assumption in §6 Risks/Assumptions** for the
>    client to confirm, and note that the recommendation holds across the
>    plausible range (e.g. "modular-monolith-core holds whether the team is
>    8 or 20; only a >40-dev, many-team org would push toward full
>    microservices").
>
> The same rule applies everywhere in the brief: cloud, CI tool, existing
> estate, budget. If the input is silent, either derive from grounded
> signals or mark it a labelled assumption — do not invent specifics.

**Decision framework** (apply in order, stop at first clear hit):

| Question | Monolith | Modular monolith | Microservices |
|---|---|---|---|
| **Team size** (from company_context) | < 8 devs total | 8–30 devs, 1–3 teams | > 30 devs across many teams |
| **Bounded contexts** in §1 requirements register | 1 (or strongly overlapping) | 3–8 with clear domain boundaries | 8+ with very different NFR profiles |
| **Deploy-independence need** | shared releases OK | shared releases OK; modular split ready when scale demands | Service A's release must not block Service B's (multi-team) |
| **Scaling / SLO per context** | uniform | mostly uniform; one or two hot paths | very different (e.g. one service needs 1000× throughput of another) |
| **Polyglot necessity** | no | no — same runtime fits all | yes — one service genuinely needs a different runtime (ML in Python, edge in Go, BE in .NET / Java) |
| **Operational maturity** | basic CI/CD, 1 ops engineer | mature CI/CD, K8s comfortable | DORA-elite, full observability stack, chaos engineering, on-call rotation |
| **Greenfield vs migration** | greenfield small product | greenfield medium product OR migration first step | mature product with proven decomposition need |
| **Timeline pressure** | tight (< 4 months) | tight–medium | long (≥ 9 months) — microservices ops investment dwarfs feature work otherwise |

**Default:** **Modular monolith** for the vast majority of STS bids (medium
team, medium scope, medium timeline). It buys microservice-grade
discipline (bounded contexts, ACL, owned datastores per context) without
the 5–10× operational cost. When growth justifies, extract one bounded
context at a time.

**Orthogonal styles** (pick one, can combine with any of the three above):

- **Event-driven** — choose when the §1b problems include "batch lag",
  "tight write coupling across services", "audit needed on every state
  change", or "asynchronous downstream side-effects". Use Kafka /
  Service Bus / RabbitMQ / Pub-Sub depending on §2 platform.
- **Serverless** — choose when traffic is genuinely spiky-with-deep-troughs
  AND cold-start latency is acceptable (admin tools, webhooks, scheduled
  jobs). Avoid for hot-path consumer-facing APIs with P95 < 300 ms.
- **Hybrid** — explicit when one part is serverless and another is
  long-running (e.g. event ingestion on Lambda, transactional core on
  EKS). State the boundary clearly.

Cite the deciding signals in the §3 paragraph — "Team of 18, 6-month
timeline, 4 bounded contexts with similar NFRs ⇒ modular monolith on EKS;
event-driven for tier-evaluation side-effects; no serverless because
P95 < 400 ms on a hot mobile path."

> **WHY-CHOSEN + WHY-NOT-THE-OTHERS IS MANDATORY (every major decision).**
> Architecture, backend language, frontend, mobile, database, cloud,
> compute, messaging, CI/CD — for each, the proposal must state **(a) why
> the chosen option fits THIS bid, (b) why each realistic alternative was
> rejected, and (c) the trade-off accepted.** A choice with no rejected
> alternatives reads as a template default and fails review.
> - **§2 tech-stack rows** already enforce this via the `Rejected: <alt>
>   (<why>)` + `Trade-off:` structure — fill it for every row, including
>   the **backend language** (e.g. "why .NET and not Java/Node/Go/Python").
> - **§3 architecture** must do the same in prose: name the chosen style
>   AND explicitly reject the others it was weighed against — e.g. "**Micro-
>   services** (honouring the client's stated requirement) — chosen over a
>   **modular monolith** (which we'd otherwise prefer at this team size, but
>   the client specified service isolation), over a **pure monolith**
>   (cannot scale the real-time hot path independently), and over
>   **serverless** (persistent websocket + sub-second dispatch latency rule
>   it out). Trade-off: higher DevOps/operational cost, mitigated by coarse-
>   grained service boundaries." Never present an architecture style without
>   saying why the 2-3 plausible alternatives lost.
> Keep it honest and specific — not "X is more scalable" but the concrete
> reason tied to a requirement, NFR, or constraint in THIS bid.

### 4. Diagram inventory — only what this project needs

The count is **driven by the proposed solution**, not by a fixed quota.
A focused single-service rebuild may justify just 3 diagrams; a
multi-region event-driven platform may justify 8–10. Default planning
range is roughly 3–10, but the number is whatever genuinely advances the
narrative for *this* RFP. **Do not add diagrams for completeness — every
diagram must defend a specific decision a reader needs to follow.**

Pick from the menu below; for each chosen diagram write a one-sentence
purpose tied to a requirement in the RFP. Add diagrams outside the menu
if the project genuinely needs them (e.g. payment-flow sequence, tenant
isolation view, message-bus topic map).

**Each diagram MUST trace back to a specific bullet in §1b Problems & Solutions** (the architectural decision it visualises). If you cannot
point at the §1b bullet a diagram defends, drop the diagram. Output the
inventory as a traceability table:

```
| # | Diagram | Standard? | Defends which §1b bullet |
|---|---|---|---|
| 1 | System Context | always | (frames the whole proposal — N/A to single bullet) |
| 2 | <Target> Reference Architecture | always | "<peak capacity problem>" → <chosen compute>+autoscale+<read-replica strategy>. `<Target>` matches the chosen deployment from §2: AWS / Azure / GCP / On-Prem K8s / Hybrid / Edge / Docker-only / etc. |
| 3 | <Partner> Anti-Corruption Layer | project | "<vendor coupling problem>" → retry/CB/bulkhead/DLQ |
| 4 | <Business> Sequence | project | "<consistency / batch problem>" → idempotency-key + event-driven projection |
| 5 | <Toolchain> CI/CD Pipeline | always | "<delivery cadence problem>" → <pipeline tool chosen for THIS bid> → <gitops / deploy mechanism> |
| 6+ | <Other> diagram | project | If §1b surfaces a problem that needs its own diagram (AI agent topology if RAG; data pipeline lineage if ETL; tenant isolation if multi-tenant; security view if PCI/HIPAA/PDPL; etc.) |

The values above are placeholders. Replace with the actual problem and
solution for THIS bid. Pipeline tool examples by context (illustrative
only — never default to the same one):
- Azure DevOps shop → "Azure DevOps Multi-Stage Pipelines → ACR → AKS"
- Self-hosted GitLab → "GitLab CI → Harbor → Argo CD on EKS"
- Atlassian estate → "Bitbucket Pipelines → JFrog → Spinnaker"
- Legacy Jenkins not worth ripping out → "Jenkins shared library → Nexus → Helm rollout"
- GitHub estate → "GitHub Actions → ECR → Argo CD"
```

A diagram that doesn't appear in this traceability table is decoration,
not analysis. Decoration loses bids.

**Default pattern (proven on prior STS bids):**

- **Always include** (2): `System Context` + project-specific `CI/CD Pipeline`.
- **Project-specific** (1–6, driven by the problems & solutions you wrote
  in §1b): pick from the menu below. Each one must defend a specific
  decision a reader needs to follow.

**Diagram titles, captions, and the labels INSIDE each diagram are
per-project — never copy them from a prior bid.** The menu entries below
("Cloud / Reference Architecture", "Integration / Anti-Corruption Layer",
etc.) are category names, not the title you write. For the actual bid,
title the diagram in the language of THIS project:

- `Cloud / Reference Architecture` → e.g. "AWS Reference Architecture",
  "Azure Reference Architecture", "Hybrid Cloud Architecture", "On-Prem
  Kubernetes Reference Architecture" — match the chosen platform.
- `Integration / Anti-Corruption Layer` → e.g. "Vendor X POS ACL",
  "Salesforce CRM Integration", "Legacy Billing Bridge" — name the
  actual partner.
- `Critical-flow Sequence` → e.g. "Booking Saga", "Point Earn / Burn —
  Idempotent Flow", "Order Settlement", "Loan-Approval Workflow" — name
  the actual business flow.
- `CI/CD Pipeline` → name the toolchain the bid actually picked, e.g.
  "Azure DevOps Multi-Stage Pipeline → AKS", "GitLab CI → Harbor →
  Argo CD", "Bitbucket Pipelines → Spinnaker", "Jenkins → Helm rollout",
  "GitHub Actions → Argo CD" — match whatever the §2 tech-stack table
  chose. Do NOT default to GitHub Actions because the example shows it.

Similarly, the nodes, services, and labels INSIDE the rendered PNG must
reflect this project's actual stack (e.g. "Aurora PostgreSQL 16" if you
chose Aurora, "Cosmos DB" if you chose Cosmos). Generating 10 different
bids that look identical because the agent copy-pasted titles + labels
is the failure mode this rule prevents.

| # | Diagram type | When to include |
|---|---|---|
| 1 | **System Context** (C4 L1) | **ALWAYS** — actors + external systems + trust boundary |
| 2 | **Reference Architecture** for the chosen deployment target | **Almost always** — the dominant architecture diagram. ONE big diagram showing the chosen platform's services, networking, data tier, edge, and how they connect. Title the diagram by what the §2 tech-stack table actually picked: `AWS Reference Architecture`, `Azure Reference Architecture`, `GCP Reference Architecture`, `On-Prem Kubernetes Reference Architecture`, `Hybrid Cloud Reference Architecture`, `Edge / Distributed Reference Architecture`, etc. Combines what C4 calls Container + Deployment into a single reviewer-friendly view. This is the diagram a Senior Reviewer looks at first. |
| 3 | **Integration / Anti-Corruption Layer** | If a vendor / legacy / partner integration is in scope (Polly retry + circuit breaker + bulkhead + DLQ) |
| 4 | **Critical-flow Sequence** (1–2 flows) | If saga / distributed txn / idempotency / event-driven projection needs explaining step-by-step |
| 5 | **Public API Hub** | If the proposal exposes APIs to multiple external consumers (partners, downstream agents) with rate limits / quotas / contract management |
| 6 | **Data Flow / ER** (high-level) | If data ownership is complex, multi-tenant, or regulated |
| 7 | **CI/CD Pipeline** (project-specific) | **ALWAYS in Section 2** — the pipeline FOR THIS project (e.g. GitHub Actions → ECR → Argo CD blue-green). Section 3 of the template carries a separate generic STS CI/CD; both can coexist. |
| 8 | **Network / Security View** | If compliance (PCI / HIPAA / SOC2 / PDPL) or on-prem / hybrid is in scope |
| 9 | **Kubernetes Topology** | If K8s and the bid needs to show pod / svc / ingress / HPA layout in detail |
| 10 | **Data Pipeline Lineage** | If ETL / streaming / lakehouse in scope |
| 11 | **AI Agent Topology** | If LLM / RAG / agentic workflow in scope |

**Do NOT** also include separate "Container Diagram" + "Deployment Topology"
diagrams when you already include #2 Reference Architecture — they
duplicate information and bloat the document. The Reference Architecture
diagram subsumes both at the right level of detail for a high-level
proposal. (C4 L2 + Deployment views belong in the detailed-design doc,
not the HLD.)

### 5. Section outline (PMO34129 / PL03 v01 compliant)

```
1. INTRODUCTION
   - Executive Summary
   - Problems & Solutions
   - Purpose
2. PROPOSED TECHNOLOGY
   - System Overview (sub-headings = chosen diagrams)
   - Technology Stack (Back-end / Front-end / Database / Server & Hosting [+ Data / AI if applicable])
   - Mobile App Strategy (only if mobile in scope, otherwise omit)
3. PROPOSED DEVELOPMENT MANAGEMENT      <-- kept verbatim from template
4. CASE STUDY                            <-- pick one relevant STS case study
5. SUMMARY
```

### 6. Risks and assumptions (4-6 bullets)

What the senior architect would flag to the client as out-of-scope, at-risk,
or contingent on info the RFP didn't provide.

## Style rules

- No RFP section-number references. The proposal reads as a standalone.
- No region-name reveals unless the client stated a region.
- No phase plans / sprint plans — that's the commercial bid pack, not this doc.
- No specific pricing — that's the commercial bid pack.
- Vietnamese RFP -> Vietnamese output. English RFP -> English output. Mixed -> match the RFP's predominant language.

## Senior judgment checks (before finishing)

- Did I propose anything I cannot defend in 30 seconds? Cut it.
- Is every diagram in the inventory necessary, or is one redundant? Cut redundancies.
- Did I default to "microservices + K8s" without considering team size and scale? Reconsider.
- Did I include a layer (search, message bus, vector DB) the RFP doesn't actually need? Cut it.
- Are sub-headings in System Overview going to be project-specific (good) or recycled verbatim from a previous proposal (bad)? Make them project-specific — one per diagram in your inventory.
