#!/usr/bin/env python3
"""Tiered cloud/infra architecture SPECS for the manual-grid renderer (build_cloud.py).

These are the SKILL's canonical brochure-grade cloud diagrams. Phase 3 copies the
closest spec and adapts labels/counts/tech to the project, then renders with
`build_cloud.render(spec, out)`. Icons are 'provider/stem' (resolved from the
mingrammer bundled icon PNGs). Layout discipline is built into build_cloud:
tier-columns left→right, a VPC/VNet wrap spanning the tiers, a bottom shared band
(no edges — position implies scope), orthogonal connectors, real icons.
"""

AWS = {
 "title": "AWS Reference Architecture — Multi-AZ", "legend": True,
 "columns": [
   {"id": "edge", "boundary": {"label": "Edge / Global", "fill": "#FFF8E1", "stroke": "#F9A825"},
    "nodes": [{"id": "dns", "label": "Route 53", "icon": "aws/route-53"}, {"id": "cdn", "label": "CloudFront", "icon": "aws/cloudfront"}, {"id": "waf", "label": "AWS WAF", "icon": "aws/waf"}]},
   {"id": "public", "boundary": {"label": "Public Subnets (AZ-a/b)", "fill": "#FBF3E0", "stroke": "#F9A825", "icon": "aws/public-subnet"},
    "nodes": [{"id": "alb", "label": "ALB (TLS, 2 AZ)", "icon": "aws/elb-application-load-balancer"}, {"id": "nat", "label": "NAT GW x2", "icon": "aws/nat-gateway"}]},
   {"id": "eks", "boundary": {"label": "Private Subnets — EKS (autoscale 3-12)", "fill": "#FBE9E7", "stroke": "#D84315", "icon": "aws/private-subnet"},
    "nodes": [{"id": "eks", "label": "EKS services", "icon": "aws/elastic-kubernetes-service", "tech": "Fargate"}]},
   {"id": "data", "boundary": {"label": "Data Subnets (Multi-AZ)", "fill": "#E7F0FA", "stroke": "#1E88E5", "icon": "aws/private-subnet"},
    "nodes": [{"id": "aur", "label": "Aurora primary", "icon": "aws/aurora"}, {"id": "aur2", "label": "Aurora replica", "icon": "aws/aurora"}, {"id": "redis", "label": "ElastiCache", "icon": "aws/elasticache"}, {"id": "os", "label": "OpenSearch", "icon": "aws/amazon-opensearch-service"}]},
   {"id": "msg", "boundary": {"label": "Messaging", "fill": "#F3E5F5", "stroke": "#8E24AA"},
    "nodes": [{"id": "msk", "label": "Amazon MSK", "icon": "aws/managed-streaming-for-kafka"}, {"id": "sqs", "label": "SQS + DLQ", "icon": "aws/simple-queue-service"}]},
 ],
 "wraps": [{"label": "VPC 10.0.0.0/16", "fill": "#FFFFFF", "stroke": "#8C4FFF", "dashed": True, "icon": "aws/vpc", "cols": ["public", "eks", "data", "msg"]}],
 "shared": {"label": "Security & Observability  (account-scoped)", "fill": "#FDECEA", "stroke": "#DD344C",
   "anchor": {"from": "eks", "label": "IAM / KMS / Secrets / TLS / metrics  (all tiers)"},
   "nodes": [{"id": "iam", "label": "IAM", "icon": "aws/identity-and-access-management"}, {"id": "kms", "label": "KMS", "icon": "aws/key-management-service"}, {"id": "sec", "label": "Secrets Mgr", "icon": "aws/secrets-manager"}, {"id": "cw", "label": "CloudWatch", "icon": "aws/cloudwatch"}, {"id": "s3", "label": "S3 backup", "icon": "aws/simple-storage-service"}]},
 "edges": [
   {"from": "dns", "to": "cdn"}, {"from": "cdn", "to": "waf"}, {"from": "waf", "to": "alb", "label": "HTTPS"},
   {"from": "alb", "to": "eks", "label": "HTTP/WSS"}, {"from": "eks", "to": "aur", "label": "SQL/TLS"}, {"from": "eks", "to": "redis", "label": "cache"},
   {"from": "aur", "to": "aur2", "label": "replication", "style": "dashed", "color": "#2E7D32"},
   {"from": "eks", "to": "os", "label": "search"}, {"from": "eks", "to": "msk", "label": "events", "style": "dashed"}, {"from": "msk", "to": "sqs", "style": "dashed"},
 ],
}

