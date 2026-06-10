"""Emit a draw.io (diagrams.net) XML file for the same logical diagram the
Phase-4 agent rendered as PNG. The output `.drawio` file:

  • opens in app.diagrams.net or the desktop draw.io app,
  • is fully editable (drag boxes, change labels, reroute arrows),
  • carries clusters as drawio "container" groups so structural grouping
    is preserved,
  • renders AWS / Azure / GCP shapes when a `shape` hint is provided,
    otherwise falls back to a labelled rounded rectangle.

Designed to be called by Agent A right after each PNG is rendered, with
the same node/edge data the diagrams DSL was driven from. The user can
then ship the PNG to the client and keep the `.drawio` source for
later edits — no Python knowledge required.
"""
from __future__ import annotations

import html
from pathlib import Path
from xml.sax.saxutils import escape


# Map common shape hints to draw.io style strings.
#
# Stencil conventions (verified against jgraph/drawio @ dev, May 2026):
#   - AWS4 services live under `shape=mxgraph.aws4.<name>` AND require
#     `aspect=fixed` plus AWS-orange fill so the stencil binds correctly.
#     Without `aspect=fixed` drawio falls back to an empty rectangle.
#   - Azure shapes are NOT mxgraph stencils — they are SVG image refs
#     under `img/lib/azure2/<group>/<Name>.svg`. The legacy
#     `mxgraph.azure.*` namespace does not contain modern services
#     (no kubernetes_services, no sql_database) — that is what caused
#     the original "empty boxes" bug.
#   - GCP shapes use the `gcp2` namespace (flat), not the legacy
#     `gcp.compute.*` / `gcp.databases.*` nested paths.
#   - Kubernetes shapes share a single stencil `mxgraph.kubernetes.icon2`
#     and select the glyph via a `prIcon=` attribute.
_AWS_FILL = "fillColor=#E7157B;strokeColor=#ffffff;"  # AWS database/storage magenta; drawio overrides per-service
_AWS_BASE = "sketch=0;outlineConnect=0;fontColor=#232F3E;dashed=0;verticalLabelPosition=bottom;verticalAlign=top;align=center;html=1;fontSize=12;fontStyle=0;aspect=fixed;"
_AZURE_BASE = "image;aspect=fixed;html=1;points=[];align=center;fontSize=12;labelPosition=center;verticalLabelPosition=bottom;verticalAlign=top;"
_GCP_BASE = "sketch=0;html=1;aspect=fixed;strokeColor=none;shadow=0;dashed=0;verticalLabelPosition=bottom;labelPosition=center;verticalAlign=top;align=center;fillColor=#4284F3;"
_K8S_BASE = "aspect=fixed;sketch=0;html=1;dashed=0;whitespace=wrap;verticalLabelPosition=bottom;verticalAlign=top;fillColor=#326CE5;strokeColor=#ffffff;"


def _aws(stencil: str, color: str = "#E7157B") -> str:
    """Build an AWS4 style string with the required attributes."""
    return f"{_AWS_BASE}fillColor={color};strokeColor=#ffffff;shape=mxgraph.aws4.{stencil};"


def _azure(svg_path: str) -> str:
    """Build an Azure2 image style string. svg_path is relative to img/lib/azure2/."""
    return f"{_AZURE_BASE}image=img/lib/azure2/{svg_path};"


def _gcp(stencil: str, color: str = "#4284F3") -> str:
    """Build a GCP2 style string."""
    return f"{_GCP_BASE.replace('#4284F3', color)}shape=mxgraph.gcp2.{stencil};"


def _k8s(pr_icon: str) -> str:
    """Build a Kubernetes style string. pr_icon: pod, svc, deploy, ing, ns, etc."""
    return f"{_K8S_BASE}shape=mxgraph.kubernetes.icon2;prIcon={pr_icon};"


