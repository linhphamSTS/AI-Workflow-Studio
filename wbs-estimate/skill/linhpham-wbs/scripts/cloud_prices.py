#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull real list prices for a cloud region, deterministically.

    python cloud_prices.py --provider aws   --region me-central-1 --out prices.json
    python cloud_prices.py --provider azure --region uaenorth     --out prices.json
    python cloud_prices.py --provider azure --region uaenorth --probe
    python cloud_prices.py --provider aws --region me-central-1 --probe
    python cloud_prices.py --provider aws --region me-central-1 \
           --dump AmazonRDS --filter "Aurora PostgreSQL" --cols "Instance Type,Deployment Option,usageType"

Why this exists rather than a web search or a page fetch:

  * Two reads of the same AWS pricing JSON through a summarising model returned two
    different prices for the same instance type, and both were wrong. A large file read
    by a model is not a source.
  * Search results give a region-less headline price. Regional prices differ by 20% or
    more, and a residency requirement usually fixes the region.

So this streams the vendor's own CSV offer file and parses it exactly. Nothing is
inferred, nothing is scaled from another region, and every figure carries the usageType
it came from so a line in the estimate can be traced back.

**Filter on attributes, never on a substring of the file.** The same instance type
appears many times: Aurora Standard versus I/O-Optimized, Redis versus Valkey versus
Memcached, extended-support years. A loose filter silently keeps whichever row came last.
Use `--dump` to see every variant with the columns that distinguish them, then choose.
"""
import argparse
import csv
import json
import os
import sys
import urllib.request
from datetime import date

AWS_BASE = "https://pricing.us-east-1.amazonaws.com"
UA = {"User-Agent": "Mozilla/5.0 (cost-estimation)"}
CACHE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".pricecache")


def _get(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def aws_region_urls(region, services):
    """service code -> the regional offer URL, for services present in that region."""
    index = json.loads(_get(f"{AWS_BASE}/offers/v1.0/aws/index.json"))
    offers, out, absent = index["offers"], {}, []
    for code in services:
        offer = offers.get(code)
        if not offer:
            absent.append(f"{code} (not published)")
            continue
        regions = json.loads(_get(AWS_BASE + offer["currentRegionIndexUrl"]))["regions"]
        entry = regions.get(region)
        if entry:
            out[code] = AWS_BASE + "/" + entry["currentVersionUrl"].lstrip("/")
        else:
            absent.append(f"{code} (no {region})")
    return out, absent


def rows(service, url):
    """Stream the CSV offer. Cached on disk; the files are large and immutable per version."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, service + ".csv")
    if not os.path.exists(path):
        print(f"  downloading {service} ...", file=sys.stderr, flush=True)
        req = urllib.request.Request(url.replace("index.json", "index.csv"), headers=UA)
        with urllib.request.urlopen(req, timeout=900) as resp, open(path, "wb") as fh:
            while True:
                chunk = resp.read(1 << 20)
                if not chunk:
                    break
                fh.write(chunk)
    with open(path, "r", encoding="utf-8", newline="") as fh:
        for _ in range(5):          # the bulk CSV has five preamble lines
            fh.readline()
        for row in csv.DictReader(fh):
            yield row


# Services worth pulling for a typical platform estimate. NAT Gateway lives under
# AmazonEC2, not AmazonVPC, which costs an hour to discover the first time. CloudFront has
# no regional index at all: it is priced by edge location, not by origin region.
DEFAULT_SERVICES = [
    "AmazonEC2", "AmazonRDS", "AmazonElastiCache", "AmazonS3", "AWSELB", "AmazonEKS",
    "AmazonMSK", "AmazonES", "AmazonVPC", "AWSSecretsManager", "awskms",
    "AmazonCloudWatch", "AmazonSNS", "AmazonSES", "AmazonBedrock", "AWSDataTransfer",
    "AmazonApiGateway", "AmazonRoute53",
]