AZURE = {
 "title": "Azure Reference Architecture — Hub / Spoke", "legend": True,
 "columns": [
   {"id": "edge", "boundary": {"label": "Edge / Global", "fill": "#FFF8E1", "stroke": "#F9A825"},
    "nodes": [{"id": "fd", "label": "Front Door + WAF", "icon": "azure/front-doors"}]},
   {"id": "agw", "boundary": {"label": "Subnet: App Gateway", "fill": "#FBF3E0", "stroke": "#F9A825", "icon": "azure/subnets"},
    "nodes": [{"id": "agw", "label": "App Gateway (WAF v2)", "icon": "azure/application-gateway"}]},
   {"id": "aks", "boundary": {"label": "Subnet: AKS", "fill": "#FBE9E7", "stroke": "#D84315", "icon": "azure/subnets"},
    "nodes": [{"id": "lb", "label": "Internal LB", "icon": "azure/load-balancers"}, {"id": "aks", "label": "AKS pools", "icon": "azure/kubernetes-services", "tech": "system+user"}]},
   {"id": "data", "boundary": {"label": "Private Endpoints", "fill": "#E7F0FA", "stroke": "#1E88E5", "icon": "azure/subnets"},
    "nodes": [{"id": "sql", "label": "Azure SQL", "icon": "azure/sql-database"}, {"id": "redis", "label": "Cache for Redis", "icon": "azure/cache-redis"}, {"id": "blob", "label": "Blob Storage", "icon": "azure/blob-storage"}]},
   {"id": "msg", "boundary": {"label": "Messaging", "fill": "#F3E5F5", "stroke": "#8E24AA"},
    "nodes": [{"id": "sb", "label": "Service Bus", "icon": "azure/service-bus"}]},
 ],
 "wraps": [{"label": "VNet 10.1.0.0/16 (zone-redundant)", "fill": "#FFFFFF", "stroke": "#0078D4", "dashed": True, "icon": "azure/virtual-networks", "cols": ["agw", "aks", "data", "msg"]}],
 "shared": {"label": "Shared Services  (subscription-scoped)", "fill": "#F3E9FB", "stroke": "#8E24AA",
   "anchor": {"from": "aks", "label": "Entra ID / Key Vault / Monitor  (all tiers)"},
   "nodes": [{"id": "entra", "label": "Entra ID", "icon": "azure/azure-active-directory"}, {"id": "kv", "label": "Key Vault", "icon": "azure/key-vaults"}, {"id": "mon", "label": "Monitor", "icon": "azure/azure-monitor"}]},
 "edges": [
   {"from": "fd", "to": "agw", "label": "HTTPS"}, {"from": "agw", "to": "lb", "label": "HTTPS"}, {"from": "lb", "to": "aks"},
   {"from": "aks", "to": "sql", "label": "SQL"}, {"from": "aks", "to": "redis", "label": "cache"}, {"from": "aks", "to": "blob", "label": "assets"},
   {"from": "aks", "to": "sb", "label": "events", "style": "dashed"},
 ],
}

