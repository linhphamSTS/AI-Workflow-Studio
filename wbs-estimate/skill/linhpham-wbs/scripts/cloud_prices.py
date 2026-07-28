#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Pull real list prices for a cloud region, deterministically.

    python cloud_prices.py --provider aws --region me-central-1 --out prices.json
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", default="aws", choices=["aws"])
    ap.add_argument("--region", required=True)
    ap.add_argument("--out")
    ap.add_argument("--probe", action="store_true")
    ap.add_argument("--dump", help="service code, e.g. AmazonRDS")
    ap.add_argument("--filter", default="", help="substring the row must contain")
    ap.add_argument("--cols", default="Instance Type,usageType")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--reserved", default="m7g.large,m7g.xlarge,r7g.large")
    a = ap.parse_args()

    if a.probe:
        probe(a.region)
        return
    if a.dump:
        dump(a.region, a.dump, a.filter, a.cols, a.limit)
        return
    if not a.out:
        ap.error("--out is required unless --probe or --dump is used")

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