SHAPE_STYLES = {
    # AWS — colors per AWS architecture-icons palette: compute orange, db magenta, storage green, net purple, ml teal
    "aws-eks":            _aws("eks", "#ED7100"),
    "aws-ec2":            _aws("ec2", "#ED7100"),
    "aws-ecs":            _aws("ecs", "#ED7100"),
    "aws-fargate":        _aws("fargate", "#ED7100"),
    "aws-lambda":         _aws("lambda", "#ED7100"),
    "aws-aurora":         _aws("aurora", "#C925D1"),
    "aws-rds":            _aws("rds", "#C925D1"),
    "aws-dynamodb":       _aws("dynamodb", "#C925D1"),
    "aws-redis":          _aws("elasticache", "#C925D1"),
    "aws-msk":            _aws("managed_streaming_for_apache_kafka", "#C925D1"),
    "aws-sqs":            _aws("simple_queue_service", "#E7157B"),
    "aws-sns":            _aws("simple_notification_service", "#E7157B"),
    "aws-s3":             _aws("simple_storage_service", "#7AA116"),
    "aws-glacier":        _aws("s3_glacier", "#7AA116"),
    "aws-cloudfront":     _aws("cloudfront", "#8C4FFF"),
    "aws-api-gateway":    _aws("api_gateway", "#FF4F8B"),
    "aws-alb":            _aws("application_load_balancer", "#8C4FFF"),
    "aws-nlb":            _aws("network_load_balancer", "#8C4FFF"),
    "aws-route53":        _aws("route_53", "#8C4FFF"),
    "aws-cognito":        _aws("cognito", "#DD344C"),
    "aws-iam":            _aws("identity_and_access_management", "#DD344C"),
    "aws-kms":            _aws("key_management_service", "#DD344C"),
    "aws-secrets":        _aws("secrets_manager", "#DD344C"),
    "aws-vpc":            _aws("vpc", "#8C4FFF"),
    "aws-waf":            _aws("waf", "#DD344C"),
    "aws-cloudwatch":     _aws("cloudwatch", "#E7157B"),
    "aws-cloudtrail":     _aws("cloudtrail", "#DD344C"),
    "aws-eventbridge":    _aws("eventbridge", "#E7157B"),
    "aws-stepfunctions":  _aws("step_functions", "#E7157B"),
    "aws-codebuild":      _aws("codebuild", "#C925D1"),
    "aws-codepipeline":   _aws("codepipeline", "#C925D1"),
    "aws-ecr":            _aws("elastic_container_registry", "#ED7100"),

    # Azure — image-based SVG refs (paths verified against drawio's azure2 sidebar)
    "azure-vm":               _azure("compute/Virtual_Machine.svg"),
    "azure-aks":              _azure("compute/Kubernetes_Services.svg"),
    "azure-app-service":      _azure("app_services/App_Services.svg"),
    "azure-functions":        _azure("compute/Function_Apps.svg"),
    "azure-front-door":       _azure("networking/Front_Doors.svg"),
    "azure-app-gateway":      _azure("networking/Application_Gateways.svg"),
    "azure-api-management":   _azure("app_services/API_Management_Services.svg"),
    "azure-sql":              _azure("databases/SQL_Database.svg"),
    "azure-postgres":         _azure("databases/Azure_Database_PostgreSQL_Server.svg"),
    "azure-mysql":            _azure("databases/Azure_Database_MySQL_Server.svg"),
    "azure-cosmos":           _azure("databases/Azure_Cosmos_DB.svg"),
    "azure-redis":            _azure("databases/Cache_Redis.svg"),
    "azure-service-bus":      _azure("integration/Service_Bus.svg"),
    "azure-event-hub":        _azure("analytics/Event_Hubs.svg"),
    "azure-event-grid":       _azure("integration/Event_Grid_Subscriptions.svg"),
    "azure-storage":          _azure("storage/Storage_Accounts.svg"),
    "azure-blob":             _azure("storage/Storage_Accounts.svg"),
    "azure-keyvault":         _azure("security/Key_Vaults.svg"),
    "azure-entra":            _azure("identity/Azure_Active_Directory.svg"),
    "azure-monitor":          _azure("monitor/Monitor.svg"),
    "azure-devops":           _azure("devops/Azure_DevOps.svg"),
    "azure-container-reg":    _azure("containers/Container_Registries.svg"),
    "azure-cdn":              _azure("networking/CDN_Profiles.svg"),
    "azure-firewall":         _azure("networking/Firewalls.svg"),
    "azure-waf":              _azure("networking/Web_Application_Firewall_Policies(WAF).svg"),

    # GCP — gcp2 namespace (verified against drawio sidebar)
    "gcp-gke":            _gcp("kubernetes_engine"),
    "gcp-gce":            _gcp("compute_engine"),
    "gcp-cloud-run":      _gcp("cloud_run"),
    "gcp-cloud-functions":_gcp("cloud_functions"),
    "gcp-sql":            _gcp("cloud_sql"),
    "gcp-spanner":        _gcp("cloud_spanner"),
    "gcp-firestore":      _gcp("firestore"),
    "gcp-bigtable":       _gcp("cloud_bigtable"),
    "gcp-pubsub":         _gcp("cloud_pub_sub"),
    "gcp-gcs":            _gcp("cloud_storage"),
    "gcp-load-balancing": _gcp("cloud_load_balancing"),
    "gcp-cloud-cdn":      _gcp("cloud_cdn"),
    "gcp-iam":            _gcp("identity_and_access_management"),
    "gcp-kms":            _gcp("key_management_service"),

    # Kubernetes (on-prem / vendor-neutral)
    "k8s-pod":            _k8s("pod"),
    "k8s-deploy":         _k8s("deploy"),
    "k8s-svc":            _k8s("svc"),
    "k8s-ing":            _k8s("ing"),
    "k8s-ns":             _k8s("ns"),
    "k8s-cm":             _k8s("cm"),
    "k8s-secret":         _k8s("secret"),
    "k8s-statefulset":    _k8s("sts"),
    "k8s-daemonset":      _k8s("ds"),
    "k8s-job":            _k8s("job"),
    "k8s-cronjob":        _k8s("cronjob"),
    "k8s-node":           _k8s("node"),

    # Generic
    "user":     "shape=mxgraph.networks.user;sketch=0;html=1;aspect=fixed;",
    "users":    "shape=mxgraph.networks.user;sketch=0;html=1;aspect=fixed;",
    "mobile":   "shape=mxgraph.android.phone2;sketch=0;html=1;aspect=fixed;",
    "client":   "shape=mxgraph.networks.user;sketch=0;html=1;aspect=fixed;",
    "browser":  "shape=mxgraph.networks.pc;sketch=0;html=1;aspect=fixed;",
    "server":   "shape=mxgraph.servers.application_server;sketch=0;html=1;aspect=fixed;",
    "database": "shape=cylinder3;whiteSpace=wrap;html=1;boundedLbl=1;backgroundOutline=1;size=15;",
    "firewall": "shape=mxgraph.networks.firewall;sketch=0;html=1;aspect=fixed;",
    "router":   "shape=mxgraph.networks.router;sketch=0;html=1;aspect=fixed;",
    "switch":   "shape=mxgraph.networks.switch;sketch=0;html=1;aspect=fixed;",
    "internet": "shape=mxgraph.networks.cloud;sketch=0;html=1;aspect=fixed;",
    "cloud":    "ellipse;shape=cloud;whiteSpace=wrap;html=1;",
}