GCP = {
 "title": "GCP Reference Architecture — Global VPC", "legend": True,
 "columns": [
   {"id": "edge", "boundary": {"label": "Edge / Global", "fill": "#FFF8E1", "stroke": "#F9A825"},
    "nodes": [{"id": "dns", "label": "Cloud DNS", "icon": "gcp/dns"}, {"id": "cdn", "label": "Cloud CDN", "icon": "gcp/cdn"}, {"id": "arm", "label": "Cloud Armor", "icon": "gcp/armor"}]},
   {"id": "lb", "boundary": {"label": "Global LB", "fill": "#FBF3E0", "stroke": "#F9A825"},
    "nodes": [{"id": "glb", "label": "Global external LB", "icon": "gcp/load-balancing"}]},
   {"id": "compute", "boundary": {"label": "Region: us-central1", "fill": "#FBE9E7", "stroke": "#D84315"},
    "nodes": [{"id": "run", "label": "Cloud Run", "icon": "gcp/run"}, {"id": "gke", "label": "GKE regional", "icon": "gcp/kubernetes-engine"}]},
   {"id": "data", "boundary": {"label": "Data", "fill": "#E7F0FA", "stroke": "#1E88E5"},
    "nodes": [{"id": "sql", "label": "Cloud SQL primary", "icon": "gcp/sql"}, {"id": "sql2", "label": "read replica", "icon": "gcp/sql"}, {"id": "mem", "label": "Memorystore", "icon": "gcp/memorystore"}]},
   {"id": "msg", "boundary": {"label": "Messaging", "fill": "#F3E5F5", "stroke": "#8E24AA"},
    "nodes": [{"id": "ps", "label": "Pub/Sub", "icon": "gcp/pubsub"}]},
 ],
 "wraps": [{"label": "VPC (global) 10.8.0.0/14", "fill": "#F6F6F6", "stroke": "#4285F4", "dashed": True, "icon": "gcp/virtual-private-cloud", "cols": ["lb", "compute", "data", "msg"]}],
 "shared": {"label": "Shared Services  (project-scoped)", "fill": "#E8F5E9", "stroke": "#34A853",
   "anchor": {"from": "gke", "label": "Cloud IAM / KMS / Ops  (all tiers)"},
   "nodes": [{"id": "iam", "label": "Cloud IAM", "icon": "gcp/iam"}, {"id": "kms", "label": "Cloud KMS", "icon": "gcp/key-management-service"}, {"id": "ops", "label": "Cloud Ops", "icon": "gcp/monitoring"}, {"id": "gcs", "label": "Cloud Storage", "icon": "gcp/storage"}]},
 "edges": [
   {"from": "dns", "to": "cdn"}, {"from": "cdn", "to": "arm"}, {"from": "arm", "to": "glb", "label": "HTTPS"},
   {"from": "glb", "to": "run"}, {"from": "run", "to": "gke", "label": "gRPC"},
   {"from": "gke", "to": "sql", "label": "SQL"}, {"from": "gke", "to": "mem", "label": "cache"},
   {"from": "sql", "to": "sql2", "label": "replication", "style": "dashed", "color": "#2E7D32"},
   {"from": "gke", "to": "ps", "label": "events", "style": "dashed"},
 ],
}

ONPREM = {
 "title": "Hybrid — On-Prem Data Center + AWS", "legend": True,
 "columns": [
   {"id": "net", "boundary": None, "nodes": [{"id": "net", "label": "Internet", "icon": "onprem/internet"}]},
   {"id": "dmz", "boundary": {"label": "DMZ", "fill": "#FDECEA", "stroke": "#DD344C"},
    "nodes": [{"id": "lb", "label": "HAProxy LB", "icon": "onprem/haproxy"}, {"id": "rp", "label": "Reverse proxy", "icon": "onprem/nginx"}]},
   {"id": "app", "boundary": {"label": "App Tier", "fill": "#FBF3E0", "stroke": "#F9A825"},
    "nodes": [{"id": "a1", "label": "App servers x3", "icon": "onprem/server"}]},
   {"id": "dbt", "boundary": {"label": "Data Tier", "fill": "#E7F0FA", "stroke": "#1E88E5"},
    "nodes": [{"id": "db", "label": "Oracle RAC", "icon": "onprem/oracle"}, {"id": "san", "label": "SAN storage", "icon": "onprem/server"}]},
   {"id": "cloud", "boundary": {"label": "VPC", "fill": "#FBE9E7", "stroke": "#8C4FFF", "icon": "aws/vpc"},
    "nodes": [{"id": "eks", "label": "EKS workloads", "icon": "aws/elastic-kubernetes-service"}]},
 ],
 "wraps": [{"label": "On-Premises Data Center", "fill": "#FFFFFF", "stroke": "#607D8B", "cols": ["dmz", "app", "dbt"]},
           {"label": "AWS (ap-southeast-1)", "fill": "#FFFFFF", "stroke": "#8C4FFF", "dashed": True, "cols": ["cloud"]}],
 "edges": [
   {"from": "net", "to": "lb", "label": "HTTPS"}, {"from": "lb", "to": "rp"}, {"from": "rp", "to": "a1"}, {"from": "a1", "to": "db", "label": "SQL"}, {"from": "db", "to": "san"},
   {"from": "a1", "to": "eks", "label": "Direct Connect"}, {"from": "a1", "to": "eks", "label": "VPN (failover)", "style": "dashed"},
 ],
}