def probe(region):
    urls, absent = aws_region_urls(region, DEFAULT_SERVICES)
    print(f"region {region}: {len(urls)} service(s) available")
    for code in sorted(urls):
        print(f"  {code}")
    if absent:
        print("absent:")
        for a in absent:
            print(f"  {a}")
    return urls


def dump(region, service, needle, cols, limit):
    """Every variant matching `needle`, with the columns that tell them apart."""
    urls, _ = aws_region_urls(region, [service])
    if service not in urls:
        sys.exit(f"! {service} has no offer in {region}")
    cols = [c.strip() for c in cols.split(",") if c.strip()]
    seen, n = set(), 0
    for row in rows(service, urls[service]):
        blob = " ".join(str(v) for v in row.values())
        if needle and needle.lower() not in blob.lower():
            continue
        if row.get("TermType") != "OnDemand":
            continue
        key = tuple(row.get(c, "") for c in cols) + (row.get("PricePerUnit"),)
        if key in seen:
            continue
        seen.add(key)
        print("  %14s /%-14s %s" % (
            row.get("PricePerUnit"), row.get("Unit"),
            "  ".join(f"{c}={row.get(c, '')!r}" for c in cols)))
        n += 1
        if n >= limit:
            print("   ... truncated, narrow the filter")
            break
    if not n:
        print("  no matching on-demand rows")


def reserved_table(region, types):
    """Reserved discount versus on-demand, per term and purchase option.

    The percentages are read from the price list, not quoted from memory, because they
    differ by region and by instance family and a bid should not carry a remembered number.
    """
    urls, _ = aws_region_urls(region, ["AmazonEC2"])
    od, ri = {}, {}
    for row in rows("AmazonEC2", urls["AmazonEC2"]):
        if (row.get("Instance Type") not in types
                or row.get("Tenancy") != "Shared"
                or row.get("Operating System") != "Linux"
                or row.get("Pre Installed S/W") not in ("", "NA")
                or row.get("CapacityStatus") != "Used"
                or row.get("License Model") not in ("", "No License required")):
            continue
        try:
            price = float(row["PricePerUnit"])
        except (TypeError, ValueError):
            continue
        it = row["Instance Type"]
        if row["TermType"] == "OnDemand":
            od[it] = price
        elif row["TermType"] == "Reserved" and row.get("OfferingClass") == "standard":
            key = (it, row.get("LeaseContractLength"), row.get("PurchaseOption"))
            slot = ri.setdefault(key, {})
            slot["upfront" if row.get("Unit") == "Quantity" else "hourly"] = price

    out = []
    for (it, term, opt), parts in sorted(ri.items()):
        years = 3 if str(term).startswith("3") else 1
        eff = parts.get("hourly", 0.0) + parts.get("upfront", 0.0) / (8760 * years)
        base = od.get(it)
        if base and eff > 0:
            out.append({"instance": it, "term": term, "option": opt,
                        "on_demand": round(base, 6), "effective": round(eff, 6),
                        "saving": round(1 - eff / base, 4)})
    return out



# --------------------------------------------------------------------------- Azure
AZURE_BASE = "https://prices.azure.com/api/retail/prices"
AZURE_API_VERSION = "2023-01-01-preview"

#: Azure renames services in the price list, so a name that returns nothing is usually the
#: wrong name rather than an absent service. These are the ones that have caught us.
AZURE_RENAMES = {
    "Azure Cache for Redis": "Redis Cache",
    "Azure OpenAI": "Foundry Models",
    "Cognitive Services": "Foundry Models",
    "Azure AI Search": "Azure Cognitive Search",
}

#: The services a platform estimate normally needs. Names as the price list spells them.
AZURE_SERVICES = [
    "Virtual Machines", "Azure Kubernetes Service", "Azure Database for PostgreSQL",
    "Redis Cache", "Azure Cognitive Search", "Storage", "Bandwidth", "Key Vault",
    "Azure Monitor", "Log Analytics", "Application Gateway", "Virtual Network",
    "API Management", "Service Bus", "Event Hubs", "Container Registry",
    "Foundry Models", "Azure Firewall", "Functions",
]


