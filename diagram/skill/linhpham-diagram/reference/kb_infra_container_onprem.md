# Knowledge Base — Kubernetes / Docker / On-Prem / CI-CD Diagram Conventions

> Reference for the diagram-authoring phase. Renderer = Python `diagrams` (mingrammer) + Graphviz.
> Covers: Kubernetes topology, Docker/container composition, on-prem & hybrid deployment, CI/CD & GitOps.

## 0. Renderer notes (mingrammer `diagrams` + Graphviz)

- `Diagram(direction="TB"|"LR")` — layered infra (ingress → app → data) reads **TB**; pipelines / request-flow read **LR**.
- `Cluster("label")` is the **only** grouping primitive. Nest `Cluster` inside `Cluster` for containment (VPC → subnet → node → pod). Nesting depth = the real topology; flat sibling clusters read as tool-generated.
- `Edge(label=, style="dashed", color=)` — dashed = control/async/reconcile; solid = request/data flow.
- No legend primitive → emulate with a small `Cluster("Legend")` of labelled nodes + always add a caption.
- Graphviz gotcha: deep TB graphs overflow page width → flip to LR; break long labels before `(`.

Colour principle (from the official k8s diagram guide): one accent colour for "our platform" resources, **grey for external/third-party actors**, light border on the outermost boundary, consistent per-tier fills.

## 1. Kubernetes topology — TWO distinct diagrams (don't merge)

### 1A. Cluster-internals (control plane vs workers)
Elements: **Control plane** = kube-apiserver (hub — everything talks through it), etcd (state store, apiserver-only), kube-scheduler, kube-controller-manager, optional cloud-controller-manager. **Worker node** = kubelet, kube-proxy, container runtime (containerd/CRI-O), Pods. Addons: CoreDNS, CNI, metrics.
- Layout TB: control plane on top, worker nodes below.
- **Edge direction (commonly wrong):** apiserver is the hub; scheduler/controllers/etcd connect ONLY to apiserver; each node's kubelet initiates connection to apiserver. etcd never connects directly to nodes.
- HA: multiple apiserver replicas behind LB + odd-numbered etcd quorum.
- mingrammer: `k8s.controlplane.API/Sched/CM/Kubelet/KProxy`, `k8s.infra.ETCD/Master/Node`.

### 1B. Workload / traffic view (the one most proposals need)
Elements: External client/Internet (grey, outside cluster) → **Ingress**/LoadBalancer Service → **Service** (ClusterIP internal vs LB/NodePort external) → **Deployment/StatefulSet/DaemonSet** → **Pod** → container. ConfigMap/Secret attached via dashed edges. PVC→PV→StorageClass for stateful. Namespace boundaries group everything.
- Traffic reads **LEFT→RIGHT** into the cluster: `Internet → Ingress → Service → Pods` = the visual spine.
- Namespaces = parallel slices on shared nodes. Multi-AZ: wrap node-clusters in AZ-clusters, cloud LB in front.
- Colour: k8s-native = blue `#326CE5`; external = grey; group by Namespace (fill per ns). Reserve fill for grouping, not node kind (icons carry kind).
- mingrammer: `k8s.group.NS`, `k8s.compute.Deploy/STS/DS/Pod/RS/Job/Cronjob`, `k8s.network.SVC/Ing/Ep/Netpol`, `k8s.podconfig.CM/Secret`, `k8s.storage.PV/PVC/SC/Vol`, `k8s.clusterconfig.HPA/Limits/Quota`, `k8s.rbac.Role/RB/CRole/CRB/SA`.
- ⚠ Naming trap: `k8s.podconfig.CM`=ConfigMap vs `k8s.controlplane.CM`=ControllerManager — import explicitly.

## 2. Docker / container composition

### 2A. Docker engine (client–server)
`docker` CLI → `dockerd` daemon over REST (socket/TCP); daemon manages images/containers/networks/volumes; Registry (Hub/private) push-pull. Flow: `Dockerfile →(build)→ Image →(push/pull)→ Registry →(run)→ Container`. Layout **LR**: client left, daemon centre, registry right.

### 2B. docker-compose service graph
Each service = container box labelled **name + ports** (`host:container`). Group services by **network** (`Cluster` per network) — communication boundary. Volumes attach to services that mount them; **distinguish stateful (volume-backed) from stateless** by colour/shape. Show `depends_on`/call edges + host port bindings. Do-not-omit checklist: service names, exposed ports, volume mounts, network boundaries. Host/ingress port at top/left; data stores at bottom.
- mingrammer: `onprem.container.Docker`, `onprem.database.Postgresql/Mysql/Mongodb/...`, `onprem.inmemory.Redis/Memcached`, `onprem.queue.Kafka/Rabbitmq`, `onprem.network.Nginx/Traefik/Haproxy/Caddy`, `onprem.registry.Harbor`.