DEFAULT_NODE_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=#f5f5f5;strokeColor=#666666;"
    "fontSize=12;align=center;"
)
CLUSTER_STYLE = (
    "rounded=1;whiteSpace=wrap;html=1;fillColor=none;strokeColor=#888888;"
    "dashed=1;verticalAlign=top;fontSize=12;fontStyle=1;"
)
EDGE_STYLE = (
    "edgeStyle=orthogonalEdgeStyle;rounded=0;orthogonalLoop=1;jettySize=auto;"
    "html=1;exitX=0.5;exitY=1;exitDx=0;exitDy=0;entryX=0.5;entryY=0;"
    "entryDx=0;entryDy=0;"
)
EDGE_STYLE_DASHED = EDGE_STYLE + "dashed=1;"


def _node_style(shape: str | None) -> str:
    if shape and shape in SHAPE_STYLES:
        return SHAPE_STYLES[shape]
    return DEFAULT_NODE_STYLE


def _validate_style(style: str, shape_hint: str | None) -> None:
    """Sanity-check that styles destined for a stencil actually bind to one.

    Raised early so a broken SHAPE_STYLES entry surfaces on first use rather
    than as silent empty rectangles in the user's drawio file.
    """
    if not shape_hint or shape_hint not in SHAPE_STYLES:
        return
    if shape_hint.startswith("azure-"):
        if "image=img/lib/azure2/" not in style:
            raise ValueError(
                f"Azure shape '{shape_hint}' must bind via image=img/lib/azure2/...svg "
                f"(legacy mxgraph.azure.* stencils do not contain modern services). "
                f"Got: {style!r}"
            )
        return
    if "shape=" not in style:
        raise ValueError(
            f"Shape '{shape_hint}' has no `shape=` binding in its style: {style!r}"
        )


