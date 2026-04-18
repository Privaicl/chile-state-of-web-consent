"""Compute precision/recall/F1 for banner_validator and button_classifier agents.

Reads:
  - results/validations/labels.json   — human labels written by label_server.py
  - results/validations/<rank>/predictions.json — per-site predictions

Uses the SQLite DB (results/study.db by default) to cross-check banner_validator
against the ground truth `has_banner` column.

Usage:
    uv run python scripts/compute_agent_f1.py
    uv run python scripts/compute_agent_f1.py --db results/study.db \
        --validations results/validations --out results/agent_f1_report.json
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

CATEGORIES = ["accept", "reject", "settings", "save", "pay"]


# ---------------------------------------------------------------------------
# F1 primitives
# ---------------------------------------------------------------------------

@dataclass
class Counts:
    tp: int = 0
    fp: int = 0
    fn: int = 0

    def precision(self) -> Optional[float]:
        denom = self.tp + self.fp
        return self.tp / denom if denom > 0 else None

    def recall(self) -> Optional[float]:
        denom = self.tp + self.fn
        return self.tp / denom if denom > 0 else None

    def f1(self) -> Optional[float]:
        p = self.precision()
        r = self.recall()
        if p is None or r is None:
            return None
        denom = p + r
        return 2 * p * r / denom if denom > 0 else 0.0


def _fmt(v: Optional[float]) -> str:
    return f"{v:.3f}" if v is not None else "N/A"


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_labels(labels_path: Path) -> dict[str, dict[str, str]]:
    """Return {rank_str: {field: label}}."""
    if not labels_path.exists():
        return {}
    return json.loads(labels_path.read_text(encoding="utf-8"))


def load_predictions(validations_dir: Path) -> dict[int, dict]:
    """Return {rank: predictions_doc}."""
    out: dict[int, dict] = {}
    for d in validations_dir.iterdir():
        if not d.is_dir() or not d.name.isdigit():
            continue
        pred_path = d / "predictions.json"
        if not pred_path.exists():
            continue
        try:
            out[int(d.name)] = json.loads(pred_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return out


def load_db_banners(db_path: Path) -> dict[int, int]:
    """Return {rank: has_banner} from the sites table."""
    if not db_path.exists():
        return {}
    try:
        con = sqlite3.connect(db_path)
        cur = con.execute("SELECT rank, has_banner FROM sites")
        result = {int(r[0]): int(r[1] or 0) for r in cur.fetchall()}
        con.close()
        return result
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# banner_validator metrics
# ---------------------------------------------------------------------------

def compute_banner_f1(
    labels: dict[str, dict[str, str]],
    db_banners: dict[int, int],
) -> tuple[Counts, dict]:
    """
    TP = human label "yes"  AND has_banner=1 in DB (validator correctly found a real banner)
    FP = human label "no"   AND has_banner=1 in DB (validator found something that isn't a banner)
    FN = human label "yes"  AND has_banner=0 in DB (real banner existed but validator missed it;
                                                     this can only happen if the site was not
                                                     flagged at all — so there's no predictions.json
                                                     or it has banner_validator_confidence absent)

    Note: human label "unsure" is skipped (treated as no opinion).
    """
    c = Counts()
    details: list[dict] = []

    for rank_str, site_labels in labels.items():
        banner_label = site_labels.get("banner")
        if not banner_label or banner_label == "unsure":
            continue

        rank = int(rank_str)
        has_banner_db = db_banners.get(rank)

        # If rank not in DB at all, we cannot compute — skip
        if has_banner_db is None:
            continue

        if banner_label == "yes":
            if has_banner_db == 1:
                c.tp += 1
                outcome = "TP"
            else:
                c.fn += 1
                outcome = "FN"
        elif banner_label == "no":
            if has_banner_db == 1:
                c.fp += 1
                outcome = "FP"
            else:
                # True negative (correctly skipped) — not counted
                outcome = "TN"
        else:
            outcome = "skip"

        details.append({"rank": rank, "banner_label": banner_label,
                         "has_banner_db": has_banner_db, "outcome": outcome})

    return c, {"per_site": details}


# ---------------------------------------------------------------------------
# button_classifier metrics (per category)
# ---------------------------------------------------------------------------

def compute_button_f1(
    labels: dict[str, dict[str, str]],
    predictions: dict[int, dict],
) -> dict[str, tuple[Counts, list]]:
    """
    For each category (accept/reject/settings/save/pay):
      TP = predicted ref (non-null) AND human says "ok"
      FP = predicted ref (non-null) AND human says "wrong"
      FN = predicted null           AND human says "wrong"
                                    (a real button existed but we missed it)
      TN = predicted null           AND human says "na"   -> not counted
    """
    cat_counts: dict[str, Counts] = {cat: Counts() for cat in CATEGORIES}
    cat_details: dict[str, list] = {cat: [] for cat in CATEGORIES}

    for rank_str, site_labels in labels.items():
        rank = int(rank_str)
        pred_doc = predictions.get(rank, {})
        preds = pred_doc.get("predictions") or {}

        for cat in CATEGORIES:
            human = site_labels.get(cat)
            if not human:
                continue  # no label for this category

            pred = preds.get(cat)
            predicted_ref = pred.get("ref") if isinstance(pred, dict) else None
            has_prediction = predicted_ref is not None

            if has_prediction and human == "ok":
                cat_counts[cat].tp += 1
                outcome = "TP"
            elif has_prediction and human == "wrong":
                cat_counts[cat].fp += 1
                outcome = "FP"
            elif not has_prediction and human == "wrong":
                cat_counts[cat].fn += 1
                outcome = "FN"
            elif not has_prediction and human == "na":
                outcome = "TN"  # not counted
            else:
                outcome = "skip"

            cat_details[cat].append({
                "rank": rank,
                "has_prediction": has_prediction,
                "human": human,
                "outcome": outcome,
            })

    return {cat: (cat_counts[cat], cat_details[cat]) for cat in CATEGORIES}


# ---------------------------------------------------------------------------
# Report building
# ---------------------------------------------------------------------------

def _counts_dict(c: Counts) -> dict:
    return {
        "tp": c.tp, "fp": c.fp, "fn": c.fn,
        "precision": c.precision(),
        "recall": c.recall(),
        "f1": c.f1(),
    }


def build_report(
    labels: dict[str, dict[str, str]],
    predictions: dict[int, dict],
    db_banners: dict[int, int],
) -> dict:
    banner_counts, banner_details = compute_banner_f1(labels, db_banners)
    button_results = compute_button_f1(labels, predictions)

    # Macro F1 across categories (only for categories with non-None F1)
    f1_values = [
        button_results[cat][0].f1()
        for cat in CATEGORIES
        if button_results[cat][0].f1() is not None
    ]
    macro_f1 = sum(f1_values) / len(f1_values) if f1_values else None

    button_report: dict[str, dict] = {}
    for cat in CATEGORIES:
        c, _ = button_results[cat]
        button_report[cat] = _counts_dict(c)

    return {
        "banner_validator": _counts_dict(banner_counts),
        "button_classifier": {
            "by_category": button_report,
            "macro_f1": macro_f1,
        },
        "_details": {
            "banner_validator": banner_details,
            "button_classifier": {
                cat: dets for cat, (_, dets) in button_results.items()
            },
        },
    }


# ---------------------------------------------------------------------------
# Pretty-print table
# ---------------------------------------------------------------------------

def _print_table(report: dict) -> None:
    bv = report["banner_validator"]
    print("\n=== banner_validator ===")
    print(f"  TP={bv['tp']}  FP={bv['fp']}  FN={bv['fn']}")
    print(f"  Precision : {_fmt(bv['precision'])}")
    print(f"  Recall    : {_fmt(bv['recall'])}")
    print(f"  F1        : {_fmt(bv['f1'])}")

    bc = report["button_classifier"]
    print("\n=== button_classifier (per category) ===")
    header = f"  {'Category':12s}  {'TP':>4}  {'FP':>4}  {'FN':>4}  {'Prec':>7}  {'Rec':>7}  {'F1':>7}"
    print(header)
    print("  " + "-" * (len(header) - 2))
    for cat in CATEGORIES:
        d = bc["by_category"][cat]
        print(
            f"  {cat:12s}  {d['tp']:>4}  {d['fp']:>4}  {d['fn']:>4}"
            f"  {_fmt(d['precision']):>7}  {_fmt(d['recall']):>7}  {_fmt(d['f1']):>7}"
        )
    print(f"\n  Macro F1 : {_fmt(bc['macro_f1'])}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    p = argparse.ArgumentParser(description="Compute precision/recall/F1 for LLM agents")
    p.add_argument("--db", default="results/study.db",
                   help="SQLite DB path (default: results/study.db)")
    p.add_argument("--validations", default="results/validations",
                   help="Validations directory (default: results/validations)")
    p.add_argument("--out", default="results/agent_f1_report.json",
                   help="Output JSON path (default: results/agent_f1_report.json)")
    args = p.parse_args()

    val_dir = Path(args.validations)
    labels_path = val_dir / "labels.json"
    out_path = Path(args.out)

    labels = load_labels(labels_path)
    if not labels:
        print(f"No labels found at {labels_path}. Run the audit and save labels first.")
        raise SystemExit(1)

    predictions = load_predictions(val_dir)
    db_banners = load_db_banners(Path(args.db))

    report = build_report(labels, predictions, db_banners)

    _print_table(report)

    # Write JSON (strip _details for cleanliness, but keep it in file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport written to {out_path}")


if __name__ == "__main__":
    main()
