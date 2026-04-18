"""Generate a deterministic, no-LLM report from study.db.

Reads results/study.db plus the per-site validations directory and emits:

    results/study_report/
    ├── INDEX.md
    ├── summary.md
    ├── findings.json
    ├── segments/
    │   ├── gov.md
    │   └── other.md
    └── per_site/
        └── <rank>.md          (selective; see SECTION 5.4 of the spec)

All aggregations are deterministic SQL/Python over the persisted DB. No
LLM calls are issued during execution. Two consecutive runs against the
same DB produce bit-identical output.

Usage:
    uv run python scripts/study_report.py
    uv run python scripts/study_report.py --db results/study.db \
        --out results/study_report
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
import subprocess
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA_VERSION = 1
TRACKING_CATEGORIES = {"analytics", "marketing", "advertising", "social"}
TEMPLATE_PREFIX_LEN = 100  # chars of normalized banner_text_snippet for clustering


def _git_sha(repo_root: Path) -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode == 0:
            return out.stdout.strip()
    except Exception:
        pass
    return None


def _is_gov(url: str | None) -> bool:
    return bool(url) and ".gob.cl" in url.lower()


def _normalize_text(s: str | None) -> str:
    if not s:
        return ""
    n = unicodedata.normalize("NFKD", s)
    n = "".join(c for c in n if not unicodedata.combining(c))
    return " ".join(n.lower().split())


def _template_key(snippet: str | None) -> str | None:
    n = _normalize_text(snippet)
    if not n:
        return None
    prefix = n[:TEMPLATE_PREFIX_LEN]
    return hashlib.sha1(prefix.encode("utf-8")).hexdigest()[:12]


# ─── Data loading ──────────────────────────────────────────────────────────

def _dictify(cur: sqlite3.Cursor, row: tuple) -> dict:
    return {d[0]: row[i] for i, d in enumerate(cur.description)}


def load_data(db_path: Path) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row

    sites = [dict(r) for r in con.execute(
        "SELECT * FROM sites ORDER BY rank"
    ).fetchall()]

    scenarios = [dict(r) for r in con.execute(
        "SELECT * FROM scenario_runs ORDER BY rank, scenario, id"
    ).fetchall()]

    cookies = [dict(r) for r in con.execute(
        "SELECT * FROM cookies ORDER BY run_id, name, domain"
    ).fetchall()]

    third_party = [dict(r) for r in con.execute(
        "SELECT * FROM third_party_domains ORDER BY run_id, domain"
    ).fetchall()]

    con.close()

    # Index helpers
    scenarios_by_rank: dict[int, dict[str, dict]] = defaultdict(dict)
    for sr in scenarios:
        scenarios_by_rank[sr["rank"]][sr["scenario"]] = sr

    cookies_by_run: dict[int, list[dict]] = defaultdict(list)
    for c in cookies:
        cookies_by_run[c["run_id"]].append(c)

    third_party_by_run: dict[int, list[dict]] = defaultdict(list)
    for tp in third_party:
        third_party_by_run[tp["run_id"]].append(tp)

    return {
        "sites": sites,
        "scenarios_by_rank": dict(scenarios_by_rank),
        "cookies_by_run": dict(cookies_by_run),
        "third_party_by_run": dict(third_party_by_run),
    }


# ─── Findings computation ─────────────────────────────────────────────────

def _segment(site: dict) -> str:
    return "gov" if _is_gov(site.get("url")) else "other"


def compute_coverage(sites: list[dict]) -> dict:
    by_status: Counter = Counter()
    by_segment_status: dict[str, Counter] = {"gov": Counter(), "other": Counter()}
    for s in sites:
        st = s.get("status") or "unknown"
        by_status[st] += 1
        by_segment_status[_segment(s)][st] += 1
    return {
        "n_sites": len(sites),
        "by_status": dict(sorted(by_status.items())),
        "by_segment": {
            seg: dict(sorted(c.items())) for seg, c in by_segment_status.items()
        },
    }


def compute_banner_detection(sites: list[dict]) -> dict:
    out: dict[str, dict] = {}
    for seg in ("all", "gov", "other"):
        ok = [s for s in sites if s.get("status") == "ok"
              and (seg == "all" or _segment(s) == seg)]
        with_banner = sum(1 for s in ok if s.get("has_banner") == 1)
        out[seg] = {
            "ok_loads": len(ok),
            "with_banner": with_banner,
            "pct": round(100.0 * with_banner / len(ok), 1) if ok else None,
        }
    return out


def compute_cmps(sites: list[dict]) -> dict:
    banners = [s for s in sites if s.get("has_banner") == 1]
    counts: Counter = Counter()
    sources: Counter = Counter()
    for s in banners:
        name = s.get("cmp_name") or "<sin CMP reconocida>"
        counts[name] += 1
        sources[s.get("cmp_source") or "<none>"] += 1
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "n_banners": len(banners),
        "ranked": [{"name": n, "count": c} for n, c in ranked],
        "by_source": dict(sorted(sources.items())),
    }


def compute_buttons(sites: list[dict]) -> dict:
    banners = [s for s in sites if s.get("has_banner") == 1]
    n = len(banners)
    out: dict[str, dict] = {}
    for col in ("has_accept", "has_reject", "has_settings", "has_save", "has_pay"):
        n_present = sum(1 for s in banners if s.get(col) == 1)
        out[col] = {
            "n": n_present,
            "pct_of_banners": round(100.0 * n_present / n, 1) if n else None,
        }
    out["n_banners"] = n
    return out


def compute_reject_ux(sites: list[dict]) -> dict:
    have_reject = [s for s in sites if s.get("has_reject") == 1]
    n = len(have_reject)
    layer_counts: Counter = Counter()
    visual_eq_counts: Counter = Counter()
    for s in have_reject:
        layer_counts[s.get("reject_layer")] += 1
        visual_eq_counts[s.get("visual_equal")] += 1
    return {
        "n_with_reject": n,
        "by_layer": {
            "layer_1": layer_counts.get(1, 0),
            "layer_2": layer_counts.get(2, 0),
            "null_or_unknown": layer_counts.get(None, 0),
        },
        "visual_equal": {
            "yes": visual_eq_counts.get(1, 0),
            "no": visual_eq_counts.get(0, 0),
            "null_or_unknown": visual_eq_counts.get(None, 0),
        },
    }


def compute_compliance(sites: list[dict]) -> dict:
    """Count compliance using is_minimally_compliant directly.

    Note: a site can have is_minimally_compliant=1 but has_banner=0 in the
    current row, when a successful prior scrape set the compliance flag and
    a later re-scrape failed to find a banner (partial upsert preserves the
    flag). We count the persisted compliance signal because it reflects an
    observed positive case.
    """
    banners_now = [s for s in sites if s.get("has_banner") == 1]
    compliant = [s for s in sites if s.get("is_minimally_compliant") == 1]
    n_banners = len(banners_now)
    # Denominator for the percentage: banners observed *at any point*.
    # A site with is_minimally_compliant=1 was a banner at scrape time even
    # if the latest re-scrape lost it.
    n_banners_ever = len({s["rank"] for s in banners_now}
                         | {s["rank"] for s in compliant})

    fails: Counter = Counter()
    for s in banners_now:
        rule_fails = (s.get("compliance_rule_fails") or "").strip()
        if rule_fails:
            for r in rule_fails.split(","):
                r = r.strip()
                if r:
                    fails[r] += 1
    fails_ranked = sorted(fails.items(), key=lambda kv: (-kv[1], kv[0]))
    return {
        "n_banners_now": n_banners,
        "n_banners_ever_observed": n_banners_ever,
        "n_compliant": len(compliant),
        "pct_of_banners_ever": round(100.0 * len(compliant) / n_banners_ever, 1)
                               if n_banners_ever else None,
        "rule_fails": [{"rule": r, "count": c} for r, c in fails_ranked],
        "compliant_sites": sorted(
            [{"rank": s["rank"], "company": s["company"],
              "cmp_name": s.get("cmp_name") or "",
              "accept_text": s.get("accept_text") or "",
              "reject_text": s.get("reject_text") or "",
              "has_banner_now": s.get("has_banner")}
             for s in compliant],
            key=lambda r: r["rank"],
        ),
    }


def _cookie_is_tracking(c: dict) -> bool:
    cat = (c.get("classification_category") or "").strip().lower()
    return cat in TRACKING_CATEGORIES


def compute_tracking_baseline(data: dict) -> list[dict]:
    out: list[dict] = []
    for s in data["sites"]:
        if s.get("status") != "ok":
            continue
        baseline = data["scenarios_by_rank"].get(s["rank"], {}).get("baseline")
        if not baseline:
            continue
        cookies = data["cookies_by_run"].get(baseline["id"], [])
        tracking = [c for c in cookies if _cookie_is_tracking(c)]
        if not tracking:
            continue
        cat_counts: Counter = Counter()
        for c in tracking:
            cat_counts[(c.get("classification_category") or "").lower()] += 1
        n_llm = sum(1 for c in tracking if c.get("classified_by") == "llm")
        out.append({
            "rank": s["rank"],
            "company": s["company"],
            "url": s["url"],
            "segment": _segment(s),
            "n_tracking_cookies": len(tracking),
            "by_category": dict(sorted(cat_counts.items())),
            "n_llm_classified": n_llm,
            "cookies": sorted([
                {"name": c["name"], "domain": c.get("domain"),
                 "category": (c.get("classification_category") or "").lower(),
                 "platform": c.get("classification_platform"),
                 "classified_by": c.get("classified_by")}
                for c in tracking
            ], key=lambda c: (c["category"], c["name"])),
        })
    out.sort(key=lambda r: (-r["n_tracking_cookies"], r["rank"]))
    return out


def compute_reject_ineffective(data: dict) -> list[dict]:
    out: list[dict] = []
    for s in data["sites"]:
        if s.get("status") != "ok":
            continue
        if s.get("reject_layer") not in (1, 2):
            continue
        reject = data["scenarios_by_rank"].get(s["rank"], {}).get("reject")
        if not reject:
            continue
        cookies = data["cookies_by_run"].get(reject["id"], [])
        tracking = [c for c in cookies if _cookie_is_tracking(c)]
        if not tracking:
            continue
        out.append({
            "rank": s["rank"],
            "company": s["company"],
            "url": s["url"],
            "segment": _segment(s),
            "reject_layer": s.get("reject_layer"),
            "n_tracking_after_reject": len(tracking),
            "cookies": sorted([
                {"name": c["name"], "domain": c.get("domain"),
                 "category": (c.get("classification_category") or "").lower(),
                 "platform": c.get("classification_platform")}
                for c in tracking
            ], key=lambda c: (c["category"], c["name"])),
        })
    out.sort(key=lambda r: (-r["n_tracking_after_reject"], r["rank"]))
    return out


def compute_gov(data: dict) -> list[dict]:
    out: list[dict] = []
    for s in data["sites"]:
        if not _is_gov(s.get("url")) or s.get("status") != "ok":
            continue
        scenarios = data["scenarios_by_rank"].get(s["rank"], {})
        per_scenario: dict[str, dict] = {}
        for sc_name in ("baseline", "accept", "reject"):
            sc = scenarios.get(sc_name)
            if not sc:
                per_scenario[sc_name] = {"present": False}
                continue
            cookies = data["cookies_by_run"].get(sc["id"], [])
            cat_counts: Counter = Counter()
            for c in cookies:
                cat_counts[(c.get("classification_category") or "<none>").lower()] += 1
            per_scenario[sc_name] = {
                "present": True,
                "status": sc.get("status"),
                "n_cookies": len(cookies),
                "by_category": dict(sorted(cat_counts.items())),
                "tracking_cookies": sorted([
                    {"name": c["name"], "domain": c.get("domain"),
                     "category": (c.get("classification_category") or "").lower(),
                     "platform": c.get("classification_platform")}
                    for c in cookies if _cookie_is_tracking(c)
                ], key=lambda c: (c["category"], c["name"])),
            }
        out.append({
            "rank": s["rank"],
            "company": s["company"],
            "url": s["url"],
            "scraped_url": s.get("scraped_url"),
            "has_banner": s.get("has_banner"),
            "cmp_name": s.get("cmp_name"),
            "scenarios": per_scenario,
        })
    out.sort(key=lambda r: r["rank"])
    return out


def compute_templates(sites: list[dict]) -> list[dict]:
    by_key: dict[str, list[dict]] = defaultdict(list)
    for s in sites:
        if s.get("has_banner") != 1:
            continue
        k = _template_key(s.get("banner_text_snippet"))
        if not k:
            continue
        by_key[k].append(s)
    out: list[dict] = []
    for k, members in by_key.items():
        if len(members) < 2:
            continue
        sorted_members = sorted(members, key=lambda s: s["rank"])
        n_accept = sum(1 for s in members if s.get("has_accept") == 1)
        n_reject = sum(1 for s in members if s.get("has_reject") == 1)
        cmps = sorted({s.get("cmp_name") or "<sin CMP>" for s in members})
        out.append({
            "template_key": k,
            "n_members": len(members),
            "n_with_accept": n_accept,
            "n_with_reject": n_reject,
            "cmps": cmps,
            "snippet_excerpt": (members[0].get("banner_text_snippet") or "")[:120],
            "members": [
                {"rank": s["rank"], "company": s["company"],
                 "has_accept": s.get("has_accept"), "has_reject": s.get("has_reject"),
                 "cmp_name": s.get("cmp_name") or ""}
                for s in sorted_members
            ],
        })
    out.sort(key=lambda r: (-r["n_members"], r["template_key"]))
    return out


def compute_segment_comparison(findings: dict) -> dict:
    cov = findings["coverage"]["by_segment"]
    bd = findings["banner_detection"]
    rows = []
    for seg in ("gov", "other"):
        ok = cov.get(seg, {}).get("ok", 0)
        rows.append({
            "segment": seg,
            "n_total": sum(cov.get(seg, {}).values()),
            "n_ok": ok,
            "n_with_banner": bd.get(seg, {}).get("with_banner", 0),
            "pct_with_banner": bd.get(seg, {}).get("pct"),
        })
    return {"rows": rows}


def compute_findings(data: dict, db_path: Path) -> dict:
    sites = data["sites"]
    findings: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "db_path": str(db_path),
        "git_sha": _git_sha(Path(__file__).resolve().parents[1]),
        "coverage": compute_coverage(sites),
        "banner_detection": compute_banner_detection(sites),
        "cmps": compute_cmps(sites),
        "buttons": compute_buttons(sites),
        "reject_ux": compute_reject_ux(sites),
        "compliance": compute_compliance(sites),
        "tracking_baseline": compute_tracking_baseline(data),
        "reject_ineffective": compute_reject_ineffective(data),
        "gov": compute_gov(data),
        "templates": compute_templates(sites),
    }
    findings["segment_comparison"] = compute_segment_comparison(findings)
    return findings


# ─── Markdown rendering ───────────────────────────────────────────────────

def _md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |"]
    lines.append("|" + "|".join("---" for _ in headers) + "|")
    for r in rows:
        cells = [str(c) if c is not None else "" for c in r]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def render_summary_md(f: dict) -> str:
    out: list[str] = []
    out.append("# Estado del Consentimiento Web en Chile — Reporte agregado\n")
    out.append(f"*Generado:* `{f['generated_at']}`")
    out.append(f"*DB:* `{f['db_path']}`  *git:* `{f['git_sha'] or '<no git>'}`\n")
    out.append("> Salida puramente determinística sobre `study.db`. "
               "Sin invocaciones a modelos de lenguaje en la fase de reporte.")

    # 1. Cobertura
    out.append("\n## 1. Cobertura del estudio\n")
    cov = f["coverage"]
    out.append(f"Total de sitios en la base: **{cov['n_sites']}**.\n")
    by_status_rows = [[k, v] for k, v in cov["by_status"].items()]
    out.append(_md_table(["status", "count"], by_status_rows))
    out.append("\nPor segmento:")
    seg_headers = ["status", "gov", "other"]
    all_status_keys = sorted(set(cov["by_segment"]["gov"]) | set(cov["by_segment"]["other"]))
    seg_rows = [[k, cov["by_segment"]["gov"].get(k, 0), cov["by_segment"]["other"].get(k, 0)]
                for k in all_status_keys]
    out.append(_md_table(seg_headers, seg_rows))

    # 2. Banner detection
    out.append("\n## 2. Detección de banner\n")
    bd = f["banner_detection"]
    rows = [[seg, bd[seg]["with_banner"], bd[seg]["ok_loads"],
             f"{bd[seg]['pct']}%" if bd[seg]["pct"] is not None else "—"]
            for seg in ("all", "gov", "other")]
    out.append(_md_table(["segmento", "con banner", "cargas ok", "%"], rows))

    # 3. CMPs
    out.append("\n## 3. CMPs identificados\n")
    cmps = f["cmps"]
    out.append(f"Sitios con banner: **{cmps['n_banners']}**.\n")
    rows = [[c["name"], c["count"]] for c in cmps["ranked"]]
    out.append(_md_table(["CMP", "count"], rows))
    out.append("\nFuente de identificación (`cmp_source`):")
    rows = [[k, v] for k, v in cmps["by_source"].items()]
    out.append(_md_table(["fuente", "count"], rows))

    # 4. Botones
    out.append("\n## 4. Botones presentes en banners\n")
    btn = f["buttons"]
    out.append(f"Base: **{btn['n_banners']}** sitios con banner.\n")
    rows = []
    for col in ("has_accept", "has_reject", "has_settings", "has_save", "has_pay"):
        b = btn[col]
        rows.append([col.replace("has_", ""), b["n"],
                     f"{b['pct_of_banners']}%" if b["pct_of_banners"] is not None else "—"])
    out.append(_md_table(["botón", "n", "% de banners"], rows))

    # 5. Reject UX
    out.append("\n## 5. UX del botón de rechazo\n")
    rj = f["reject_ux"]
    out.append(f"Sitios con `has_reject=1`: **{rj['n_with_reject']}**.\n")
    out.append("Capa donde aparece el rechazo:")
    rows = [["layer 1", rj["by_layer"]["layer_1"]],
            ["layer 2", rj["by_layer"]["layer_2"]],
            ["NULL / desconocido", rj["by_layer"]["null_or_unknown"]]]
    out.append(_md_table(["reject_layer", "count"], rows))
    out.append("\n`visual_equal` (botones aceptar/rechazar con prominencia visual similar):")
    rows = [["sí", rj["visual_equal"]["yes"]],
            ["no", rj["visual_equal"]["no"]],
            ["NULL / desconocido", rj["visual_equal"]["null_or_unknown"]]]
    out.append(_md_table(["visual_equal", "count"], rows))

    # 6. Compliance
    out.append("\n## 6. Cumplimiento determinístico (regla Nouwens)\n")
    cp = f["compliance"]
    out.append(f"Banners observados (incluyendo los que un re-scrape posterior pudo no haber detectado): **{cp['n_banners_ever_observed']}**. "
               f"Cumplen la regla mínima: **{cp['n_compliant']}** "
               f"({cp['pct_of_banners_ever']}% del total observado).\n")
    if cp["rule_fails"]:
        out.append("Top fallas (entre banners actualmente detectados):")
        rows = [[r["rule"], r["count"]] for r in cp["rule_fails"][:15]]
        out.append(_md_table(["regla incumplida", "count"], rows))
    if cp["compliant_sites"]:
        out.append("\nSitios mínimamente conformes:")
        rows = [[s["rank"], s["company"], s["cmp_name"],
                 s["accept_text"], s["reject_text"],
                 "✓" if s["has_banner_now"] == 1 else "✗ (perdido en re-scrape)"]
                for s in cp["compliant_sites"]]
        out.append(_md_table(["rank", "sitio", "CMP", "aceptar", "rechazar", "banner ahora"], rows))

    # 7. Tracking sin consentimiento (baseline)
    out.append("\n## 7. Cookies de tracking depositadas sin consentimiento (escenario baseline)\n")
    tb = f["tracking_baseline"]
    out.append(f"**{len(tb)}** sitios depositan cookies de tracking "
               f"(categorías: {', '.join(sorted(TRACKING_CATEGORIES))}) en la primera carga.\n")
    rows = [[r["rank"], r["company"], r["segment"], r["n_tracking_cookies"],
             r["n_llm_classified"]]
            for r in tb[:50]]
    out.append(_md_table(["rank", "sitio", "segmento", "n cookies", "n clasificadas LLM"], rows))
    if len(tb) > 50:
        out.append(f"\n*(Mostrando los primeros 50 de {len(tb)}; ver `findings.json` para el listado completo.)*")

    # 8. Efectividad del rechazo
    out.append("\n## 8. Efectividad del rechazo\n")
    ri = f["reject_ineffective"]
    out.append(f"**{len(ri)}** sitios donde el clic 'rechazar' tuvo éxito "
               f"(`reject_layer NOT NULL`) y aún así se setearon cookies de tracking en el escenario `reject`.\n")
    rows = [[r["rank"], r["company"], r["segment"], r["reject_layer"],
             r["n_tracking_after_reject"]]
            for r in ri]
    if rows:
        out.append(_md_table(["rank", "sitio", "segmento", "layer", "n tracking post-rechazo"], rows))

    # 9. Sector gobierno
    out.append("\n## 9. Sector gobierno (`*.gob.cl`)\n")
    gov = f["gov"]
    out.append(f"**{len(gov)}** dominios gubernamentales con `status='ok'`.\n")
    out.append("Resumen por sitio:")
    rows = []
    for r in gov:
        n_b = r["scenarios"].get("baseline", {}).get("n_cookies", "—")
        n_track_b = len(r["scenarios"].get("baseline", {}).get("tracking_cookies", []))
        rows.append([r["rank"], r["company"], r["has_banner"], n_b, n_track_b,
                     r.get("cmp_name") or ""])
    out.append(_md_table(
        ["rank", "sitio", "has_banner", "cookies baseline", "tracking baseline", "CMP"],
        rows,
    ))

    # 10. Comparación entre segmentos
    out.append("\n## 10. Comparación entre segmentos\n")
    sc = f["segment_comparison"]
    rows = [[r["segment"], r["n_total"], r["n_ok"], r["n_with_banner"],
             f"{r['pct_with_banner']}%" if r["pct_with_banner"] is not None else "—"]
            for r in sc["rows"]]
    out.append(_md_table(["segmento", "total", "ok", "con banner", "% con banner"], rows))

    # 11. Plantillas compartidas
    out.append("\n## 11. Plantillas de banner compartidas (clusters)\n")
    out.append("Clusters de sitios con prefijo idéntico de `banner_text_snippet` "
               f"(primeros {TEMPLATE_PREFIX_LEN} caracteres normalizados):\n")
    tmpls = f["templates"]
    if not tmpls:
        out.append("*Sin clusters de tamaño ≥ 2.*")
    else:
        for t in tmpls:
            out.append(f"\n### Cluster `{t['template_key']}` — {t['n_members']} sitios "
                       f"(accept={t['n_with_accept']}, reject={t['n_with_reject']})")
            out.append(f"> *Snippet:* `{t['snippet_excerpt']}…`")
            rows = [[m["rank"], m["company"], m["has_accept"], m["has_reject"],
                     m["cmp_name"]] for m in t["members"]]
            out.append(_md_table(["rank", "sitio", "accept", "reject", "CMP"], rows))

    # 12. Validación de agentes
    out.append("\n## 12. Validación de los agentes (F1 contra etiquetas humanas)\n")
    out.append("*Sin labels humanos en `results/validations/labels.json`. "
               "Para activar esta sección: ejecutar `python scripts/label_server.py`, "
               "etiquetar desde `results/audit_report.html`, y regenerar el reporte.*")

    return "\n".join(out) + "\n"


def render_segment_md(f: dict, segment: str) -> str:
    out: list[str] = []
    title = "Sitios `*.gob.cl`" if segment == "gov" else "Sitios privados / no-gob"
    out.append(f"# {title}\n")
    out.append(f"*Generado:* `{f['generated_at']}`\n")

    cov = f["coverage"]["by_segment"][segment]
    out.append("## Cobertura\n")
    rows = [[k, v] for k, v in cov.items()]
    out.append(_md_table(["status", "count"], rows))

    bd = f["banner_detection"][segment]
    out.append(f"\n## Detección de banner\n")
    out.append(f"Cargas ok: **{bd['ok_loads']}**. Con banner: **{bd['with_banner']}** "
               f"({bd['pct']}%).\n" if bd["pct"] is not None else
               f"Cargas ok: **{bd['ok_loads']}**. Con banner: **{bd['with_banner']}**.\n")

    if segment == "gov":
        out.append("\n## Detalle por sitio\n")
        for r in f["gov"]:
            out.append(f"\n### Rank {r['rank']} — {r['company']}\n")
            out.append(f"- URL: {r['url']}")
            out.append(f"- URL final: {r['scraped_url'] or '—'}")
            out.append(f"- has_banner: {r['has_banner']}  CMP: {r.get('cmp_name') or '—'}")
            for sc_name in ("baseline", "accept", "reject"):
                sc = r["scenarios"].get(sc_name, {})
                if not sc.get("present"):
                    out.append(f"- escenario `{sc_name}`: no ejecutado")
                    continue
                out.append(f"- escenario `{sc_name}`: status={sc.get('status')}, "
                           f"n_cookies={sc.get('n_cookies')}, "
                           f"categorías={sc.get('by_category')}")
                for c in sc.get("tracking_cookies", []):
                    out.append(f"    - `{c['name']}`  ({c['domain']})  "
                               f"{c['category']} / {c.get('platform') or '—'}")
    else:
        # For 'other' segment, list the tracking-baseline + reject-ineffective sites
        tb_other = [r for r in f["tracking_baseline"] if r["segment"] == "other"]
        out.append(f"\n## Cookies de tracking en baseline (escenario sin interacción)\n")
        out.append(f"**{len(tb_other)}** sitios afectados.\n")
        rows = [[r["rank"], r["company"], r["n_tracking_cookies"]]
                for r in tb_other[:60]]
        out.append(_md_table(["rank", "sitio", "n cookies tracking"], rows))

        ri_other = [r for r in f["reject_ineffective"] if r["segment"] == "other"]
        if ri_other:
            out.append("\n## Rechazo inefectivo\n")
            out.append(f"**{len(ri_other)}** sitios donde el rechazo se ejecutó pero las cookies de tracking persistieron.\n")
            rows = [[r["rank"], r["company"], r["reject_layer"], r["n_tracking_after_reject"]]
                    for r in ri_other]
            out.append(_md_table(["rank", "sitio", "layer", "n tracking post-rechazo"], rows))

    return "\n".join(out) + "\n"


def get_relevant_ranks(f: dict) -> set[int]:
    ranks: set[int] = set()
    ranks.update(r["rank"] for r in f["tracking_baseline"])
    ranks.update(r["rank"] for r in f["reject_ineffective"])
    ranks.update(r["rank"] for r in f["gov"])
    ranks.update(r["rank"] for r in f["compliance"]["compliant_sites"])
    for t in f["templates"]:
        ranks.update(m["rank"] for m in t["members"])
    return ranks


def render_per_site_md(rank: int, data: dict, f: dict) -> str:
    site = next((s for s in data["sites"] if s["rank"] == rank), None)
    if not site:
        return ""
    out: list[str] = []
    out.append(f"# Rank {rank} — {site['company']}\n")
    out.append(f"- URL declarada: {site.get('url')}")
    out.append(f"- URL final: {site.get('scraped_url') or '—'}")
    out.append(f"- status: {site.get('status')}")
    out.append(f"- has_banner: {site.get('has_banner')}")
    out.append(f"- CMP: {site.get('cmp_name') or '—'}  (fuente: {site.get('cmp_source') or '—'})")
    out.append(f"- banner_validator_confidence: {site.get('banner_validator_confidence')}")
    out.append(f"- is_minimally_compliant: {site.get('is_minimally_compliant')}")
    out.append(f"- compliance_rule_fails: {site.get('compliance_rule_fails') or '—'}\n")

    out.append("## Botones detectados\n")
    rows = []
    for cat, has, txt in (
        ("accept", site.get("has_accept"), site.get("accept_text")),
        ("reject", site.get("has_reject"), site.get("reject_text")),
        ("settings", site.get("has_settings"), site.get("settings_text")),
        ("save", site.get("has_save"), site.get("save_text")),
        ("pay", site.get("has_pay"), site.get("pay_text")),
    ):
        rows.append([cat, has, txt or ""])
    out.append(_md_table(["categoría", "presente", "texto"], rows))

    out.append("\n## Cookies por escenario\n")
    scenarios = data["scenarios_by_rank"].get(rank, {})
    for sc_name in ("baseline", "accept", "reject"):
        sc = scenarios.get(sc_name)
        out.append(f"\n### Escenario `{sc_name}`")
        if not sc:
            out.append("- (sin datos)")
            continue
        cookies = sorted(
            data["cookies_by_run"].get(sc["id"], []),
            key=lambda c: ((c.get("classification_category") or "").lower(),
                           c.get("name") or ""),
        )
        out.append(f"- status escenario: {sc.get('status')}")
        out.append(f"- cookies_count: {sc.get('cookies_count')}")
        out.append(f"- third_party_domains_count: {sc.get('third_party_domains_count')}")
        if cookies:
            rows = [[c["name"], c.get("domain") or "",
                     (c.get("classification_category") or "").lower(),
                     c.get("classification_platform") or "",
                     c.get("classified_by") or ""]
                    for c in cookies[:50]]
            out.append("")
            out.append(_md_table(
                ["nombre", "dominio", "categoría", "plataforma", "fuente"],
                rows,
            ))
            if len(cookies) > 50:
                out.append(f"\n*(Mostrando 50 de {len(cookies)} cookies.)*")

    return "\n".join(out) + "\n"


def render_index_md(f: dict, n_per_site: int) -> str:
    out = ["# Reporte del estudio — Índice\n",
           f"*Generado:* `{f['generated_at']}`\n",
           "## Documentos\n",
           "- [`summary.md`](summary.md) — hallazgos agregados (todas las tablas)",
           "- [`findings.json`](findings.json) — datos crudos en formato maquinable",
           "- [`segments/gov.md`](segments/gov.md) — sitios `*.gob.cl`",
           "- [`segments/other.md`](segments/other.md) — sitios privados",
           f"- `per_site/` — {n_per_site} fichas individuales\n",
           "## Resumen rápido\n"]
    bd = f["banner_detection"]["all"]
    cp = f["compliance"]
    out.append(f"- Sitios totales: **{f['coverage']['n_sites']}** "
               f"(ok: **{f['coverage']['by_status'].get('ok', 0)}**)")
    out.append(f"- Banners detectados: **{bd['with_banner']} / {bd['ok_loads']}** "
               f"({bd['pct']}% de las cargas exitosas)")
    out.append(f"- Sitios mínimamente conformes (Nouwens): **{cp['n_compliant']} / {cp['n_banners_ever_observed']}** banners observados ({cp['pct_of_banners_ever']}%)")
    out.append(f"- Sitios `.gob.cl` analizados: **{len(f['gov'])}**")
    out.append(f"- Sitios depositando tracking en `baseline`: **{len(f['tracking_baseline'])}**")
    out.append(f"- Sitios con rechazo inefectivo: **{len(f['reject_ineffective'])}**")
    return "\n".join(out) + "\n"


# ─── Driver ────────────────────────────────────────────────────────────────

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    p.add_argument("--db", default="results/study.db")
    p.add_argument("--validations", default="results/validations")
    p.add_argument("--out", default="results/study_report")
    args = p.parse_args(argv)

    db_path = Path(args.db)
    out_dir = Path(args.out)
    if not db_path.exists():
        print(f"DB not found: {db_path}", file=__import__("sys").stderr)
        return 2

    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "segments").mkdir(exist_ok=True)
    (out_dir / "per_site").mkdir(exist_ok=True)

    data = load_data(db_path)
    findings = compute_findings(data, db_path)

    # findings.json — sorted keys for bit-identical output
    (out_dir / "findings.json").write_text(
        json.dumps(findings, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # summary.md
    (out_dir / "summary.md").write_text(render_summary_md(findings), encoding="utf-8")

    # segments
    (out_dir / "segments" / "gov.md").write_text(
        render_segment_md(findings, "gov"), encoding="utf-8"
    )
    (out_dir / "segments" / "other.md").write_text(
        render_segment_md(findings, "other"), encoding="utf-8"
    )

    # per_site
    relevant = sorted(get_relevant_ranks(findings))
    for r in relevant:
        md = render_per_site_md(r, data, findings)
        if md:
            (out_dir / "per_site" / f"{r}.md").write_text(md, encoding="utf-8")

    # INDEX
    (out_dir / "INDEX.md").write_text(
        render_index_md(findings, len(relevant)), encoding="utf-8"
    )

    print(f"Wrote {out_dir}/  ({len(relevant)} per-site exhibits)")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
