#!/usr/bin/env python3
"""Canonical clean-layout builders for CLOUD / INFRA / TECH diagrams (mingrammer).

THIS IS PART OF THE SKILL, not just the samples. Phase 3 (`03_generate.md`) must
COPY the closest builder here and adapt node labels/counts/tech to the project —
do NOT freehand a mingrammer script, or you lose the layout discipline that stops
the "curvy-arrow spaghetti + big empty box" look. Each builder already encodes the
rules from `reference/kb_diagram_layout.md`:

  • splines=ortho (right-angle edges), one flow axis, ONE clean spine
  • shared/cross-cutting services (IAM/KMS/Secrets/monitoring) = a compact BAND
    packed with an invisible edge-chain and anchored by ONE grouped dashed edge
    (never a fan-out edge to each — that IS the spider web)
  • nested, shrink-wrapped boundaries (VPC>subnet, cluster>namespace, zones)
  • multi-AZ data (primary + replica with one replication edge), messaging
  • real vendor icons; tight, even spacing

Every builder renders `<out_dir>/<slug>.png` + `.svg` (self-contained) + `.drawio`.
`TEMPLATES` maps slug -> builder so a run (or the sample generator) can pick one.
"""
from __future__ import annotations

import sys
from pathlib import Path

_here = Path(__file__).resolve().parent
sys.path.insert(0, str(_here))
from diagrams_runtime import bootstrap, wrap_label          # noqa: E402
from svg_util import inline_images, png_to_drawio           # noqa: E402

L = lambda s, n=16: wrap_label(s, n)
INK, PUR, GREEN = "#37474F", "#8E24AA", "#2E7D32"
# splines=ortho is the single biggest anti-spaghetti setting; tight even spacing.
G = dict(fontsize="20", bgcolor="white", pad="0.7", nodesep="0.6", ranksep="0.9",
         splines="ortho", dpi="300", compound="true", labelloc="t", fontname="Segoe UI")
N = {"fontsize": "13", "fontname": "Segoe UI"}


def _finish(out_dir: Path, slug: str):
    """Make the SVG self-contained + emit an editable .drawio for the PNG."""
    out_dir = Path(out_dir)
    try:
        inline_images(out_dir / f"{slug}.svg")
    except Exception:  # noqa: BLE001
        pass
    try:
        png_to_drawio(out_dir / f"{slug}.png", slug)
    except Exception:  # noqa: BLE001
        pass


def _diagram(title, out_dir, slug, direction="LR"):
    from diagrams import Diagram
    return Diagram(title, filename=str(Path(out_dir) / slug), outformat=["png", "svg"],
                   show=False, direction=direction, graph_attr=G, node_attr=N)


# Cloud/infra reference architectures use the pixel-perfect MANUAL-GRID renderer
# (build_cloud + cloud_specs) — the brochure-grade path. Adapt cloud_specs.py.
from build_cloud import render as _render_cloud   # noqa: E402
from cloud_specs import SPECS as _CLOUD_SPECS      # noqa: E402

def _cloud_builder(slug):
    def fn(out_dir, slug=slug):
        # build_cloud emits a NATIVE editable .drawio (draggable icons/boxes/edges),
        # so do NOT overwrite it with an image-backed one.
        _render_cloud(_CLOUD_SPECS[slug], Path(out_dir) / f"{slug}.png")
    return fn