## 3. On-prem / hybrid deployment

### 3A. On-prem data-center (tiered + zoned) — TB, top=least trusted
1. Internet/untrusted (top, grey) → 2. Perimeter firewall → **DMZ** (LBs + reverse proxies live here) → 3. Inner firewall (stricter) → Trusted LAN → 4. **App tier** (app/web servers) → 5. **Data tier** (DB cluster + SAN/NAS/object storage), innermost/most protected.
- Firewalls = explicit boundary objects between zones (different firewall DMZ↔Internet vs DMZ↔intranet). Each zone = a `Cluster`; nest tiers inside zones.
- Show redundancy (paired LBs, clustered DBs, N+1). Bare-metal vs VM vs container = nesting depth (Server → hypervisor/VMs → containers).
- Colour by trust zone (red/orange perimeter-DMZ, blue trusted LAN, green data).

### 3B. Hybrid cloud connectivity — LR, on-prem left, cloud right
Two boundaries: on-prem box + cloud VPC/VNet box. Private link is one of: **Site-to-Site VPN** (IPsec over Internet — dashed tunnel through the Internet cloud) OR **AWS Direct Connect / Azure ExpressRoute** (dedicated private circuit — solid line that visibly bypasses the Internet, via a provider/colo hop). Customer edge router ↔ cloud gateway (VNet Gateway / DX Gateway / VPG). Common HA pattern: ExpressRoute/DX primary + VPN failover (dashed, "failover"). **Always label the link with type + private-vs-encrypted-over-internet** — that distinction is the whole point.
- mingrammer: `onprem.network.Vyos/Nginx/Envoy/Istio/Internet`, `onprem.compute.Server`, `generic.network.{Firewall,Router,VPN,Switch,Subnet}`, `generic.storage.Storage` (SAN/NAS); cloud side `aws.network.VPC/DirectConnect/VPNGateway` or `azure.network.VirtualNetworks/ExpressrouteCircuits/VirtualNetworkGateways`.

## 4. CI/CD & GitOps

### 4A. Classic CI/CD (push) — strictly LR linear
`Source (SCM) → Build → Test → Package/Registry → Deploy → Environment`. Tests early ("when failure is cheap"). Environments dev→stage→prod = successive stages with gates/approvals between (diamond or "manual approval" edge). Stage order left→right must match execution order. Parallel jobs in a stage → `Cluster`.

### 4B. GitOps (pull, Argo CD) — the direction people get wrong
Two Git repos (app source + config/manifests). CI builds+tests+pushes image, then **writes the new image tag to the config repo** (CI ends at Git, never touches the cluster). **Argo CD runs INSIDE the cluster and PULLS desired state from the config repo, continuously reconciling.**
- **The reconcile arrow points FROM Argo CD (in-cluster) TO Git — the cluster pulls; CI never pushes to the cluster.** Draw a reconcile LOOP (dashed, "pull/reconcile"), not a one-shot arrow. Cluster credentials never leave the cluster.
- mingrammer: `onprem.vcs.Git/Github/Gitlab`, `onprem.ci.Jenkins/Gitlabci/GithubActions/Circleci/Droneci`, `onprem.cd.Spinnaker/Tekton`, `onprem.gitops.Argocd/Flux/Flagger`, `onprem.registry.Harbor`, `onprem.iac.Terraform/Ansible`, `onprem.monitoring.Prometheus/Grafana`.
- CI/CD tool = platform-fit & control-aware, NOT reflexive GitHub Actions. Regulated/in-VPC → self-hostable (GitLab self-managed, Jenkins, Azure DevOps Server); unknown SCM → present neutral "GitHub Actions / GitLab CI / CodePipeline" deferred to kickoff.

## 5. Cross-cutting conventions
| Concern | Convention |
|---|---|
| Reading direction | Layered infra (zones/tiers, k8s workload) = TB, trust/ingress at top. Flows (request path, Docker client→daemon, CI/CD, hybrid link) = LR, time/traffic left→right. |
| Containment | Nested `Cluster`s for "inside" (cloud→VPC→subnet→node→pod; host→VM→container; zone→tier). |
| Colour | One accent for "our platform," grey for external/Internet, per-zone/tier fills for grouping. K8s blue `#326CE5`. |
| Edges | Solid = request/data/artifact; dashed = control/async/reconcile/config; label protocol/port/action; failover = dashed + "failover." |
| Legend | Mandatory when >2 edge types or colour groups. Build a `Cluster("Legend")`. |
| Stateful vs stateless | Always distinguish volume/PV-backed stores from stateless nodes (colour or shape). |
| Overflow | Deep TB graphs → flip to LR; break labels before `(`. |