K8S = {
 "title": "Kubernetes Architecture — Control Plane + Workload", "legend": True,
 "columns": [
   {"id": "ing", "boundary": {"label": "Ingress", "fill": "#FBF3E0", "stroke": "#F9A825"},
    "nodes": [{"id": "ing", "label": "Ingress", "icon": "k8s/ing"}]},
   {"id": "svc", "boundary": {"label": "Service", "fill": "#E8F1FB", "stroke": "#326CE5"},
    "nodes": [{"id": "svc", "label": "Service (ClusterIP)", "icon": "k8s/svc"}]},
   {"id": "dep", "boundary": {"label": "Deployment: web (HPA 3-10)", "fill": "#FBE9E7", "stroke": "#D84315"},
    "nodes": [{"id": "pod", "label": "Pod x3", "icon": "k8s/pod"}, {"id": "hpa", "label": "HPA", "icon": "k8s/hpa"}]},
   {"id": "sts", "boundary": {"label": "StatefulSet: db", "fill": "#E7F0FA", "stroke": "#1E88E5"},
    "nodes": [{"id": "db", "label": "db", "icon": "k8s/sts"}, {"id": "pvc", "label": "PVC", "icon": "k8s/pvc"}, {"id": "pv", "label": "PV", "icon": "k8s/pv"}]},
 ],
 "wraps": [{"label": "Kubernetes Cluster — Namespace: app", "fill": "#FFFFFF", "stroke": "#326CE5", "dashed": True, "icon": "k8s/ns", "cols": ["ing", "svc", "dep", "sts"]}],
 "shared": {"label": "Control Plane (HA) + Config", "fill": "#E3F2FD", "stroke": "#1565C0",
   "anchor": {"from": "svc", "label": "kube-apiserver / ConfigMap / Secret  (cluster-wide)"},
   "nodes": [{"id": "api", "label": "kube-apiserver", "icon": "k8s/api"}, {"id": "etcd", "label": "etcd", "icon": "k8s/etcd"}, {"id": "cm", "label": "ConfigMap", "icon": "k8s/cm"}, {"id": "sec", "label": "Secret", "icon": "k8s/secret"}]},
 "edges": [
   {"from": "ing", "to": "svc", "label": "HTTP"}, {"from": "svc", "to": "pod", "label": "LB"}, {"from": "hpa", "to": "pod", "label": "scale", "style": "dashed"},
   {"from": "pod", "to": "db", "label": "SQL"}, {"from": "db", "to": "pvc"}, {"from": "pvc", "to": "pv"},
 ],
}

DOCKER = {
 "title": "Docker Compose — Multi-Service App", "legend": True,
 "columns": [
   {"id": "proxy", "boundary": None, "nodes": [{"id": "rp", "label": "nginx :443", "icon": "onprem/nginx"}]},
   {"id": "app", "boundary": {"label": "frontend network", "fill": "#E8F1FB", "stroke": "#1E88E5"},
    "nodes": [{"id": "api", "label": "api :3000", "icon": "onprem/docker"}, {"id": "web", "label": "web :80", "icon": "onprem/docker"}]},
   {"id": "wk", "boundary": {"label": "worker network", "fill": "#F3E5F5", "stroke": "#8E24AA"},
    "nodes": [{"id": "worker", "label": "worker", "icon": "onprem/docker"}, {"id": "mq", "label": "RabbitMQ", "icon": "onprem/rabbitmq"}]},
   {"id": "data", "boundary": {"label": "data network (volumes)", "fill": "#E7F0FA", "stroke": "#00897B"},
    "nodes": [{"id": "pg", "label": "postgres (vol)", "icon": "onprem/postgresql"}, {"id": "redis", "label": "redis (vol)", "icon": "onprem/redis"}]},
 ],
 "edges": [
   {"from": "rp", "to": "api", "label": "/api"}, {"from": "rp", "to": "web", "label": "/"},
   {"from": "api", "to": "pg", "label": "SQL"}, {"from": "api", "to": "redis", "label": "cache"},
   {"from": "api", "to": "mq", "label": "jobs", "style": "dashed"}, {"from": "mq", "to": "worker", "style": "dashed"}, {"from": "worker", "to": "pg"},
 ],
}