def azure_fetch(odata_filter, page_cap=60):
    """Every row matching an OData filter, following NextPageLink to the end.

    urllib rejects a space inside the percent-encoded query, so nothing may be left
    unescaped. This is why the filter is built through urlencode rather than by hand.
    """
    import urllib.parse
    query = urllib.parse.urlencode(
        {"api-version": AZURE_API_VERSION, "$filter": odata_filter},
        quote_via=urllib.parse.quote)
    url = f"{AZURE_BASE}?{query}"
    items, pages = [], 0
    while url and pages < page_cap:
        payload = json.loads(_get(url, timeout=120))
        items.extend(payload.get("Items", []))
        url = payload.get("NextPageLink")
        pages += 1
    return items


def azure_service_rows(region, service):
    name = AZURE_RENAMES.get(service, service)
    return azure_fetch(f"armRegionName eq '{region}' and serviceName eq '{name}'")


def azure_probe(region):
    """Which services this region actually prices, and how many meters each has.

    A zero here is a finding, not a failure: it means either the name is wrong, in which
    case try the rename table, or the service genuinely is not offered regionally, in which
    case the estimate must state that rather than carry a number from somewhere else.
    """
    print(f"Azure {region}: probing {len(AZURE_SERVICES)} service(s)")
    absent = []
    for svc in AZURE_SERVICES:
        rows = azure_service_rows(region, svc)
        cons = sum(1 for r in rows if r.get("type") == "Consumption")
        resv = sum(1 for r in rows if r.get("type") == "Reservation")
        print(f"  {svc:<34} {len(rows):>5} meters  (consumption {cons}, reservation {resv})")
        if not rows:
            absent.append(svc)
    if absent:
        print("")
        print("  NO METERS for: " + ", ".join(absent))
        print("  Check the rename table before concluding a service is unavailable, and if it")
        print("  really is absent, say so on the sheet instead of pricing it from elsewhere.")


def azure_dump(region, service, needle, limit):
    """Every variant of a meter with the columns that tell them apart.

    productName is printed because it is what separates two Consumption rows for the same
    SKU: "Virtual Machines Dasv6 Series" against "... Windows", at roughly double the price.
    """
    rows = azure_service_rows(region, service)
    hit = [r for r in rows
           if not needle or needle.lower() in json.dumps(r).lower()]
    hit.sort(key=lambda r: (str(r.get("productName")), str(r.get("meterName")),
                            str(r.get("type")), r.get("retailPrice") or 0))
    hdr = "%-11s %-34s %-11s %-8s %-13s %s"
    print(hdr % ("retailPrice", "meterName", "type", "resTerm", "unit", "productName"))
    print("-" * 150)
    for r in hit[:limit]:
        print(hdr % (r.get("retailPrice"), str(r.get("meterName"))[:34],
                     str(r.get("type"))[:11], str(r.get("reservationTerm") or "")[:8],
                     str(r.get("unitOfMeasure"))[:13], str(r.get("productName"))[:46]))
    if len(hit) > limit:
        print(f"... {len(hit) - limit} more; narrow the filter")


