# Knowledge Base — Cloud Reference-Architecture Conventions (AWS · Azure · GCP)

> Renderer = mingrammer `diagrams` v0.25.1 + Graphviz. Draw for the cloud chosen; never default to AWS.

## 0. Universal conventions (all clouds)
- **One view per diagram** (context / container / network / data-flow / deployment / sequence). Split, don't overload.
- **North→south flow:** users/Internet top → edge (DNS/CDN/WAF/global LB) → network boundary → app tier → **data tier innermost/bottom**. `rankdir=TB`; flip LR only on overflow.
- **Trust boundaries = labelled NESTED rectangles** (nested `Cluster()`); the frame carries the boundary name + region/zone/CIDR.
- **Edge/CDN/WAF sit ABOVE/OUTSIDE the network boundary** (global/regional, not subnet-scoped). Exception: an L7 gateway injected into the network (AWS ALB in a public subnet; Azure App Gateway in a dedicated subnet).
- **Identity + secrets + observability = a side rail OUTSIDE the network boundary**, wired with dashed diagnostics/identity lines.
- **Single-ended arrows** in request/data direction (two flows for req/resp, not a bidirectional arrow). Dashed double-headed only for peering / health-check.
- **Line semantics + mandatory legend:** solid = sync request / primary data (label protocol+port); dashed = async / peering / private-link / telemetry. Any semantic → a compact legend (let the engine place it, never hard-code a corner).
- **Numbered flow steps** (①②③ on the canvas + an ordered "how it works / Dataflow" list) = the signature reference-arch convention on all three clouds.
- **Annotate:** region/AZ/zone on frames; ports/protocols on edges; **RPO/RTO** on cross-region replication; data-classification (`[PII]`, "encrypted at rest, KMS").

