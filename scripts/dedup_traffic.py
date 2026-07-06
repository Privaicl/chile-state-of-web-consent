"""Dedup the traffic dataset against the curated baseline.

Reads `companies.json` (curated baseline) and `data/companies_traffic.json`
(traffic ranking), removes traffic entries whose registered domain already
appears in baseline, and writes the surviving entries renumbered starting
at rank 101 to avoid collisions with baseline rows in `study.db`.

Usage:
    uv run python scripts/dedup_traffic.py
    uv run python scripts/dedup_traffic.py --baseline companies.json \
        --traffic data/companies_traffic.json \
        --out data/companies_traffic_new.json \
        --start-rank 101
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Resolve repo paths so `scraper.firstparty` is importable when invoked from anywhere.
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from scraper.firstparty import registered_domain  # noqa: E402


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