def azure_reserved_table(region, skus):
    """Reservation discounts derived from the price list.

    A Reservation row states the TOTAL for the term while its unitOfMeasure still reads
    "1 Hour", so the discount is 1 - term_total / (on_demand_hourly * hours_in_term).
    Reading the field as an hourly rate gives a figure hundreds of times too large, and it
    looks plausible enough in a spreadsheet to survive review.
    """
    HOURS = {"1 Year": 8760, "3 Years": 26280, "5 Years": 43800}
    out = []
    for sku in sorted(skus):
        rows = azure_fetch(
            f"armRegionName eq '{region}' and armSkuName eq 'Standard_{sku}'")
        base = None
        for r in rows:
            if (r.get("type") == "Consumption"
                    and "Windows" not in str(r.get("productName"))
                    and "Spot" not in str(r.get("meterName"))
                    and "Low Priority" not in str(r.get("meterName"))):
                base = r.get("retailPrice")
                break
        if not base:
            continue
        for r in rows:
            if r.get("type") != "Reservation":
                continue
            term = r.get("reservationTerm")
            hours = HOURS.get(term)
            if not hours or not r.get("retailPrice"):
                continue
            eff = r["retailPrice"] / hours
            out.append({"sku": sku, "term": term,
                        "on_demand_hourly": round(base, 6),
                        "term_total": r["retailPrice"],
                        "effective_hourly": round(eff, 6),
                        "saving": round(1 - eff / base, 4)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="aws", choices=["aws", "azure"])
    ap.add_argument("--region", required=True)
    ap.add_argument("--out")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dump", help="service code, e.g. AmazonRDS")
    ap.add_argument("--filter", default="", help="substring the row must contain")
    ap.add_argument("--cols", default="Instance Type,usageType")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--reserved", default="m7g.large,m7g.xlarge,r7g.large",
                    help="AWS instance types, or Azure SKUs without the "
                         "Standard_ prefix such as D4ps_v6")
    a = ap.parse_args()

    if a.probe:
        azure_probe(a.region) if a.provider == "azure" else probe(a.region)
        return
    if a.dump:
        if a.provider == "azure":
            azure_dump(a.region, a.dump, a.filter, a.limit)
        else:
            dump(a.region, a.dump, a.filter, a.cols, a.limit)
        return
    if not a.out:
        ap.error("--out is required unless --probe or --dump is used")

    if a.provider == "azure":
        available, absent = {}, []
        for svc in AZURE_SERVICES:
            rows = azure_service_rows(a.region, svc)
            (available.__setitem__(svc, len(rows)) if rows else absent.append(svc))
        table = azure_reserved_table(a.region, set(a.reserved.split(",")))
        payload = {
            "provider": "azure",
            "region": a.region,
            "extracted": date.today().isoformat(),
            "source": f"{AZURE_BASE}?api-version={AZURE_API_VERSION}"
                      f"&$filter=armRegionName eq '{a.region}' and serviceName eq '<name>'",
            "note": ("LIST prices, excluding any enterprise agreement or credits the client "
                     "holds. Two traps when reading the raw rows: the same SKU has a "
                     "separate Windows row at roughly double the price, so select on "
                     "productName; and a Reservation row reports unitOfMeasure '1 Hour' "
                     "while retailPrice is the TOTAL for the term."),
            "services_available": available,
            "services_absent": absent,
            "reserved_discounts": table,
            "prices": {},
        }
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=1)
        print(f"Written: {a.out}")
        print(f"  {len(available)} service(s) priced in {a.region}")
        if absent:
            print("  no meters for: " + ", ".join(absent))
            print("  A service with no regional meter must be stated as such on the sheet, "
                  "never priced from another region.")
        return

    urls, absent = aws_region_urls(a.region, DEFAULT_SERVICES)
    table = reserved_table(a.region, set(a.reserved.split(",")))
    payload = {
        "provider": a.provider,
        "region": a.region,
        "extracted": date.today().isoformat(),
        "source": f"{AWS_BASE}/offers/v1.0/aws/<service>/current/{a.region}/index.csv",
        "note": ("LIST prices. They exclude any enterprise agreement, credits or private "
                 "pricing the client already holds. Re-extract before the number goes out."),
        "services_available": sorted(urls),
        "services_absent": absent,
        "reserved_discounts": table,
        "prices": {},
    }
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=1)
    print(f"Written: {a.out}")
    print(f"  {len(urls)} service(s) available in {a.region}")
    if absent:
        print(f"  absent: {', '.join(absent)}")
    if table:
        print("  reserved discounts (standard class):")
        seen = set()
        for row in table:
            k = (row["term"], row["option"])
            if k in seen:
                continue
            seen.add(k)
            print("    %-8s %-16s %5.1f%%" % (row["term"], row["option"],
                                              row["saving"] * 100))
    print()
    print("  Now populate `prices` by choosing a SKU per line with --dump, and put the")
    print("  usageType in each entry so the workbook can show where the figure came from.")


if __name__ == "__main__":
    main()