## The network boundary per cloud (the frame that wraps everything)
| Cloud | Network boundary name | Scope | Nesting order (outer → inner) |
|---|---|---|---|
| **AWS** | **VPC** (Virtual Private Cloud) | **Regional** | `AWS Cloud → Region → VPC → Availability Zone → Subnet (public/private) → resource` |
| **Azure** | **VNet** (Virtual Network) | **Regional** | `Management Group → Subscription → Resource Group → VNet → Subnet → compute` |
| **GCP** | **VPC** (Virtual Private Cloud) | **GLOBAL** (subnets regional) | `Organization → Folder → Project → VPC (global) → Region → Subnet (regional) → resource`, all inside a grey "Google Cloud" wrapper box |
> **GCP quirk (the biggest structural difference):** a GCP VPC is a GLOBAL object spanning every region; **subnets are regional**. So draw ONE VPC box that ENCLOSES multiple region boxes, each region holding its regional subnet — do NOT draw one VPC per region (that's the AWS/Azure model). Resources in different regions on the same VPC talk over internal IP with no peering.

## AWS
- **Diagram types:** 3-tier web app; microservices on ECS/EKS/Fargate; serverless event-driven (Lambda, usually NO VPC/AZ boxes); data lake on S3 (raw→processed→curated + Glue + Athena/Redshift + QuickSight); event messaging (SNS fan-out / SQS+DLQ / Kinesis); hub-and-spoke via Transit Gateway; multi-region DR (two Region boxes + RPO/RTO arrows + Route 53 failover).
- **Boundary rules:** Route 53/CloudFront/WAF/API GW OUTSIDE+ABOVE the VPC. Data tier in PRIVATE subnets (never internet-reachable); RDS/Aurora Multi-AZ across a DB subnet group. Internet Gateway on the VPC boundary; **NAT Gateway in a PUBLIC subnet (one per AZ)**; ALB/NLB span public subnets across AZs. IAM/Secrets/KMS/CloudWatch/CloudTrail drawn OUTSIDE the VPC in a shared-services sidebar. Security groups = dashed boxes wrapping resources, edges labelled by port.
- **AWS is the ONLY cloud with a true category color system** (icon fill = category):
  | Category | Hex |
  |---|---|
  | Compute, Containers | `#ED7100` orange |
  | Storage | `#7AA116` green |
  | Networking & Content Delivery, **Analytics**, Serverless | `#8C4FFF` purple |
  | Database, Developer Tools | `#C925D1` magenta |
  | Application Integration, Management & Governance | `#E7157B` pink |
  | Security, Identity & Compliance | `#DD344C` red |
  | AI/ML | `#01A88D` teal |
  | General / group borders / text | `#232F3E` navy |
  Group-box borders reuse category colors: Region teal `#00A4A6` dashed, VPC purple `#8C4FFF`, AZ teal dashed, Public subnet green `#7AA116`, Private subnet blue `#147EBA`, SG red `#DD344C` dashed, ASG orange `#ED7100` dashed. **Corrections:** current Database = magenta `#C925D1` (NOT the pre-2021 blue); Networking & Analytics SHARE purple `#8C4FFF` (disambiguate by icon).
- **Top services (icon priority):** VPC, EC2, S3, Lambda, RDS/Aurora, ELB(ALB/NLB), DynamoDB, API Gateway, CloudFront, Route 53, IAM, CloudWatch. Runners-up: ECS/EKS/Fargate, SQS/SNS, IGW/NAT, KMS/Secrets.

## Azure
- **Diagram types:** N-tier IaaS (Front Door/TM → App Gateway+WAF → Azure Firewall → internal LB → VMSS tiers → SQL-on-VMs AG across AZs); PaaS App Service baseline (VNet-integrated, private endpoints); baseline AKS (hub-spoke, system+user node pools); serverless (Event Grid → Service Bus/Event Hubs → Functions); modern data warehouse (Data Factory → ADLS Gen2 Bronze/Silver/Gold → Synapse → Power BI); hub-and-spoke landing zone; multi-region (Front Door/TM over mirrored stamps).
- **Boundary rules:** Front Door/Traffic Manager/CDN/DDoS OUTSIDE+ABOVE the VNet. **Exception: App Gateway+WAF and Azure Firewall live INSIDE the VNet in dedicated subnets** (`AzureFirewallSubnet`, `GatewaySubnet`, `AzureBastionSubnet`). Inspection order: App Gateway(WAF L7) → Azure Firewall → internal LB → workload. **PaaS data (Azure SQL, Cosmos, Blob) drawn OUTSIDE the VNet, reached via a private endpoint NIC in a dedicated subnet — never "inside" a subnet.** Entra ID / Key Vault / Monitor off to the side. VNet peering = dashed double-headed "virtual network peering".
- **Color:** Azure has **NO category color system** — icons are individually multicolored, do NOT recolor. Brand blue `#0078D4` (third-party sourced, unverified) for neutral chrome only. Encode meaning via nesting + labels + line style, not fill.
- **Signature:** the numbered **"Dataflow"** prose section (1..N) with matching numbered markers on the flow.
- **Top services:** VNet+Subnet, App Gateway(+WAF), Azure Firewall, Monitor/Log Analytics, Entra ID, Key Vault, App Service, AKS, Azure SQL DB, Blob/ADLS Gen2, Front Door/Traffic Manager, Load Balancer.

## GCP
- **Diagram types:** 3-tier serverless (Cloud LB → Cloud Run frontend → Cloud Run API → Memorystore → Cloud SQL); 3-tier VM (MIG of Compute Engine); microservices on GKE + Cloud Service Mesh; serverless event-driven (Eventarc/Pub/Sub → Cloud Run/Functions Gen2); data lakehouse (Pub/Sub → Dataflow → GCS zones / Dataproc → BigQuery → Looker); global front-end (Cloud DNS → Cloud CDN → global ALB → Cloud Armor); hub-and-spoke Shared VPC (host project owns VPC+subnets, service projects attach).
- **Boundary rules:** wrap ALL resources in one grey **"Google Cloud"** box (logo corner); users/on-prem/SaaS outside. Nest Project → Region → Zone → VPC → subnet. Cloud DNS/global ALB/Cloud CDN/Cloud Armor at the very top/outside. Cloud SQL private-IP inside a subnet; Spanner/Firestore/BigQuery = managed, no subnet (bottom of Project). IAM/Secret Manager/KMS/Cloud Ops Suite = side rail / shared-services project. **Global-VPC-over-regions** (see quirk above).
- **Color:** GCP has **NO category color system** — per-product 4-color icons (Google brand: blue `#4285F4`, red `#EA4335`, yellow `#FBBC04`, green `#34A853`), do NOT recolor. Grouping boxes neutral grey + colored accent.
- **Top services:** VPC, Cloud Load Balancing, Compute Engine, GKE, Cloud Run, GCS, Cloud SQL, BigQuery, Pub/Sub, Cloud Functions, Cloud IAM, Cloud CDN+DNS. **Eventarc has NO node class in `diagrams`** — substitute Pub/Sub or a custom SVG.

## Appendix A — Verified mingrammer import paths (`diagrams` v0.25.1)
### AWS
```python
diagrams.aws.network:  VPC, PublicSubnet, PrivateSubnet, ELB, ALB, NLB, CloudFront, Route53, APIGateway, InternetGateway, NATGateway, TransitGateway
diagrams.aws.compute:  EC2, EC2Instances, Lambda, ECS, EKS, Fargate, ElasticBeanstalk, Batch
diagrams.aws.database: RDS, Aurora, Dynamodb, ElastiCache, Redshift
diagrams.aws.storage:  S3, EFS, EBS
diagrams.aws.integration: SQS, SNS, Eventbridge, StepFunctions
diagrams.aws.security: IAM, SecretsManager, WAF, Cognito, Shield, CertificateManager
diagrams.aws.management: Cloudwatch, Cloudformation, Cloudtrail, SystemsManager, Organizations
diagrams.aws.analytics: Glue, Athena, Redshift, Kinesis, KinesisDataStreams, EMR, Quicksight
```
### Azure
```python
diagrams.azure.network: VirtualNetworks, Subnets, ApplicationGateway, LoadBalancers, FrontDoors, CDNProfiles, TrafficManagerProfiles, DNSZones, VirtualNetworkGateways, RouteTables
diagrams.azure.compute: VM, VMWindows, VMLinux, VMScaleSet, AKS, FunctionApps, AppServices   # AKS is HERE, not .containers
diagrams.azure.containers: KubernetesServices, ContainerInstances, ContainerRegistries
diagrams.azure.database: SQLDatabases, SQLServers, CosmosDb, DatabaseForPostgresqlServers, CacheForRedis
diagrams.azure.storage: BlobStorage, StorageAccounts, DataLakeStorage, QueuesStorage
diagrams.azure.identity: ActiveDirectory, AzureActiveDirectory, ManagedIdentities
diagrams.azure.security: KeyVaults           # plural, NOT KeyVault
diagrams.azure.integration: ServiceBus, EventGridTopics, LogicApps, APIManagement
diagrams.azure.analytics: SynapseAnalytics, DataFactories, EventHubs, Databricks
diagrams.azure.monitor: Monitor, LogAnalyticsWorkspaces, Metrics
diagrams.azure.devops: Devops, Pipelines, Repos
```
### GCP
```python
diagrams.gcp.compute:   ComputeEngine (GCE), KubernetesEngine (GKE), Run, Functions, AppEngine
diagrams.gcp.network:   VPC, LoadBalancing, CDN, Armor, DNS, Router, NAT, VPN, FirewallRules
diagrams.gcp.database:  SQL, Spanner, Firestore, Bigtable, Datastore, Memorystore
diagrams.gcp.storage:   Storage (GCS), PersistentDisk, Filestore
diagrams.gcp.analytics: BigQuery, PubSub, Dataflow, Dataproc, Composer   # casing: BigQuery, PubSub (NOT Bigquery/Pubsub)
diagrams.gcp.security:  Iam, KeyManagementService, SecurityCommandCenter, ResourceManager
diagrams.gcp.devtools:  Build, ContainerRegistry, SourceRepositories
diagrams.gcp.operations: Monitoring, Logging
diagrams.gcp.api:       APIGateway, Endpoints
```
Nesting/edge: `Cluster(label, direction='LR', graph_attr={"bgcolor":..,"pencolor":..,"style":"dashed"})`; `Edge(label='', color='', style='dashed')`.

## Appendix B — Cross-cloud quick comparison
| Dimension | AWS | Azure | GCP |
|---|---|---|---|
| Network boundary | **VPC** (regional) | **VNet** (regional) | **VPC** (GLOBAL) — 1 VPC over many regions |
| Nesting | Cloud→Region→VPC→AZ→Subnet | MgmtGrp→Sub→RG→VNet→Subnet | Org→Folder→Project→VPC→Region→Subnet (grey "Google Cloud" wrapper) |
| Edge (CDN/WAF/LB) | above VPC | above VNet; App GW+WAF & Firewall INSIDE VNet | above the "Google Cloud" box |
| Data tier | private subnets | IaaS in subnet; PaaS outside via private endpoint | Cloud SQL in subnet; Spanner/BigQuery managed, no subnet |
| Color system | category-coded (see table) | NO categories; multicolored icons | NO categories; per-product 4-color icons |
| Signature | numbered steps + dashed SG boxes | numbered "Dataflow" + PaaS-outside-subnet | grey "Google Cloud" wrapper + global-VPC |