CICD = {
 "title": "CI/CD Pipeline — Commit to Production", "legend": True,
 "columns": [
   {"id": "src", "boundary": {"label": "Source", "fill": "#FFF8E1", "stroke": "#F9A825"}, "nodes": [{"id": "dev", "label": "app repo (Git)", "icon": "onprem/github"}]},
   {"id": "ci", "boundary": {"label": "CI (runner)", "fill": "#E8F1FB", "stroke": "#1E88E5"}, "nodes": [{"id": "ci", "label": "build + test + scan", "icon": "onprem/github-actions"}]},
   {"id": "reg", "boundary": {"label": "Registry", "fill": "#FBF3E0", "stroke": "#F9A825"}, "nodes": [{"id": "reg", "label": "Amazon ECR", "icon": "aws/ec2-container-registry"}, {"id": "cfg", "label": "config repo", "icon": "onprem/github"}]},
   {"id": "cd", "boundary": {"label": "CD", "fill": "#FBE9E7", "stroke": "#D84315"}, "nodes": [{"id": "argo", "label": "Argo CD", "icon": "onprem/argocd"}]},
   {"id": "prod", "boundary": {"label": "Runtime", "fill": "#E7F0FA", "stroke": "#1E88E5"}, "nodes": [{"id": "dep", "label": "EKS blue/green", "icon": "aws/elastic-kubernetes-service"}]},
 ],
 "wraps": [{"label": "Kubernetes Cluster", "fill": "#FFFFFF", "stroke": "#326CE5", "icon": "k8s/k8s", "cols": ["cd", "prod"]}],
 "edges": [{"from": "dev", "to": "ci"}, {"from": "ci", "to": "reg", "label": "push image"}, {"from": "ci", "to": "cfg", "label": "write tag"}, {"from": "argo", "to": "cfg", "label": "pull / reconcile", "style": "dashed"}, {"from": "reg", "to": "argo"}, {"from": "argo", "to": "dep", "label": "apply"}],
}

DATA_PIPELINE = {
 "title": "Data Pipeline — Batch + Streaming Lineage", "legend": True,
 "columns": [
   {"id": "src", "boundary": {"label": "Source", "fill": "#FFF8E1", "stroke": "#F9A825"}, "nodes": [{"id": "src", "label": "PostgreSQL OLTP", "icon": "onprem/postgresql"}]},
   {"id": "ing", "boundary": {"label": "Ingest (stream)", "fill": "#F3E5F5", "stroke": "#8E24AA"}, "nodes": [{"id": "k", "label": "Kafka CDC", "icon": "onprem/kafka"}]},
   {"id": "tx", "boundary": {"label": "Transform", "fill": "#E8F1FB", "stroke": "#1E88E5"}, "nodes": [{"id": "sp", "label": "Spark ETL", "icon": "onprem/spark"}]},
   {"id": "store", "boundary": {"label": "Lake / Warehouse", "fill": "#E7F0FA", "stroke": "#00897B"}, "nodes": [{"id": "lake", "label": "S3 lake", "icon": "aws/simple-storage-service"}, {"id": "wh", "label": "Redshift", "icon": "aws/redshift"}]},
   {"id": "serve", "boundary": {"label": "Serve", "fill": "#E8F5E9", "stroke": "#43A047"}, "nodes": [{"id": "bi", "label": "QuickSight BI", "icon": "aws/quicksight"}]},
 ],
 "edges": [{"from": "src", "to": "k", "label": "CDC", "style": "dashed"}, {"from": "k", "to": "sp", "label": "stream"}, {"from": "sp", "to": "lake", "label": "curate"}, {"from": "lake", "to": "wh", "label": "load"}, {"from": "wh", "to": "bi", "label": "query"}],
}

