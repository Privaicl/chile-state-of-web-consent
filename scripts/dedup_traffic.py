"""Dedup the traffic dataset against the curated baseline.

Reads `companies.json` (curated baseline) and `data/companies_traffic.json`
(traffic ranking), removes traffic entries whose registered domain already
appears in baseline, and writes the surviving entries renumbered starting
at rank 101 to avoid collisions with baseline rows in `study.db`.

Usage:
    python scripts/dedup_traffic.py
    python scripts/dedup_traffic.py --baseline companies.json \
        --traffic data/companies_traffic.json \
        --out data/companies_traffic_new.json \
        --start-rank 101

Dependencies: tldextract  (pip install tldextract)
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.parse import urlparse

import tldextract

# Static suffix list (no network fetch at runtime).
_extract = tldextract.TLDExtract(suffix_list_urls=[])


def registered_domain(url_or_host: str) -> str:
    """Return the registrable (eTLD+1) portion of a URL or hostname."""
    if not url_or_host:
        return ""
    host = url_or_host
    if "://" in url_or_host:
        host = urlparse(url_or_host).hostname or ""
    parts = _extract(host)
    if not parts.domain or not parts.suffix:
        return host.lower()
    return f"{parts.domain}.{parts.suffix}".lower()


def dedup(baseline: list[dict], traffic: list[dict], start_rank: int) -> list[dict]:
    baseline_rd = {registered_domain(r["url"]) for r in baseline}
    out: list[dict] = []
    next_rank = start_rank
    for r in traffic:
        rd = registered_domain(r["url"])
        if rd in baseline_rd:
            continue
        out.append({"rank": next_rank, "name": r["name"], "url": r["url"]})
        next_rank += 1
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--baseline", default="companies.json")
    p.add_argument("--traffic", default="data/companies_traffic.json")
    p.add_argument("--out", default="data/companies_traffic_new.json")
    p.add_argument("--start-rank", type=int, default=101)
    args = p.parse_args(argv)

    baseline = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    traffic = json.loads(Path(args.traffic).read_text(encoding="utf-8"))

    new = dedup(baseline, traffic, args.start_rank)

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(new, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    n_dup = len(traffic) - len(new)
    print(
        f"baseline={len(baseline)}  traffic={len(traffic)}  "
        f"dup={n_dup}  new={len(new)}  ranks={args.start_rank}-{args.start_rank + len(new) - 1}\n"
        f"wrote {out_path}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