# --------------------------------------------------------------------------- AWS
def build_aws_ref(out_dir, slug="aws_ref"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.aws.network import Route53, CloudFront, ELB, NATGateway
    from diagrams.aws.security import WAF, IAM, KMS, SecretsManager
    from diagrams.aws.compute import EKS
    from diagrams.aws.database import Aurora, ElastiCache
    from diagrams.aws.integration import SNS, SQS
    from diagrams.aws.storage import S3
    from diagrams.aws.management import Cloudwatch
    from diagrams.onprem.client import Users
    with _diagram("AWS Reference Architecture — Multi-AZ", out_dir, slug):
        users = Users("End users")
        with Cluster("Edge / Global", graph_attr={"bgcolor": "#FFF8E1", "pencolor": "#F9A825"}):
            dns = Route53(L("Route 53")); cdn = CloudFront("CloudFront"); waf = WAF("AWS WAF")
            dns >> Edge(color=INK) >> cdn >> Edge(color=INK) >> waf
        with Cluster("VPC 10.0.0.0/16", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#8C4FFF", "style": "rounded,dashed", "fontsize": "15"}):
            with Cluster("Public Subnets (AZ-a/b)", graph_attr={"bgcolor": "#FBF3E0"}):
                alb = ELB(L("ALB (TLS, 2 AZ)")); NATGateway(L("NAT GW x2"))
            with Cluster("Private App Subnets — EKS (autoscale 3-12)", graph_attr={"bgcolor": "#FBE9E7"}):
                eks = [EKS("svc"), EKS("svc"), EKS("svc")]
            with Cluster("Data Subnets (Multi-AZ)", graph_attr={"bgcolor": "#E7F0FA"}):
                aur1 = Aurora(L("Aurora primary [SoR][PII]")); aur2 = Aurora(L("Aurora replica")); redis = ElastiCache(L("ElastiCache"))
                aur1 >> Edge(label="replication", color=GREEN, style="dashed") >> aur2
            with Cluster("Messaging", graph_attr={"bgcolor": "#F3E5F5"}):
                sns = SNS("SNS"); sqs = SQS(L("SQS + DLQ")); sns >> Edge(color=PUR, style="dashed") >> sqs
        with Cluster("Security & Observability", graph_attr={"bgcolor": "#FDECEA", "pencolor": "#DD344C"}):
            iam = IAM("IAM"); kms = KMS("KMS"); sec = SecretsManager(L("Secrets")); cw = Cloudwatch("CloudWatch"); s3 = S3(L("S3 backup"))
        users >> Edge(color=INK) >> dns; waf >> Edge(label="HTTPS", color=INK) >> alb; alb >> Edge(label="HTTP/WSS", color=INK) >> eks[1]
        eks[1] >> Edge(label="SQL/TLS", color=INK) >> aur1; eks[1] >> Edge(label="cache", color=INK) >> redis; eks[1] >> Edge(label="events", color=PUR, style="dashed") >> sns
        iam >> Edge(style="invis") >> kms >> Edge(style="invis") >> sec >> Edge(style="invis") >> cw >> Edge(style="invis") >> s3
        eks[1] >> Edge(label="IAM / KMS / secrets / metrics", color=PUR, style="dashed") >> iam
    _finish(out_dir, slug)


# ------------------------------------------------------------------------- Azure
def build_azure_ref(out_dir, slug="azure_ref"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.azure.network import FrontDoors, ApplicationGateway, LoadBalancers
    from diagrams.azure.compute import AKS
    from diagrams.azure.database import SQLDatabases, CacheForRedis
    from diagrams.azure.storage import BlobStorage
    from diagrams.azure.integration import ServiceBus
    from diagrams.azure.security import KeyVaults
    from diagrams.azure.identity import AzureActiveDirectory
    from diagrams.azure.monitor import Monitor
    from diagrams.onprem.client import Users
    with _diagram("Azure Reference Architecture", out_dir, slug):
        users = Users("End users"); fd = FrontDoors(L("Front Door + WAF"))
        with Cluster("VNet 10.1.0.0/16 (zone-redundant)", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#0078D4", "style": "rounded,dashed", "fontsize": "15"}):
            with Cluster("Subnet: App Gateway", graph_attr={"bgcolor": "#FBF3E0"}): agw = ApplicationGateway(L("App Gateway (WAF v2)"))
            with Cluster("Subnet: AKS", graph_attr={"bgcolor": "#FBE9E7"}): lb = LoadBalancers(L("Internal LB")); aks = AKS(L("AKS system+user pools")); lb >> Edge(color=INK) >> aks
            with Cluster("Subnet: Private Endpoints", graph_attr={"bgcolor": "#E7F0FA"}): sql = SQLDatabases(L("Azure SQL [SoR][PII]")); redis = CacheForRedis(L("Redis")); blob = BlobStorage(L("Blob"))
            with Cluster("Messaging", graph_attr={"bgcolor": "#F3E5F5"}): sb = ServiceBus(L("Service Bus"))
        with Cluster("Shared Services", graph_attr={"bgcolor": "#F3E9FB", "pencolor": "#8E24AA"}): entra = AzureActiveDirectory("Entra ID"); kv = KeyVaults("Key Vault"); mon = Monitor(L("Monitor"))
        users >> Edge(color=INK) >> fd >> Edge(label="HTTPS", color=INK) >> agw >> Edge(label="HTTPS", color=INK) >> lb
        aks >> Edge(label="SQL", color=INK) >> sql; aks >> Edge(label="cache", color=INK) >> redis; aks >> Edge(label="events", color=PUR, style="dashed") >> sb; aks >> Edge(label="assets", color=INK) >> blob
        entra >> Edge(style="invis") >> kv >> Edge(style="invis") >> mon
        aks >> Edge(label="identity / secrets / metrics", color=PUR, style="dashed") >> entra
    _finish(out_dir, slug)


# --------------------------------------------------------------------------- GCP
def build_gcp_ref(out_dir, slug="gcp_ref"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.gcp.network import LoadBalancing, CDN, Armor, DNS
    from diagrams.gcp.compute import GKE, Run
    from diagrams.gcp.database import SQL, Memorystore
    from diagrams.gcp.storage import Storage
    from diagrams.gcp.analytics import PubSub
    from diagrams.gcp.security import Iam, KeyManagementService
    from diagrams.gcp.operations import Monitoring
    from diagrams.onprem.client import Users
    with _diagram("GCP Reference Architecture — Global VPC", out_dir, slug):
        users = Users("End users")
        with Cluster("Edge / Global", graph_attr={"bgcolor": "#FFF8E1", "pencolor": "#F9A825"}):
            dns = DNS("Cloud DNS"); cdn = CDN("Cloud CDN"); glb = LoadBalancing(L("Global LB")); arm = Armor("Cloud Armor")
            dns >> Edge(color=INK) >> cdn >> Edge(color=INK) >> glb >> Edge(color=INK) >> arm
        with Cluster("VPC (global) 10.8.0.0/14", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#4285F4", "style": "rounded,dashed", "fontsize": "15"}):
            with Cluster("Region: us-central1", graph_attr={"bgcolor": "#FBF3E0"}): run = Run(L("Cloud Run")); gke = GKE(L("GKE regional"))
            with Cluster("Region: europe-west1 (DR)", graph_attr={"bgcolor": "#ECEFF1"}): GKE(L("GKE standby"))
            with Cluster("Data", graph_attr={"bgcolor": "#E7F0FA"}): sql = SQL(L("Cloud SQL primary [SoR]")); sql2 = SQL(L("read replica")); mem = Memorystore("Memorystore"); sql >> Edge(label="replication", color=GREEN, style="dashed") >> sql2
            with Cluster("Messaging", graph_attr={"bgcolor": "#F3E5F5"}): ps = PubSub("Pub/Sub")
        with Cluster("Shared Services", graph_attr={"bgcolor": "#E8F5E9", "pencolor": "#34A853"}): iam = Iam("Cloud IAM"); kms = KeyManagementService("Cloud KMS"); ops = Monitoring(L("Cloud Ops")); gcs = Storage(L("GCS"))
        users >> Edge(color=INK) >> dns; arm >> Edge(label="HTTPS", color=INK) >> run >> Edge(label="gRPC", color=INK) >> gke
        gke >> Edge(label="SQL", color=INK) >> sql; gke >> Edge(label="cache", color=INK) >> mem; gke >> Edge(label="events", color=PUR, style="dashed") >> ps; gke >> Edge(label="assets", color=INK) >> gcs
        iam >> Edge(style="invis") >> kms >> Edge(style="invis") >> ops
        gke >> Edge(label="IAM / KMS / ops", color=PUR, style="dashed") >> iam
    _finish(out_dir, slug)


# --------------------------------------------------------------------- Kubernetes
def build_k8s_topology(out_dir, slug="k8s_topology"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.k8s.network import Ingress, Service
    from diagrams.k8s.compute import Pod, StatefulSet
    from diagrams.k8s.podconfig import ConfigMap, Secret
    from diagrams.k8s.clusterconfig import HPA
    from diagrams.k8s.storage import PV, PVC
    from diagrams.k8s.controlplane import API
    from diagrams.k8s.infra import ETCD, Node
    from diagrams.onprem.client import Users
    with _diagram("Kubernetes Architecture — Control Plane + Workload", out_dir, slug):
        users = Users("Users")
        with Cluster("Control Plane (HA)", graph_attr={"bgcolor": "#E3F2FD", "pencolor": "#1565C0"}): api = API("kube-apiserver"); etcd = ETCD("etcd"); api >> Edge(color=INK) >> etcd
        with Cluster("Kubernetes Cluster", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#326CE5", "style": "rounded,dashed", "fontsize": "15"}):
            with Cluster("Namespace: app", graph_attr={"bgcolor": "#FBF3E0"}):
                ing = Ingress("Ingress"); svc = Service(L("Service"))
                with Cluster("Deployment: web (HPA 3-10)", graph_attr={"bgcolor": "#FFFFFF"}): hpa = HPA("HPA"); pods = [Pod("pod"), Pod("pod"), Pod("pod")]
                with Cluster("StatefulSet: db", graph_attr={"bgcolor": "#E7F0FA"}): db = StatefulSet("db"); pvc = PVC("PVC"); pv = PV("PV"); db >> Edge(color=INK) >> pvc >> Edge(color=INK) >> pv
                cm = ConfigMap("ConfigMap"); sec = Secret("Secret")
            node = Node(L("worker node x3"))
        users >> Edge(label="HTTPS", color=INK) >> ing >> Edge(color=INK) >> svc >> Edge(label="LB", color=INK) >> pods[1]
        hpa >> Edge(label="scale", color=PUR, style="dashed") >> pods[0]; cm >> Edge(color=PUR, style="dashed") >> pods[0]; sec >> Edge(color=PUR, style="dashed") >> pods[0]
        pods[1] >> Edge(label="SQL", color=INK) >> db; api >> Edge(label="schedules", color=PUR, style="dashed") >> node
    _finish(out_dir, slug)


# ------------------------------------------------------------------------- Docker
def build_docker_compose(out_dir, slug="docker_compose"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.onprem.network import Nginx
    from diagrams.onprem.container import Docker
    from diagrams.onprem.database import Postgresql
    from diagrams.onprem.inmemory import Redis
    from diagrams.onprem.queue import Rabbitmq
    from diagrams.onprem.client import Users
    with _diagram("Docker Compose — Multi-Service App", out_dir, slug):
        users = Users("Users"); rp = Nginx(L("nginx reverse proxy :443"))
        with Cluster("frontend network", graph_attr={"bgcolor": "#E8F1FB"}): api1 = Docker(L("api :3000")); web = Docker(L("web :80"))
        with Cluster("worker network", graph_attr={"bgcolor": "#F3E5F5"}): worker = Docker("worker"); mq = Rabbitmq(L("RabbitMQ"))
        with Cluster("data network (volumes)", graph_attr={"bgcolor": "#E7F0FA"}): pg = Postgresql(L("postgres (vol)")); redis = Redis(L("redis (vol)"))
        users >> Edge(label="HTTPS", color=INK) >> rp; rp >> Edge(label="/api", color=INK) >> api1; rp >> Edge(label="/", color=INK) >> web
        api1 >> Edge(label="SQL", color=INK) >> pg; api1 >> Edge(label="cache", color=INK) >> redis; api1 >> Edge(label="jobs", color=PUR, style="dashed") >> mq >> Edge(color=PUR, style="dashed") >> worker; worker >> Edge(color=INK) >> pg
    _finish(out_dir, slug)


# ------------------------------------------------------------------- On-prem hybrid
def build_onprem_hybrid(out_dir, slug="onprem_hybrid"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.generic.network import Firewall
    from diagrams.onprem.network import Haproxy, Nginx, Internet
    from diagrams.onprem.compute import Server
    from diagrams.onprem.database import Oracle
    from diagrams.aws.compute import EKS
    with _diagram("Hybrid — On-Prem Data Center + AWS", out_dir, slug):
        net = Internet("Internet")
        with Cluster("On-Premises Data Center", graph_attr={"bgcolor": "#ECEFF1", "pencolor": "#607D8B"}):
            pf = Firewall("Perimeter FW")
            with Cluster("DMZ", graph_attr={"bgcolor": "#FDECEA"}): lb = Haproxy("HAProxy LB"); rp = Nginx("Reverse proxy")
            inf = Firewall("Internal FW")
            with Cluster("App Tier", graph_attr={"bgcolor": "#FBF3E0"}): a1 = Server(L("App servers x3"))
            with Cluster("Data Tier", graph_attr={"bgcolor": "#E7F0FA"}): db = Oracle(L("Oracle RAC")); san = Server(L("SAN storage"))
            pf >> Edge(color=INK) >> lb >> Edge(color=INK) >> rp >> Edge(color=INK) >> inf >> Edge(color=INK) >> a1 >> Edge(label="SQL", color=INK) >> db >> Edge(color=INK) >> san
        with Cluster("AWS (ap-southeast-1)", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#8C4FFF", "style": "rounded,dashed"}):
            with Cluster("VPC", graph_attr={"bgcolor": "#FBE9E7"}): eks = EKS(L("EKS workloads"))
        net >> Edge(label="HTTPS", color=INK) >> pf; a1 >> Edge(label="Direct Connect (primary)", color=INK) >> eks; a1 >> Edge(label="VPN (failover)", color=PUR, style="dashed") >> eks
    _finish(out_dir, slug)


# --------------------------------------------------------------------------- CI/CD
def build_cicd(out_dir, slug="cicd"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.onprem.vcs import Github
    from diagrams.onprem.ci import GithubActions
    from diagrams.onprem.container import Docker
    from diagrams.onprem.gitops import Argocd
    from diagrams.k8s.compute import Deployment
    from diagrams.onprem.client import Users
    with _diagram("CI/CD Pipeline — Commit to Production", out_dir, slug):
        dev = Users("Developer"); src = Github(L("app repo (Git)"))
        with Cluster("CI (runner)", graph_attr={"bgcolor": "#E8F1FB"}): ci = GithubActions(L("build + test + Trivy scan"))
        reg = Docker(L("Container Registry")); cfg = Github(L("config repo"))
        with Cluster("Kubernetes Cluster", graph_attr={"bgcolor": "#FBE9E7", "pencolor": "#326CE5"}): argo = Argocd("Argo CD"); dep = Deployment(L("Deployment (blue/green)"))
        dev >> Edge(color=INK) >> src >> Edge(color=INK) >> ci; ci >> Edge(label="push image", color=INK) >> reg; ci >> Edge(label="write image tag", color=INK) >> cfg
        argo >> Edge(label="pull / reconcile", color=PUR, style="dashed") >> cfg; reg >> Edge(color=INK) >> argo >> Edge(label="apply", color=INK) >> dep
    _finish(out_dir, slug)


# ------------------------------------------------------------------- Data pipeline
def build_data_pipeline(out_dir, slug="data_pipeline"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.onprem.database import Postgresql
    from diagrams.onprem.queue import Kafka
    from diagrams.onprem.analytics import Spark
    from diagrams.aws.storage import S3
    from diagrams.aws.analytics import Redshift, Quicksight
    with _diagram("Data Pipeline — Batch + Streaming Lineage", out_dir, slug):
        with Cluster("Source", graph_attr={"bgcolor": "#FFF8E1"}): src = Postgresql(L("PostgreSQL OLTP"))
        with Cluster("Ingest (stream)", graph_attr={"bgcolor": "#F3E5F5"}): kafka = Kafka(L("Kafka CDC"))
        with Cluster("Transform", graph_attr={"bgcolor": "#E8F1FB"}): spark = Spark(L("Spark ETL"))
        with Cluster("Lake / Warehouse", graph_attr={"bgcolor": "#E7F0FA"}): lake = S3(L("S3 lake (bronze/silver/gold)")); wh = Redshift(L("Redshift warehouse"))
        with Cluster("Serve", graph_attr={"bgcolor": "#E8F5E9"}): bi = Quicksight(L("QuickSight BI"))
        src >> Edge(label="CDC", color=PUR, style="dashed") >> kafka >> Edge(label="stream", color=INK) >> spark >> Edge(label="raw->curated", color=INK) >> lake >> Edge(label="load", color=INK) >> wh >> Edge(label="query", color=INK) >> bi
    _finish(out_dir, slug)


# ------------------------------------------------------------------------- GitOps
def build_gitops(out_dir, slug="gitops"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.onprem.vcs import Github, Git
    from diagrams.onprem.ci import GithubActions
    from diagrams.onprem.gitops import Argocd
    from diagrams.onprem.container import Docker
    from diagrams.k8s.compute import Deployment
    with _diagram("GitOps — Argo CD Pull / Reconcile", out_dir, slug):
        src = Github(L("app repo")); ci = GithubActions(L("CI: build + test")); reg = Docker("Registry"); cfg = Git(L("config repo"))
        with Cluster("Kubernetes Cluster", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#326CE5"}): argo = Argocd("Argo CD"); dep = Deployment(L("Deployment (blue/green)"))
        src >> Edge(color=INK) >> ci; ci >> Edge(label="push image", color=INK) >> reg; ci >> Edge(label="write image tag", color=INK) >> cfg
        argo >> Edge(label="pull / reconcile", color=PUR, style="dashed") >> cfg; argo >> Edge(label="apply", color=INK) >> dep
    _finish(out_dir, slug)


# ------------------------------------------------------------------- Microservices
def build_microservices(out_dir, slug="microservices"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.programming.language import Csharp, Go
    from diagrams.onprem.database import Postgresql
    from diagrams.onprem.queue import Kafka
    from diagrams.onprem.network import Nginx
    from diagrams.onprem.client import Users
    with _diagram("Microservices Decomposition — E-commerce", out_dir, slug, direction="TB"):
        client = Users("Web / Mobile"); gw = Nginx(L("API Gateway (Kong)"))
        with Cluster("Users Context", graph_attr={"bgcolor": "#E8F1FB"}): us = Csharp(L(".NET 8 Users")); ud = Postgresql("Users DB")
        with Cluster("Orders Context", graph_attr={"bgcolor": "#FBF3E0"}): os = Csharp(L(".NET 8 Orders")); od = Postgresql("Orders DB")
        with Cluster("Payments Context", graph_attr={"bgcolor": "#FDECEA"}): ps = Go(L("Payments (Go)")); pd = Postgresql("Payments DB")
        bus = Kafka(L("Event Bus (Kafka)"))
        client >> Edge(label="HTTPS", color=INK) >> gw; gw >> Edge(label="REST", color=INK) >> us; gw >> Edge(label="REST", color=INK) >> os
        us >> Edge(label="SQL", color=INK) >> ud; os >> Edge(label="SQL", color=INK) >> od; ps >> Edge(label="SQL", color=INK) >> pd
        os >> Edge(label="OrderPlaced", color=PUR, style="dashed") >> bus; bus >> Edge(label="OrderPlaced", color=PUR, style="dashed") >> ps; ps >> Edge(label="PaymentSettled", color=PUR, style="dashed") >> bus
    _finish(out_dir, slug)


# ------------------------------------------------------------------- C4 container
def build_c4_container(out_dir, slug="c4_container"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.programming.framework import React
    from diagrams.programming.language import Csharp
    from diagrams.onprem.database import Postgresql
    from diagrams.onprem.compute import Server
    from diagrams.onprem.client import Client
    with _diagram("Container Diagram — Internet Banking", out_dir, slug):
        cust = Client("Customer")
        with Cluster("Internet Banking System", graph_attr={"bgcolor": "#E8F1FB", "pencolor": "#1565C0"}): spa = React(L("SPA (React)")); api = Csharp(L("API (.NET 8)")); db = Postgresql("Database")
        mail = Server(L("Email System (SendGrid)")); core = Server(L("Mainframe Banking"))
        cust >> Edge(label="HTTPS", color=INK) >> spa >> Edge(label="JSON/HTTPS", color=INK) >> api >> Edge(label="SQL/TLS", color=INK) >> db
        api >> Edge(label="send email", color=PUR, style="dashed") >> mail; api >> Edge(label="accounts [XML]", color=INK) >> core
    _finish(out_dir, slug)


# ----------------------------------------------------------------- UML deployment
def build_uml_deployment(out_dir, slug="uml_deployment"):
    bootstrap()
    from diagrams import Edge
    from diagrams.onprem.network import Nginx
    from diagrams.onprem.compute import Server
    from diagrams.onprem.database import Postgresql
    from diagrams.onprem.client import Client
    with _diagram("Deployment Diagram — Web App", out_dir, slug):
        cl = Client("Client Device"); web = Nginx(L("Web Server (nginx)")); app = Server(L("App Server (Node.js)")); db = Postgresql(L("DB Server (PostgreSQL)"))
        cl >> Edge(label="HTTPS", color=INK) >> web >> Edge(label="reverse proxy", color=INK) >> app >> Edge(label="TCP 5432", color=INK) >> db
    _finish(out_dir, slug)


# --------------------------------------------------------------------- AI / RAG
def build_ai_rag(out_dir, slug="ai_rag"):
    bootstrap()
    from diagrams import Cluster, Edge
    from diagrams.custom import Custom
    from diagrams.onprem.client import Users
    from diagrams.onprem.compute import Server
    AI = _here.parent / "assets" / "icons" / "ai" / "png"; ic = lambda n: str(AI / f"{n}.png")
    with _diagram("AI RAG + Multi-Model Gateway", out_dir, slug):
        user = Users("User"); app = Server(L("Chat App / API")); orch = Custom(L("LangChain orchestrator"), ic("langchain"))
        with Cluster("Model providers", graph_attr={"bgcolor": "#E8F1FB"}): oai = Custom("OpenAI", ic("openai")); cl = Custom("Claude", ic("claude")); gm = Custom("Gemini", ic("gemini")); dsk = Custom("DeepSeek", ic("deepseek"))
        with Cluster("Retrieval", graph_attr={"bgcolor": "#E8F5E9"}): emb = Custom(L("Embeddings"), ic("huggingface")); vdb = Custom(L("Qdrant vector DB"), ic("qdrant"))
        user >> Edge(label="prompt", color=INK) >> app >> Edge(color=INK) >> orch; orch >> Edge(label="route", color=INK) >> oai; orch >> Edge(color=INK) >> cl; orch >> Edge(color=INK) >> gm; orch >> Edge(color=INK) >> dsk
        app >> Edge(label="embed", color=INK) >> emb >> Edge(label="upsert / search", color=INK) >> vdb; vdb >> Edge(label="context", color=PUR, style="dashed") >> orch
    _finish(out_dir, slug)


# Cloud/infra ref-arch (aws/azure/gcp/onprem/k8s/docker) → manual-grid build_cloud
# (pixel-perfect). Flow/structure diagrams → mingrammer builders above.
TEMPLATES = {
    "aws_ref": _cloud_builder("aws_ref"), "azure_ref": _cloud_builder("azure_ref"),
    "gcp_ref": _cloud_builder("gcp_ref"), "onprem_hybrid": _cloud_builder("onprem_hybrid"),
    "k8s_topology": _cloud_builder("k8s_topology"), "docker_compose": _cloud_builder("docker_compose"),
    "cicd": _cloud_builder("cicd"), "data_pipeline": _cloud_builder("data_pipeline"), "gitops": _cloud_builder("gitops"),
    "microservices": _cloud_builder("microservices"), "c4_container": _cloud_builder("c4_container"),
    "uml_deployment": _cloud_builder("uml_deployment"), "ai_rag": _cloud_builder("ai_rag"),
}

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="Render a clean cloud/infra/tech template.")
    ap.add_argument("--name", required=True, choices=list(TEMPLATES))
    ap.add_argument("--out", default=".")
    a = ap.parse_args()
    Path(a.out).mkdir(parents=True, exist_ok=True)
    TEMPLATES[a.name](a.out)
    print(f"rendered {a.name} -> {a.out}")