GITOPS = {
 "title": "GitOps — Argo CD Pull / Reconcile", "legend": True,
 "columns": [
   {"id": "src", "boundary": {"label": "Source", "fill": "#FFF8E1", "stroke": "#F9A825"}, "nodes": [{"id": "app", "label": "app repo", "icon": "onprem/github"}, {"id": "cfg", "label": "config repo", "icon": "onprem/github"}]},
   {"id": "ci", "boundary": {"label": "CI", "fill": "#E8F1FB", "stroke": "#1E88E5"}, "nodes": [{"id": "ci", "label": "build + test", "icon": "onprem/github-actions"}]},
   {"id": "reg", "boundary": {"label": "Registry", "fill": "#FBF3E0", "stroke": "#F9A825"}, "nodes": [{"id": "reg", "label": "Registry", "icon": "onprem/docker"}]},
   {"id": "cluster", "boundary": {"label": "Kubernetes Cluster", "fill": "#FFFFFF", "stroke": "#326CE5", "icon": "k8s/k8s"}, "nodes": [{"id": "argo", "label": "Argo CD", "icon": "onprem/argocd"}, {"id": "dep", "label": "Deployment (blue/green)", "icon": "aws/elastic-kubernetes-service"}]},
 ],
 "edges": [{"from": "app", "to": "ci"}, {"from": "ci", "to": "reg", "label": "push image"}, {"from": "ci", "to": "cfg", "label": "write tag"}, {"from": "argo", "to": "cfg", "label": "pull / reconcile", "style": "dashed"}, {"from": "reg", "to": "argo"}, {"from": "argo", "to": "dep", "label": "apply"}],
}

MICROSERVICES = {
 "title": "Microservices Decomposition — Bounded Contexts", "legend": True,
 "columns": [
   {"id": "cl", "boundary": None, "nodes": [{"id": "cl", "label": "Web / Mobile", "icon": "onprem/client"}]},
   {"id": "gw", "boundary": {"label": "API Gateway", "fill": "#FFF8E1", "stroke": "#F9A825"}, "nodes": [{"id": "gw", "label": "Gateway (BFF)", "icon": "onprem/nginx"}]},
   {"id": "users", "boundary": {"label": "Users Context", "fill": "#E8F1FB", "stroke": "#1E88E5"}, "nodes": [{"id": "us", "label": "Users (.NET)", "icon": "programming/csharp"}, {"id": "ud", "label": "Users DB", "icon": "onprem/postgresql"}]},
   {"id": "orders", "boundary": {"label": "Orders Context", "fill": "#FBF3E0", "stroke": "#F9A825"}, "nodes": [{"id": "os", "label": "Orders (.NET)", "icon": "programming/csharp"}, {"id": "od", "label": "Orders DB", "icon": "onprem/postgresql"}]},
   {"id": "pay", "boundary": {"label": "Payments Context", "fill": "#FDECEA", "stroke": "#DD344C"}, "nodes": [{"id": "ps", "label": "Payments (Go)", "icon": "programming/go"}, {"id": "pd", "label": "Payments DB", "icon": "onprem/postgresql"}]},
   {"id": "msg", "boundary": {"label": "Messaging", "fill": "#F3E5F5", "stroke": "#8E24AA"}, "nodes": [{"id": "bus", "label": "Kafka / MSK", "icon": "onprem/kafka"}]},
 ],
 "edges": [{"from": "cl", "to": "gw", "label": "HTTPS"}, {"from": "gw", "to": "us", "label": "REST"}, {"from": "gw", "to": "os", "label": "REST"},
   {"from": "us", "to": "ud"}, {"from": "os", "to": "od"}, {"from": "ps", "to": "pd"},
   {"from": "os", "to": "bus", "label": "OrderPlaced", "style": "dashed"}, {"from": "bus", "to": "ps", "label": "OrderPlaced", "style": "dashed"}, {"from": "ps", "to": "bus", "label": "PaymentSettled", "style": "dashed"}],
}