def export_drawio(
    nodes: list[dict],
    edges: list[dict],
    clusters: list[dict] | None = None,
    out_path: str | Path = "diagram.drawio",
    title: str = "Diagram",
) -> Path:
    """Write a draw.io XML file representing the diagram.

    Args:
        nodes:     [{id, label, x, y, [width, height, shape]}]
        edges:     [{from, to, [label, dashed]}]
        clusters:  [{id, label, members, [x, y, width, height]}]
        out_path:  where to write the .drawio file
        title:     diagram tab title

    Returns the Path of the written file. Geometries default to a tidy grid
    if the caller didn't supply explicit coordinates.
    """
    out_path = Path(out_path)
    clusters = clusters or []

    # Auto-layout: if any node has no x/y, lay nodes out left-to-right.
    if any("x" not in n or "y" not in n for n in nodes):
        for i, n in enumerate(nodes):
            n.setdefault("x", 40 + (i % 5) * 200)
            n.setdefault("y", 40 + (i // 5) * 150)

    cells = []
    cell_id = 2  # 0 and 1 are reserved by drawio

    # Cluster (group) cells first so node cells can reference them as parent.
    cluster_ids: dict[str, int] = {}
    for c in clusters:
        members = [n for n in nodes if n["id"] in c.get("members", [])]
        if not members:
            continue
        xs = [n["x"] for n in members]
        ys = [n["y"] for n in members]
        ws = [n.get("width", 120) for n in members]
        hs = [n.get("height", 80) for n in members]
        cx = min(xs) - 30
        cy = min(ys) - 50
        cw = max(x + w for x, w in zip(xs, ws)) - cx + 30
        ch = max(y + h for y, h in zip(ys, hs)) - cy + 30
        cluster_id = cell_id
        cluster_ids[c["id"]] = cluster_id
        cells.append(
            f'<mxCell id="{cluster_id}" value="{escape(c.get("label",""))}" '
            f'style="{CLUSTER_STYLE}" vertex="1" parent="1">'
            f'<mxGeometry x="{int(cx)}" y="{int(cy)}" '
            f'width="{int(cw)}" height="{int(ch)}" as="geometry"/></mxCell>'
        )
        cell_id += 1

    # Node cells
    node_ids: dict[str, int] = {}
    for n in nodes:
        nid = cell_id
        node_ids[n["id"]] = nid
        # Find parent (cluster) if this node belongs to one
        parent = "1"
        for c in clusters:
            if n["id"] in c.get("members", []) and c["id"] in cluster_ids:
                parent = str(cluster_ids[c["id"]])
                break
        shape_hint = n.get("shape")
        style = _node_style(shape_hint)
        _validate_style(style, shape_hint)
        cells.append(
            f'<mxCell id="{nid}" value="{escape(n.get("label",""))}" '
            f'style="{style}" vertex="1" parent="{parent}">'
            f'<mxGeometry x="{int(n["x"])}" y="{int(n["y"])}" '
            f'width="{int(n.get("width",120))}" height="{int(n.get("height",80))}" as="geometry"/></mxCell>'
        )
        cell_id += 1

    # Edges
    for e in edges:
        src = node_ids.get(e["from"])
        dst = node_ids.get(e["to"])
        if src is None or dst is None:
            continue
        style = EDGE_STYLE_DASHED if e.get("dashed") else EDGE_STYLE
        cells.append(
            f'<mxCell id="{cell_id}" value="{escape(e.get("label",""))}" '
            f'style="{style}" edge="1" parent="1" '
            f'source="{src}" target="{dst}">'
            f'<mxGeometry relative="1" as="geometry"/></mxCell>'
        )
        cell_id += 1

    xml = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<mxfile host="app.diagrams.net" version="24.0">\n'
        f'  <diagram name="{escape(title)}" id="diagram-1">\n'
        f'    <mxGraphModel dx="1200" dy="800" grid="1" gridSize="10" guides="1" '
        f'tooltips="1" connect="1" arrows="1" fold="1" page="1" pageScale="1" '
        f'pageWidth="1100" pageHeight="850" math="0" shadow="0">\n'
        f'      <root>\n'
        f'        <mxCell id="0"/>\n'
        f'        <mxCell id="1" parent="0"/>\n'
        + "\n".join("        " + c for c in cells) + "\n"
        f'      </root>\n'
        f'    </mxGraphModel>\n'
        f'  </diagram>\n'
        f'</mxfile>\n'
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")
    return out_path