C4_CONTAINER = {
 "title": "Container Diagram — Internet Banking", "legend": True,
 "columns": [
   {"id": "cust", "boundary": None, "nodes": [{"id": "cust", "label": "Customer", "icon": "onprem/client"}]},
   {"id": "spa", "boundary": None, "nodes": [{"id": "spa", "label": "SPA (React)", "icon": "programming/react"}]},
   {"id": "api", "boundary": None, "nodes": [{"id": "api", "label": "API (.NET 8)", "icon": "programming/csharp"}]},
   {"id": "db", "boundary": None, "nodes": [{"id": "db", "label": "Database", "icon": "onprem/postgresql"}]},
   {"id": "ext", "boundary": None, "nodes": [{"id": "mail", "label": "Email (SendGrid)", "icon": "onprem/server"}, {"id": "core", "label": "Mainframe", "icon": "onprem/server"}]},
 ],
 "wraps": [{"label": "Internet Banking System", "fill": "#FFFFFF", "stroke": "#1565C0", "cols": ["spa", "api", "db"]}],
 "edges": [{"from": "cust", "to": "spa", "label": "HTTPS"}, {"from": "spa", "to": "api", "label": "JSON/HTTPS"}, {"from": "api", "to": "db", "label": "SQL/TLS"}, {"from": "api", "to": "mail", "label": "send email", "style": "dashed"}, {"from": "api", "to": "core", "label": "accounts [XML]"}],
}

UML_DEPLOYMENT = {
 "title": "Deployment Diagram — Web App",
 "columns": [
   {"id": "cl", "boundary": None, "nodes": [{"id": "cl", "label": "Client Device", "icon": "onprem/client"}]},
   {"id": "web", "boundary": {"label": "Web Server", "fill": "#FBF3E0", "stroke": "#F9A825"}, "nodes": [{"id": "web", "label": "nginx", "icon": "onprem/nginx"}]},
   {"id": "app", "boundary": {"label": "App Server", "fill": "#E8F1FB", "stroke": "#1E88E5"}, "nodes": [{"id": "app", "label": "Node.js", "icon": "onprem/server"}]},
   {"id": "db", "boundary": {"label": "DB Server", "fill": "#E7F0FA", "stroke": "#00897B"}, "nodes": [{"id": "db", "label": "PostgreSQL", "icon": "onprem/postgresql"}]},
 ],
 "edges": [{"from": "cl", "to": "web", "label": "HTTPS"}, {"from": "web", "to": "app", "label": "reverse proxy"}, {"from": "app", "to": "db", "label": "TCP 5432"}],
}

AI_RAG = {
 "title": "AI RAG + Multi-Model Gateway", "legend": True,
 "columns": [
   {"id": "user", "boundary": None, "nodes": [{"id": "user", "label": "User", "icon": "onprem/users"}]},
   {"id": "app", "boundary": None, "nodes": [{"id": "app", "label": "Chat App / API", "icon": "onprem/server"}]},
   {"id": "orch", "boundary": {"label": "Orchestration", "fill": "#FFF8E1", "stroke": "#F9A825"}, "nodes": [{"id": "orch", "label": "LangChain", "icon": "ai/langchain"}]},
   {"id": "models", "boundary": {"label": "Model providers", "fill": "#E8F1FB", "stroke": "#1E88E5"},
    "nodes": [{"id": "oai", "label": "OpenAI", "icon": "ai/openai"}, {"id": "cl", "label": "Claude", "icon": "ai/claude"}, {"id": "gm", "label": "Gemini", "icon": "ai/gemini"}, {"id": "dsk", "label": "DeepSeek", "icon": "ai/deepseek"}]},
   {"id": "rag", "boundary": {"label": "Retrieval", "fill": "#E8F5E9", "stroke": "#43A047"},
    "nodes": [{"id": "emb", "label": "Embeddings", "icon": "ai/huggingface"}, {"id": "vdb", "label": "Qdrant vector DB", "icon": "ai/qdrant"}]},
 ],
 "edges": [{"from": "user", "to": "app", "label": "prompt"}, {"from": "app", "to": "orch"},
   {"from": "orch", "to": "oai", "label": "route"}, {"from": "orch", "to": "cl"}, {"from": "orch", "to": "gm"}, {"from": "orch", "to": "dsk"},
   {"from": "app", "to": "emb", "label": "embed"}, {"from": "emb", "to": "vdb", "label": "search"}, {"from": "vdb", "to": "orch", "label": "context", "style": "dashed"}],
}

SPECS = {"aws_ref": AWS, "azure_ref": AZURE, "gcp_ref": GCP, "onprem_hybrid": ONPREM, "k8s_topology": K8S,
         "docker_compose": DOCKER, "cicd": CICD, "data_pipeline": DATA_PIPELINE, "gitops": GITOPS,
         "microservices": MICROSERVICES, "c4_container": C4_CONTAINER, "uml_deployment": UML_DEPLOYMENT, "ai_rag": AI_RAG}
